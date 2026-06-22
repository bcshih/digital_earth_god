"""FastMCP spatial-db server for 數位土地公.

Exposes the Tainan seed dataset as MCP tools for 地基主 agents.

Run standalone (blocks on stdio):
    python -m deg.mcp.spatial_db.server

Connect via ADK:
    McpToolset(connection_params=StdioServerParameters(
        command=sys.executable, args=["-m", "deg.mcp.spatial_db.server"]
    ))
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from deg.schemas import Poi
from deg.seed.loader import load_streets

mcp = FastMCP("deg-spatial-db", instructions="台南中西區空間資料庫 MCP 服務")

# Index seed data once at import time (small, read-only, constant).
_STREETS = {s.street_id: s for s in load_streets()}


def _poi_to_dict(p: Poi) -> dict:
    return {
        "name": p.name,
        "category": p.category,
        "location": {"lat": p.location.lat, "lng": p.location.lng},
        "tags": p.tags,
        "note": p.note,
    }


@mcp.tool()
def get_street_info(street_id: str) -> dict:
    """Returns historical context and metadata for a street/li.

    Args:
        street_id: The identifier of the street or li (e.g. wutiaogang).
    """
    st = _STREETS.get(street_id)
    if st is None:
        return {"error_message": f"Unknown street_id '{street_id}'. Valid: {list(_STREETS)}"}
    return {
        "street_id": st.street_id,
        "name": st.name,
        "agent_id": st.agent_id,
        "centroid": {"lat": st.centroid.lat, "lng": st.centroid.lng},
        "history": st.history,
        "poi_count": len(st.pois),
    }


@mcp.tool()
def get_street_pois(street_id: str) -> dict:
    """Returns all points of interest in a street/li.

    Args:
        street_id: The identifier of the street or li.
    """
    st = _STREETS.get(street_id)
    if st is None:
        return {"error_message": f"Unknown street_id '{street_id}'. Valid: {list(_STREETS)}"}
    return {"pois": [_poi_to_dict(p) for p in st.pois]}


@mcp.tool()
def search_pois_by_constraints(street_id: str, constraints: list[str]) -> dict:
    """Finds POIs in a street/li that match keyword constraints.

    Args:
        street_id: The identifier of the street or li.
        constraints: Keywords to match against name/category/note/tags (e.g. ["quiet", "安靜"]).
                     Empty list returns all POIs.
    """
    st = _STREETS.get(street_id)
    if st is None:
        return {"error_message": f"Unknown street_id '{street_id}'. Valid: {list(_STREETS)}"}

    lower = [c.lower() for c in constraints]

    def _matches(poi) -> bool:
        if not lower:
            return True
        haystack = " ".join([poi.name, poi.category, poi.note] + poi.tags).lower()
        return any(kw in haystack for kw in lower)

    matching = [p for p in st.pois if _matches(p)]
    return {
        "total_pois": len(st.pois),
        "matching_count": len(matching),
        "matching_pois": [_poi_to_dict(p) for p in matching],
    }


@mcp.tool()
def get_all_agents() -> list[dict]:
    """Returns a list of all available street/li agents."""
    return [{"street_id": st.street_id, "name": st.name, "agent_id": st.agent_id} for st in _STREETS.values()]


if __name__ == "__main__":
    mcp.run()
