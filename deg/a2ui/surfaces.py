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

from deg.schemas import BiddingProposal, DebateMessage, JudgmentResult, Poi, TaskBroadcast, ScoutResult

SURFACE_ID = "explore"

from deg.seed.loader import load_agents

def _get_street_labels() -> dict[str, str]:
    try:
        return {a.to_street().agent_id: a.to_street().name for a in load_agents()}
    except Exception:
        return {}

_STREET_LABELS = _get_street_labels()


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

def scout_data(result: ScoutResult) -> dict[str, Any]:
    return {
        "agent_id": result.agent_id,
        "street": _STREET_LABELS.get(result.agent_id, result.agent_id),
        "confidence_score": f"{result.confidence_score}/10",
        "reason": result.reason,
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
         "children": ["broadcast-card", "scouts-row", "negotiation-board", "verdict-card"]},
        # — broadcast (招標令) —
        {"id": "broadcast-card", "component": "Card", "child": "broadcast-body"},
        {"id": "broadcast-body", "component": "Column",
         "children": ["broadcast-title", "broadcast-intent"]},
        {"id": "broadcast-title", "component": "Text",
         "text": "土地公已發出招標令，地基主們各顯神通", "variant": "h2"},
        {"id": "broadcast-intent", "component": "Text", "text": {"path": "/broadcast/intent"}},
        # — scouts (前哨回報) —
        {"id": "scouts-row", "component": "List",
         "children": {"path": "/scouts", "componentId": "scout-card"}},
        {"id": "scout-card", "component": "Card", "child": "scout-card-body"},
        {"id": "scout-card-body", "component": "Column",
         "children": ["scout-card-street", "scout-card-score", "scout-card-reason"]},
        {"id": "scout-card-street", "component": "Text",
         "text": {"path": "street"}, "variant": "h2"},
        {"id": "scout-card-score", "component": "Text", "text": {"path": "confidence_score"}, "variant": "score"},
        {"id": "scout-card-reason", "component": "Text", "text": {"path": "reason"}},
        # — negotiation-board placeholder —
        {"id": "negotiation-board", "component": "Card", "child": "negotiation-placeholder"},
        {"id": "negotiation-placeholder", "component": "Text", "text": "正在等候地基主投標..."},
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

def debate_data(msg: DebateMessage) -> dict[str, Any]:
    return {
        "agent_id": msg.agent_id,
        "street": _STREET_LABELS.get(msg.agent_id, msg.agent_id),
        "debate_text": msg.debate_text,
    }


# ── Verdict / recommendation (土地公裁決) ─────────────────────────────────────

def judgment_data(result: JudgmentResult) -> dict[str, Any]:
    itinerary_data = []
    for idx, stop in enumerate(result.itinerary):
        street_name = _STREET_LABELS.get(stop.agent_id, stop.agent_id)
        itinerary_data.append({
            "day": stop.day,
            "poi_name": stop.poi.name,
            "lat": stop.poi.location.lat,
            "lng": stop.poi.location.lng,
            "category": stop.poi.category,
            "note": stop.poi.note,
            "tags": stop.poi.tags,
            "stop_title": f"第 {stop.day} 天，第 {idx+1} 站：{stop.poi.name} ({street_name})",
            "stop_duration": f"停留 {stop.duration_mins} 分鐘",
            "stop_activity": stop.activity,
            "transit": f"前往下一站：{stop.transit_to_next}" if stop.transit_to_next else "本日行程結束"
        })

    return {
        "recommendation": result.recommendation,
        "reasoning": result.reasoning,
        "itinerary": itinerary_data,
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
         "children": ["verdict-title", "verdict-text", "itinerary-list"]},
        {"id": "verdict-title", "component": "Text", "text": "土地公為您安排的跨區行程", "variant": "h1"},
        {"id": "verdict-text", "component": "Text", "text": {"path": "/verdict/recommendation"}},
        {"id": "itinerary-list", "component": "List",
         "children": {"path": "/verdict/itinerary", "componentId": "itinerary-stop"}},
        
        {"id": "itinerary-stop", "component": "Card", "child": "itinerary-stop-col"},
        {"id": "itinerary-stop-col", "component": "Column",
         "children": ["stop-title", "stop-duration", "stop-activity", "stop-transit"]},
        {"id": "stop-title", "component": "Text", "text": {"path": "stop_title"}, "variant": "h2"},
        {"id": "stop-duration", "component": "Text", "text": {"path": "stop_duration"}, "variant": "caption"},
        {"id": "stop-activity", "component": "Text", "text": {"path": "stop_activity"}},
        {"id": "stop-transit", "component": "Text", "text": {"path": "transit"}, "variant": "caption"},
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


