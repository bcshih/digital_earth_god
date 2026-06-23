# tests/test_geo.py
import math
import pytest
from pathlib import Path

from deg.seed.geo import haversine_m, li_centroid, nearest_li
from deg.seed.loader import load_agents, LiAgentData, GeoJsonPolygon, GeoProperty, Metadata

_LI_DIR = Path(__file__).resolve().parents[1] / "dijizu_agent_new"


def _make_li(lng: float, lat: float, name: str = "TestLi") -> LiAgentData:
    """Create a minimal LiAgentData with a spatial_boundary polygon."""
    poly = GeoJsonPolygon(
        type="Polygon",
        coordinates=[[[lng, lat], [lng + 0.001, lat], [lng + 0.001, lat + 0.001], [lng, lat + 0.001], [lng, lat]]],
    )
    geo_prop = GeoProperty(
        type="GeoProperty",
        description=f"Test polygon for {name}",
        value=poly
    )
    metadata = Metadata(
        agent_name=name,
        managed_by=None,
        personality=None
    )
    return LiAgentData(
        id=f"urn:ngsi-ld:EarthGodAgent:Tainan:WestCentral:{name}",
        type="EarthGodAgent",
        metadata=metadata,
        spatial_boundary=geo_prop
    )


def _make_li_no_boundary(name: str = "NoBoundary") -> LiAgentData:
    """Create a LiAgentData without a spatial_boundary."""
    metadata = Metadata(
        agent_name=name,
        managed_by=None,
        personality=None
    )
    return LiAgentData(
        id=f"urn:ngsi-ld:EarthGodAgent:Tainan:WestCentral:{name}",
        type="EarthGodAgent",
        metadata=metadata,
        spatial_boundary=None
    )


def test_haversine_same_point():
    """Haversine distance between identical points should be ~0."""
    assert haversine_m(22.999, 120.196, 22.999, 120.196) == pytest.approx(0.0, abs=1e-6)


def test_haversine_known_distance():
    """1 degree latitude ≈ 111,195 m."""
    d = haversine_m(0.0, 0.0, 1.0, 0.0)
    assert 111_000 < d < 112_000


def test_haversine_symmetry():
    """Haversine should be symmetric."""
    d1 = haversine_m(22.999, 120.196, 23.100, 120.300)
    d2 = haversine_m(23.100, 120.300, 22.999, 120.196)
    assert d1 == pytest.approx(d2)


def test_li_centroid_simple_square():
    """Centroid of a small square polygon should be approximately the center."""
    li = _make_li(120.196, 22.999)
    result = li_centroid(li)
    assert result is not None
    lat_c, lng_c = result
    assert lat_c == pytest.approx(22.9995, abs=1e-3)
    assert lng_c == pytest.approx(120.1964, abs=1e-3)


def test_li_centroid_no_boundary():
    """LiAgentData without spatial_boundary should return None."""
    li = _make_li_no_boundary()
    result = li_centroid(li)
    assert result is None


def test_li_centroid_empty_coordinates():
    """LiAgentData with empty polygon coordinates should return None."""
    metadata = Metadata(agent_name="Empty", managed_by=None, personality=None)
    poly = GeoJsonPolygon(type="Polygon", coordinates=[])
    geo_prop = GeoProperty(type="GeoProperty", value=poly)
    li = LiAgentData(
        id="urn:ngsi-ld:EarthGodAgent:Tainan:WestCentral:Empty",
        type="EarthGodAgent",
        metadata=metadata,
        spatial_boundary=geo_prop
    )
    result = li_centroid(li)
    assert result is None


def test_nearest_li_returns_n_closest():
    """nearest_li should return the n closest agents."""
    agents = [
        _make_li(120.196, 22.999, "Near"),
        _make_li(120.300, 23.100, "Far"),
        _make_li(120.197, 23.000, "Medium"),
    ]
    result = nearest_li(lat=22.999, lng=120.196, n=2, agents=agents)
    assert len(result) == 2
    first_li, first_dist = result[0]
    assert first_li.metadata.agent_name == "Near"
    assert first_dist < 200  # meters


def test_nearest_li_with_no_boundary_skips():
    """LiAgentData without spatial_boundary should be silently skipped."""
    agents = [
        _make_li(120.196, 22.999, "WithBoundary"),
        _make_li_no_boundary("NoBoundary"),
    ]
    result = nearest_li(lat=22.999, lng=120.196, n=2, agents=agents)
    assert len(result) == 1
    assert result[0][0].metadata.agent_name == "WithBoundary"


def test_nearest_li_default_n():
    """nearest_li should default to n=3."""
    agents = [
        _make_li(120.196, 22.999, "A"),
        _make_li(120.197, 23.000, "B"),
        _make_li(120.198, 23.001, "C"),
        _make_li(120.300, 23.100, "D"),
    ]
    result = nearest_li(lat=22.999, lng=120.196, agents=agents)
    assert len(result) == 3


def test_nearest_li_returns_tuples_with_distance():
    """nearest_li results should be tuples of (LiAgentData, distance_in_meters)."""
    agents = [_make_li(120.196, 22.999, "Test")]
    result = nearest_li(lat=22.999, lng=120.196, n=1, agents=agents)
    assert len(result) == 1
    li, dist = result[0]
    assert isinstance(li, LiAgentData)
    assert isinstance(dist, float)
    # Distance should be very small (centroid is at center of polygon)
    assert dist < 100


@pytest.mark.skipif(not _LI_DIR.exists(), reason="dijizu_agent_new/ not present")
def test_nearest_li_loads_default_agents_if_none():
    """nearest_li should load from dijizu_agent_new/ if agents=None."""
    # This test only passes if dijizu_agent_new/ exists with valid JSON files.
    result = nearest_li(lat=22.999, lng=120.196, n=5)
    assert len(result) > 0
    assert all(isinstance(li, LiAgentData) for li, _ in result)
    assert all(isinstance(dist, float) for _, dist in result)
