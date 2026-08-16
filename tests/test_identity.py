from datetime import datetime, timezone, timedelta
from app.identity import distance_meters, is_overlapping


def test_distance_meters_same_point():
    d = distance_meters(23.0301, 72.5802, 23.0301, 72.5802)
    assert round(d, 2) == 0.0


def test_distance_meters_known_distance():
    # Approx ~200 meters separation
    d = distance_meters(23.0301, 72.5802, 23.0318, 72.5808)
    assert 150 < d < 250


def test_is_overlapping_within_bounds():
    t1 = datetime(2026, 8, 16, 17, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 16, 17, 30, 0, tzinfo=timezone.utc)  # 30 mins later
    
    overlap = is_overlapping(23.0301, 72.5802, t1, 23.0315, 72.5808, t2)
    assert overlap is True


def test_is_overlapping_exceeds_distance_boundary():
    t1 = datetime(2026, 8, 16, 17, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 16, 17, 10, 0, tzinfo=timezone.utc)
    
    # Distance > 1km
    overlap = is_overlapping(23.0301, 72.5802, t1, 23.0450, 72.5802, t2)
    assert overlap is False


def test_is_overlapping_exceeds_time_boundary():
    t1 = datetime(2026, 8, 16, 17, 0, 0, tzinfo=timezone.utc)
    t2 = t1 + timedelta(minutes=61)  # 61 minutes later (>3600s)
    
    # Same location, but time difference > 1 hour
    overlap = is_overlapping(23.0301, 72.5802, t1, 23.0301, 72.5802, t2)
    assert overlap is False
