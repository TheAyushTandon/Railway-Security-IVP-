from datetime import datetime, timedelta, timezone
from app.tracking.tracker_service import TrackerService
from app.vision.detection_schema import Detection


def test_tracker_creates_tracks():
    service = TrackerService()
    t0 = datetime.now(timezone.utc)
    detections = [
        Detection(class_name="person", confidence=0.9, bbox_norm=[0.2, 0.2, 0.3, 0.7]),
        Detection(class_name="person", confidence=0.85, bbox_norm=[0.6, 0.2, 0.7, 0.7]),
    ]
    tracks = service.update("cam_01", detections, t0)
    assert len(tracks) == 2
    track_ids = {t.track_id for t in tracks}
    assert track_ids == {1, 2}


def test_tracker_maintains_identity_across_frames():
    service = TrackerService()
    t0 = datetime.now(timezone.utc)
    t1 = t0 + timedelta(seconds=1.1)  # Simulating ~1 Hz jittered sample

    # Frame 1
    d1 = [Detection(class_name="person", confidence=0.9, bbox_norm=[0.2, 0.2, 0.3, 0.7])]
    tracks1 = service.update("cam_01", d1, t0)
    id1 = tracks1[0].track_id

    # Frame 2: person slightly moved east
    d2 = [Detection(class_name="person", confidence=0.9, bbox_norm=[0.25, 0.2, 0.35, 0.7])]
    tracks2 = service.update("cam_01", d2, t1)

    assert len(tracks2) == 1
    assert tracks2[0].track_id == id1
    assert tracks2[0].direction_estimate == "EAST"
    assert len(tracks2[0].trajectory) == 2


def test_tracker_camera_isolation():
    service = TrackerService()
    t0 = datetime.now(timezone.utc)

    d_cam1 = [Detection(class_name="person", confidence=0.9, bbox_norm=[0.2, 0.2, 0.3, 0.7])]
    d_cam2 = [Detection(class_name="person", confidence=0.9, bbox_norm=[0.2, 0.2, 0.3, 0.7])]

    tracks_cam1 = service.update("cam_01", d_cam1, t0)
    tracks_cam2 = service.update("cam_02", d_cam2, t0)

    # Both start at local track ID 1
    assert tracks_cam1[0].track_id == 1
    assert tracks_cam2[0].track_id == 1
    assert tracks_cam1[0].camera_id == "cam_01"
    assert tracks_cam2[0].camera_id == "cam_02"


def test_tracker_expires_stale_tracks():
    service = TrackerService(max_missed_samples=2)
    t0 = datetime.now(timezone.utc)
    t1 = t0 + timedelta(seconds=1)
    t2 = t1 + timedelta(seconds=1)
    t3 = t2 + timedelta(seconds=1)

    # Frame 1: Person present
    d1 = [Detection(class_name="person", confidence=0.9, bbox_norm=[0.2, 0.2, 0.3, 0.7])]
    tracks = service.update("cam_01", d1, t0)
    assert len(tracks) == 1

    # Frame 2: Person missed (sample 1)
    tracks = service.update("cam_01", [], t1)
    assert len(tracks) == 1
    assert tracks[0].missed_sample_count == 1

    # Frame 3: Person missed (sample 2)
    tracks = service.update("cam_01", [], t2)
    assert len(tracks) == 1
    assert tracks[0].missed_sample_count == 2

    # Frame 4: Person missed (exceeds max_missed_samples=2) -> removed
    tracks = service.update("cam_01", [], t3)
    assert len(tracks) == 0
