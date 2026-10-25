from datetime import datetime, timezone
import numpy as np

from app.analytics.pipeline import PipelineOrchestrator
from app.storage.repository import Repository


def test_full_pipeline_e2e(tmp_path):
    # Use isolated SQLite database in temp directory
    db_file = tmp_path / "test_metro.db"
    repo = Repository(db_url=f"sqlite:///{db_file}")

    orchestrator = PipelineOrchestrator(repository=repo)

    # Configure ROIs: waiting area and yellow safety line
    orchestrator.configure_camera_rois(
        camera_id="cam_test_01",
        rois={
            "waiting_concourse": [(0.1, 0.1), (0.9, 0.1), (0.9, 0.6), (0.1, 0.6)],
            "platform_edge": [(0.1, 0.6), (0.9, 0.6), (0.9, 0.9), (0.1, 0.9)]
        },
        hazard_zones={
            "track_hazard_strip": [(0.0, 0.70), (1.0, 0.70), (1.0, 1.0), (0.0, 1.0)]
        }
    )

    # Synthetic test frame (640x480, 3 channels)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    now = datetime.now(timezone.utc)

    # Process frame through the entire data plane
    snapshot, alerts = orchestrator.process_sampled_frame(
        camera_id="cam_test_01",
        frame=frame,
        captured_at=now,
        bucket_start=now,
        sample_offset_ms=450
    )

    # 1. Verify AnalyticsSnapshot properties
    assert snapshot.schema_version == "1.0"
    assert snapshot.camera_id == "cam_test_01"
    assert snapshot.visible_detection_count == 3
    assert snapshot.active_track_count == 3
    assert "waiting_concourse" in snapshot.roi_counts
    assert snapshot.density.class_ in ["LOW", "MEDIUM", "HIGH"]
    assert snapshot.inference_ms > 0
    assert snapshot.pipeline_ms > 0

    # 2. Verify Hazard Zone Platform Intrusion Alert
    # Mock detector emits people at y2=0.75 and 0.80, which intersect track_hazard_strip (y >= 0.70)
    assert len(alerts) >= 1
    assert any(a.type == "PLATFORM_INTRUSION" for a in alerts)

    # 3. Verify SQLite persistence
    persisted_alerts = repo.list_alerts(camera_id="cam_test_01")
    assert len(persisted_alerts) >= 1
    assert persisted_alerts[0].camera_id == "cam_test_01"
