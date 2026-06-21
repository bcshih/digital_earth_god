"""Wire-level data contracts for 數位土地公.

These models are the single source of truth for the A2A payloads (Contract Net
Schema A/B) and the Warm-data Wish. They are pure Pydantic — no I/O, no LLM.
The JSON they serialize is what gets carried inside A2A message DataParts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class LatLng(BaseModel):
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)


class Poi(BaseModel):
    """A point of interest a 地基主 can recommend."""

    name: str
    category: str
    location: LatLng
    tags: list[str] = Field(default_factory=list)
    note: str = ""


class Evidence(BaseModel):
    """Supporting evidence a 地基主 cites in its bid."""

    sensor: str | None = None  # 巡境使: traffic/weather/crowd summary
    social: str | None = None  # 虎爺: social/IG intel summary


class TaskBroadcast(BaseModel):
    """Schema A — the call-for-proposals 土地公 broadcasts to all 地基主."""

    task_id: str
    intent: str
    user_location: LatLng
    constraints: list[str] = Field(default_factory=list)
    timeout_ms: int = 3000  # soft preference hint; real-LLM bidding uses a wider window


class BiddingProposal(BaseModel):
    """Schema B — a 地基主's bid back to 土地公."""

    agent_id: str
    task_id: str
    fitness_score: float = Field(ge=0.0, le=10.0)
    reasoning: str
    spatial_data: LatLng
    tags: list[str] = Field(default_factory=list)
    candidate_pois: list[Poi] = Field(default_factory=list)
    evidence: Evidence | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class Wish(BaseModel):
    """Warm-data — a citizen wish made via 上香許願."""

    wish_id: str
    raw_text: str
    category: str
    location: LatLng
    photo_ref: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "received"


class JudgmentResult(BaseModel):
    """土地公 LLM-as-Judge final output for a Contract Net round."""

    task_id: str
    winner_agent_id: str
    winner_street: str
    recommendation: str
    recommended_pois: list[Poi] = Field(default_factory=list)
    ranked_agent_ids: list[str] = Field(default_factory=list)
    reasoning: str
