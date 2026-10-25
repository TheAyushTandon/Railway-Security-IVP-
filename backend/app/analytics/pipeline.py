import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import numpy as np

from app.vision.detector import DetectorService
from app.vision.detection_schema import DetectionBatch, AnalyticsSnapshot, AlertEvent, DensityInfo
from app.vision.annotator import render_ai_overlay
from app.tracking.tracker_service import TrackerService, TrackState
from app.analytics.counting import CountingService
from app.analytics.density import DensityService
from app.analytics.anomaly_rules import AnomalyRuleEngine
from app.storage.repository import Repository

logger = logging.getLogger("metro.pipeline")


class PipelineOrchestrator:
    """
    Unified Data Plane Pipeline:
    Connects Detector -> Tracker -> Counting -> Density -> Anomaly Rules -> Repository.
    One camera sample in -> AnalyticsSnapshot & AlertEvents out.
    """

    def __init__(
        self,
        detector: Optional[DetectorService] = None,
        tracker: Optional[TrackerService] = None,
        counting: Optional[CountingService] = None,
        density: Optional[DensityService] = None,
        rules: Optional[AnomalyRuleEngine] = None,
        repository: Optional[Repository] = None
    ):
        self.detector = detector or DetectorService()
        self.tracker = tracker or TrackerService()
        self.counting = counting or CountingService()
        self.density = density or DensityService()
        self.rules = rules or AnomalyRuleEngine()
        self.repository = repository or Repository()

        # Configured ROIs and Hazard Zones per camera
        self._roi_polygons: Dict[str, Dict[str, List[Tuple[float, float]]]] = {}
        self._hazard_polygons: Dict[str, Dict[str, List[Tuple[float, float]]]] = {}
        self._loiter_polygons: Dict[str, Dict[str, List[Tuple[float, float]]]] = {}
        self._latest_annotated_frames: Dict[str, np.ndarray] = {}

    def get_annotated_frame(self, camera_id: str) -> Optional[np.ndarray]:
        return self._latest_annotated_frames.get(camera_id)

    def configure_camera_rois(
        self,
        camera_id: str,
        rois: Dict[str, List[Tuple[float, float]]],
        hazard_zones: Optional[Dict[str, List[Tuple[float, float]]]] = None,
        loiter_zones: Optional[Dict[str, List[Tuple[float, float]]]] = None
    ):
        self._roi_polygons[camera_id] = rois
        if hazard_zones:
            self._hazard_polygons[camera_id] = hazard_zones
        if loiter_zones:
            self._loiter_polygons[camera_id] = loiter_zones

    def process_sampled_frame(
        self,
        camera_id: str,
        frame: np.ndarray,
        captured_at: datetime,
        bucket_start: datetime,
        sample_offset_ms: int
    ) -> Tuple[AnalyticsSnapshot, List[AlertEvent]]:
        """
        Executes the entire analytics pipeline on a single sampled frame.
        """
        t_pipe_start = time.perf_counter()

        # 1. Vision Detection (Person A)
        batch: DetectionBatch = self.detector.detect(
            frame=frame,
            camera_id=camera_id,
            captured_at=captured_at,
            bucket_start=bucket_start,
            sample_offset_ms=sample_offset_ms
        )

        # 2. Tracking (Person B)
        tracks: List[TrackState] = self.tracker.update(
            camera_id=camera_id,
            detections=batch.detections,
            captured_at=captured_at
        )

        # 3. ROI Counting (Person B)
        active_rois = self._roi_polygons.get(camera_id, {
            "platform_a": [(0.1, 0.2), (0.9, 0.2), (0.9, 0.8), (0.1, 0.8)]
        })
        roi_counts = self.counting.compute_roi_counts(tracks, active_rois)

        # 4. Crowd Density Evaluation (Person B)
        density_eval: DensityInfo = self.density.evaluate_density(
            camera_id=camera_id,
            active_count=len(tracks),
            capacity_limit=25
        )

        # 5. Anomaly Rules & Safety Violations (Person B)
        hazard_zones = self._hazard_polygons.get(camera_id, {
            "yellow_safety_line": [(0.0, 0.75), (1.0, 0.75), (1.0, 1.0), (0.0, 1.0)]
        })
        loiter_zones = self._loiter_polygons.get(camera_id, {})
        alerts: List[AlertEvent] = self.rules.evaluate_rules(
            camera_id=camera_id,
            tracks=tracks,
            density=density_eval,
            restricted_zones=hazard_zones,
            loiter_zones=loiter_zones,
            timestamp=captured_at
        )

        pipeline_ms = (time.perf_counter() - t_pipe_start) * 1000
        now = datetime.now(timezone.utc)
        sample_age_ms = int((now - captured_at).total_seconds() * 1000)

        # 6. Assemble AnalyticsSnapshot
        snapshot = AnalyticsSnapshot(
            schema_version="1.0",
            camera_id=camera_id,
            sampled_at=captured_at,
            visible_detection_count=len(batch.detections),
            active_track_count=len(tracks),
            roi_counts=roi_counts,
            density=density_eval,
            inference_ms=batch.inference_ms,
            pipeline_ms=round(pipeline_ms, 1),
            sample_age_ms=max(0, sample_age_ms)
        )

        # 7. Persist to SQLite
        try:
            self.repository.record_snapshot(
                camera_id=camera_id,
                sampled_at=captured_at,
                visible_count=snapshot.visible_detection_count,
                active_count=snapshot.active_track_count,
                density_class=density_eval.class_,
                density_score=density_eval.score,
                inference_ms=snapshot.inference_ms,
                pipeline_ms=snapshot.pipeline_ms,
                sample_age_ms=snapshot.sample_age_ms
            )
            for alert in alerts:
                self.repository.save_alert(
                    event_id=alert.event_id,
                    camera_id=alert.camera_id,
                    event_type=alert.type,
                    severity=alert.severity,
                    confidence=alert.confidence,
                    evidence=alert.evidence,
                    occurred_at=alert.occurred_at
                )
        except Exception as e:
            logger.error(f"Persistence error: {e}")

        # Render visual overlay with bounding boxes, yellow lines, and alerts
        try:
            intrusion_active = any(a.type == "platform_intrusion" for a in alerts)
            self._latest_annotated_frames[camera_id] = render_ai_overlay(
                frame,
                batch.detections,
                tracks,
                intrusion_active=intrusion_active
            )
        except Exception as e:
            logger.warning(f"Failed to render AI overlay: {e}")
            self._latest_annotated_frames[camera_id] = frame

        return snapshot, alerts
