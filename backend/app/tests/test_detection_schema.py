import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from app.vision.detection_schema import (
    Detection,
    DetectionBatch,
    DensityInfo,
    AnalyticsSnapshot,
    AlertEvent,
)
from app.tests.fixtures.mock_detections import (
    get_mock_detection_batch_sparse,
    get_mock_analytics_snapshot,
    get_mock_alert_event,
)


def test_valid_detection():
    det = Detection(class_name="person", confidence=0.95, bbox_norm=[0.1, 0.2, 0.3, 0.8])
    assert det.class_name == "person"
    assert det.confidence == 0.95
    assert det.bbox_norm == [0.1, 0.2, 0.3, 0.8]


def test_invalid_bbox_out_of_bounds():
    with pytest.raises(ValidationError):
        Detection(class_name="person", confidence=0.9, bbox_norm=[-0.1, 0.2, 0.3, 0.8])

    with pytest.raises(ValidationError):
        Detection(class_name="person", confidence=0.9, bbox_norm=[0.1, 0.2, 1.2, 0.8])


def test_invalid_bbox_inverted_coords():
    with pytest.raises(ValidationError):
        # x2 < x1
        Detection(class_name="person", confidence=0.9, bbox_norm=[0.5, 0.2, 0.3, 0.8])


def test_detection_batch_fixture():
    batch = get_mock_detection_batch_sparse("cam_platform_01")
    assert batch.camera_id == "cam_platform_01"
    assert len(batch.detections) == 3
    assert batch.schema_version == "1.0"


def test_analytics_snapshot_fixture():
    snapshot = get_mock_analytics_snapshot("cam_platform_01")
    assert snapshot.visible_detection_count == 3
    assert snapshot.density.class_ == "LOW"
    assert snapshot.sample_age_ms > 0


def test_alert_event_fixture():
    alert = get_mock_alert_event("cam_platform_01")
    assert alert.type == "PLATFORM_INTRUSION"
    assert alert.status == "new"
    assert alert.evidence["roi_id"] == "track_hazard_strip"
