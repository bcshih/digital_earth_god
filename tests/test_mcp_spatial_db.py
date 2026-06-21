"""Unit tests for MCP spatial-db tool functions.

Call tool functions directly — no MCP subprocess, no LLM, no API key needed.
FastMCP's @mcp.tool() returns the original callable, so direct calls work.
"""

from deg.mcp.spatial_db.server import (
    get_street_info,
    get_street_pois,
    search_pois_by_constraints,
)


def test_get_street_info_shennong():
    result = get_street_info("shennong")
    assert result["street_id"] == "shennong"
    assert result["name"] == "神農街"
    assert result["agent_id"] == "street_shennong_node"
    assert "history" in result
    assert result["poi_count"] >= 1


def test_get_street_info_unknown_returns_error():
    result = get_street_info("nowhere")
    assert "error_message" in result


def test_get_street_pois_structure():
    result = get_street_pois("shennong")
    pois = result["pois"]
    assert len(pois) >= 1
    for p in pois:
        assert {"name", "category", "location", "tags", "note"} <= p.keys()
        assert {"lat", "lng"} <= p["location"].keys()


def test_search_pois_cafe_constraint():
    result = search_pois_by_constraints("shennong", ["cafe"])
    assert result["matching_count"] >= 1
    for p in result["matching_pois"]:
        text = " ".join([p["name"], p["category"], p.get("note", "")] + p.get("tags", []))
        assert "cafe" in text.lower() or "咖啡" in text


def test_search_pois_empty_constraints_returns_all():
    result = search_pois_by_constraints("haian", [])
    assert result["matching_count"] == result["total_pois"]


def test_all_three_streets_have_pois():
    for street_id in ["shennong", "haian", "zhengxing"]:
        result = get_street_pois(street_id)
        assert len(result["pois"]) >= 1, f"{street_id} has no POIs"
