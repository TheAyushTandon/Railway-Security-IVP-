import cv2
import numpy as np
from typing import List, Optional
from app.vision.detection_schema import Detection
from app.tracking.tracker_service import TrackState


def render_ai_overlay(
    frame: np.ndarray,
    detections: List[Detection],
    tracks: Optional[List[TrackState]] = None,
    intrusion_active: bool = False
) -> np.ndarray:
    """
    Renders visual bounding boxes, passenger track tags, and platform hazard lines
    onto a sampled frame for operator dashboard visualization.
    """
    vis = frame.copy()
    h, w = vis.shape[:2]

    # 1. Platform Edge Yellow Hazard Line (at y = 75% of height)
    line_y = int(h * 0.75)
    line_color = (0, 60, 255) if intrusion_active else (0, 215, 255) # Red if intrusion else Gold
    cv2.line(vis, (0, line_y), (w, line_y), line_color, 3)
    cv2.putText(
        vis,
        "PLATFORM HAZARD THRESHOLD [KEEP CLEAR]",
        (15, line_y - 8),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        line_color,
        1,
        cv2.LINE_AA
    )

    # 2. Concourse Zone Box (top 30%)
    zone_overlay = vis.copy()
    cv2.rectangle(zone_overlay, (20, 40), (w - 20, int(h * 0.40)), (50, 50, 50), -1)
    cv2.addWeighted(zone_overlay, 0.25, vis, 0.75, 0, vis)
    cv2.putText(
        vis,
        "ZONE: CONCOURSE WAITING AREA",
        (30, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (200, 200, 200),
        1,
        cv2.LINE_AA
    )

    # 3. Render Detections and Tracks
    for i, det in enumerate(detections):
        x1 = int(det.bbox_norm[0] * w)
        y1 = int(det.bbox_norm[1] * h)
        x2 = int(det.bbox_norm[2] * w)
        y2 = int(det.bbox_norm[3] * h)

        # Check if bottom of bbox has crossed the yellow line
        is_hazard = y2 >= line_y
        box_color = (0, 0, 255) if is_hazard else (0, 220, 80) # Red if hazard, Emerald if safe
        box_thickness = 2 if not is_hazard else 3

        # Draw Bounding Box
        cv2.rectangle(vis, (x1, y1), (x2, y2), box_color, box_thickness)

        # Draw Header Tag
        tag = f"Passenger {int(det.confidence * 100)}%"
        if is_hazard:
            tag = f"! INTRUSION {int(det.confidence * 100)}%"

        tag_size, _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        tag_w, tag_h = tag_size[0] + 6, tag_size[1] + 6
        cv2.rectangle(vis, (x1, max(0, y1 - tag_h)), (x1 + tag_w, max(tag_h, y1)), box_color, -1)
        cv2.putText(
            vis,
            tag,
            (x1 + 3, max(tag_h - 4, y1 - 4)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (255, 255, 255) if is_hazard else (0, 20, 0),
            1,
            cv2.LINE_AA
        )

        # Foot Centroid Dot
        foot_x = (x1 + x2) // 2
        foot_y = y2
        cv2.circle(vis, (foot_x, foot_y), 4, (0, 255, 255), -1)

    # 4. HUD Telemetry Bar
    cv2.rectangle(vis, (0, 0), (w, 30), (15, 20, 25), -1)
    status_str = f"METRO AI DETECTOR | PASSENGERS: {len(detections)} | ACTIVE TRACKS: {len(tracks or [])}"
    cv2.putText(vis, status_str, (12, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1, cv2.LINE_AA)

    return vis