# ── Community Ask surface ────────────────────────────────────────────────────

from deg.schemas import CommunityAnswer, CommunityQueryResult  # noqa: E402

COMMUNITY_SURFACE_ID = "community"


def community_input_components() -> list[dict[str, Any]]:
    return [
        {"id": "root", "component": "Column",
         "children": ["community-title", "community-sub", "community-field", "community-submit"]},
        {"id": "community-title", "component": "Text",
         "text": "問土地公", "variant": "h1"},
        {"id": "community-sub", "component": "Text",
         "text": "有什麼社區大小事，都可以問土地公。活動、修繕、抱怨——神明一律收。",
         "variant": "caption"},
        {"id": "community-field", "component": "TextField",
         "label": "你想問什麼？（例如：最近有什麼活動？哪裡在施工？）",
         "value": {"path": "/community/question"}, "textFieldType": "text"},
        {"id": "community-submit-label", "component": "Text", "text": "叩問神明"},
        {"id": "community-submit", "component": "Button", "child": "community-submit-label",
         "variant": "primary",
         "checks": [{"condition": {"call": "required",
                                   "args": {"value": {"path": "/community/question"}}},
                     "message": "請先輸入你的問題"}],
         "action": {"event": {"name": "submit_community",
                              "context": {"question": {"path": "/community/question"}}}}},
    ]


def community_negotiation_components() -> list[dict[str, Any]]:
    """Stable skeleton after question submitted: question card + answer list + summary placeholder."""
    return [
        {"id": "root", "component": "Column",
         "children": ["community-q-card", "scouts-row", "answers-row", "community-summary-card"]},
        # — question recap —
        {"id": "community-q-card", "component": "Card", "child": "community-q-body"},
        {"id": "community-q-body", "component": "Column",
         "children": ["community-q-title", "community-q-text"]},
        {"id": "community-q-title", "component": "Text",
         "text": "土地公正在問各地神明…", "variant": "h2"},
        {"id": "community-q-text", "component": "Text", "text": {"path": "/community/question"}},
        # — scouts (前哨回報) —
        {"id": "scouts-row", "component": "List",
         "children": {"path": "/scouts", "componentId": "scout-card"}},
        {"id": "scout-card", "component": "Card", "child": "scout-card-body"},
        {"id": "scout-card-body", "component": "Column",
         "children": ["scout-card-street", "scout-card-score", "scout-card-reason"]},
        {"id": "scout-card-street", "component": "Text",
         "text": {"path": "street"}, "variant": "h2"},
        {"id": "scout-card-score", "component": "Text", "text": {"path": "confidence_score"}, "variant": "score"},
        {"id": "scout-card-reason", "component": "Text", "text": {"path": "reason"}},
        # — answers (data-bound List) —
        {"id": "answers-row", "component": "List",
         "children": {"path": "/answers", "componentId": "answer-card"}},
        {"id": "answer-card", "component": "Card", "child": "answer-card-body"},
        {"id": "answer-card-body", "component": "Column",
         "children": ["answer-card-street", "answer-card-text", "answer-card-sources"]},
        {"id": "answer-card-street", "component": "Text",
         "text": {"path": "street_name"}, "variant": "h2"},
        {"id": "answer-card-text", "component": "Text", "text": {"path": "answer_text"}},
        {"id": "answer-card-sources", "component": "Text",
         "text": {"path": "sources_label"}, "variant": "caption"},
        # — summary placeholder —
        {"id": "community-summary-card", "component": "Card", "child": "community-summary-wait"},
        {"id": "community-summary-wait", "component": "Text",
         "text": "靜待土地公彙整神諭…", "variant": "caption"},
    ]


