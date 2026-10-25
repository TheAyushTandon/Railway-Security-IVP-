import time
import threading
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger("metro.source")


class CameraSourceWorker:
    """
    Dedicated thread worker for a video or RTSP source.
    Maintains a thread-safe, latest-frame slot (capacity 1).
    Old decoded frames are overwritten rather than queued to prevent latency backlog.
    """

    def __init__(self, camera_id: str, source_ref: str, reconnect_backoff_sec: float = 2.0):
        self.camera_id = camera_id
        self.source_ref = source_ref
        self.reconnect_backoff_sec = reconnect_backoff_sec

        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_capture_time: Optional[datetime] = None
        self._frame_width: int = 1920
        self._frame_height: int = 1080

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.status = "INITIALIZED"  # "CONNECTED", "DEGRADED", "STOPPED"

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, name=f"cam-{self.camera_id}", daemon=True)
        self._thread.start()
        logger.info(f"Started capture worker for camera '{self.camera_id}' ({self.source_ref})")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self.status = "STOPPED"
        logger.info(f"Stopped capture worker for camera '{self.camera_id}'")

    def _capture_loop(self):
        while self._running:
            # Handle integer webcam index if digits provided
            src = int(self.source_ref) if self.source_ref.isdigit() else self.source_ref
            cap = cv2.VideoCapture(src)

            if not cap.isOpened():
                self.status = "DEGRADED"
                logger.warning(f"Failed to open source '{self.source_ref}'. Retrying in {self.reconnect_backoff_sec}s...")
                time.sleep(self.reconnect_backoff_sec)
                continue

            self.status = "CONNECTED"
            self._frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
            self._frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080

            while self._running:
                ret, frame = cap.read()
                if not ret or frame is None:
                    # End of file or network stream drop
                    if isinstance(src, str) and (src.endswith(".mp4") or src.endswith(".avi") or src.endswith(".mkv")):
                        # Loop video for continuous playback in prototype
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        self.status = "DEGRADED"
                        logger.warning(f"Stream dropped for camera '{self.camera_id}'. Reconnecting...")
                        break

                captured_at = datetime.now(timezone.utc)

                # Overwrite slot with latest frame
                with self._lock:
                    self._latest_frame = frame
                    self._latest_capture_time = captured_at

                # Modest sleep to prevent 100% CPU on video file replay
                time.sleep(0.01)

            cap.release()
            if self._running:
                time.sleep(self.reconnect_backoff_sec)

    def get_latest_frame(self) -> Tuple[Optional[np.ndarray], Optional[datetime], int, int]:
        """Thread-safe retrieval of the freshest frame from the capacity-1 slot."""
        with self._lock:
            if self._latest_frame is None:
                return None, None, self._frame_width, self._frame_height
            return self._latest_frame.copy(), self._latest_capture_time, self._frame_width, self._frame_height

    def clear_slot(self):
        with self._lock:
            self._latest_frame = None
            self._latest_capture_time = None
