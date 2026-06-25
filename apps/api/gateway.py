"""FastAPI gateway for 數位土地公 — exploration golden path.

Pipeline per request:
    intent_text + GPS
      → 五營兵將 (LlmAgent)            → TaskBroadcast
      → 選派使者 (RouterAgent)         → RouterResult (Top N agents)
      → 土地公 create_dynamic_pipeline → ParallelAgent(N×地基主) + LLM-as-Judge
      → JudgmentResult

Endpoints:
    GET  /health        liveness probe
    POST /intent        non-streaming: returns the final JudgmentResult
    WS   /ws/explore    streaming: phase / task_broadcast / agent_event / judgment
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Awaitable, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)

_PIPELINE_TIMEOUT = 120.0  # seconds per full Contract Net round-trip
_WISH_TIMEOUT = 60.0
_PIPELINE_MAX_ATTEMPTS = 5
_PIPELINE_BACKOFF_CAP = 30  # seconds
_COUNCIL_MAX_ROUNDS = 3   # 里長大會 discussion rounds (cost cap; early-break on a silent round)
_COUNCIL_STAGGER = 0.6    # seconds between streaming each statement (搶話 theater)
_COUNCIL_SCOUT_TOP = 15   # max 里 joining the council (more = livelier, scout filters relevance)

# Repo root + agents/ on sys.path so agents import cleanly.
_REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (_REPO_ROOT, _REPO_ROOT / "agents"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_REPO_ROOT / ".env")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types as genai_types  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from deg.schemas import (  # noqa: E402
    BiddingProposal,
    Blessing,
    CommunityAnswer,
    CommunityQueryResult,
    CouncilStatement,
    CouncilVerdict,
    DebateMessage,
    DivinationReading,
    ItineraryStop,
    JudgmentResult,
    LatLng,
    Poi,
    TaskBroadcast,
    Wish,
    WishAnalysis,
    WuyingOutput,
)
from tudigong.agent import (  # noqa: E402
    create_community_judge,
    create_council_judge,
    create_dynamic_pipeline,
    create_refinement_judge,
    get_random_mood,
)
from dijizhu.agent import (  # noqa: E402
    create_community_agent,
    create_community_scout,
    create_council_speaker,
    create_scout,
)
from tudigong.blessing_agent import create_blessing_agent  # noqa: E402
from wuying.agent import create_wuying  # noqa: E402
from wuying.wish_agent import create_wish_categorizer  # noqa: E402
from divination.agent import build_divination_prompt, create_divination_agent  # noqa: E402

from deg.seed.geo import nearest_li  # noqa: E402
from deg.contracts_frontend import (  # noqa: E402
    bidding_to_agent_event,
    debate_to_agent_event,
    itinerary_to_days,
    poi_to_spot,
)
from deg.a2ui import create_surface, update_components, update_data_model  # noqa: E402
from deg.a2ui.surfaces import (  # noqa: E402
    SURFACE_ID,
    WISH_SURFACE_ID,
    COMMUNITY_SURFACE_ID,
    COUNCIL_SURFACE_ID,
    bid_data,
    debate_data,
    blessing_components,
    broadcast_data,
    clarification_components,
    community_answer_data,
    community_input_components,
    community_negotiation_components,
    community_summary_components,
    community_summary_data,
    council_assembly_components,
    council_boundary_payload,
    council_input_components,
    council_statement_data,
    council_verdict_components,
    council_verdict_data,
    intent_input_components,
    judgment_components,
    judgment_data,
    negotiation_components,
    wish_input_components,
)
from deg.warmdata import WarmDataStore  # noqa: E402

EventSink = Callable[[dict[str, Any]], Awaitable[None]]


class IntentRequest(BaseModel):
    intent_text: str = Field(min_length=1)
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)


class WishRequest(BaseModel):
    wish_text: str = Field(min_length=1)
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)
    photo_ref: str | None = None


class DivinationRequest(BaseModel):
    god_id: str = "tudigong"
    question: str = ""
    poe_result: str = "yin"   # sheng / yin / xiao
    weather: str | None = None


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    markers = ("503", "unavailable", "overload", "429", "resource_exhausted", "rate limit", "quota")
    if any(m in msg for m in markers):
        return True
    sub_exceptions = getattr(exc, "exceptions", None)
    if sub_exceptions:
        return any(_is_retryable(e) for e in sub_exceptions)
    return False


def _extract_json(text: str) -> str:
    if not text:
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text.strip()


async def _send_wuying_message(
    wuying_runner: Runner,
    session_service: InMemorySessionService,
    payload: str,
) -> WuyingOutput:
    for attempt in range(3):
        session_id = uuid4().hex
        await session_service.create_session(
            app_name="deg", user_id="gateway", session_id=session_id
        )
        msg = genai_types.Content(role="user", parts=[genai_types.Part(text=payload)])
        final_text = ""
        try:
            async for event in wuying_runner.run_async(
                user_id="gateway", session_id=session_id, new_message=msg
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    final_text = event.content.parts[0].text or ""
                    break
        except Exception as exc:
            if _is_retryable(exc) and attempt < 2:
                wait = 2 ** attempt
                logger.warning("五營兵將 503 (attempt %d), retry in %ds: %s", attempt + 1, wait, exc)
                await asyncio.sleep(wait)
                continue
            raise
        if not final_text:
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
                continue
            raise RuntimeError("五營兵將未能解析意圖，請再試一次。")
        try:
            return WuyingOutput.model_validate_json(_extract_json(final_text))
        except Exception as exc:
            if attempt < 2:
                logger.warning("五營兵將 JSON parse failed (attempt %d), retry: %s", attempt + 1, exc)
                await asyncio.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"五營兵將回傳格式有誤：{exc}") from exc
    raise RuntimeError("五營兵將未能解析意圖，請再試一次。")


def _wuying_payload(
    lat: float, lng: float, task_id: str,
    history: list[dict], force_ready: bool,
) -> str:
    return json.dumps(
        {"lat": lat, "lng": lng, "task_id": task_id,
         "force_ready": force_ready, "history": history},
        ensure_ascii=False,
    )


async def _run_wuying(
    wuying_runner: Runner,
    session_service: InMemorySessionService,
    intent_text: str,
    lat: float,
    lng: float,
    task_id: str,
) -> TaskBroadcast:
    payload = _wuying_payload(
        lat, lng, task_id,
        history=[{"role": "user", "text": intent_text}],
        force_ready=True,
    )
    output = await _send_wuying_message(wuying_runner, session_service, payload)
    if output.task_broadcast:
        tb = output.task_broadcast
        tb.task_id = task_id
        tb.user_location = LatLng(lat=lat, lng=lng)
        return tb
    raise RuntimeError("五營兵將未能生成招標令，請再試一次。")


async def _run_scout_round(
    session_service: InMemorySessionService,
    task: TaskBroadcast,
    on_event: EventSink | None,
) -> list[str]:
    if on_event:
        await on_event({"type": "phase", "phase": "routing", "message": "全體地基主前哨正在評估轄區資源..."})

    from deg.seed.loader import load_agents
    from google.adk.agents import ParallelAgent
    
    all_li = load_agents()
    scouts = []
    for li in all_li:
        street = li.to_street()
        scouts.append(create_scout(street.street_id, street.name, street.agent_id, li))
        
    scout_round_agent = ParallelAgent(
        name="scout_round",
        sub_agents=scouts,
    )
    
    scout_runner = Runner(agent=scout_round_agent, app_name="deg", session_service=session_service)
    session_id = uuid4().hex
    await session_service.create_session(app_name="deg", user_id="gateway", session_id=session_id)
    msg = genai_types.Content(role="user", parts=[genai_types.Part(text=task.model_dump_json())])

    from deg.schemas import ScoutResult
    
    results: list[ScoutResult] = []
    async for event in scout_runner.run_async(user_id="gateway", session_id=session_id, new_message=msg):
        if event.is_final_response() and event.content and event.content.parts:
            text = event.content.parts[0].text or ""
            try:
                res = ScoutResult.model_validate_json(_extract_json(text))
                results.append(res)
                if on_event:
                    await on_event({"type": "scout_result", "data": res})
            except Exception as e:
                logger.warning("Scout parsing failed: %s, text: %s", e, text)
                pass

    # Sort descending by confidence_score
    results.sort(key=lambda x: x.confidence_score, reverse=True)
    
    days = (task.travel_context.duration_days if task.travel_context else None) or 1
    select_count = max(5, days * 4)  # 4 agents per day gives enough POI variety
    top_agents = results[:select_count]
    if not top_agents:
        raise RuntimeError("所有地基主均放棄投標。")
        
    return [r.agent_id for r in top_agents]



async def _run_community_scout(
    session_service: InMemorySessionService,
    question: str,
    on_event: EventSink | None = None,
    top_n: int = 5,
) -> list[str]:
    from deg.seed.loader import load_agents
    from deg.schemas import ScoutResult
    from google.adk.agents import ParallelAgent

    all_li = load_agents()
    scouts = []
    for li in all_li:
        street = li.to_street()
        scouts.append(create_community_scout(street.street_id, street.name, street.agent_id, li))

    scout_round = ParallelAgent(name="community_scout_round", sub_agents=scouts)
    runner = Runner(agent=scout_round, app_name="deg", session_service=session_service)
    session_id = uuid4().hex
    await session_service.create_session(app_name="deg", user_id="gateway", session_id=session_id)
    msg = genai_types.Content(role="user", parts=[genai_types.Part(text=question)])

    results: list[ScoutResult] = []
    async for event in runner.run_async(user_id="gateway", session_id=session_id, new_message=msg):
        if event.is_final_response() and event.content and event.content.parts:
            text = event.content.parts[0].text or ""
            try:
                res = ScoutResult.model_validate_json(_extract_json(text))
                results.append(res)
                if on_event:
                    await on_event({"type": "scout_result", "data": res})
            except Exception as e:
                logger.warning("Community scout parse failed: %s", e)

    results.sort(key=lambda x: x.confidence_score, reverse=True)
    top = results[:top_n]
    if not top:
        raise RuntimeError("所有地基主均表示與問題無關。")
    return [r.agent_id for r in top]


async def _run_community_answers(
    session_service: InMemorySessionService,
    question: str,
    selected_agent_ids: list[str],
) -> list[CommunityAnswer]:
    from deg.seed.loader import load_agents
    from google.adk.agents import ParallelAgent

    all_li = {li.to_street().agent_id: li for li in load_agents()}
    agents = []
    for agent_id in selected_agent_ids:
        li = all_li.get(agent_id)
        if li is None:
            continue
        street = li.to_street()
        agents.append(create_community_agent(street.street_id, street.name, street.agent_id, li))

    if not agents:
        raise RuntimeError("無可用的地基主回答問題。")

    answer_round = ParallelAgent(name="community_answer_round", sub_agents=agents)
    runner = Runner(agent=answer_round, app_name="deg", session_service=session_service)
    session_id = uuid4().hex
    await session_service.create_session(app_name="deg", user_id="gateway", session_id=session_id)
    msg = genai_types.Content(role="user", parts=[genai_types.Part(text=question)])

    answers: list[CommunityAnswer] = []
    async for event in runner.run_async(user_id="gateway", session_id=session_id, new_message=msg):
        if event.is_final_response() and event.content and event.content.parts:
            text = event.content.parts[0].text or ""
            try:
                answer = CommunityAnswer.model_validate_json(_extract_json(text))
                answers.append(answer)
            except Exception as e:
                logger.warning("Community answer parse failed: %s", e)
    return answers


def _format_council_transcript(statements: list[CouncilStatement]) -> str:
    if not statements:
        return "（目前還沒有人發言）"
    lines = []
    for s in statements:
        tag = {"support": "附議", "oppose": "反駁", "question": "提問", "inform": "補充"}.get(s.stance, "")
        ref = f"（回應 {s.responds_to}）" if s.responds_to else ""
        lines.append(f"[第{s.round}輪｜{s.street_name}｜{tag}{ref}] {s.statement_text}")
    return "\n".join(lines)


async def _run_council_discussion(
    session_service: InMemorySessionService,
    topic: str,
    selected_agent_ids: list[str],
    on_statement: Callable[[CouncilStatement], Awaitable[None]] | None = None,
) -> list[CouncilStatement]:
    """Free-for-all 里長大會: each round every selected 里 sees the running transcript.

    Within a round speakers are parallel; across rounds they see prior turns.
    Non-silent statements are streamed via on_statement. Stops early if a whole
    round is silent.
    """
    from deg.seed.loader import load_agents
    from google.adk.agents import ParallelAgent

    all_li = {li.to_street().agent_id: li for li in load_agents()}
    resolved = [(aid, all_li[aid]) for aid in selected_agent_ids if aid in all_li]
    if not resolved:
        raise RuntimeError("無可用的地基主參與大會。")

    transcript: list[CouncilStatement] = []
    for r in range(1, _COUNCIL_MAX_ROUNDS + 1):
        speakers = []
        for _aid, li in resolved:
            street = li.to_street()
            speakers.append(create_council_speaker(street.street_id, street.name, street.agent_id, li))

        round_agent = ParallelAgent(name=f"council_round_{r}", sub_agents=speakers)
        runner = Runner(agent=round_agent, app_name="deg", session_service=session_service)
        session_id = uuid4().hex
        await session_service.create_session(app_name="deg", user_id="gateway", session_id=session_id)
        prompt = (
            f"【議題】{topic}\n\n"
            f"【目前討論記錄（逐字稿）】\n{_format_council_transcript(transcript)}\n\n"
            f"這是第 {r} 輪。請以你轄區的立場發言，或回 silent 把舞台讓給別人。"
        )
        msg = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])

        spoke_this_round = False
        async for event in runner.run_async(user_id="gateway", session_id=session_id, new_message=msg):
            if event.is_final_response() and event.content and event.content.parts:
                text = event.content.parts[0].text or ""
                try:
                    stmt = CouncilStatement.model_validate_json(_extract_json(text))
                except Exception as e:
                    logger.warning("Council statement parse failed: %s", e)
                    continue
                stmt.round = r
                if stmt.stance == "silent" or not stmt.statement_text.strip():
                    continue
                spoke_this_round = True
                transcript.append(stmt)
                if on_statement:
                    await on_statement(stmt)

        if not spoke_this_round:
            break

    return transcript


async def _run_pipeline(
    session_service: InMemorySessionService,
    task: TaskBroadcast,
    selected_agent_ids: list[str],
    on_event: EventSink | None,
) -> JudgmentResult:
    pipeline_runner = Runner(
        agent=create_dynamic_pipeline(selected_agent_ids), 
        app_name="deg", 
        session_service=session_service
    )
    
    session_id = uuid4().hex
    await session_service.create_session(
        app_name="deg", user_id="gateway", session_id=session_id
    )
    mood = get_random_mood()
    days = (task.travel_context.duration_days if task.travel_context else None) or 1
    day_banner = (
        f"\n\n【⚠️ 行程天數強制要求】旅人明確要求 {days} 天的行程。"
        f"itinerary 節點的 day 欄位必須從 1 到 {days}，"
        f"每天至少 3 個節點，絕對不得全部都是 day=1。"
    )
    msg_text = task.model_dump_json() + day_banner + f"\n\n【今日神明心情】{mood}"
    msg = genai_types.Content(
        role="user", parts=[genai_types.Part(text=msg_text)]
    )

    names = _agent_name_map()
    final_text = ""
    async for event in pipeline_runner.run_async(
        user_id="gateway", session_id=session_id, new_message=msg
    ):
        author = getattr(event, "author", None)
        if event.content and event.content.parts:
            text = event.content.parts[0].text or ""
            # The 土地公 judge's final output is the JudgmentResult JSON — capture it,
            # never surface it as chat. 地基主 bid/debate JSON → readable agent_event.
            if event.is_final_response() and author == "tudigong_judge" and text:
                final_text = text
            elif text and on_event is not None:
                ev = _readable_agent_event(text, names)
                if ev is not None:
                    await on_event(ev)
            if event.is_final_response() and text and not final_text:
                final_text = text

    if not final_text:
        raise RuntimeError("土地公未能作出裁決，請再試一次。")
    try:
        return JudgmentResult.model_validate_json(_extract_json(final_text))
    except Exception as exc:
        raise RuntimeError(f"土地公裁決格式有誤：{exc}") from exc


# ── Frontend conversational explore: shared helpers ──────────────────────────

_AGENT_NAME_CACHE: dict[str, str] | None = None


def _agent_name_map() -> dict[str, str]:
    """Cached {agent_id: 里名} for labelling chat dialogue with real 里 names."""
    global _AGENT_NAME_CACHE
    if _AGENT_NAME_CACHE is None:
        from deg.seed.loader import load_agents
        m: dict[str, str] = {}
        for li in load_agents():
            street = li.to_street()
            m[street.agent_id] = street.name
        _AGENT_NAME_CACHE = m
    return _AGENT_NAME_CACHE


def _readable_agent_event(text: str, names: dict[str, str]) -> dict[str, Any] | None:
    """Turn a raw 地基主 event into a chat-friendly agent_event.

    Tries BiddingProposal then DebateMessage; falls back to extracting
    reasoning/debate_text directly from partial JSON so messages always surface.
    Drops only true garbage (JSON with no recognisable text field).
    """
    import json as _json
    stripped = text.strip()
    json_str = _extract_json(text)
    if "debate_text" in json_str:
        try:
            debate = DebateMessage.model_validate_json(json_str)
            return debate_to_agent_event(debate, names.get(debate.agent_id, debate.agent_id))
        except Exception:
            pass
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            bid = BiddingProposal.model_validate_json(json_str)
            return bidding_to_agent_event(bid, names.get(bid.agent_id, bid.agent_id))
        except Exception:
            pass
        # Full validation failed — try extracting readable fields from partial JSON
        try:
            obj = _json.loads(json_str)
            if isinstance(obj, dict):
                agent_id = obj.get("agent_id", "")
                readable = (
                    obj.get("reasoning")
                    or obj.get("debate_text")
                    or obj.get("text")
                    or ""
                )
                if readable and agent_id:
                    return {
                        "type": "agent_event",
                        "agent": agent_id,
                        "agent_name": names.get(agent_id, agent_id),
                        "text": readable,
                    }
        except Exception:
            pass
        return None  # JSON with no readable field — never surface raw
    # Plain prose — pass through.
    return {"type": "agent_event", "agent": None, "agent_name": "", "text": text}


class _ExploreSession:
    """Per-connection conversational state for the 遊府城 chat → itinerary flow."""

    def __init__(self) -> None:
        self.task: TaskBroadcast | None = None
        self.task_id: str = ""
        self.itinerary: list[ItineraryStop] = []
        self.participating: set[str] = set()

    def days_payload(self) -> list[dict[str, Any]]:
        return itinerary_to_days(self.itinerary, _agent_name_map())


def _li_poi_pool(agent_ids: list[str]) -> list[dict[str, Any]]:
    """Candidate-POI pool (from layer_3 data) for the given 里, for the judge."""
    from deg.seed.loader import load_agents
    all_li = {li.to_street().agent_id: li for li in load_agents()}
    pool: list[dict[str, Any]] = []
    for aid in agent_ids:
        li = all_li.get(aid)
        if not li:
            continue
        street = li.to_street()
        pool.append({
            "agent_id": street.agent_id,
            "street_name": street.name,
            "pois": [
                {
                    "name": p.name,
                    "category": p.category,
                    "location": {"lat": p.location.lat, "lng": p.location.lng},
                    "note": p.note,
                }
                for p in street.pois
            ],
        })
    return pool


async def _run_refinement(
    session_service: InMemorySessionService,
    session: _ExploreSession,
    content: str,
    answers: list[CommunityAnswer],
    pool: list[dict[str, Any]],
) -> JudgmentResult:
    """土地公 incrementally revises the current itinerary for the user's new ask."""
    runner = Runner(
        agent=create_refinement_judge(), app_name="deg", session_service=session_service
    )
    sid = uuid4().hex
    await session_service.create_session(app_name="deg", user_id="gateway", session_id=sid)

    current = json.dumps([s.model_dump() for s in session.itinerary], ensure_ascii=False)
    comments = "\n".join(f"[{a.street_name}] {a.answer_text}" for a in answers) or "（無）"
    pool_json = json.dumps(pool, ensure_ascii=False)
    mood = get_random_mood()
    prompt = (
        f"task_id: {session.task_id or 'refine'}\n\n"
        f"【目前行程】\n{current}\n\n"
        f"【旅人的新需求】\n{content}\n\n"
        f"【相關里的意見】\n{comments}\n\n"
        f"【相關里的候選景點】\n{pool_json}\n\n"
        f"【今日神明心情】{mood}"
    )
    msg = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
    final = ""
    async for event in runner.run_async(user_id="gateway", session_id=sid, new_message=msg):
        if event.is_final_response() and event.content and event.content.parts:
            final = event.content.parts[0].text or ""
    if not final:
        raise RuntimeError("土地公未能調整行程，請再試一次。")
    return JudgmentResult.model_validate_json(_extract_json(final))


