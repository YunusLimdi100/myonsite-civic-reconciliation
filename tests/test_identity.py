from datetime import datetime, timezone, timedelta
from app.identity import distance_meters, is_overlapping, get_confidence_level, evaluate_overlap


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


# --- CONFIDENCE LEVEL BOUNDARY TESTS ---

def test_boundary_100m_900s_high():
    confidence, ambiguous = get_confidence_level(100.0, 900.0)
    assert confidence == "HIGH"
    assert ambiguous is False


def test_boundary_300m_1800s_medium():
    confidence, ambiguous = get_confidence_level(300.0, 1800.0)
    assert confidence == "MEDIUM"
    assert ambiguous is False


def test_boundary_500m_3600s_low_ambiguous():
    confidence, ambiguous = get_confidence_level(500.0, 3600.0)
    assert confidence == "LOW"
    assert ambiguous is True


def test_boundary_100_01m_900s_medium():
    confidence, ambiguous = get_confidence_level(100.01, 900.0)
    assert confidence == "MEDIUM"
    assert ambiguous is False


def test_boundary_300_01m_1800s_low_ambiguous():
    confidence, ambiguous = get_confidence_level(300.01, 1800.0)
    assert confidence == "LOW"
    assert ambiguous is True


def test_evaluate_overlap_boundary_500_01m_no_match():
    t1 = datetime(2026, 8, 16, 17, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 16, 17, 15, 0, tzinfo=timezone.utc)

    # Calculate offset for approx 500.01 meters: lat_offset = 500.01 / 111000 = ~0.0045046
    lat1, lng1 = 23.0300, 72.5800
    lat2 = lat1 + (500.01 / 111000.0)
    lng2 = lng1

    ex_report = {
        "report_id": "r-existing",
        "location": {"lat": lat1, "lng": lng1},
        "timestamp": t1.isoformat()
    }

    is_match, evidence = evaluate_overlap(lat2, lng2, t2, ex_report, max_distance_meters=500.0, max_time_seconds=3600.0)
    assert is_match is False
    assert evidence is None


def test_evaluate_overlap_boundary_3600_01s_no_match():
    t1 = datetime(2026, 8, 16, 17, 0, 0, tzinfo=timezone.utc)
    t2 = t1 + timedelta(seconds=3600.01)

    ex_report = {
        "report_id": "r-existing",
        "location": {"lat": 23.0300, "lng": 72.5800},
        "timestamp": t1.isoformat()
    }

    is_match, evidence = evaluate_overlap(23.0300, 72.5800, t2, ex_report, max_distance_meters=500.0, max_time_seconds=3600.0)
    assert is_match is False
    assert evidence is None
