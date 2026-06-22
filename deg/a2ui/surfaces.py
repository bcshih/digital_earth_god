"""Domain objects (TaskBroadcast / BiddingProposal / JudgmentResult) → A2UI surfaces.

All components use the basic catalog so any A2UI renderer can draw them. Data lives
in the data model (bound by path); components carry presentation intent only.

Durable contract — the emission is designed so every `updateComponents` message is a
self-contained, valid flat-adjacency-list fragment (no cross-message child refs):

1. `intent_input_components()` — the 五營兵將 prompt surface (its own root).
2. `negotiation_components()` — the STABLE skeleton emitted once after intent:
   broadcast card + a `List` (`bids-row`) bound to `/bids` via a `bid-card` TEMPLATE
   + a `verdict-card` placeholder. Root never changes after this.
   - Each 地基主 bid arrives as a pure data-model append: update `/bids/<i>` — no
     component message, so no cross-fragment id references ever occur.
3. `judgment_components()` — redefines ONLY the `verdict-card` subtree in place; root
   still references it, so broadcast + bids remain visible beneath the verdict.
"""

from __future__ import annotations

from typing import Any

from deg.schemas import BiddingProposal, JudgmentResult, Poi, TaskBroadcast

SURFACE_ID = "explore"

# agent_id → human street label (BiddingProposal carries only agent_id).
_STREET_LABELS = {
    "street_shennong_node": "神農街",
    "street_haian_node": "海安路",
    "street_zhengxing_node": "正興街",
}


def _poi_dict(p: Poi) -> dict[str, Any]:
    return {
        "name": p.name,
        "category": p.category,
        "lat": p.location.lat,
        "lng": p.location.lng,
        "tags": p.tags,
        "note": p.note,
    }


# ── Intent input surface (五營兵將 dialogue) ──────────────────────────────────