def _remove_stop(itinerary: list[ItineraryStop], item_id: str) -> ItineraryStop | None:
    """Remove the stop matching a frontend item id `stop-{day}-{order}` (1-based)."""
    parts = item_id.split("-") if item_id else []
    if len(parts) != 3:
        return None
    try:
        day, order = int(parts[1]), int(parts[2])
    except ValueError:
        return None
    day_stops = [s for s in itinerary if (s.day or 1) == day]
    if 1 <= order <= len(day_stops):
        target = day_stops[order - 1]
        itinerary.remove(target)
        return target
    return None


def _replacement_suggestions(
    removed: ItineraryStop, itinerary: list[ItineraryStop], k: int = 3
) -> list[dict[str, Any]]:
    """Real alternative POIs nearest the removed stop, excluding ones already in plan."""
    from deg.seed.loader import load_agents

    used = {(s.poi.name, round(s.poi.location.lat, 5), round(s.poi.location.lng, 5))
            for s in itinerary}
    names = _agent_name_map()
    rlat, rlng = removed.poi.location.lat, removed.poi.location.lng
    candidates: list[tuple[float, str, Any]] = []
    for li in load_agents():
        street = li.to_street()
        for p in street.pois:
            key = (p.name, round(p.location.lat, 5), round(p.location.lng, 5))
            if key in used or p.name == removed.poi.name:
                continue
            d = (p.location.lat - rlat) ** 2 + (p.location.lng - rlng) ** 2
            candidates.append((d, street.agent_id, p))
    candidates.sort(key=lambda c: c[0])
    out: list[dict[str, Any]] = []
    for _d, aid, p in candidates[:k]:
        village = names.get(aid, "台南市")
        out.append({
            "spot": poi_to_spot(p, village),
            "reason": f"離原地點不遠的{village}好去處",
            "tags": list(p.tags) + ([p.category] if p.category else []),
        })
    return out


