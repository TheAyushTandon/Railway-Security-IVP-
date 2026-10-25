import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Any
import numpy as np

from app.vision.detection_schema import Detection, DetectionBatch

logger = logging.getLogger("metro.detector")


class DetectorService:
    """
    Detector Service (Person A interface):
    Runs single-model inference on sampled frames. Emits typed DetectionBatch.
    Falls back gracefully to mock detections when weights are not yet present.
    """

    def __init__(self, model_path: Optional[str] = None, conf_threshold: float = 0.40):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.model = None
        self._load_model()

    def _load_model(self):
        if not self.model_path:
            logger.info("Detector initialized in mock/standalone mode (no weights path provided).")
            return

        try:
            from ultralytics import YOLO
            import torch
            device = 0 if torch.cuda.is_available() else "cpu"
            self.model = YOLO(self.model_path)
            logger.info(f"Loaded YOLO detector from '{self.model_path}' on device '{device}'.")
        except Exception as e:
            logger.warning(f"Could not load YOLO model ({e}). Using mock detector fallback.")
            self.model = None

    def detect(
        self,
        frame: np.ndarray,
        camera_id: str,
        captured_at: datetime,
        bucket_start: datetime,
        sample_offset_ms: int
    ) -> DetectionBatch:
        """
        Runs inference on a single sampled frame and emits DetectionBatch with normalized [0, 1] coordinates.
        """
        h, w = frame.shape[:2]
        t_start = time.perf_counter()
        detections: List[Detection] = []

        if self.model is not None:
            # Real YOLO inference
            results = self.model.predict(frame, imgsz=640, conf=self.conf_threshold, verbose=False)
            inference_ms = (time.perf_counter() - t_start) * 1000

            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = r.names.get(cls_id, "unknown")
                    if cls_name == "person":
                        conf = float(box.conf[0])
                        xyxy = box.xyxy[0].tolist()
                        x1 = max(0.0, min(xyxy[0] / w, 1.0))
                        y1 = max(0.0, min(xyxy[1] / h, 1.0))
                        x2 = max(0.0, min(xyxy[2] / w, 1.0))
                        y2 = max(0.0, min(xyxy[3] / h, 1.0))
                        detections.append(
                            Detection(class_name="person", confidence=conf, bbox_norm=[x1, y1, x2, y2])
                        )
        else:
            # Deterministic mock detector (simulates 3 people in realistic positions)
            inference_ms = 14.5
            detections = [
                Detection(class_name="person", confidence=0.92, bbox_norm=[0.20, 0.25, 0.28, 0.75]),
                Detection(class_name="person", confidence=0.88, bbox_norm=[0.48, 0.30, 0.56, 0.80]),
                Detection(class_name="person", confidence=0.90, bbox_norm=[0.72, 0.22, 0.80, 0.72]),
            ]

        return DetectionBatch(
            schema_version="1.0",
            camera_id=camera_id,
            frame_id=str(uuid.uuid4()),
            captured_at=captured_at,
            sample_bucket_start=bucket_start,
            sample_offset_ms=sample_offset_ms,
            frame_width=w,
            frame_height=h,
            model_name="yolo26n-metro-v1" if self.model else "mock-detector-v1",
            inference_ms=round(inference_ms, 1),
            detections=detections
        )
