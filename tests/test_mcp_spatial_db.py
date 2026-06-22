"""Unit tests for MCP spatial-db tool functions.

Call tool functions directly — no MCP subprocess, no LLM, no API key needed.
FastMCP's @mcp.tool() returns the original callable, so direct calls work.
"""

from deg.mcp.spatial_db.server import (
    get_street_info,
    get_street_pois,
    search_pois_by_constraints,
)


def test_get_street_info_wutiaogang():
    info = get_street_info("wutiaogang")
    assert info["street_id"] == "wutiaogang"
    assert info["name"] == "五條港里"
    assert "pois" not in info


def test_get_street_info_unknown_returns_error():
    result = get_street_info("nowhere")
    assert "error_message" in result


def test_get_street_pois_structure():
    result = get_street_pois("wutiaogang")
    pois = result["pois"]
    assert isinstance(pois, list)
    assert len(pois) > 0
    p = pois[0]
    assert "name" in p
    assert "category" in p
    assert "location" in p
    assert "tags" in p
    assert "note" in p
    assert "lat" in p["location"]
    assert "lng" in p["location"]


def test_search_pois_cafe_constraint():
    result = search_pois_by_constraints("chihkan", ["歷史"])
    results = result["matching_pois"]
    for p in results:
        # either category is history, or tags contain history, or note contains history
        # (This is just a loose check on the data we seeded)
        is_history = p["category"] == "history" or "歷史" in p["tags"] or "歷史" in p["note"]
        assert is_history


def test_search_pois_empty_constraints_returns_all():
    all_pois = get_street_pois("chihkan")["pois"]
    searched = search_pois_by_constraints("chihkan", [])["matching_pois"]
    assert len(all_pois) == len(searched)


def test_all_streets_have_pois():
    for node in ["wutiaogang", "chihkan", "junwang"]:
        assert len(get_street_pois(node)["pois"]) > 0