def intent_input_components() -> list[dict[str, Any]]:
    return [
        {"id": "root", "component": "Column",
         "children": ["intent-title", "intent-sub", "intent-field", "intent-submit"]},
        {"id": "intent-title", "component": "Text",
         "text": "向土地公問路", "variant": "h1"},
        {"id": "intent-sub", "component": "Text",
         "text": "說出你的心意，五營兵將為你傳達，土地公親自裁奪", "variant": "caption"},
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


# ── 五營兵將 clarification question surface ───────────────────────────────────

def clarification_components(question: str, round_n: int = 0) -> list[dict[str, Any]]:
    """Ask one clarifying question; user types answer and presses 稟報.

    Replaces the intent-input root in place — old intent-* components are
    orphaned (not reachable from root) and the renderer won't draw them.
    The fragment is self-contained: root → clarify-* only.
    """
    round_label = f"第 {round_n + 1} 問"
    return [
        {"id": "root", "component": "Column",
         "children": ["clarify-badge", "clarify-q", "clarify-field", "clarify-submit"]},
        {"id": "clarify-badge", "component": "Text",
         "text": f"五營兵將追問 · {round_label}", "variant": "caption"},
        {"id": "clarify-q", "component": "Text",
         "text": question, "variant": "h2"},
        {"id": "clarify-field", "component": "TextField",
         "label": "請稟報",
         "value": {"path": "/clarify/answer"}, "textFieldType": "text"},
        {"id": "clarify-submit-label", "component": "Text", "text": "稟報"},
        {"id": "clarify-submit", "component": "Button", "child": "clarify-submit-label",
         "variant": "primary",
         "action": {"event": {"name": "submit_clarify",
                              "context": {"answer": {"path": "/clarify/answer"}}}}},
    ]


# ── Task broadcast data (招標令) ──────────────────────────────────────────────

def broadcast_data(tb: TaskBroadcast) -> dict[str, Any]:
    return {
        "task_id": tb.task_id,
        "intent": tb.intent,
        "constraints": tb.constraints,
        "lat": tb.user_location.lat,
        "lng": tb.user_location.lng,
    }


# ── Negotiation skeleton (broadcast + bids List template + verdict placeholder) ─

def negotiation_components() -> list[dict[str, Any]]:
    """The stable surface skeleton, emitted once after the TaskBroadcast is ready.

    `bids-row` is a `List` whose children are a TEMPLATE (`bid-card`) bound to the
    `/bids` array — adding a bid is a data-model append, not a component change.
    `verdict-card` starts as a placeholder; `judgment_components()` fills it later.
    Inside the template, binding paths are RELATIVE to the array item
    (e.g. `{"path": "street"}` → `/bids/<i>/street`).
    """
    return [
        {"id": "root", "component": "Column",
         "children": ["broadcast-card", "bids-row", "verdict-card"]},
        # — broadcast (招標令) —
        {"id": "broadcast-card", "component": "Card", "child": "broadcast-body"},
        {"id": "broadcast-body", "component": "Column",
         "children": ["broadcast-title", "broadcast-intent"]},
        {"id": "broadcast-title", "component": "Text",
         "text": "土地公已發出招標令，地基主們各顯神通", "variant": "h2"},
        {"id": "broadcast-intent", "component": "Text", "text": {"path": "/broadcast/intent"}},
        # — bids (地基主投標) as a data-bound List + card template —
        {"id": "bids-row", "component": "List",
         "children": {"path": "/bids", "componentId": "bid-card"}},
        {"id": "bid-card", "component": "Card", "child": "bid-card-body"},
        {"id": "bid-card-body", "component": "Column",
         "children": ["bid-card-street", "bid-card-score", "bid-card-reason"]},
        {"id": "bid-card-street", "component": "Text",
         "text": {"path": "street"}, "variant": "h2"},
        {"id": "bid-card-score", "component": "Text", "text": {"path": "fitness_score"}},
        {"id": "bid-card-reason", "component": "Text", "text": {"path": "reasoning"}},
        # — verdict placeholder (filled in place by judgment_components) —
        {"id": "verdict-card", "component": "Card", "child": "verdict-wait"},
        {"id": "verdict-wait", "component": "Text",
         "text": "靜待土地公擲筊定奪…", "variant": "caption"},
    ]


# ── Bid data (one entry appended to the /bids array) ──────────────────────────

def bid_data(proposal: BiddingProposal) -> dict[str, Any]:
    ev = proposal.evidence
    return {
        "agent_id": proposal.agent_id,
        "street": _STREET_LABELS.get(proposal.agent_id, proposal.agent_id),
        "fitness_score": proposal.fitness_score,
        "reasoning": proposal.reasoning,
        "tags": proposal.tags,
        "sensor": (ev.sensor if ev else None),
        "social": (ev.social if ev else None),
        "candidate_pois": [_poi_dict(p) for p in proposal.candidate_pois],
    }


# ── Verdict / recommendation (土地公裁決) ─────────────────────────────────────

def judgment_data(result: JudgmentResult) -> dict[str, Any]:
    return {
        "winner_agent_id": result.winner_agent_id,
        "winner_street": result.winner_street,
        "recommendation": result.recommendation,
        "reasoning": result.reasoning,
        "ranked_agent_ids": result.ranked_agent_ids,
        "recommended_pois": [_poi_dict(p) for p in result.recommended_pois],
    }


def judgment_components() -> list[dict[str, Any]]:
    """Redefine the `verdict-card` subtree in place.

    Root (from `negotiation_components`) still lists `verdict-card`, so the broadcast
    card and bid List stay visible beneath the verdict. This fragment is self-contained:
    `verdict-card` is the single unreferenced root and every child resolves internally.
    """
    return [
        {"id": "verdict-card", "component": "Card", "child": "verdict-body"},
        {"id": "verdict-body", "component": "Column",
         "children": ["verdict-title", "verdict-street", "verdict-text"]},
        {"id": "verdict-title", "component": "Text", "text": "土地公親降裁決", "variant": "h1"},
        {"id": "verdict-street", "component": "Text",
         "text": {"path": "/verdict/winner_street"}, "variant": "h2"},
        {"id": "verdict-text", "component": "Text", "text": {"path": "/verdict/recommendation"}},
    ]


WISH_SURFACE_ID = "wish"


def wish_input_components() -> list[dict[str, Any]]:
    return [
        {"id": "root", "component": "Column",
         "children": ["wish-title", "wish-sub", "wish-field", "wish-submit"]},
        {"id": "wish-title", "component": "Text", "text": "向土地公上香許願", "variant": "h1"},
        {"id": "wish-sub", "component": "Text",
         "text": "說出你對這座城市的心願，土地公親收，一願一心記", "variant": "caption"},
        {"id": "wish-field", "component": "TextField",
         "label": "你的心願（例如：希望海安路多裝路燈）",
         "value": {"path": "/wish/text"}, "textFieldType": "text"},
        {"id": "wish-submit-label", "component": "Text", "text": "上香許願"},
        {"id": "wish-submit", "component": "Button", "child": "wish-submit-label",
         "variant": "primary",
         "checks": [{"condition": {"call": "required",
                                   "args": {"value": {"path": "/wish/text"}}},
                     "message": "請先說出你的心願"}],
         "action": {"event": {"name": "submit_wish",
                              "context": {"text": {"path": "/wish/text"}}}}},
    ]


def blessing_components() -> list[dict[str, Any]]:
    return [
        {"id": "root", "component": "Column",
         "children": ["blessing-card"]},
        {"id": "blessing-card", "component": "Card", "child": "blessing-body"},
        {"id": "blessing-body", "component": "Column",
         "children": ["blessing-title", "blessing-ack", "blessing-text", "blessing-cat"]},
        {"id": "blessing-title", "component": "Text", "text": "土地公收到了，有話說", "variant": "h1"},
        {"id": "blessing-ack", "component": "Text", "text": {"path": "/blessing/acknowledgment"}},
        {"id": "blessing-text", "component": "Text", "text": {"path": "/blessing/blessing"},
         "variant": "h2"},
        {"id": "blessing-cat", "component": "Text", "text": {"path": "/blessing/category"},
         "variant": "caption"},
    ]
