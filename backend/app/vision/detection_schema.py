from datetime import datetime
from typing import Dict, List, Literal, Optional, Any
from pydantic import BaseModel, Field, field_validator


class Detection(BaseModel):
    class_name: str = Field(default="person", description="Detected class name, typically person")
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence score")
    bbox_norm: List[float] = Field(
        description="Normalized coordinates [x1, y1, x2, y2] relative to frame dimensions"
    )

    @field_validator("bbox_norm")
    @classmethod
    def validate_bbox(cls, v: List[float]) -> List[float]:
        if len(v) != 4:
            raise ValueError(f"bbox_norm must contain exactly 4 coordinates [x1, y1, x2, y2], got {len(v)}")
        x1, y1, x2, y2 = v
        if not (0.0 <= x1 <= 1.0 and 0.0 <= y1 <= 1.0 and 0.0 <= x2 <= 1.0 and 0.0 <= y2 <= 1.0):
            raise ValueError(f"All coordinates in bbox_norm must be between 0.0 and 1.0, got {v}")
        if x2 < x1 or y2 < y1:
            raise ValueError(f"Coordinates must satisfy x1 <= x2 and y1 <= y2, got {v}")
        return v


class DetectionBatch(BaseModel):
    schema_version: Literal["1.0"] = Field(default="1.0", description="Contract schema version")
    camera_id: str = Field(description="Unique, stable identifier for the source camera feed")
    frame_id: str = Field(description="Unique frame UUID")
    captured_at: datetime = Field(description="UTC timestamp of the frame capture")
    sample_bucket_start: datetime = Field(description="Nominal 1-second bucket start in UTC")
    sample_offset_ms: int = Field(ge=0, description="Target offset within the 1s bucket in ms")
    frame_width: int = Field(gt=0, description="Width of the original image frame in pixels")
    frame_height: int = Field(gt=0, description="Height of the original image frame in pixels")
    model_name: str = Field(description="Detector model identifier used for inference")
    inference_ms: float = Field(ge=0.0, description="GPU/CPU inference duration in milliseconds")
    detections: List[Detection] = Field(default_factory=list, description="List of detected objects in the frame")


class DensityInfo(BaseModel):
    class_: Literal["LOW", "MEDIUM", "HIGH"] = Field(alias="class", description="Categorical density state")
    score: float = Field(ge=0.0, le=1.0, description="Normalized density score or occupancy ratio")
    thresholds_version: str = Field(description="Identifier for active ROI threshold configuration")

    model_config = {
        "populate_by_name": True
    }


class AnalyticsSnapshot(BaseModel):
    schema_version: Literal["1.0"] = Field(default="1.0", description="Contract schema version")
    camera_id: str = Field(description="Camera ID for which analytics were computed")
    sampled_at: datetime = Field(description="Timestamp of the sampled frame analyzed")
    visible_detection_count: int = Field(ge=0, description="Total persons detected in this single frame")
    active_track_count: int = Field(ge=0, description="Active trajectories currently tracked by ByteTrack")
    roi_counts: Dict[str, int] = Field(default_factory=dict, description="Counts broken down per designated ROI")
    density: DensityInfo = Field(description="Overall or primary ROI crowd density evaluation")
    inference_ms: float = Field(ge=0.0, description="Inference latency of detector")
    pipeline_ms: float = Field(ge=0.0, description="Total analytics processing latency")
    sample_age_ms: int = Field(ge=0, description="Time elapsed from capture to snapshot generation in ms")


class AlertEvent(BaseModel):
    event_id: str = Field(description="Unique event UUID. Stable across updates to the same ongoing incident.")
    camera_id: str = Field(description="Camera where the anomaly was detected")
    type: Literal["DENSITY_HIGH", "PLATFORM_INTRUSION", "WRONG_DIRECTION", "LOITERING"] = Field(
        description="Type of anomaly alert"
    )
    severity: Literal["info", "warning", "critical"] = Field(description="Urgency level")
    status: Literal["new", "acknowledged", "resolved"] = Field(default="new", description="Lifecycle status")
    occurred_at: datetime = Field(description="UTC timestamp when the event condition occurred/updated")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence of the rule trigger")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic payload (ROI, track ID, dwell, etc.)")
    acknowledged_at: Optional[datetime] = Field(default=None, description="UTC timestamp of operator acknowledgement")
    resolved_at: Optional[datetime] = Field(default=None, description="UTC timestamp when condition normalized")


class WebSocketEnvelope(BaseModel):
    schema_version: Literal["1.0"] = Field(default="1.0")
    event_id: str
    type: Literal[
        "camera.status.changed",
        "frame.sampled",
        "analytics.snapshot.updated",
        "alert.created",
        "alert.acknowledged",
        "pipeline.metrics.updated",
        "heartbeat"
    ]
    occurred_at: datetime
    camera_id: str
    data: Dict[str, Any]
