from datetime import datetime, timedelta, timezone
from app.analytics.anomaly_rules import AnomalyRuleEngine
from app.tracking.tracker_service import TrackState
from app.vision.detection_schema import DensityInfo


def test_platform_intrusion_and_alert_deduplication():
    engine = AnomalyRuleEngine(rule_version="rules-test-v1")
    t0 = datetime.now(timezone.utc)
    t1 = t0 + timedelta(seconds=1)

    # Define hazard zone along platform edge
    hazard_zones = {
        "yellow_strip": [(0.0, 0.7), (1.0, 0.7), (1.0, 1.0), (0.0, 1.0)]
    }

    # Passenger track entering the hazard zone (ground pt y=0.85)
    track = TrackState(
        camera_id="cam_01",
        track_id=42,
        bbox_norm=[0.4, 0.5, 0.5, 0.85],
        centroid_norm=(0.45, 0.675),
        first_seen_at=t0,
        last_seen_at=t0,
        last_update_at=t0,
        confidence=0.92,
        trajectory=[(0.45, 0.675)]
    )
    density = DensityInfo(class_="LOW", score=0.2, thresholds_version="v1")

    # Frame 1: Triggers alert
    alerts1 = engine.evaluate_rules(
        camera_id="cam_01",
        tracks=[track],
        density=density,
        restricted_zones=hazard_zones,
        loiter_zones={},
        timestamp=t0
    )
    assert len(alerts1) == 1
    assert alerts1[0].type == "PLATFORM_INTRUSION"
    assert alerts1[0].status == "new"
    initial_event_id = alerts1[0].event_id

    # Frame 2: Passenger still in hazard zone -> Alert de-duplication must update existing event_id!
    track.last_seen_at = t1
    track.last_update_at = t1
    alerts2 = engine.evaluate_rules(
        camera_id="cam_01",
        tracks=[track],
        density=density,
        restricted_zones=hazard_zones,
        loiter_zones={},
        timestamp=t1
    )
    assert len(alerts2) == 1
    assert alerts2[0].event_id == initial_event_id
    assert alerts2[0].occurred_at == t1


def test_alert_acknowledgement():
    engine = AnomalyRuleEngine()
    t0 = datetime.now(timezone.utc)
    density = DensityInfo(class_="HIGH", score=0.85, thresholds_version="v1")

    alerts = engine.evaluate_rules(
        camera_id="cam_01",
        tracks=[],
        density=density,
        restricted_zones={},
        loiter_zones={},
        timestamp=t0
    )
    assert len(alerts) == 1
    event_id = alerts[0].event_id
    assert alerts[0].status == "new"

    # Operator acknowledges alert
    ack_event = engine.acknowledge_alert(event_id, actor_id="station_controller_7")
    assert ack_event is not None
    assert ack_event.status == "acknowledged"
    assert ack_event.evidence["acknowledged_by"] == "station_controller_7"
