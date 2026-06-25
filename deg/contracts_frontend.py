"""Frontend-facing payload mappers for the tainan-travel client.

The tainan-travel frontend (Vite/React/Zustand) speaks a simple typed
`{type, ...}` WebSocket protocol and renders plain `Spot` / `DayItinerary`
shapes (see its `src/types/index.ts`). These helpers translate the backend's
internal contracts (`Poi`, `ItineraryStop`, `BiddingProposal`, `DebateMessage`)
into exactly those frontend shapes, so the client never has to reshape data.

Pure functions — no I/O, no LLM. The single source of truth for the wire format
is `docs/integration/frontend-api-contract.md`.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

from deg.schemas import BiddingProposal, DebateMessage, ItineraryStop, Poi

# All 20 里 in the dataset are in Tainan's West Central District.
_DISTRICT = "中西區"
def _streetview_url(lat: float, lng: float) -> str | None:
    key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not key:
        return None
    return (
        f"https://maps.googleapis.com/maps/api/streetview"
        f"?size=400x300&location={lat},{lng}&key={key}"
    )


def poi_to_spot(
    poi: Poi,
    village: str,
    *,
    spot_id: str | None = None,
    open_hours: str = "",
    description: str | None = None,
) -> dict[str, Any]:
    """Map a backend `Poi` to the frontend `Spot` shape.

    `village` is the 里 name (e.g. "五條港里"); `district` is fixed to 中西區.
    `open_hours` / `description` let callers inject itinerary context
    (停留時間 / 活動建議) the bare POI does not carry.
    """
    tags = list(poi.tags)
    if poi.category and poi.category not in tags:
        tags.append(poi.category)
    result: dict[str, Any] = {
        "id": spot_id or f"{village}-{poi.name}",
        "name": poi.name,
        "district": _DISTRICT,
        "village": village,
        "address": "",
        "openHours": open_hours,
        "description": description if description is not None else poi.note,
        "tags": tags,
        "lat": poi.location.lat,
        "lng": poi.location.lng,
    }
    img = _streetview_url(poi.location.lat, poi.location.lng)
    if img:
        result["imageUrl"] = img
    return result


def itinerary_to_days(
    stops: list[ItineraryStop],
    agent_name_by_id: dict[str, str],
) -> list[dict[str, Any]]:
    """Group `ItineraryStop`s by day and emit the frontend `DayItinerary[]` shape.

    `agent_name_by_id` maps agent_id → 里名 so each spot carries its real
    contributing 里 as `village`.
    """
    by_day: dict[int, list[ItineraryStop]] = {}
    for stop in stops:
        by_day.setdefault(stop.day or 1, []).append(stop)

    days: list[dict[str, Any]] = []
    for day in sorted(by_day):
        items = []
        for order, stop in enumerate(by_day[day], start=1):
            village = agent_name_by_id.get(stop.agent_id, "台南市")
            spot = poi_to_spot(
                stop.poi,
                village,
                spot_id=f"stop-{day}-{order}",
                open_hours=f"建議停留 {stop.duration_mins} 分鐘",
                description=stop.activity or poi_note(stop.poi),
            )
            items.append({
                "id": f"stop-{day}-{order}",
                "order": order,
                "spot": spot,
                "durationMinutes": stop.duration_mins,
                "note": stop.transit_to_next or "",
            })
        day_date = (date.today() + timedelta(days=day - 1)).isoformat()
        days.append({"day": day, "date": day_date, "items": items})
    return days


def poi_note(poi: Poi) -> str:
    return poi.note or ""


def bidding_to_agent_event(
    proposal: BiddingProposal,
    agent_name: str,
) -> dict[str, Any]:
    """A readable chat-room `agent_event` from a 地基主's bid.

    Carries `reasoning` as the dialogue line plus the first candidate POI as an
    `attachedSpot` so the frontend can pop a 籤 card.
    """
    event: dict[str, Any] = {
        "type": "agent_event",
        "agent": proposal.agent_id,
        "agent_name": agent_name,
        "text": proposal.reasoning,
    }
    if proposal.candidate_pois:
        event["attachedSpot"] = poi_to_spot(proposal.candidate_pois[0], agent_name)
    return event


def debate_to_agent_event(
    debate: DebateMessage,
    agent_name: str,
) -> dict[str, Any]:
    """A readable chat-room `agent_event` from a 地基主's debate turn."""
    return {
        "type": "agent_event",
        "agent": debate.agent_id,
        "agent_name": agent_name,
        "text": debate.debate_text,
    }
