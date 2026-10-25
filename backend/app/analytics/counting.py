from typing import Dict, List, Tuple
from app.tracking.tracker_service import TrackState


def is_point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """
    Standard Ray-Casting algorithm for point-in-polygon detection in normalized coordinates [0, 1].
    """
    x, y = point
    inside = False
    n = len(polygon)
    if n < 3:
        return False

    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def do_segments_intersect(
    p1: Tuple[float, float], p2: Tuple[float, float],
    q1: Tuple[float, float], q2: Tuple[float, float]
) -> bool:
    """Checks if line segment p1-p2 intersects line segment q1-q2 using 2D cross product orientations."""
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

    return (ccw(p1, q1, q2) != ccw(p2, q1, q2)) and (ccw(p1, p2, q1) != ccw(p1, p2, q2))


class CountingService:
    """
    Person B Counting Service:
    Calculates per-ROI headcounts, visible vs active counts, and tripwire line crossings.
    """

    def __init__(self):
        # Per-camera line crossing tracking: camera_id -> set of (line_id, track_id) already crossed
        self._crossed_records: Dict[str, set] = {}

    def compute_roi_counts(
        self,
        tracks: List[TrackState],
        roi_polygons: Dict[str, List[Tuple[float, float]]]
    ) -> Dict[str, int]:
        """
        Counts active passengers located inside each defined ROI polygon.
        """
        counts = {roi_id: 0 for roi_id in roi_polygons}
        for track in tracks:
            # Check bottom center of bbox or centroid (bottom center is closer to actual ground position)
            ground_pt = (track.centroid_norm[0], track.bbox_norm[3])
            for roi_id, polygon in roi_polygons.items():
                if is_point_in_polygon(ground_pt, polygon) or is_point_in_polygon(track.centroid_norm, polygon):
                    counts[roi_id] += 1
        return counts

    def detect_line_crossings(
        self,
        camera_id: str,
        tracks: List[TrackState],
        lines: Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]]
    ) -> Dict[str, int]:
        """
        Evaluates track trajectories against directional tripwire lines.
        Guarantees repeated samples of the same track do not re-increment crossing count.
        """
        if camera_id not in self._crossed_records:
            self._crossed_records[camera_id] = set()

        already_crossed = self._crossed_records[camera_id]
        crossings = {line_id: 0 for line_id in lines}

        for track in tracks:
            if len(track.trajectory) < 2:
                continue

            prev_pt = track.trajectory[-2]
            curr_pt = track.trajectory[-1]

            for line_id, (p1, p2) in lines.items():
                cross_key = (line_id, track.track_id)
                if cross_key in already_crossed:
                    continue

                if do_segments_intersect(prev_pt, curr_pt, p1, p2):
                    already_crossed.add(cross_key)
                    crossings[line_id] += 1

        return crossings

    def reset_camera(self, camera_id: str) -> None:
        if camera_id in self._crossed_records:
            self._crossed_records[camera_id].clear()
