import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from app.tracking.tracker_service import TrackState
from app.analytics.counting import is_point_in_polygon
from app.vision.detection_schema import DensityInfo, AlertEvent


class AnomalyRuleEngine:
    """
    Person B Anomaly Rules Engine:
    Evaluates passenger behaviors, intrusions, and crowd conditions.
    Features stateful alert de-duplication with stable event_id and cooldown handling.
    """

    def __init__(self, loiter_threshold_seconds: float = 10.0, rule_version: str = "rules-v1"):
        self.loiter_threshold_seconds = loiter_threshold_seconds
        self.rule_version = rule_version

        # Active open incidents: (camera_id, rule_type, entity_key) -> AlertEvent
        self._active_events: Dict[Tuple[str, str, str], AlertEvent] = {}

    def _get_or_create_alert(
        self,
        camera_id: str,
        rule_type: str,
        entity_key: str,
        severity: str,
        confidence: float,
        evidence: dict,
        occurred_at: datetime
    ) -> AlertEvent:
        key = (camera_id, rule_type, entity_key)
        if key in self._active_events:
            # Alert de-duplication: update timestamp and evidence on existing event_id
            event = self._active_events[key]
            event.occurred_at = occurred_at
            event.evidence.update(evidence)
            event.confidence = confidence
            return event

        new_event = AlertEvent(
            event_id=f"evt_{uuid.uuid4()}",
            camera_id=camera_id,
            type=rule_type,
            severity=severity,
            status="new",
            occurred_at=occurred_at,
            confidence=confidence,
            evidence=evidence
        )
        self._active_events[key] = new_event
        return new_event

    def evaluate_rules(
        self,
        camera_id: str,
        tracks: List[TrackState],
        density: DensityInfo,
        restricted_zones: Dict[str, List[Tuple[float, float]]],
        loiter_zones: Dict[str, List[Tuple[float, float]]],
        timestamp: datetime
    ) -> List[AlertEvent]:
        """
        Runs safety checks for the frame and returns all active or updated alerts.
        """
        alerts: List[AlertEvent] = []
        active_keys_this_frame = set()

        # Rule 1: High Crowd Density
        if density.class_ == "HIGH":
            key = (camera_id, "DENSITY_HIGH", "global")
            active_keys_this_frame.add(key)
            alert = self._get_or_create_alert(
                camera_id=camera_id,
                rule_type="DENSITY_HIGH",
                entity_key="global",
                severity="warning",
                confidence=density.score,
                evidence={
                    "density_score": density.score,
                    "thresholds_version": density.thresholds_version,
                    "rule_version": self.rule_version
                },
                occurred_at=timestamp
            )
            alerts.append(alert)

        # Rule 2: Platform Hazard Zone Intrusion
        for track in tracks:
            ground_pt = (track.centroid_norm[0], track.bbox_norm[3])
            for zone_id, polygon in restricted_zones.items():
                if is_point_in_polygon(ground_pt, polygon) or is_point_in_polygon(track.centroid_norm, polygon):
                    key = (camera_id, "PLATFORM_INTRUSION", f"{zone_id}_{track.track_id}")
                    active_keys_this_frame.add(key)
                    dwell = (timestamp - track.first_seen_at).total_seconds()
                    alert = self._get_or_create_alert(
                        camera_id=camera_id,
                        rule_type="PLATFORM_INTRUSION",
                        entity_key=f"{zone_id}_{track.track_id}",
                        severity="critical",
                        confidence=track.confidence,
                        evidence={
                            "roi_id": zone_id,
                            "track_id": track.track_id,
                            "dwell_duration_sec": round(dwell, 1),
                            "rule_version": self.rule_version
                        },
                        occurred_at=timestamp
                    )
                    alerts.append(alert)

        # Rule 3: Loitering Detection
        for track in tracks:
            dwell = (timestamp - track.first_seen_at).total_seconds()
            if dwell >= self.loiter_threshold_seconds:
                for zone_id, polygon in loiter_zones.items():
                    if is_point_in_polygon(track.centroid_norm, polygon):
                        key = (camera_id, "LOITERING", f"{zone_id}_{track.track_id}")
                        active_keys_this_frame.add(key)
                        alert = self._get_or_create_alert(
                            camera_id=camera_id,
                            rule_type="LOITERING",
                            entity_key=f"{zone_id}_{track.track_id}",
                            severity="info",
                            confidence=track.confidence,
                            evidence={
                                "roi_id": zone_id,
                                "track_id": track.track_id,
                                "dwell_duration_sec": round(dwell, 1),
                                "rule_version": self.rule_version
                            },
                            occurred_at=timestamp
                        )
                        alerts.append(alert)

        # Auto-resolve incidents that are no longer active
        for key in list(self._active_events.keys()):
            if key[0] == camera_id and key not in active_keys_this_frame:
                event = self._active_events[key]
                event.status = "resolved"
                event.resolved_at = timestamp
                del self._active_events[key]

        return alerts

    def acknowledge_alert(self, event_id: str, actor_id: str = "operator") -> Optional[AlertEvent]:
        for event in self._active_events.values():
            if event.event_id == event_id:
                event.status = "acknowledged"
                event.acknowledged_at = datetime.now(timezone.utc)
                event.evidence["acknowledged_by"] = actor_id
                return event
        return None
