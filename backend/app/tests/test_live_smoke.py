import time
from fastapi.testclient import TestClient
from app.main import app


def test_live_camera_start_and_snapshot_lifecycle():
    with TestClient(app) as client:
        # 1. Health check
        h = client.get("/health")
        assert h.status_code == 200

        # 2. Start camera (opens data/sample_platform.mp4 in worker thread)
        r_start = client.post("/api/v1/cameras/cam_01/start")
        assert r_start.status_code == 202
        assert r_start.json()["status"] == "ANALYSIS_ACTIVE"

        # 3. Wait briefly for worker to decode frames and sampler loop to process
        time.sleep(1.2)

        # 4. Fetch live snapshot
        r_snap = client.get("/api/v1/cameras/cam_01/snapshot")
        assert r_snap.status_code == 200
        snap = r_snap.json()
        assert snap["camera_id"] == "cam_01"
        assert snap["schema_version"] == "1.0"
        assert snap["visible_detection_count"] >= 0

        # 5. Fetch frame.jpg
        r_frame = client.get("/api/v1/cameras/cam_01/frame.jpg")
        assert r_frame.status_code == 200
        assert r_frame.headers["content-type"] == "image/jpeg"
        assert len(r_frame.content) > 100  # Valid JPEG binary

        # 6. Stop camera cleanly
        r_stop = client.post("/api/v1/cameras/cam_01/stop")
        assert r_stop.status_code == 202
        assert r_stop.json()["status"] == "STOPPED"
