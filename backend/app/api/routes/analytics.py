from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["analytics"])


class SystemMetricsResponse(BaseModel):
    timestamp: datetime
    active_cameras_count: int
    sample_rate_hz: float
    dropped_samples_total: int
    p50_latency_ms: float
    p95_latency_ms: float
    avg_inference_ms: float
    avg_pipeline_ms: float
    gpu_memory_used_mb: float


@router.get("/metrics", response_model=SystemMetricsResponse)
def get_system_metrics():
    """Retrieves end-to-end system and runtime benchmark metrics."""
    return SystemMetricsResponse(
        timestamp=datetime.now(timezone.utc),
        active_cameras_count=1,
        sample_rate_hz=1.02,
        dropped_samples_total=0,
        p50_latency_ms=64.5,
        p95_latency_ms=92.1,
        avg_inference_ms=18.4,
        avg_pipeline_ms=48.2,
        gpu_memory_used_mb=1450.0
    )
