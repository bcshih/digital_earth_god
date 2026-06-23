"""Wire-level data contracts for 數位土地公.

These models are the single source of truth for the A2A payloads (Contract Net
Schema A/B) and the Warm-data Wish. They are pure Pydantic — no I/O, no LLM.
The JSON they serialize is what gets carried inside A2A message DataParts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

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


class TravelContext(BaseModel):
    """Structured travel-party context gathered by 五營兵將 during clarification."""

    trip_type: str | None = None            # solo / couple / family / group
    travel_date: str | None = None          # 旅遊時間 (free text, e.g. "週末下午")
    party_size: int | None = None           # 人數
    has_elderly: bool | None = None         # 有老人
    has_children: bool | None = None        # 有小孩
    interests: list[str] = Field(default_factory=list)            # 偏好
    dietary_restrictions: list[str] = Field(default_factory=list) # 忌口
    wishlist: list[str] = Field(default_factory=list)             # 使用者想去的地點


class TaskBroadcast(BaseModel):
    """Schema A — the call-for-proposals 土地公 broadcasts to all 地基主."""

    task_id: str
    intent: str
    user_location: LatLng
    constraints: list[str] = Field(default_factory=list)
    timeout_ms: int = 3000  # soft preference hint; real-LLM bidding uses a wider window
    travel_context: TravelContext | None = None
    wishlist: list[str] = Field(
        default_factory=list, description="Specific named places the user wants to visit"
    )


class ScoutResult(BaseModel):
    agent_id: str = Field(description="The ID of the responding agent")
    confidence_score: float = Field(
        ge=0.0, le=10.0, description="How confident the agent is in fulfilling the task (0-10)"
    )
    reason: str = Field(description="A single sentence explaining the score")


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


class DebateMessage(BaseModel):
    """地基主在第二輪辯論階段互相反駁或支持的發言"""
    agent_id: str
    debate_text: str


class Wish(BaseModel):
    """Warm-data — a citizen wish made via 上香許願."""

    wish_id: str
    raw_text: str
    category: str
    location: LatLng
    photo_ref: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "received"


class WishAnalysis(BaseModel):
    """五營兵將's LLM classification of a raw wish."""

    category: str           # 交通 / 環境清潔 / 公共安全 / 公共設施 / 社區營造 / 商業活動 / 其他
    tags: list[str] = Field(default_factory=list)
    summary: str            # one-line normalized restatement
    sentiment: str = "中性"  # 正面 / 中性 / 負面 / 急迫


class Blessing(BaseModel):
    """土地公's blessing response to a citizen wish."""

    acknowledgment: str     # warm restatement showing the wish was heard
    blessing: str           # 神明口吻 的祝福（繁體中文）


class ItineraryStop(BaseModel):
    day: int = 1
    poi: Poi
    agent_id: str
    duration_mins: int
    activity: str
    transit_to_next: str | None = None


class JudgmentResult(BaseModel):
    """土地公 LLM-as-Judge final output for a Contract Net round."""

    task_id: str
    recommendation: str
    itinerary: list[ItineraryStop] = Field(default_factory=list)
    contributing_agent_ids: list[str] = Field(default_factory=list)
    reasoning: str


class WuyingOutput(BaseModel):
    """五營兵將's per-round output: either a clarifying question or the final TaskBroadcast."""

    status: Literal["ready", "clarifying"]
    question: str | None = None                                   # clarification question (when status=clarifying)
    collected: TravelContext = Field(default_factory=TravelContext)  # updated after each round
    task_broadcast: TaskBroadcast | None = None                   # populated when status=ready


class CommunityAnswer(BaseModel):
    """One 地基主's answer to a community question."""

    agent_id: str
    street_name: str
    answer_text: str
    sources: list[str] = Field(default_factory=list)


class CommunityQueryResult(BaseModel):
    """土地公's consolidated answer to a community query."""

    question: str
    answers: list[CommunityAnswer] = Field(default_factory=list)
    tudigong_summary: str


# ── 里長大會 (Council) — multi-里 discussion ──────────────────────────────────

Stance = Literal["support", "oppose", "question", "inform", "silent"]


class CouncilStatement(BaseModel):
    """One 地基主's turn in the 里長大會 discussion."""

    agent_id: str
    street_name: str
    round: int = 1
    stance: Stance = "inform"
    responds_to: str | None = None  # agent_id this statement reacts to, or None
    statement_text: str = ""
    sources: list[str] = Field(default_factory=list)


class CouncilAlignment(BaseModel):
    """One 里's final stance, used to paint the consensus map."""

    agent_id: str
    street_name: str
    final_stance: Stance


class CouncilVerdict(BaseModel):
    """土地公's closing 裁示 for a 里長大會 discussion."""

    topic: str
    tudigong_summary: str
    alignments: list[CouncilAlignment] = Field(default_factory=list)
