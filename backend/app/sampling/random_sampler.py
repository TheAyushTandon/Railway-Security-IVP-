import random
import time
from datetime import datetime, timezone
from typing import Optional, Any
from dataclasses import dataclass


@dataclass
class SampleDecision:
    camera_id: str
    bucket_start: datetime
    target_offset_ms: int
    target_time: datetime
    actual_capture_time: Optional[datetime]
    frame_data: Optional[Any]
    status: str  # "ACCEPTED", "MISSED", "LATE"
    sample_age_ms: int = 0


class RandomBucketSampler:
    """
    Randomized 1 Hz Frame Sampler:
    Selects exactly one frame per nominal 1-second bucket with a random jitter offset in [0.20, 0.80]s.
    Caps detector workload to ~1 inference per camera per second without fixed periodicity.
    """

    def __init__(
        self,
        min_offset_sec: float = 0.20,
        max_offset_sec: float = 0.80,
        late_tolerance_ms: int = 400,
        seed: Optional[int] = 42
    ):
        self.min_offset_sec = min_offset_sec
        self.max_offset_sec = max_offset_sec
        self.late_tolerance_ms = late_tolerance_ms
        self.rng = random.Random(seed) if seed is not None else random.Random()

        # Track last bucket per camera to enforce <= 1 sample per second bucket
        self._last_bucket_per_cam: dict[str, int] = {}

    def compute_target_offset(self) -> float:
        """Draws uniform random offset in [min_offset_sec, max_offset_sec]."""
        return self.rng.uniform(self.min_offset_sec, self.max_offset_sec)

    def evaluate_sample(
        self,
        camera_id: str,
        current_time: Optional[datetime] = None,
        latest_slot_frame: Optional[Any] = None,
        frame_captured_at: Optional[datetime] = None
    ) -> SampleDecision:
        """
        Evaluates whether the frame in the camera's latest slot satisfies the current bucket's sample target.
        """
        now = current_time or datetime.now(timezone.utc)
        current_second_epoch = int(now.timestamp())
        bucket_start = datetime.fromtimestamp(current_second_epoch, tz=timezone.utc)

        # Check if this bucket already yielded an accepted sample
        if self._last_bucket_per_cam.get(camera_id) == current_second_epoch:
            return SampleDecision(
                camera_id=camera_id,
                bucket_start=bucket_start,
                target_offset_ms=0,
                target_time=now,
                actual_capture_time=frame_captured_at,
                frame_data=None,
                status="ALREADY_SAMPLED"
            )

        offset_sec = self.compute_target_offset()
        offset_ms = int(offset_sec * 1000)
        target_time = datetime.fromtimestamp(current_second_epoch + offset_sec, tz=timezone.utc)

        # If no frame available in slot
        if latest_slot_frame is None or frame_captured_at is None:
            return SampleDecision(
                camera_id=camera_id,
                bucket_start=bucket_start,
                target_offset_ms=offset_ms,
                target_time=target_time,
                actual_capture_time=None,
                frame_data=None,
                status="MISSED"
            )

        # Compute sample age relative to now
        age_ms = int((now - frame_captured_at).total_seconds() * 1000)

        # If frame is older than late tolerance, it's stale/late
        if age_ms > self.late_tolerance_ms:
            return SampleDecision(
                camera_id=camera_id,
                bucket_start=bucket_start,
                target_offset_ms=offset_ms,
                target_time=target_time,
                actual_capture_time=frame_captured_at,
                frame_data=latest_slot_frame,
                status="LATE",
                sample_age_ms=age_ms
            )

        # Mark bucket as sampled
        self._last_bucket_per_cam[camera_id] = current_second_epoch

        return SampleDecision(
            camera_id=camera_id,
            bucket_start=bucket_start,
            target_offset_ms=offset_ms,
            target_time=target_time,
            actual_capture_time=frame_captured_at,
            frame_data=latest_slot_frame,
            status="ACCEPTED",
            sample_age_ms=age_ms
        )

    def reset_camera(self, camera_id: str) -> None:
        self._last_bucket_per_cam.pop(camera_id, None)
