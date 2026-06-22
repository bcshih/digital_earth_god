"""Domain objects (TaskBroadcast / BiddingProposal / JudgmentResult) → A2UI surfaces.

All components use the basic catalog so any A2UI renderer can draw them. Data lives
in the data model (bound by path); components carry presentation intent only.
"""

from __future__ import annotations

from typing import Any

from deg.schemas import BiddingProposal, JudgmentResult, Poi, TaskBroadcast

SURFACE_ID = "explore"


def _poi_dict(p: Poi) -> dict[str, Any]:
    return {
        "name": p.name,
        "category": p.category,
        "lat": p.location.lat,
        "lng": p.location.lng,
        "tags": p.tags,
        "note": p.note,
    }


# -- Intent input surface (五營兵將 dialogue) --

def intent_input_components() -> list[dict[str, Any]]:
    return [
        {"id": "root", "component": "Column",
         "children": ["intent-title", "intent-sub", "intent-field", "intent-submit"]},
        {"id": "intent-title", "component": "Text",
         "text": "向土地公稟報你的心願", "variant": "h1"},
        {"id": "intent-sub", "component": "Text",
         "text": "五營兵將會將你的凡人語言轉成招標令", "variant": "caption"},
        {"id": "intent-field", "component": "TextField",
         "label": "你想找什麼？（例如：安靜的老宅咖啡）",
         "value": {"path": "/intent/text"}, "textFieldType": "text"},
        {"id": "intent-submit-label", "component": "Text", "text": "上香稟報"},
        {"id": "intent-submit", "component": "Button", "child": "intent-submit-label",
         "variant": "primary",
         "checks": [{"condition": {"call": "required",
                                   "args": {"value": {"path": "/intent/text"}}},
                     "message": "請先說出你的心願"}],
         "action": {"event": {"name": "submit_intent",
                              "context": {"text": {"path": "/intent/text"}}}}},
    ]


# -- Task broadcast (招標令) --

def broadcast_data(tb: TaskBroadcast) -> dict[str, Any]:
    return {
        "task_id": tb.task_id,
        "intent": tb.intent,
        "constraints": tb.constraints,
        "lat": tb.user_location.lat,
        "lng": tb.user_location.lng,
    }


def broadcast_components() -> list[dict[str, Any]]:
    """The negotiation surface root + broadcast card + empty bids row."""
    return [
        {"id": "root", "component": "Column",
         "children": ["broadcast-card", "bids-row"]},
        {"id": "broadcast-card", "component": "Card", "child": "broadcast-body"},
        {"id": "broadcast-body", "component": "Column",
         "children": ["broadcast-title", "broadcast-intent"]},
        {"id": "broadcast-title", "component": "Text", "text": "土地公發出招標令", "variant": "h2"},
        {"id": "broadcast-intent", "component": "Text", "text": {"path": "/broadcast/intent"}},
        {"id": "bids-row", "component": "Row", "children": []},
    ]


# -- Bid card (地基主投標) --

def bid_data(proposal: BiddingProposal) -> dict[str, Any]:
    ev = proposal.evidence
    return {
        "agent_id": proposal.agent_id,
        "fitness_score": proposal.fitness_score,
        "reasoning": proposal.reasoning,
        "tags": proposal.tags,
        "sensor": (ev.sensor if ev else None),
        "social": (ev.social if ev else None),
        "candidate_pois": [_poi_dict(p) for p in proposal.candidate_pois],
    }


def bid_card_components(proposal: BiddingProposal, index: int) -> list[dict[str, Any]]:
    """Components for ONE bid card. Ids are namespaced by agent_id so cards coexist.

    NOTE: the caller must also resend `bids-row` with this card's root id appended
    to its children, and call update_data_model('/bids/<agent_id>', bid_data(...)).
    """
    aid = proposal.agent_id
    card = f"bid-{aid}"
    body = f"bid-body-{aid}"
    score = f"bid-score-{aid}"
    reason = f"bid-reason-{aid}"
    path = f"/bids/{aid}"
    return [
        {"id": card, "component": "Card", "child": body},
        {"id": body, "component": "Column", "children": [score, reason]},
        {"id": score, "component": "Text",
         "text": {"path": f"{path}/fitness_score"}, "variant": "h2"},
        {"id": reason, "component": "Text", "text": {"path": f"{path}/reasoning"}},
    ]


def bid_card_root_id(proposal: BiddingProposal) -> str:
    return f"bid-{proposal.agent_id}"


# -- Verdict / recommendation (土地公裁決) --

def judgment_data(result: JudgmentResult) -> dict[str, Any]:
    return {
        "winner_agent_id": result.winner_agent_id,
        "winner_street": result.winner_street,
        "recommendation": result.recommendation,
        "reasoning": result.reasoning,
        "ranked_agent_ids": result.ranked_agent_ids,
        "recommended_pois": [_poi_dict(p) for p in result.recommended_pois],
    }


def judgment_components(result: JudgmentResult) -> list[dict[str, Any]]:
    """Self-contained verdict surface (root → verdict card).

    This is emitted as a standalone updateComponents replacing the surface root with
    the verdict. Earlier broadcast/bid components remain in the renderer's component
    set; this list only needs to be internally consistent (flat-adjacency contract).
    """
    return [
        {"id": "root", "component": "Column",
         "children": ["verdict-card"]},
        {"id": "verdict-card", "component": "Card", "child": "verdict-body"},
        {"id": "verdict-body", "component": "Column",
         "children": ["verdict-title", "verdict-street", "verdict-text"]},
        {"id": "verdict-title", "component": "Text", "text": "土地公的裁決", "variant": "h1"},
        {"id": "verdict-street", "component": "Text",
         "text": {"path": "/verdict/winner_street"}, "variant": "h2"},
        {"id": "verdict-text", "component": "Text", "text": {"path": "/verdict/recommendation"}},
    ]
