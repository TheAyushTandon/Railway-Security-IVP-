import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.vision.detection_schema import Detection


class TrackState(BaseModel):
    camera_id: str
    track_id: int
    bbox_norm: List[float]
    centroid_norm: Tuple[float, float]
    first_seen_at: datetime
    last_seen_at: datetime
    last_update_at: datetime
    missed_sample_count: int = 0
    confidence: float
    direction_estimate: Optional[str] = None  # e.g. "NORTH", "SOUTH", "EAST", "WEST", "STATIONARY"
    trajectory: List[Tuple[float, float]] = Field(default_factory=list)


class TrackerService:
    """
    Person B Tracker Service:
    Maintains per-camera identity continuity across sparse, jittered 1 Hz sampled frames.
    Does NOT load YOLO weights. Operates entirely on normalized coordinates and capture timestamps.
    """

    def __init__(self, max_missed_samples: int = 3, max_match_distance: float = 0.15):
        self.max_missed_samples = max_missed_samples
        self.max_match_distance = max_match_distance
        # Per-camera track store: camera_id -> {track_id: TrackState}
        self._camera_tracks: Dict[str, Dict[int, TrackState]] = {}
        # Per-camera ID counter
        self._next_track_ids: Dict[str, int] = {}

    def _compute_centroid(self, bbox: List[float]) -> Tuple[float, float]:
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def _euclidean_distance(self, c1: Tuple[float, float], c2: Tuple[float, float]) -> float:
        return math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2)

    def _estimate_direction(
        self, prev_centroid: Tuple[float, float], curr_centroid: Tuple[float, float], delta_seconds: float
    ) -> Optional[str]:
        if delta_seconds <= 0.001:
            return None
        dx = curr_centroid[0] - prev_centroid[0]
        dy = curr_centroid[1] - prev_centroid[1]
        dist = math.sqrt(dx ** 2 + dy ** 2)
        
        # If movement within jitter noise threshold, passenger is stationary
        if dist < 0.02:
            return "STATIONARY"

        if abs(dx) > abs(dy):
            return "EAST" if dx > 0 else "WEST"
        else:
            return "SOUTH" if dy > 0 else "NORTH"

    def update(
        self,
        camera_id: str,
        detections: List[Detection],
        captured_at: datetime
    ) -> List[TrackState]:
        """
        Updates active tracks for the given camera using incoming frame detections.
        Calculates movement trend using actual timestamp delta (accounting for randomized sampling jitter).
        """
        if camera_id not in self._camera_tracks:
            self._camera_tracks[camera_id] = {}
            self._next_track_ids[camera_id] = 1

        active_tracks = self._camera_tracks[camera_id]
        new_centroids = [self._compute_centroid(d.bbox_norm) for d in detections]

        matched_tracks = set()
        matched_detections = set()

        # Greedy bipartite centroid matching (lightweight, zero-GPU baseline)
        if active_tracks and new_centroids:
            track_items = list(active_tracks.items())
            pairs = []
            for t_idx, (t_id, track) in enumerate(track_items):
                for d_idx, c_new in enumerate(new_centroids):
                    dist = self._euclidean_distance(track.centroid_norm, c_new)
                    if dist <= self.max_match_distance:
                        pairs.append((dist, t_id, d_idx))

            # Match nearest first
            pairs.sort(key=lambda x: x[0])
            for dist, t_id, d_idx in pairs:
                if t_id not in matched_tracks and d_idx not in matched_detections:
                    matched_tracks.add(t_id)
                    matched_detections.add(d_idx)

                    # Update existing track
                    track = active_tracks[t_id]
                    c_new = new_centroids[d_idx]
                    det = detections[d_idx]
                    delta_t = (captured_at - track.last_seen_at).total_seconds()
                    direction = self._estimate_direction(track.centroid_norm, c_new, delta_t)

                    track.bbox_norm = det.bbox_norm
                    track.centroid_norm = c_new
                    track.last_seen_at = captured_at
                    track.last_update_at = captured_at
                    track.missed_sample_count = 0
                    track.confidence = det.confidence
                    if direction is not None:
                        track.direction_estimate = direction
                    track.trajectory.append(c_new)
                    if len(track.trajectory) > 30:
                        track.trajectory.pop(0)

        # Handle unmatched active tracks (mark as missed sample)
        for t_id, track in list(active_tracks.items()):
            if t_id not in matched_tracks:
                track.missed_sample_count += 1
                track.last_update_at = captured_at
                if track.missed_sample_count > self.max_missed_samples:
                    del active_tracks[t_id]

        # Register unmatched detections as new tracks
        for d_idx, det in enumerate(detections):
            if d_idx not in matched_detections:
                new_id = self._next_track_ids[camera_id]
                self._next_track_ids[camera_id] += 1
                c_new = new_centroids[d_idx]

                active_tracks[new_id] = TrackState(
                    camera_id=camera_id,
                    track_id=new_id,
                    bbox_norm=det.bbox_norm,
                    centroid_norm=c_new,
                    first_seen_at=captured_at,
                    last_seen_at=captured_at,
                    last_update_at=captured_at,
                    missed_sample_count=0,
                    confidence=det.confidence,
                    direction_estimate="STATIONARY",
                    trajectory=[c_new]
                )

        return list(active_tracks.values())

    def reset_camera(self, camera_id: str) -> None:
        """Cleans state for a degraded or restarted camera feed."""
        if camera_id in self._camera_tracks:
            self._camera_tracks[camera_id].clear()
            self._next_track_ids[camera_id] = 1
