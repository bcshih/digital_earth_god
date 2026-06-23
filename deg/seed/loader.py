"""Load and validate the Tainan NGSI-LD agent datasets into typed objects.

Reads from the 20 li JSON files in dijizu_agent_new/ and provides both raw
NGSI-LD models and backward-compatible Street models for the MCP spatial db.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from deg.schemas import LatLng, Poi

# repo root: deg/seed/loader.py -> parents[2]
_DEFAULT_LI_DIR = Path(__file__).resolve().parents[2] / "dijizu_agent_new"


class GeoJsonPoint(BaseModel):
    type: str
    coordinates: list[float]  # [lng, lat]


class GeoJsonPolygon(BaseModel):
    type: str
    coordinates: list[list[list[float]]]


class GeoProperty(BaseModel):
    type: str
    description: str | None = None
    value: GeoJsonPolygon | Any


class Metadata(BaseModel):
    agent_name: str
    managed_by: str | None = None
    personality: str | None = None


class DynamicPoi(BaseModel):
    poi_id: str
    name: str
    category: str
    description: str
    location: GeoJsonPoint


class PoiListProperty(BaseModel):
    type: str
    value: list[DynamicPoi]


class LiAgentData(BaseModel):
    """Represents a NGSI-LD agent data file for a Li."""
    id: str
    type: str
    metadata: Metadata
    spatial_boundary: GeoProperty | None = None
    layer_1_objective: dict | None = None
    layer_2_dynamic_activities: dict | None = None
    layer_3_dynamic_pois: PoiListProperty | None = None
    layer_4_citizen_opinions: dict | None = None

    def to_street(self) -> Street:
        """Convert to the legacy internal Street object for backward compatibility."""
        # Extract agent ID from URN: urn:ngsi-ld:VillageAgent:Tainan:WestCentral:Wutiaogang -> wutiaogang
        agent_id_suffix = self.id.split(":")[-1].lower()
        agent_id = f"street_{agent_id_suffix}_node"
        
        # Calculate centroid from polygon or default
        centroid = LatLng(lat=22.999, lng=120.197) # fallback
        if self.spatial_boundary and self.spatial_boundary.value and self.spatial_boundary.value.type == "Polygon":
            coords = self.spatial_boundary.value.coordinates[0]
            if coords:
                avg_lng = sum(p[0] for p in coords) / len(coords)
                avg_lat = sum(p[1] for p in coords) / len(coords)
                centroid = LatLng(lat=avg_lat, lng=avg_lng)

        # Convert POIs
        pois = []
        if self.layer_3_dynamic_pois and self.layer_3_dynamic_pois.value:
            for p in self.layer_3_dynamic_pois.value:
                if not p.name: # skip empty template pois
                    continue
                pois.append(Poi(
                    name=p.name,
                    category=p.category,
                    location=LatLng(lat=p.location.coordinates[1], lng=p.location.coordinates[0]),
                    tags=[],
                    note=p.description
                ))
        
        history = ""
        if self.layer_1_objective and "value" in self.layer_1_objective:
            history = self.layer_1_objective["value"].get("history", "")

        return Street(
            street_id=agent_id_suffix,
            name=self.metadata.agent_name.replace("地基主", ""),
            agent_id=agent_id,
            centroid=centroid,
            history=history,
            pois=pois
        )


class Street(BaseModel):
    """A 街廓/里 represented by one 地基主 agent."""
    street_id: str
    name: str
    agent_id: str
    centroid: LatLng
    history: str
    pois: list[Poi]


def _get_val(obs: dict, key: str, default: Any = "") -> Any:
    val = obs.get(key)
    if isinstance(val, dict) and "value" in val:
        return val["value"]
    return val if val is not None else default


def parse_ngsi_ld_graph(data: dict) -> LiAgentData:
    """Transform the new JSON-LD @graph format into the expected LiAgentData structure."""
    if "@graph" not in data:
        # Fallback to old format if directly provided
        return LiAgentData.model_validate(data)

    graph = data.get("@graph", [])
    village = next((item for item in graph if item.get("type") == "VillageAgent"), None)
    if not village:
        raise ValueError("No VillageAgent node found in @graph")

    observations = [item for item in graph if item.get("type") == "LocalObservation"]

    metadata = {
        "agent_name": _get_val(village, "name", "未知"),
        "managed_by": _get_val(village, "managedBy", None),
        "personality": _get_val(village, "persona", "熱心護航在地"),
    }

    spatial = _get_val(village, "spatialBoundary", None)
    spatial_prop = {"type": "GeoProperty", "value": spatial} if spatial and isinstance(spatial, dict) else None

    history = _get_val(village, "history", "")
    layer1 = {"value": {"history": history}}

    # Limit the number of observations to protect LLM token limit
    MAX_OBS = 15
    pois = []
    activities = []
    opinions = []

    for obs in observations[:MAX_OBS]:
        cat = _get_val(obs, "category", "")
        name = _get_val(obs, "name", "")
        desc = _get_val(obs, "description", "")
        loc = _get_val(obs, "location", {})
        tags = _get_val(obs, "tags", [])
        
        # Format tags to include in description or just keep them
        if tags:
            desc = f"{desc} (標籤: {', '.join(tags)})"

        if cat in ("daily_activity", "weather", "new_shop"):
            activities.append({
                "title": name,
                "content": desc,
                "category": cat
            })
        elif cat == "citizen_feedback" or "opinion" in cat.lower():
            opinions.append({
                "title": name,
                "content": desc
            })
        else:
            coords = [0.0, 0.0]
            if isinstance(loc, dict) and "value" in loc:
                loc_val = loc["value"]
                if isinstance(loc_val, dict) and "coordinates" in loc_val:
                    coords = loc_val["coordinates"]
            elif isinstance(loc, dict) and "coordinates" in loc:
                coords = loc["coordinates"]
                
            pois.append({
                "poi_id": obs.get("id", ""),
                "name": name,
                "category": cat,
                "description": desc,
                "location": {"type": "Point", "coordinates": coords}
            })

    layer2 = {"value": activities}
    layer3 = {"type": "Property", "value": pois}
    layer4 = {"value": opinions}

    raw_mapped = {
        "id": village.get("id", "unknown"),
        "type": "AgentData",
        "metadata": metadata,
        "spatial_boundary": spatial_prop,
        "layer_1_objective": layer1,
        "layer_2_dynamic_activities": layer2,
        "layer_3_dynamic_pois": layer3,
        "layer_4_citizen_opinions": layer4
    }

    return LiAgentData.model_validate(raw_mapped)


def load_agents(directory: Path | str | None = None) -> list[LiAgentData]:
    """Read all NGSI-LD agent files and return validated LiAgentData objects."""
    d = Path(directory) if directory is not None else _DEFAULT_LI_DIR
    agents = []
    if not d.exists():
        return agents
    for f in d.glob("*.json"):
        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
            agents.append(parse_ngsi_ld_graph(raw))
        except Exception as e:
            print(f"Failed to parse {f.name}: {e}")
    return agents


def load_streets(directory: Path | str | None = None) -> list[Street]:
    """Backward compatibility wrapper: loads NGSI-LD agents and converts to Streets."""
    return [a.to_street() for a in load_agents(directory)]
