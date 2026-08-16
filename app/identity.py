import math
from datetime import datetime
from typing import Tuple, Dict, Any, Optional

EARTH_RADIUS_METERS = 6371000.0  # Mean radius of Earth in meters


def distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth's surface
    using the Haversine formula. Returns distance in meters.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_METERS * c


def get_confidence_level(distance_m: float, time_diff_s: float) -> Tuple[str, bool]:
    """
    Determines deterministic confidence level and ambiguity status:
    - HIGH: distance <= 100m AND time difference <= 15 minutes (900s) [ambiguous = False]
    - MEDIUM: distance <= 300m AND time difference <= 30 minutes (1800s) [ambiguous = False]
    - LOW: otherwise within 500m/1h [ambiguous = True]
    """
    if distance_m <= 100.0 and time_diff_s <= 900.0:
        return "HIGH", False
    elif distance_m <= 300.0 and time_diff_s <= 1800.0:
        return "MEDIUM", False
    else:
        return "LOW", True


def evaluate_overlap(
    report_lat: float,
    report_lng: float,
    report_time: datetime,
    existing_report: Dict[str, Any],
    max_distance_meters: float = 500.0,
    max_time_seconds: float = 3600.0,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Evaluates whether a report overlaps with an existing report and returns
    detailed identity resolution evidence metadata.
    """
    ex_loc = existing_report.get("location")
    if isinstance(ex_loc, dict):
        ex_lat = float(ex_loc["lat"])
        ex_lng = float(ex_loc["lng"])
    else:
        ex_lat = float(existing_report["latitude"])
        ex_lng = float(existing_report["longitude"])

    ex_time = existing_report["timestamp"]
    if isinstance(ex_time, str):
        ex_time = datetime.fromisoformat(ex_time.replace("Z", "+00:00"))

    dist = distance_meters(report_lat, report_lng, ex_lat, ex_lng)
    time_diff = abs((report_time - ex_time).total_seconds())

    if dist <= max_distance_meters and time_diff <= max_time_seconds:
        confidence, ambiguous = get_confidence_level(dist, time_diff)
        evidence = {
            "matched_report_id": existing_report.get("report_id"),
            "distance_meters": round(dist, 2),
            "time_difference_seconds": round(time_diff, 2),
            "distance_threshold_meters": max_distance_meters,
            "time_threshold_seconds": max_time_seconds,
            "confidence_level": confidence,
            "ambiguous": ambiguous,
        }
        return True, evidence

    return False, None


def is_overlapping(
    report_lat: float,
    report_lng: float,
    report_time: datetime,
    incident_lat: float,
    incident_lng: float,
    incident_time: datetime,
    max_distance_meters: float = 500.0,
    max_time_seconds: float = 3600.0,
) -> bool:
    """
    Determines whether a report overlaps with an existing incident based on:
    1. Geographic distance <= max_distance_meters (default 500m)
    2. Absolute timestamp difference <= max_time_seconds (default 1 hour / 3600s)
    """
    dist = distance_meters(report_lat, report_lng, incident_lat, incident_lng)
    time_diff = abs((report_time - incident_time).total_seconds())

    return dist <= max_distance_meters and time_diff <= max_time_seconds

