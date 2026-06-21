"""Load and validate the Tainan seed spatial dataset into typed objects.

Pure read — no LLM, no network. The MCP spatial-db server (later plan) will
serve queries over these same Street objects.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from deg.schemas import LatLng, Poi

# repo root: deg/seed/loader.py -> parents[2]
_DEFAULT_SEED = Path(__file__).resolve().parents[2] / "data" / "seed" / "streets.json"


class Street(BaseModel):
    """A 街廓 represented by one 地基主 agent."""

    street_id: str
    name: str
    agent_id: str
    centroid: LatLng
    history: str
    pois: list[Poi]


def load_streets(path: Path | str | None = None) -> list[Street]:
    """Read the seed file and return validated Street objects."""
    seed_path = Path(path) if path is not None else _DEFAULT_SEED
    raw = json.loads(seed_path.read_text(encoding="utf-8"))
    return [Street.model_validate(item) for item in raw["streets"]]
