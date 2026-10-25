from datetime import datetime, timedelta, timezone
from app.sampling.random_sampler import RandomBucketSampler


def test_sampler_offset_range():
    sampler = RandomBucketSampler(min_offset_sec=0.20, max_offset_sec=0.80, seed=123)
    offsets = [sampler.compute_target_offset() for _ in range(100)]
    for o in offsets:
        assert 0.20 <= o <= 0.80


def test_sampler_reproducibility():
    s1 = RandomBucketSampler(seed=999)
    s2 = RandomBucketSampler(seed=999)

    offsets1 = [s1.compute_target_offset() for _ in range(20)]
    offsets2 = [s2.compute_target_offset() for _ in range(20)]

    assert offsets1 == offsets2


def test_sampler_accepted_single_bucket():
    sampler = RandomBucketSampler(seed=42)
    t0 = datetime(2026, 10, 25, 12, 0, 0, 500000, tzinfo=timezone.utc)
    t_frame = t0 - timedelta(milliseconds=50)

    # First call in bucket 12:00:00 -> ACCEPTED
    decision1 = sampler.evaluate_sample(
        camera_id="cam_01",
        current_time=t0,
        latest_slot_frame="dummy_frame_array",
        frame_captured_at=t_frame
    )
    assert decision1.status == "ACCEPTED"
    assert decision1.camera_id == "cam_01"
    assert decision1.frame_data == "dummy_frame_array"

    # Second call in the same bucket 12:00:00 -> ALREADY_SAMPLED (enforces <= 1 sample/sec)
    decision2 = sampler.evaluate_sample(
        camera_id="cam_01",
        current_time=t0 + timedelta(milliseconds=200),
        latest_slot_frame="dummy_frame_array",
        frame_captured_at=t_frame
    )
    assert decision2.status == "ALREADY_SAMPLED"


def test_sampler_missed_when_no_frame():
    sampler = RandomBucketSampler()
    t0 = datetime.now(timezone.utc)

    decision = sampler.evaluate_sample(
        camera_id="cam_01",
        current_time=t0,
        latest_slot_frame=None,
        frame_captured_at=None
    )
    assert decision.status == "MISSED"


def test_sampler_late_frame():
    sampler = RandomBucketSampler(late_tolerance_ms=300)
    now = datetime(2026, 10, 25, 12, 0, 0, 800000, tzinfo=timezone.utc)
    # Frame captured 600ms ago (> 300ms tolerance)
    stale_capture_time = now - timedelta(milliseconds=600)

    decision = sampler.evaluate_sample(
        camera_id="cam_01",
        current_time=now,
        latest_slot_frame="stale_frame",
        frame_captured_at=stale_capture_time
    )
    assert decision.status == "LATE"
    assert decision.sample_age_ms >= 600