def _find_poi_by_spot_id(spot_id: str) -> tuple[str, Poi] | None:
    """Resolve a frontend spot id (`{village}-{name}`) back to (agent_id, Poi)."""
    from deg.seed.loader import load_agents
    names = _agent_name_map()
    for li in load_agents():
        street = li.to_street()
        for p in street.pois:
            if f"{street.name}-{p.name}" == spot_id or p.name == spot_id:
                return street.agent_id, p
    _ = names
    return None


def _nearby_li_payload(lat: float, lng: float, n: int = 3) -> list[dict]:
    """Return serialisable nearby-li context for the wish categoriser."""
    results = nearest_li(lat=lat, lng=lng, n=n)
    out = []
    for li, dist_m in results:
        activities_raw = li.layer_2_dynamic_activities
        opinions_raw = li.layer_4_citizen_opinions
        out.append({
            "street_name": li.metadata.agent_name,
            "distance_m": round(dist_m),
            "activities": activities_raw.get("value", []) if isinstance(activities_raw, dict) else [],
            "opinions": opinions_raw.get("value", []) if isinstance(opinions_raw, dict) else [],
        })
    return out


async def _process_wish(
    wish_runner: Runner,
    blessing_runner: Runner,
    warm_store: WarmDataStore,
    session_service: InMemorySessionService,
    wish_text: str,
    lat: float,
    lng: float,
    photo_ref: str | None,
) -> tuple[Wish, WishAnalysis, Blessing]:
    sid = uuid4().hex
    await session_service.create_session(app_name="deg", user_id="gateway", session_id=sid)
    nearby = _nearby_li_payload(lat, lng)
    payload = json.dumps(
        {"raw_text": wish_text, "lat": lat, "lng": lng, "nearby_li": nearby},
        ensure_ascii=False,
    )
    msg = genai_types.Content(role="user", parts=[genai_types.Part(text=payload)])
    analysis_text = ""
    async for event in wish_runner.run_async(user_id="gateway", session_id=sid, new_message=msg):
        if event.is_final_response() and event.content and event.content.parts:
            analysis_text = event.content.parts[0].text
            break
    if not analysis_text:
        raise RuntimeError("五營兵將未能分析心願，請再試一次。")
    try:
        analysis = WishAnalysis.model_validate_json(_extract_json(analysis_text))
    except Exception as exc:
        raise RuntimeError(f"心願分析格式有誤：{exc}") from exc

    wish = Wish(
        wish_id=uuid4().hex, raw_text=wish_text, category=analysis.category,
        location=LatLng(lat=lat, lng=lng), photo_ref=photo_ref, status="received",
        summary=analysis.summary, sentiment=analysis.sentiment, tags=list(analysis.tags),
    )
    warm_store.add_wish(wish)

    sid2 = uuid4().hex
    await session_service.create_session(app_name="deg", user_id="gateway", session_id=sid2)
    bpayload = json.dumps(
        {"raw_text": wish_text, "category": analysis.category, "summary": analysis.summary},
        ensure_ascii=False,
    )
    bmsg = genai_types.Content(role="user", parts=[genai_types.Part(text=bpayload)])
    blessing_text = ""
    async for event in blessing_runner.run_async(user_id="gateway", session_id=sid2, new_message=bmsg):
        if event.is_final_response() and event.content and event.content.parts:
            blessing_text = event.content.parts[0].text
            break
    if not blessing_text:
        raise RuntimeError("土地公祝福未能送達，請再試一次。")
    try:
        blessing = Blessing.model_validate_json(_extract_json(blessing_text))
    except Exception as exc:
        raise RuntimeError(f"土地公祝福格式有誤：{exc}") from exc
    return wish, analysis, blessing


