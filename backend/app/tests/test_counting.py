from datetime import datetime, timezone
from app.analytics.counting import is_point_in_polygon, CountingService
from app.tracking.tracker_service import TrackState


def test_is_point_in_polygon():
    # Square ROI from (0.2, 0.2) to (0.6, 0.6)
    square = [(0.2, 0.2), (0.6, 0.2), (0.6, 0.6), (0.2, 0.6)]

    assert is_point_in_polygon((0.4, 0.4), square) is True
    assert is_point_in_polygon((0.1, 0.1), square) is False
    assert is_point_in_polygon((0.7, 0.5), square) is False


def test_roi_counts():
    counting = CountingService()
    now = datetime.now(timezone.utc)

    # 2 tracks: 1 in platform_a, 1 outside
    tracks = [
        TrackState(
            camera_id="cam_01",
            track_id=1,
            bbox_norm=[0.25, 0.30, 0.35, 0.60],
            centroid_norm=(0.30, 0.45),
            first_seen_at=now,
            last_seen_at=now,
            last_update_at=now,
            confidence=0.9,
            trajectory=[(0.30, 0.45)]
        ),
        TrackState(
            camera_id="cam_01",
            track_id=2,
            bbox_norm=[0.80, 0.80, 0.90, 0.95],
            centroid_norm=(0.85, 0.87),
            first_seen_at=now,
            last_seen_at=now,
            last_update_at=now,
            confidence=0.9,
            trajectory=[(0.85, 0.87)]
        ),
    ]

    rois = {
        "platform_a": [(0.2, 0.2), (0.5, 0.2), (0.5, 0.7), (0.2, 0.7)]
    }

    counts = counting.compute_roi_counts(tracks, rois)
    assert counts["platform_a"] == 1


def test_line_crossings_no_double_count():
    counting = CountingService()
    now = datetime.now(timezone.utc)

    # Line from (0.5, 0.0) to (0.5, 1.0) - vertical tripwire in middle
    lines = {"turnstile_1": ((0.5, 0.0), (0.5, 1.0))}

    # Frame 1: track moves from 0.4 to 0.6 (crosses line)
    track = TrackState(
        camera_id="cam_01",
        track_id=10,
        bbox_norm=[0.55, 0.4, 0.65, 0.7],
        centroid_norm=(0.60, 0.55),
        first_seen_at=now,
        last_seen_at=now,
        last_update_at=now,
        confidence=0.9,
        trajectory=[(0.40, 0.55), (0.60, 0.55)]
    )

    c1 = counting.detect_line_crossings("cam_01", [track], lines)
    assert c1["turnstile_1"] == 1

    # Frame 2: same track moves further to 0.7 (should NOT trigger second crossing!)
    track.trajectory.append((0.70, 0.55))
    c2 = counting.detect_line_crossings("cam_01", [track], lines)
    assert c2["turnstile_1"] == 0
