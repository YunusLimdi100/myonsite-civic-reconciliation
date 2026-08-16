import math
from datetime import datetime

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
