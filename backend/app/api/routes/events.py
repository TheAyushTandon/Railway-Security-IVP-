from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.vision.detection_schema import AlertEvent

router = APIRouter(prefix="/events", tags=["events"])

# In-memory mock alert history
_events_store: List[AlertEvent] = [
    AlertEvent(
        event_id="evt_01J8F9D7C23M4PQ1",
        camera_id="cam_01",
        type="DENSITY_HIGH",
        severity="warning",
        status="new",
        occurred_at=datetime.now(timezone.utc),
        confidence=0.88,
        evidence={"density_score": 0.88, "roi_id": "platform_edge", "rule_version": "rules-v1"}
    )
]


class AckRequest(BaseModel):
    actor_id: str = "operator_1"


@router.get("", response_model=List[AlertEvent])
def query_events(
    camera_id: Optional[str] = Query(None, description="Filter by camera_id"),
    type: Optional[str] = Query(None, description="Filter by anomaly type"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    limit: int = Query(50, ge=1, le=200)
):
    """Queries alert event history with optional filters."""
    results = _events_store
    if camera_id:
        results = [e for e in results if e.camera_id == camera_id]
    if type:
        results = [e for e in results if e.type == type]
    if severity:
        results = [e for e in results if e.severity == severity]
    return results[:limit]


@router.get("/{event_id}", response_model=AlertEvent)
def get_event(event_id: str):
    """Retrieves single alert event details."""
    for event in _events_store:
        if event.event_id == event_id:
            return event
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event '{event_id}' not found.")


@router.post("/{event_id}/ack", response_model=AlertEvent)
def acknowledge_event(event_id: str, payload: AckRequest):
    """Acknowledges an alert event by station operator."""
    for event in _events_store:
        if event.event_id == event_id:
            event.status = "acknowledged"
            event.acknowledged_at = datetime.now(timezone.utc)
            event.evidence["acknowledged_by"] = payload.actor_id
            return event
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event '{event_id}' not found.")
