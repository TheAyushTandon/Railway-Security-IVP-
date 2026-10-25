from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is False
    assert "RTX 5060" in data["gpu_name"]


def test_cameras_crud_and_snapshot():
    # 1. List cameras
    res_list = client.get("/api/v1/cameras")
    assert res_list.status_code == 200
    cameras = res_list.json()
    assert len(cameras) >= 1

    # 2. Register camera
    new_cam = {
        "camera_id": "cam_platform_02",
        "name": "Platform B - South",
        "source_ref": "data/sample_platform_b.mp4",
        "config": {}
    }
    res_reg = client.post("/api/v1/cameras", json=new_cam)
    assert res_reg.status_code == 201
    assert res_reg.json()["camera_id"] == "cam_platform_02"

    # 3. Duplicate camera rejected with 409
    res_dup = client.post("/api/v1/cameras", json=new_cam)
    assert res_dup.status_code == 409

    # 4. Start camera
    res_start = client.post("/api/v1/cameras/cam_platform_02/start")
    assert res_start.status_code == 202

    # 5. Snapshot schema validation
    res_snap = client.get("/api/v1/cameras/cam_platform_02/snapshot")
    assert res_snap.status_code == 200
    snap = res_snap.json()
    assert snap["schema_version"] == "1.0"
    assert snap["camera_id"] == "cam_platform_02"
    assert "visible_detection_count" in snap
    assert "density" in snap
    assert snap["density"]["class"] in ["LOW", "MEDIUM", "HIGH"]

    # 6. Stop camera
    res_stop = client.post("/api/v1/cameras/cam_platform_02/stop")
    assert res_stop.status_code == 202


def test_events_and_ack():
    # 1. Query events
    res_events = client.get("/api/v1/events")
    assert res_events.status_code == 200
    events = res_events.json()
    assert len(events) >= 1
    event_id = events[0]["event_id"]

    # 2. Acknowledge alert
    res_ack = client.post(f"/api/v1/events/{event_id}/ack", json={"actor_id": "controller_test"})
    assert res_ack.status_code == 200
    ack_data = res_ack.json()
    assert ack_data["status"] == "acknowledged"
    assert ack_data["evidence"]["acknowledged_by"] == "controller_test"


def test_system_metrics():
    res_metrics = client.get("/api/v1/metrics")
    assert res_metrics.status_code == 200
    metrics = res_metrics.json()
    assert "sample_rate_hz" in metrics
    assert "p95_latency_ms" in metrics
