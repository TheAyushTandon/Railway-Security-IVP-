from app.analytics.density import DensityService


def test_density_classification_thresholds():
    service = DensityService(
        low_medium_threshold=0.30,
        medium_high_threshold=0.70,
        hysteresis_steps=1,  # immediate for testing threshold values
        thresholds_version="test-v1"
    )

    # 5 out of 20 = 25% -> LOW
    d_low = service.evaluate_density("cam_01", active_count=5, capacity_limit=20)
    assert d_low.class_ == "LOW"
    assert d_low.score == 0.25

    # 10 out of 20 = 50% -> MEDIUM
    d_med = service.evaluate_density("cam_01", active_count=10, capacity_limit=20)
    assert d_med.class_ == "MEDIUM"
    assert d_med.score == 0.50

    # 16 out of 20 = 80% -> HIGH
    d_high = service.evaluate_density("cam_01", active_count=16, capacity_limit=20)
    assert d_high.class_ == "HIGH"
    assert d_high.score == 0.80


def test_density_hysteresis():
    # Hysteresis = 2 steps required before transitioning state
    service = DensityService(
        low_medium_threshold=0.30,
        medium_high_threshold=0.70,
        hysteresis_steps=2
    )

    # Starts LOW
    s1 = service.evaluate_density("cam_01", active_count=2, capacity_limit=20)
    assert s1.class_ == "LOW"

    # Spike to 18 people (HIGH candidate, step 1) -> should remain LOW due to hysteresis!
    s2 = service.evaluate_density("cam_01", active_count=18, capacity_limit=20)
    assert s2.class_ == "LOW"

    # Sustained spike (step 2) -> now transitions to HIGH
    s3 = service.evaluate_density("cam_01", active_count=18, capacity_limit=20)
    assert s3.class_ == "HIGH"
