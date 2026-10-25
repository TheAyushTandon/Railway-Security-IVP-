import uuid
from datetime import datetime, timezone
from app.vision.detection_schema import (
    Detection,
    DetectionBatch,
    DensityInfo,
    AnalyticsSnapshot,
    AlertEvent,
)


def get_mock_detection_batch_empty(camera_id: str = "cam_01") -> DetectionBatch:
    now = datetime.now(timezone.utc)
    return DetectionBatch(
        schema_version="1.0",
        camera_id=camera_id,
        frame_id=str(uuid.uuid4()),
        captured_at=now,
        sample_bucket_start=now,
        sample_offset_ms=350,
        frame_width=1920,
        frame_height=1080,
        model_name="yolo26n-mock",
        inference_ms=12.5,
        detections=[]
    )


def get_mock_detection_batch_sparse(camera_id: str = "cam_01") -> DetectionBatch:
    now = datetime.now(timezone.utc)
    return DetectionBatch(
        schema_version="1.0",
        camera_id=camera_id,
        frame_id=str(uuid.uuid4()),
        captured_at=now,
        sample_bucket_start=now,
        sample_offset_ms=420,
        frame_width=1920,
        frame_height=1080,
        model_name="yolo26n-mock",
        inference_ms=15.0,
        detections=[
            Detection(class_name="person", confidence=0.94, bbox_norm=[0.20, 0.15, 0.28, 0.70]),
            Detection(class_name="person", confidence=0.89, bbox_norm=[0.45, 0.20, 0.53, 0.78]),
            Detection(class_name="person", confidence=0.91, bbox_norm=[0.70, 0.18, 0.79, 0.75]),
        ]
    )


def get_mock_detection_batch_crowded(camera_id: str = "cam_01", count: int = 15) -> DetectionBatch:
    now = datetime.now(timezone.utc)
    detections = []
    for i in range(count):
        x1 = 0.05 + (i % 5) * 0.18
        y1 = 0.10 + (i // 5) * 0.25
        x2 = min(x1 + 0.08, 0.98)
        y2 = min(y1 + 0.22, 0.98)
        detections.append(
            Detection(class_name="person", confidence=0.85, bbox_norm=[x1, y1, x2, y2])
        )
    return DetectionBatch(
        schema_version="1.0",
        camera_id=camera_id,
        frame_id=str(uuid.uuid4()),
        captured_at=now,
        sample_bucket_start=now,
        sample_offset_ms=510,
        frame_width=1920,
        frame_height=1080,
        model_name="yolo26n-mock",
        inference_ms=19.2,
        detections=detections
    )


def get_mock_analytics_snapshot(camera_id: str = "cam_01") -> AnalyticsSnapshot:
    now = datetime.now(timezone.utc)
    return AnalyticsSnapshot(
        schema_version="1.0",
        camera_id=camera_id,
        sampled_at=now,
        visible_detection_count=3,
        active_track_count=3,
        roi_counts={"platform_edge": 1, "waiting_zone": 2},
        density=DensityInfo(
            class_="LOW",
            score=0.25,
            thresholds_version="platform-v1"
        ),
        inference_ms=15.0,
        pipeline_ms=28.4,
        sample_age_ms=45
    )


def get_mock_alert_event(camera_id: str = "cam_01") -> AlertEvent:
    now = datetime.now(timezone.utc)
    return AlertEvent(
        event_id=f"evt_{uuid.uuid4()}",
        camera_id=camera_id,
        type="PLATFORM_INTRUSION",
        severity="critical",
        status="new",
        occurred_at=now,
        confidence=0.92,
        evidence={
            "roi_id": "track_hazard_strip",
            "track_id": 104,
            "dwell_sec": 2.1,
            "rule_version": "intrusion-v1"
        }
    )
