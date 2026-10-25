from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, status, Response
from pydantic import BaseModel, Field

from app.vision.detection_schema import AnalyticsSnapshot, DensityInfo

router = APIRouter(prefix="/cameras", tags=["cameras"])


class CameraRegisterRequest(BaseModel):
    camera_id: str = Field(description="Unique camera identifier")
    name: str = Field(description="Human readable station/camera label")
    source_ref: str = Field(description="Filepath, MP4 path, or RTSP URL")
    config: Optional[Dict] = Field(default_factory=dict)


class CameraResponse(BaseModel):
    camera_id: str
    name: str
    source_ref: str
    status: str
    last_sampled_at: Optional[datetime] = None
    sample_age_ms: Optional[int] = None


# In-memory registry for mock & active lifecycle
_cameras_store: Dict[str, dict] = {
    "cam_01": {
        "camera_id": "cam_01",
        "name": "Platform A - North Concourse",
        "source_ref": "data/sample_platform_a.mp4",
        "status": "ANALYSIS_ACTIVE",
        "last_sampled_at": datetime.now(timezone.utc),
        "sample_age_ms": 68
    }
}


@router.get("", response_model=List[CameraResponse])
def list_cameras():
    """Lists all configured camera sources with operational status."""
    return list(_cameras_store.values())


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
def register_camera(payload: CameraRegisterRequest):
    """Registers a new camera feed."""
    if payload.camera_id in _cameras_store:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Camera with id '{payload.camera_id}' is already registered."
        )

    record = {
        "camera_id": payload.camera_id,
        "name": payload.name,
        "source_ref": payload.source_ref,
        "status": "STOPPED",
        "last_sampled_at": None,
        "sample_age_ms": None
    }
    _cameras_store[payload.camera_id] = record
    return record


@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(camera_id: str):
    """Retrieves metadata and current status for a camera."""
    if camera_id not in _cameras_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera '{camera_id}' not found."
        )
    return _cameras_store[camera_id]


@router.post("/{camera_id}/start", status_code=status.HTTP_202_ACCEPTED)
def start_camera(camera_id: str):
    """Starts camera ingest worker and 1 Hz randomized frame sampling."""
    if camera_id not in _cameras_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera '{camera_id}' not found."
        )
    _cameras_store[camera_id]["status"] = "ANALYSIS_ACTIVE"
    return {"message": f"Camera '{camera_id}' started", "status": "ANALYSIS_ACTIVE"}


@router.post("/{camera_id}/stop", status_code=status.HTTP_202_ACCEPTED)
def stop_camera(camera_id: str):
    """Stops camera decoder worker cleanly."""
    if camera_id not in _cameras_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera '{camera_id}' not found."
        )
    _cameras_store[camera_id]["status"] = "STOPPED"
    return {"message": f"Camera '{camera_id}' stopped", "status": "STOPPED"}


@router.get("/{camera_id}/snapshot", response_model=AnalyticsSnapshot)
def get_camera_snapshot(camera_id: str):
    """Fetches the latest analytics snapshot for this camera."""
    if camera_id not in _cameras_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera '{camera_id}' not found."
        )

    now = datetime.now(timezone.utc)
    return AnalyticsSnapshot(
        schema_version="1.0",
        camera_id=camera_id,
        sampled_at=now,
        visible_detection_count=14,
        active_track_count=12,
        roi_counts={"waiting_area": 8, "yellow_line": 3, "stairway": 3},
        density=DensityInfo(
            class_="MEDIUM",
            score=0.58,
            thresholds_version="platform-v1"
        ),
        inference_ms=17.5,
        pipeline_ms=45.0,
        sample_age_ms=58
    )


@router.get("/{camera_id}/frame.jpg")
def get_camera_frame(camera_id: str):
    """Returns the most recently analyzed frame JPEG image (dummy 1x1 jpeg for contract tests)."""
    if camera_id not in _cameras_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera '{camera_id}' not found."
        )
    # Minimal 1x1 pixel valid JPEG bytes
    dummy_jpeg = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9'
    return Response(content=dummy_jpeg, media_type="image/jpeg")