def community_answer_data(answer: CommunityAnswer) -> dict[str, Any]:
    sources_label = "來源：" + "、".join(answer.sources) if answer.sources else ""
    return {
        "agent_id": answer.agent_id,
        "street_name": answer.street_name,
        "answer_text": answer.answer_text,
        "sources": answer.sources,
        "sources_label": sources_label,
    }


def community_summary_components() -> list[dict[str, Any]]:
    """Redefine community-summary-card in place."""
    return [
        {"id": "community-summary-card", "component": "Card", "child": "community-summary-body"},
        {"id": "community-summary-body", "component": "Column",
         "children": ["community-summary-title", "community-summary-text"]},
        {"id": "community-summary-title", "component": "Text",
         "text": "土地公的神諭總結", "variant": "h1"},
        {"id": "community-summary-text", "component": "Text",
         "text": {"path": "/community/tudigong_summary"}, "variant": "h2"},
    ]


def community_summary_data(result: CommunityQueryResult) -> dict[str, Any]:
    return {"tudigong_summary": result.tudigong_summary}


# ── 里長大會 (Council) surface ────────────────────────────────────────────────

from deg.schemas import CouncilStatement, CouncilVerdict  # noqa: E402
from deg.seed.loader import LiAgentData  # noqa: E402

COUNCIL_SURFACE_ID = "council"

_STANCE_LABELS = {
    "support": "附議",
    "oppose": "反駁",
    "question": "提問",
    "inform": "補充",
    "silent": "",
}


def council_input_components() -> list[dict[str, Any]]:
    return [
        {"id": "root", "component": "Column",
         "children": ["council-title", "council-sub", "council-field", "council-submit"]},
        {"id": "council-title", "component": "Text",
         "text": "里長大會", "variant": "h1"},
        {"id": "council-sub", "component": "Text",
         "text": "丟一個議題，讓中西區相關的里坐下來吵——啊不是，是好好討論。土地公當主席。",
         "variant": "caption"},
        {"id": "council-field", "component": "TextField",
         "label": "想開什麼大會？（例如：中西區要不要合辦一個共同的夜市活動？）",
         "value": {"path": "/council/topic"}, "textFieldType": "text"},
        {"id": "council-submit-label", "component": "Text", "text": "召開大會"},
        {"id": "council-submit", "component": "Button", "child": "council-submit-label",
         "variant": "primary",
         "checks": [{"condition": {"call": "required",
                                   "args": {"value": {"path": "/council/topic"}}},
                     "message": "請先輸入議題"}],
         "action": {"event": {"name": "submit_council",
                              "context": {"topic": {"path": "/council/topic"}}}}},
    ]


