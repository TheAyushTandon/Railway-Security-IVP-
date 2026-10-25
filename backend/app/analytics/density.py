from typing import Dict, Literal
from app.vision.detection_schema import DensityInfo


class DensityService:
    """
    Person B Density Service:
    Evaluates crowd density with temporal hysteresis to prevent rapid status flickering.
    """

    def __init__(
        self,
        low_medium_threshold: float = 0.35,
        medium_high_threshold: float = 0.70,
        hysteresis_steps: int = 2,
        thresholds_version: str = "station-v1"
    ):
        self.low_medium_threshold = low_medium_threshold
        self.medium_high_threshold = medium_high_threshold
        self.hysteresis_steps = hysteresis_steps
        self.thresholds_version = thresholds_version

        # State per camera: camera_id -> current_class
        self._current_classes: Dict[str, Literal["LOW", "MEDIUM", "HIGH"]] = {}
        # Consecutively observed candidate state count: camera_id -> (candidate_class, count)
        self._candidate_counts: Dict[str, Tuple[str, int]] = {}

    def _classify_raw(self, score: float) -> Literal["LOW", "MEDIUM", "HIGH"]:
        if score >= self.medium_high_threshold:
            return "HIGH"
        elif score >= self.low_medium_threshold:
            return "MEDIUM"
        return "LOW"

    def evaluate_density(
        self,
        camera_id: str,
        active_count: int,
        capacity_limit: int = 25
    ) -> DensityInfo:
        """
        Computes score as active_count / capacity_limit (capped at 1.0).
        Applies hysteresis: only updates class if candidate state persists for hysteresis_steps.
        """
        raw_score = min(active_count / max(capacity_limit, 1), 1.0)
        raw_class = self._classify_raw(raw_score)

        if camera_id not in self._current_classes:
            self._current_classes[camera_id] = raw_class
            self._candidate_counts[camera_id] = (raw_class, 1)
            return DensityInfo(
                class_=raw_class,
                score=round(raw_score, 2),
                thresholds_version=self.thresholds_version
            )

        current_class = self._current_classes[camera_id]
        if raw_class == current_class:
            self._candidate_counts[camera_id] = (raw_class, 1)
        else:
            cand_class, count = self._candidate_counts.get(camera_id, (raw_class, 0))
            if cand_class == raw_class:
                count += 1
            else:
                cand_class = raw_class
                count = 1

            self._candidate_counts[camera_id] = (cand_class, count)

            if count >= self.hysteresis_steps:
                self._current_classes[camera_id] = cand_class

        return DensityInfo(
            class_=self._current_classes[camera_id],
            score=round(raw_score, 2),
            thresholds_version=self.thresholds_version
        )

    def reset_camera(self, camera_id: str) -> None:
        self._current_classes.pop(camera_id, None)
        self._candidate_counts.pop(camera_id, None)