def create_app() -> FastAPI:
    app = FastAPI(title="數位土地公 Gateway", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    session_service = InMemorySessionService()
    wuying_runner = Runner(
        agent=create_wuying(), app_name="deg", session_service=session_service
    )
    warm_store = WarmDataStore(os.environ.get("DEG_WARMDATA_DB") or None)
    wish_runner = Runner(
        agent=create_wish_categorizer(), app_name="deg", session_service=session_service
    )
    blessing_runner = Runner(
        agent=create_blessing_agent(), app_name="deg", session_service=session_service
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/intent")
    async def intent(req: IntentRequest) -> dict[str, Any]:
        task_id = uuid4().hex
        tb = await _run_wuying(
            wuying_runner, session_service, req.intent_text, req.lat, req.lng, task_id
        )
        selected_agent_ids = await _run_scout_round(session_service, tb, on_event=None)
        result = await _run_pipeline(session_service, tb, selected_agent_ids, on_event=None)
        return {
            "task_broadcast": tb.model_dump(),
            "judgment": result.model_dump(),
        }

    async def _explore_initial(ws: WebSocket, sink: EventSink, session: _ExploreSession,
                               req_data: dict[str, Any]) -> None:
        """First turn: full Contract Net (via swarm) → first itinerary draft."""
        req = IntentRequest.model_validate(req_data)
        await sink({"type": "phase", "phase": "intent_extraction",
                    "message": "五營兵將正在解析凡人意圖…"})
        task_id = uuid4().hex
        async with asyncio.timeout(_PIPELINE_TIMEOUT):
            tb = await _run_wuying(
                wuying_runner, session_service, req.intent_text, req.lat, req.lng, task_id,
            )
            session.task = tb
            session.task_id = tb.task_id
            await sink({"type": "task_broadcast", "data": tb.model_dump()})
            selected = await _run_scout_round(session_service, tb, on_event=sink)
            await sink({"type": "phase", "phase": "bidding",
                        "message": f"土地公向分數最高的 {len(selected)} 個候選里發出正式招標，地基主們開始投標…"})
            session.participating.update(selected)
            result = await _run_pipeline(session_service, tb, selected, on_event=sink)
        session.itinerary = list(result.itinerary)
        session.task_id = result.task_id or session.task_id
        if result.recommendation:
            await sink({"type": "verdict_text", "text": result.recommendation})
        await sink({"type": "itinerary_update", "data": session.days_payload()})

    async def _explore_chat(ws: WebSocket, sink: EventSink, session: _ExploreSession,
                            content: str) -> None:
        """Refinement turn: re-route to whoever is relevant now, mutate the itinerary."""
        if not session.itinerary and session.task is None:
            await sink({"type": "error", "message": "請先告訴土地公你的旅遊需求。"})
            return
        await sink({"type": "phase", "phase": "routing",
                    "message": "土地公請相關的里長來商量…"})
        async with asyncio.timeout(_PIPELINE_TIMEOUT):
            selected = await _run_community_scout(session_service, content, top_n=3)
            names = _agent_name_map()
            for aid in selected:
                nm = names.get(aid, aid)
                if aid not in session.participating:
                    session.participating.add(aid)
                    await sink({"type": "agent_join", "agent": aid, "agent_name": nm})
                await sink({"type": "agent_typing", "agent": aid})
            answers = await _run_community_answers(session_service, content, selected)
            for a in answers:
                await sink({"type": "agent_event", "agent": a.agent_id,
                            "agent_name": a.street_name, "text": a.answer_text})
            await sink({"type": "phase", "phase": "refining",
                        "message": "土地公正在調整行程…"})
            pool = _li_poi_pool(selected)
            result = await _run_refinement(session_service, session, content, answers, pool)
        session.itinerary = list(result.itinerary)
        if result.recommendation:
            await sink({"type": "verdict_text", "text": result.recommendation})
        await sink({"type": "itinerary_update", "data": session.days_payload()})

    async def _explore_remove(sink: EventSink, session: _ExploreSession, item_id: str) -> None:
        removed = _remove_stop(session.itinerary, item_id)
        await sink({"type": "itinerary_update", "data": session.days_payload()})
        if removed is not None:
            suggestions = _replacement_suggestions(removed, session.itinerary)
            await sink({"type": "replacement_suggestions",
                        "itemId": item_id, "suggestions": suggestions})

    async def _explore_replace(sink: EventSink, session: _ExploreSession,
                               item_id: str, new_spot_id: str) -> None:
        found = _find_poi_by_spot_id(new_spot_id)
        parts = item_id.split("-") if item_id else []
        if found and len(parts) == 3:
            agent_id, poi = found
            try:
                day, order = int(parts[1]), int(parts[2])
                day_stops = [s for s in session.itinerary if (s.day or 1) == day]
                if 1 <= order <= len(day_stops):
                    target = day_stops[order - 1]
                    target.poi = poi
                    target.agent_id = agent_id
            except ValueError:
                pass
        await sink({"type": "itinerary_update", "data": session.days_payload()})

    @app.websocket("/ws/explore")
    async def ws_explore(ws: WebSocket) -> None:
        await ws.accept()
        session = _ExploreSession()

        async def sink(msg: dict[str, Any]) -> None:
            await ws.send_json(msg)

        try:
            while True:
                incoming = await ws.receive_json()
                if not isinstance(incoming, dict):
                    continue
                mtype = incoming.get("type")
                try:
                    if mtype is None and "intent_text" in incoming:
                        await _explore_initial(ws, sink, session, incoming)
                    elif mtype == "chat":
                        content = (incoming.get("content") or "").strip()
                        if content:
                            await _explore_chat(ws, sink, session, content)
                    elif mtype == "remove_item":
                        await _explore_remove(sink, session, incoming.get("itemId", ""))
                    elif mtype == "replace_item":
                        await _explore_replace(
                            sink, session, incoming.get("itemId", ""),
                            incoming.get("newSpotId", ""),
                        )
                    elif mtype == "finalize_itinerary":
                        await sink({"type": "done"})
                    # unknown message types are ignored
                except TimeoutError:
                    await sink({"type": "error", "message": "神明降神逾時，請稍後再試。"})
                except Exception as exc:  # one bad turn shouldn't kill the conversation
                    logger.error("Explore turn error:\n%s", traceback.format_exc())
                    await sink({"type": "error", "message": str(exc)})
        except WebSocketDisconnect:
            return
        except Exception:
            logger.error("Explore socket error:\n%s", traceback.format_exc())
        finally:
            try:
                await ws.close()
            except Exception:
                pass

    @app.websocket("/ws/explore/a2ui")
    async def ws_explore_a2ui(ws: WebSocket) -> None:
        await ws.accept()
        try:
            await ws.send_json(create_surface(SURFACE_ID, send_data_model=True))
            await ws.send_json(update_components(SURFACE_ID, intent_input_components()))
            await ws.send_json(update_data_model(SURFACE_ID, "/intent", {"text": ""}))

            first_msg = await ws.receive_json()

            task_id = uuid4().hex
            tb: TaskBroadcast | None = None
            selected_agent_ids: list[str] = []

            if isinstance(first_msg, dict) and first_msg.get("task_broadcast"):
                try:
                    tb = TaskBroadcast.model_validate(first_msg["task_broadcast"])
                    task_id = tb.task_id or task_id
                except Exception:
                    tb = None  

            if tb is None:
                req = IntentRequest.model_validate(first_msg)
                history: list[dict] = [{"role": "user", "text": req.intent_text}]

                for round_n in range(4):
                    force_ready = round_n >= 3
                    payload = _wuying_payload(
                        req.lat, req.lng, task_id, history, force_ready,
                    )
                    async with asyncio.timeout(_PIPELINE_TIMEOUT):
                        output = await _send_wuying_message(
                            wuying_runner, session_service, payload
                        )

                    if output.status == "ready" and output.task_broadcast:
                        tb = output.task_broadcast
                        tb.task_id = task_id
                        tb.user_location = LatLng(lat=req.lat, lng=req.lng)
                        break

                    if output.question:
                        history.append({"role": "assistant", "question": output.question})
                        await ws.send_json({"a2uiPhase": "clarifying"})
                        await ws.send_json(
                            update_components(SURFACE_ID, clarification_components(output.question, round_n))
                        )
                        await ws.send_json(
                            update_data_model(SURFACE_ID, "/clarify",
                                             {"question": output.question, "answer": ""})
                        )
                        ans_data = await ws.receive_json()
                        answer = ans_data.get("answer_text", "")
                        history.append({"role": "user", "answer": answer})

            if tb is None:
                raise RuntimeError("五營兵將未能生成招標令，請再試一次。")
                
            await ws.send_json({"a2uiPhase": "routing"})
            await ws.send_json(update_components(SURFACE_ID, negotiation_components()))
            await ws.send_json(update_data_model(SURFACE_ID, "/broadcast", broadcast_data(tb)))
            await ws.send_json(update_data_model(SURFACE_ID, "/scouts", []))
            await ws.send_json(update_data_model(SURFACE_ID, "/bids", []))
            await ws.send_json(update_data_model(SURFACE_ID, "/debates", []))
            await ws.send_json({"a2uiResumeToken": tb.model_dump(mode="json")})

            scout_index = 0
            async def scout_sink(msg: dict[str, Any]) -> None:
                nonlocal scout_index
                if msg.get("type") == "scout_result":
                    from deg.a2ui.surfaces import scout_data
                    await ws.send_json(update_data_model(SURFACE_ID, f"/scouts/{scout_index}", scout_data(msg["data"])))
                    scout_index += 1

            selected_agent_ids = await _run_scout_round(session_service, tb, on_event=scout_sink)

            await ws.send_json({"a2uiPhase": "negotiating"})

            # Prepare dynamic pipeline
            pipeline_runner = Runner(
                agent=create_dynamic_pipeline(selected_agent_ids), 
                app_name="deg", 
                session_service=session_service
            )

            session_id = uuid4().hex
            await session_service.create_session(
                app_name="deg", user_id="gateway", session_id=session_id
            )
            mood = get_random_mood()
            msg_text = tb.model_dump_json() + f"\n\n【今日神明心情】{mood}"
            msg = genai_types.Content(
                role="user", parts=[genai_types.Part(text=msg_text)]
            )
            bid_index = 0
            debate_index = 0
            verdict_text = ""
            pipeline_error: str | None = None
            for _pipeline_attempt in range(_PIPELINE_MAX_ATTEMPTS):
                try:
                    async for event in pipeline_runner.run_async(
                        user_id="gateway", session_id=session_id, new_message=msg
                    ):
                        author = getattr(event, "author", None)
                        if not (event.content and event.content.parts):
                            continue
                        text = event.content.parts[0].text or ""
                        if not text:
                            continue
                        if author and author.startswith("dijizhu_") and event.is_final_response():
                            try:
                                json_str = _extract_json(text)
                                if "debate_text" in json_str:
                                    debate = DebateMessage.model_validate_json(json_str)
                                    await ws.send_json(
                                        update_data_model(SURFACE_ID, f"/debates/{debate_index}", debate_data(debate))
                                    )
                                    debate_index += 1
                                else:
                                    proposal = BiddingProposal.model_validate_json(json_str)
                                    await ws.send_json(
                                        update_data_model(SURFACE_ID, f"/bids/{bid_index}", bid_data(proposal))
                                    )
                                    bid_index += 1
                            except Exception:
                                continue
                        elif author == "tudigong_judge" and event.is_final_response():
                            verdict_text = text
                    break  
                except Exception as pipeline_exc:
                    if _is_retryable(pipeline_exc) and _pipeline_attempt < _PIPELINE_MAX_ATTEMPTS - 1:
                        wait = min(3 * (2 ** _pipeline_attempt), _PIPELINE_BACKOFF_CAP)
                        logger.warning(
                            "Pipeline rate-limited (attempt %d/%d), retry in %ds: %s",
                            _pipeline_attempt + 1, _PIPELINE_MAX_ATTEMPTS, wait, pipeline_exc,
                        )
                        bid_index = 0
                        debate_index = 0
                        verdict_text = ""
                        await ws.send_json({"a2uiPhase": "retrying"})
                        await ws.send_json(update_data_model(SURFACE_ID, "/bids", []))
                        await ws.send_json(update_data_model(SURFACE_ID, "/debates", []))
                        session_id = uuid4().hex
                        await session_service.create_session(
                            app_name="deg", user_id="gateway", session_id=session_id
                        )
                        await asyncio.sleep(wait)
                        await ws.send_json({"a2uiPhase": "negotiating"})
                        continue
                    pipeline_error = (
                        "神明降神時香火過旺（模型暫時繁忙），請稍後再試一次。"
                        if _is_retryable(pipeline_exc)
                        else str(pipeline_exc)
                    )
                    logger.error("Pipeline error:\n%s", traceback.format_exc())
                    break

            if verdict_text:
                try:
                    result = JudgmentResult.model_validate_json(_extract_json(verdict_text))
                    await ws.send_json(update_components(SURFACE_ID, judgment_components()))
                    await ws.send_json(
                        update_data_model(SURFACE_ID, "/verdict", judgment_data(result))
                    )
                except Exception:
                    pass  

            if pipeline_error and not verdict_text:
                await ws.send_json({"a2uiError": pipeline_error})
            else:
                await ws.send_json({"a2uiDone": True})
        except WebSocketDisconnect:
            return
        except TimeoutError:
            try:
                await ws.send_json({"a2uiError": "神明降神逾時，請稍後再試。"})
            except Exception:
                pass
        except Exception as exc:
            logger.error("WS handler error:\n%s", traceback.format_exc())
            try:
                await ws.send_json({"a2uiError": str(exc)})
            except Exception:
                pass
        finally:
            try:
                await ws.close()
            except Exception:
                pass

    @app.post("/wish")
    async def submit_wish(req: WishRequest) -> dict[str, Any]:
        wish, analysis, blessing = await _process_wish(
            wish_runner, blessing_runner, warm_store, session_service,
            req.wish_text, req.lat, req.lng, req.photo_ref,
        )
        return {
            "wish": wish.model_dump(mode="json"),
            "analysis": analysis.model_dump(),
            "blessing": blessing.model_dump(),
        }

    @app.get("/wishes")
    async def list_wishes(limit: int = 50) -> dict[str, Any]:
        return {"wishes": [w.model_dump(mode="json") for w in warm_store.list_wishes(limit)]}

    @app.get("/dashboard/summary")
    async def dashboard_summary() -> dict[str, Any]:
        return warm_store.summary()

    @app.websocket("/ws/wish/a2ui")
    async def ws_wish_a2ui(ws: WebSocket) -> None:
        await ws.accept()
        try:
            await ws.send_json(create_surface(WISH_SURFACE_ID, send_data_model=True))
            await ws.send_json(update_components(WISH_SURFACE_ID, wish_input_components()))
            await ws.send_json(update_data_model(WISH_SURFACE_ID, "/wish", {"text": ""}))

            req_data = await ws.receive_json()
            req = WishRequest.model_validate(req_data)
            async with asyncio.timeout(_WISH_TIMEOUT):
                wish, analysis, blessing = await _process_wish(
                    wish_runner, blessing_runner, warm_store, session_service,
                    req.wish_text, req.lat, req.lng, req.photo_ref,
                )
            await ws.send_json(update_components(WISH_SURFACE_ID, blessing_components()))
            await ws.send_json(update_data_model(WISH_SURFACE_ID, "/blessing", {
                "acknowledgment": blessing.acknowledgment,
                "blessing": blessing.blessing,
                "category": f"分類：{analysis.category}",
            }))
            await ws.send_json({"a2uiDone": True})
        except WebSocketDisconnect:
            return
        except TimeoutError:
            try:
                await ws.send_json({"a2uiError": "土地公正在忙碌，請稍後再試。"})
            except Exception:
                pass
        except Exception as exc:
            try:
                await ws.send_json({"a2uiError": str(exc)})
            except Exception:
                pass
        finally:
            try:
                await ws.close()
            except Exception:
                pass

    @app.websocket("/ws/ask/a2ui")
    async def ws_ask_a2ui(ws: WebSocket) -> None:
        await ws.accept()
        try:
            await ws.send_json(create_surface(COMMUNITY_SURFACE_ID, send_data_model=True))
            await ws.send_json(update_components(COMMUNITY_SURFACE_ID, community_input_components()))
            await ws.send_json(update_data_model(COMMUNITY_SURFACE_ID, "/community", {"question": ""}))

            req_data = await ws.receive_json()
            question: str = req_data.get("question", "").strip()
            if not question:
                await ws.send_json({"a2uiError": "請輸入問題"})
                return

            await ws.send_json({"a2uiPhase": "routing"})
            await ws.send_json(update_components(COMMUNITY_SURFACE_ID, community_negotiation_components()))
            await ws.send_json(update_data_model(COMMUNITY_SURFACE_ID, "/community/question", question))
            await ws.send_json(update_data_model(COMMUNITY_SURFACE_ID, "/scouts", []))
            await ws.send_json(update_data_model(COMMUNITY_SURFACE_ID, "/answers", []))

            scout_index = 0
            async def scout_sink(msg: dict[str, Any]) -> None:
                nonlocal scout_index
                if msg.get("type") == "scout_result":
                    from deg.a2ui.surfaces import scout_data
                    await ws.send_json(update_data_model(COMMUNITY_SURFACE_ID, f"/scouts/{scout_index}", scout_data(msg["data"])))
                    scout_index += 1

            selected_ids = await _run_community_scout(session_service, question, on_event=scout_sink)

            await ws.send_json({"a2uiPhase": "answering"})

            answers = await _run_community_answers(session_service, question, selected_ids)

            for i, answer in enumerate(answers):
                await ws.send_json(
                    update_data_model(COMMUNITY_SURFACE_ID, f"/answers/{i}", community_answer_data(answer))
                )

            judge_runner = Runner(
                agent=create_community_judge(), app_name="deg", session_service=session_service
            )
            session_id = uuid4().hex
            await session_service.create_session(app_name="deg", user_id="gateway", session_id=session_id)
            answers_text = "\n\n".join(
                f"[{a.street_name}] {a.answer_text}" for a in answers
            )
            judge_msg = genai_types.Content(
                role="user",
                parts=[genai_types.Part(
                    text=f"問題：{question}\n\n各地基主回答：\n{answers_text}"
                )],
            )
            verdict_text = ""
            async for event in judge_runner.run_async(
                user_id="gateway", session_id=session_id, new_message=judge_msg
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    verdict_text = event.content.parts[0].text or ""

            if verdict_text:
                try:
                    result = CommunityQueryResult.model_validate_json(_extract_json(verdict_text))
                    await ws.send_json(update_components(COMMUNITY_SURFACE_ID, community_summary_components()))
                    await ws.send_json(
                        update_data_model(COMMUNITY_SURFACE_ID, "/community", community_summary_data(result))
                    )
                except Exception as e:
                    logger.warning("Community judge parse failed: %s", e)

            await ws.send_json({"a2uiDone": True})
        except WebSocketDisconnect:
            return
        except Exception as exc:
            logger.error("Community WS error:\n%s", traceback.format_exc())
            try:
                await ws.send_json({"a2uiError": str(exc)})
            except Exception:
                pass
        finally:
            try:
                await ws.close()
            except Exception:
                pass

    @app.websocket("/ws/council/a2ui")
    async def ws_council_a2ui(ws: WebSocket) -> None:
        await ws.accept()
        try:
            await ws.send_json(create_surface(COUNCIL_SURFACE_ID, send_data_model=True))
            await ws.send_json(update_components(COUNCIL_SURFACE_ID, council_input_components()))
            await ws.send_json(update_data_model(COUNCIL_SURFACE_ID, "/council", {"topic": ""}))

            req_data = await ws.receive_json()
            topic: str = req_data.get("topic", "").strip()
            if not topic:
                await ws.send_json({"a2uiError": "請輸入議題"})
                return

            # 1) relevance selection (reuse the community scout)
            await ws.send_json({"a2uiPhase": "routing"})
            selected_ids = await _run_community_scout(session_service, topic, top_n=_COUNCIL_SCOUT_TOP)

            # 2) open the assembly: draw boundaries + empty transcript
            from deg.seed.loader import load_agents
            all_li = {li.to_street().agent_id: li for li in load_agents()}
            selected_li = [all_li[aid] for aid in selected_ids if aid in all_li]

            await ws.send_json({"a2uiPhase": "assembling"})
            await ws.send_json(update_components(COUNCIL_SURFACE_ID, council_assembly_components()))
            await ws.send_json(update_data_model(COUNCIL_SURFACE_ID, "/council/topic", topic))
            await ws.send_json(
                update_data_model(COUNCIL_SURFACE_ID, "/boundaries", council_boundary_payload(selected_li))
            )
            await ws.send_json(update_data_model(COUNCIL_SURFACE_ID, "/statements", []))

            # 3) discussion rounds — stream each statement (staggered for 搶話 feel)
            stream_index = 0

            async def on_statement(stmt: CouncilStatement) -> None:
                nonlocal stream_index
                await ws.send_json(
                    update_data_model(
                        COUNCIL_SURFACE_ID, f"/statements/{stream_index}", council_statement_data(stmt)
                    )
                )
                stream_index += 1
                await asyncio.sleep(_COUNCIL_STAGGER)

            statements = await _run_council_discussion(
                session_service, topic, selected_ids, on_statement=on_statement
            )

            # 4) 土地公 chair closes with a verdict + consensus alignments
            judge_runner = Runner(
                agent=create_council_judge(), app_name="deg", session_service=session_service
            )
            session_id = uuid4().hex
            await session_service.create_session(app_name="deg", user_id="gateway", session_id=session_id)
            judge_prompt = (
                f"【議題】{topic}\n\n"
                f"【完整討論逐字稿】\n{_format_council_transcript(statements)}"
            )
            judge_msg = genai_types.Content(role="user", parts=[genai_types.Part(text=judge_prompt)])
            verdict_text = ""
            async for event in judge_runner.run_async(
                user_id="gateway", session_id=session_id, new_message=judge_msg
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    verdict_text = event.content.parts[0].text or ""

            if verdict_text:
                try:
                    verdict = CouncilVerdict.model_validate_json(_extract_json(verdict_text))
                    vdata = council_verdict_data(verdict)
                    await ws.send_json(update_components(COUNCIL_SURFACE_ID, council_verdict_components()))
                    # Subpaths, not the whole /council object, so /council/topic survives.
                    await ws.send_json(
                        update_data_model(COUNCIL_SURFACE_ID, "/council/tudigong_summary",
                                          vdata["tudigong_summary"])
                    )
                    await ws.send_json(
                        update_data_model(COUNCIL_SURFACE_ID, "/council/alignments", vdata["alignments"])
                    )
                except Exception as e:
                    logger.warning("Council judge parse failed: %s", e)

            await ws.send_json({"a2uiDone": True})
        except WebSocketDisconnect:
            return
        except Exception as exc:
            logger.error("Council WS error:\n%s", traceback.format_exc())
            try:
                await ws.send_json({"a2uiError": str(exc)})
            except Exception:
                pass
        finally:
            try:
                await ws.close()
            except Exception:
                pass

    # ── 廟口議 Council — typed WS for the tainan-travel frontend ──────────────
    @app.websocket("/ws/council")
    async def ws_council(ws: WebSocket) -> None:
        await ws.accept()
        try:
            req_data = await ws.receive_json()
            topic: str = (req_data.get("topic") or "").strip()
            if not topic:
                await ws.send_json({"type": "error", "message": "請輸入議題"})
                return

            await ws.send_json({"type": "phase", "phase": "routing"})
            selected_ids = await _run_community_scout(
                session_service, topic, top_n=_COUNCIL_SCOUT_TOP
            )

            from deg.seed.loader import load_agents
            all_li = {li.to_street().agent_id: li for li in load_agents()}
            selected_li = [all_li[aid] for aid in selected_ids if aid in all_li]

            await ws.send_json({"type": "phase", "phase": "assembling"})
            await ws.send_json(
                {"type": "boundaries", "data": council_boundary_payload(selected_li)}
            )

            async def on_statement(stmt: CouncilStatement) -> None:
                await ws.send_json({
                    "type": "statement",
                    "data": {
                        "agent_id": stmt.agent_id,
                        "street_name": stmt.street_name,
                        "round": stmt.round,
                        "stance": stmt.stance,
                        "responds_to": stmt.responds_to,
                        "text": stmt.statement_text,
                        "sources": stmt.sources,
                    },
                })
                await asyncio.sleep(_COUNCIL_STAGGER)

            statements = await _run_council_discussion(
                session_service, topic, selected_ids, on_statement=on_statement
            )

            judge_runner = Runner(
                agent=create_council_judge(), app_name="deg", session_service=session_service
            )
            session_id = uuid4().hex
            await session_service.create_session(
                app_name="deg", user_id="gateway", session_id=session_id
            )
            judge_prompt = (
                f"【議題】{topic}\n\n"
                f"【完整討論逐字稿】\n{_format_council_transcript(statements)}"
            )
            judge_msg = genai_types.Content(role="user", parts=[genai_types.Part(text=judge_prompt)])
            verdict_text = ""
            async for event in judge_runner.run_async(
                user_id="gateway", session_id=session_id, new_message=judge_msg
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    verdict_text = event.content.parts[0].text or ""

            if verdict_text:
                try:
                    verdict = CouncilVerdict.model_validate_json(_extract_json(verdict_text))
                    await ws.send_json({
                        "type": "verdict",
                        "data": {
                            "topic": topic,
                            "tudigong_summary": verdict.tudigong_summary,
                            "alignments": [
                                {"agent_id": a.agent_id, "street_name": a.street_name,
                                 "final_stance": a.final_stance}
                                for a in verdict.alignments
                            ],
                        },
                    })
                except Exception as e:
                    logger.warning("Council typed judge parse failed: %s", e)

            await ws.send_json({"type": "done"})
        except WebSocketDisconnect:
            return
        except Exception as exc:
            logger.error("Council typed WS error:\n%s", traceback.format_exc())
            try:
                await ws.send_json({"type": "error", "message": str(exc)})
            except Exception:
                pass
        finally:
            try:
                await ws.close()
            except Exception:
                pass

    # ── Debug — verify imageUrl generation ────────────────────────────────────
    @app.get("/debug/spot-sample")
    async def debug_spot_sample() -> dict[str, Any]:
        """Returns a sample Spot to verify Street View key is wired correctly."""
        from deg.contracts_frontend import poi_to_spot
        from deg.schemas import LatLng, Poi
        sample = Poi(name="赤崁樓", category="古蹟", location=LatLng(lat=22.9972, lng=120.2028))
        spot = poi_to_spot(sample, "赤嵌里")
        has_key = bool(os.getenv("GOOGLE_MAPS_API_KEY", ""))
        return {"spot": spot, "maps_key_loaded": has_key}

    # ── 求吉籤 Fortune — one lot per 里, static data ──────────────────────────
    @app.get("/fortune/itinerary")
    async def fortune_itinerary() -> dict[str, Any]:
        import random as _random
        from deg.fortune_lots import FORTUNE_LOTS

        lot = _random.choice(FORTUNE_LOTS)
        return {"grade": lot["grade"], "poem": lot["poem"], "spots": lot["spots"]}

    # ── 問神明 Divination — a god's reading of a 擲筊 throw ───────────────────
    divination_runner = Runner(
        agent=create_divination_agent(), app_name="deg", session_service=session_service
    )

    @app.post("/divination")
    async def divination(req: DivinationRequest) -> dict[str, Any]:
        prompt = build_divination_prompt(req.god_id, req.question, req.poe_result, req.weather)
        sid = uuid4().hex
        await session_service.create_session(app_name="deg", user_id="gateway", session_id=sid)
        msg = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
        text = ""
        async with asyncio.timeout(_WISH_TIMEOUT):
            async for event in divination_runner.run_async(
                user_id="gateway", session_id=sid, new_message=msg
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    text = event.content.parts[0].text or ""
        if not text:
            raise RuntimeError("神明未給出指點，請再擲一次。")
        reading = DivinationReading.model_validate_json(_extract_json(text))
        return reading.model_dump()

    return app


app = create_app()
