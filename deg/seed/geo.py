"""Geographic utilities: Haversine distance and nearest-li lookup."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deg.seed.loader import LiAgentData


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return great-circle distance in metres between two WGS-84 points.

    Args:
        lat1: Latitude of first point (decimal degrees)
        lng1: Longitude of first point (decimal degrees)
        lat2: Latitude of second point (decimal degrees)
        lng2: Longitude of second point (decimal degrees)

    Returns:
        Distance in metres.
    """
    R = 6_371_000.0  # Earth's radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def li_centroid(li: "LiAgentData") -> tuple[float, float] | None:
    """Return (lat, lng) centroid of a li's spatial_boundary polygon, or None.

    Args:
        li: A LiAgentData object with optional spatial_boundary.

    Returns:
        A tuple (lat, lng) if a valid polygon is present, None otherwise.
    """
    if not li.spatial_boundary:
        return None
    val = li.spatial_boundary.value
    if not val or val.type != "Polygon" or not val.coordinates:
        return None
    ring = val.coordinates[0]
    if not ring:
        return None
    avg_lng = sum(p[0] for p in ring) / len(ring)
    avg_lat = sum(p[1] for p in ring) / len(ring)
    return avg_lat, avg_lng


def nearest_li(
    lat: float,
    lng: float,
    n: int = 3,
    agents: "list[LiAgentData] | None" = None,
) -> list[tuple["LiAgentData", float]]:
    """Return the n nearest LiAgentData objects and their distance in metres.

    Agents without a valid spatial_boundary are silently skipped.
    If agents is None, loads from the default dijizu_agent/ directory.

    Args:
        lat: Query latitude (decimal degrees)
        lng: Query longitude (decimal degrees)
        n: Number of nearest agents to return (default 3)
        agents: List of LiAgentData to search. If None, loads from dijizu_agent/.

    Returns:
        A list of (LiAgentData, distance_in_metres) tuples sorted by distance.
    """
    if agents is None:
        from deg.seed.loader import load_agents
        agents = load_agents()

    scored: list[tuple["LiAgentData", float]] = []
    for li in agents:
        c = li_centroid(li)
        if c is None:
            continue
        dist = haversine_m(lat, lng, c[0], c[1])
        scored.append((li, dist))

    scored.sort(key=lambda x: x[1])
    return scored[:n]