def council_assembly_components() -> list[dict[str, Any]]:
    """Live layout: topic recap + reactive map + transcript list + verdict placeholder."""
    return [
        {"id": "root", "component": "Column",
         "children": ["council-topic-card", "council-map", "transcript-row", "council-verdict-card"]},
        # — topic recap —
        {"id": "council-topic-card", "component": "Card", "child": "council-topic-body"},
        {"id": "council-topic-body", "component": "Column",
         "children": ["council-topic-title", "council-topic-text"]},
        {"id": "council-topic-title", "component": "Text",
         "text": "里長大會進行中…", "variant": "h2"},
        {"id": "council-topic-text", "component": "Text", "text": {"path": "/council/topic"}},
        # — reactive map (page decorate hook replaces this id with <CouncilMap>) —
        {"id": "council-map", "component": "Text",
         "text": "展開神界輿圖…", "variant": "caption"},
        # — transcript (data-bound List) —
        {"id": "transcript-row", "component": "List",
         "children": {"path": "/statements", "componentId": "statement-card"}},
        {"id": "statement-card", "component": "Card", "child": "statement-card-body"},
        {"id": "statement-card-body", "component": "Column",
         "children": ["statement-card-head", "statement-card-text", "statement-card-sources"]},
        {"id": "statement-card-head", "component": "Text",
         "text": {"path": "head_label"}, "variant": "h2"},
        {"id": "statement-card-text", "component": "Text", "text": {"path": "statement_text"}},
        {"id": "statement-card-sources", "component": "Text",
         "text": {"path": "sources_label"}, "variant": "caption"},
        # — verdict placeholder —
        {"id": "council-verdict-card", "component": "Card", "child": "council-verdict-wait"},
        {"id": "council-verdict-wait", "component": "Text",
         "text": "靜待土地公裁示…", "variant": "caption"},
    ]


def council_statement_data(s: CouncilStatement) -> dict[str, Any]:
    """One transcript row. head_label shows street + stance; map reads stance/responds_to."""
    stance_label = _STANCE_LABELS.get(s.stance, "")
    head_label = f"{s.street_name}　{stance_label}" if stance_label else s.street_name
    sources_label = "來源：" + "、".join(s.sources) if s.sources else ""
    return {
        "agent_id": s.agent_id,
        "street_name": s.street_name,
        "round": s.round,
        "stance": s.stance,
        "responds_to": s.responds_to,
        "statement_text": s.statement_text,
        "sources": s.sources,
        "head_label": head_label,
        "sources_label": sources_label,
    }


def council_boundary_payload(selected_li: list[LiAgentData]) -> list[dict[str, Any]]:
    """Boundary polygons for the participating 里 — what <CouncilMap> draws.

    NGSI-LD stores coordinates as [lng, lat]; Leaflet wants [lat, lng], so swap.
    """
    payload: list[dict[str, Any]] = []
    for li in selected_li:
        sb = li.spatial_boundary
        if not (sb and sb.value and getattr(sb.value, "type", None) == "Polygon"):
            continue
        ring = sb.value.coordinates[0]
        polygon = [[pt[1], pt[0]] for pt in ring]  # [lng,lat] -> [lat,lng]
        if not polygon:
            continue
        avg_lat = sum(p[0] for p in polygon) / len(polygon)
        avg_lng = sum(p[1] for p in polygon) / len(polygon)
        street = li.to_street()
        payload.append({
            "agent_id": street.agent_id,
            "street_name": street.name,
            "centroid": {"lat": avg_lat, "lng": avg_lng},
            "polygon": polygon,
        })
    return payload


def council_verdict_components() -> list[dict[str, Any]]:
    """Redefine council-verdict-card in place with the final 裁示."""
    return [
        {"id": "council-verdict-card", "component": "Card", "child": "council-verdict-body"},
        {"id": "council-verdict-body", "component": "Column",
         "children": ["council-verdict-title", "council-verdict-text"]},
        {"id": "council-verdict-title", "component": "Text",
         "text": "土地公的裁示", "variant": "h1"},
        {"id": "council-verdict-text", "component": "Text",
         "text": {"path": "/council/tudigong_summary"}, "variant": "h2"},
    ]


def council_verdict_data(v: CouncilVerdict) -> dict[str, Any]:
    """Verdict summary + per-里 alignments so the map can recolor to the consensus."""
    return {
        "tudigong_summary": v.tudigong_summary,
        "alignments": [
            {"agent_id": a.agent_id, "street_name": a.street_name, "final_stance": a.final_stance}
            for a in v.alignments
        ],
    }
