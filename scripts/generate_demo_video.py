import os
import cv2
import numpy as np


def generate_demo_video(output_path: str = "data/sample_platform.mp4", duration_sec: int = 5, fps: int = 25):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    w, h = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    total_frames = duration_sec * fps

    for f in range(total_frames):
        # Platform background (light gray station floor)
        frame = np.full((h, w, 3), 220, dtype=np.uint8)

        # Platform edge line (yellow safety hazard strip at y=360)
        cv2.rectangle(frame, (0, 360), (w, 480), (180, 210, 230), -1)  # Track zone
        cv2.line(frame, (0, 360), (w, 360), (0, 215, 255), 4)          # Yellow line

        # Concourse waiting benches at y=100
        cv2.rectangle(frame, (50, 100), (250, 130), (120, 120, 120), -1)
        cv2.putText(frame, "WAITING BENCH", (60, 122), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Passenger 1: Walking left to right across concourse (x moves from 100 to 500)
        p1_x = int(100 + (f / total_frames) * 400)
        p1_y = 200
        cv2.rectangle(frame, (p1_x - 15, p1_y - 45), (p1_x + 15, p1_y + 45), (40, 40, 180), -1)
        cv2.circle(frame, (p1_x, p1_y - 55), 10, (50, 50, 200), -1)

        # Passenger 2: Waiting stationary at concourse
        p2_x, p2_y = 350, 220
        cv2.rectangle(frame, (p2_x - 15, p2_y - 45), (p2_x + 15, p2_y + 45), (30, 140, 30), -1)
        cv2.circle(frame, (p2_x, p2_y - 55), 10, (40, 160, 40), -1)

        # Passenger 3: Walking towards and crossing the yellow hazard line!
        p3_x = 480
        p3_y = int(280 + (f / total_frames) * 110)  # Starts at 280, moves to 390 (crosses 360 line)
        cv2.rectangle(frame, (p3_x - 15, p3_y - 45), (p3_x + 15, p3_y + 45), (180, 40, 40), -1)
        cv2.circle(frame, (p3_x, p3_y - 55), 10, (200, 50, 50), -1)

        # Timestamp & Camera Watermark
        cv2.putText(frame, f"CAM_01 LIVE PREVIEW - Frame {f:03d}", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 2)

        out.write(frame)

    out.release()
    print(f"Generated demo video: {output_path} ({total_frames} frames, {duration_sec}s @ {fps}fps)")


if __name__ == "__main__":
    generate_demo_video()
