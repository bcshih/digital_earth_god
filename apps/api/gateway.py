"""FastAPI gateway for 數位土地公 — exploration golden path.

Pipeline per request:
    intent_text + GPS
      → 五營兵將 (LlmAgent)            → TaskBroadcast
      → 土地公 create_pipeline()       → ParallelAgent(3×地基主) + LLM-as-Judge
      → JudgmentResult

Endpoints:
    GET  /health        liveness probe
    POST /intent        non-streaming: returns the final JudgmentResult
    WS   /ws/explore    streaming: phase / task_broadcast / agent_event / judgment

Run:
    uvicorn apps.api.gateway:app --reload --port 8080
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

# Repo root + agents/ on sys.path so wuying.agent / tudigong.agent import cleanly.
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
    JudgmentResult,
    LatLng,
    TaskBroadcast,
    Wish,
    WishAnalysis,
    WuyingOutput,
)
from tudigong.agent import create_pipeline, get_random_mood  # noqa: E402
from tudigong.blessing_agent import create_blessing_agent  # noqa: E402
from wuying.agent import create_wuying  # noqa: E402
from wuying.wish_agent import create_wish_categorizer  # noqa: E402

from deg.a2ui import create_surface, update_components, update_data_model  # noqa: E402
from deg.a2ui.surfaces import (  # noqa: E402
    SURFACE_ID,
    WISH_SURFACE_ID,
    bid_data,
    blessing_components,
    broadcast_data,
    clarification_components,
    intent_input_components,
    judgment_components,
    judgment_data,
    negotiation_components,
    wish_input_components,
)
from deg.warmdata import WarmDataStore  # noqa: E402

# Event callback type for streaming negotiation phases.
EventSink = Callable[[dict[str, Any]], Awaitable[None]]


class IntentRequest(BaseModel):
    """A citizen's exploration request."""

    intent_text: str = Field(min_length=1)
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)


class WishRequest(BaseModel):
    wish_text: str = Field(min_length=1)
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)
    photo_ref: str | None = None


def _is_retryable(exc: Exception) -> bool:
    """Return True for transient Gemini errors worth retrying (503, overload)."""
    msg = str(exc)
    return "503" in msg or "UNAVAILABLE" in msg or "overload" in msg.lower()


def _extract_json(text: str) -> str:
    """Isolate the outermost JSON object from an LLM response.

    Non-Gemini models (Qwen via DashScope) don't honour ADK output_schema as
    strictly as Gemini's native structured output, so they sometimes wrap the
    JSON in ```json fences or add prose/reasoning around it. Grabbing the span
    from the first '{' to the last '}' recovers the object in those cases.
    """
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
    """Run 五營兵將 in a FRESH session with explicit conversation history in payload.

    Retries up to 2 times on transient 503/UNAVAILABLE errors with exponential backoff.
    """
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
            # Qwen is non-deterministic — a one-off non-JSON reply should retry.
            if attempt < 2:
                logger.warning(
                    "五營兵將 JSON parse failed (attempt %d), retry: %s",
                    attempt + 1, exc,
                )
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
    """Single-shot 五營兵將 (force_ready=True). Used by POST /intent (non-interactive)."""
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


async def _run_pipeline(
    pipeline_runner: Runner,
    session_service: InMemorySessionService,
    task: TaskBroadcast,
    on_event: EventSink | None,
) -> JudgmentResult:
    """Run the 土地公 pipeline, streaming intermediate agent events; return the judgment.

    A random divine mood is appended to the message to give 土地公 per-request personality.
    """
    session_id = uuid4().hex
    await session_service.create_session(
        app_name="deg", user_id="gateway", session_id=session_id
    )
    mood = get_random_mood()
    msg_text = task.model_dump_json() + f"\n\n【今日神明心情】{mood}"
    msg = genai_types.Content(
        role="user", parts=[genai_types.Part(text=msg_text)]
    )

    final_text = ""
    async for event in pipeline_runner.run_async(
        user_id="gateway", session_id=session_id, new_message=msg
    ):
        author = getattr(event, "author", None)
        if event.content and event.content.parts:
            text = event.content.parts[0].text or ""
            if text and on_event is not None:
                await on_event(
                    {"type": "agent_event", "agent": author, "text": text}
                )
            if event.is_final_response() and text:
                final_text = text  # judge runs last → last final response is the verdict

    if not final_text:
        raise RuntimeError("土地公未能作出裁決，請再試一次。")
    try:
        return JudgmentResult.model_validate_json(_extract_json(final_text))
    except Exception as exc:
        raise RuntimeError(f"土地公裁決格式有誤：{exc}") from exc


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
    payload = json.dumps({"raw_text": wish_text, "lat": lat, "lng": lng}, ensure_ascii=False)
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
    """Build the gateway FastAPI app. Agent construction here does NOT call the LLM."""
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
    pipeline_runner = Runner(
        agent=create_pipeline(), app_name="deg", session_service=session_service
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
        result = await _run_pipeline(pipeline_runner, session_service, tb, on_event=None)
        return {
            "task_broadcast": tb.model_dump(),
            "judgment": result.model_dump(),
        }

    @app.websocket("/ws/explore")
    async def ws_explore(ws: WebSocket) -> None:
        await ws.accept()
        try:
            req_data = await ws.receive_json()
            req = IntentRequest.model_validate(req_data)

            async def sink(msg: dict[str, Any]) -> None:
                await ws.send_json(msg)

            task_id = uuid4().hex
            await sink(
                {
                    "type": "phase",
                    "phase": "intent_extraction",
                    "message": "五營兵將正在解析凡人意圖…",
                }
            )
            async with asyncio.timeout(_PIPELINE_TIMEOUT):
                tb = await _run_wuying(
                    wuying_runner,
                    session_service,
                    req.intent_text,
                    req.lat,
                    req.lng,
                    task_id,
                )
                await sink({"type": "task_broadcast", "data": tb.model_dump()})

                await sink(
                    {
                        "type": "phase",
                        "phase": "bidding",
                        "message": "土地公發出招標，地基主們開始投標…",
                    }
                )
                result = await _run_pipeline(
                    pipeline_runner, session_service, tb, on_event=sink
                )
            await sink({"type": "judgment", "data": result.model_dump()})
            await sink({"type": "done"})
        except WebSocketDisconnect:
            return
        except TimeoutError:
            try:
                await ws.send_json({"type": "error", "message": "神明降神逾時，請稍後再試。"})
            except Exception:
                pass
        except Exception as exc:  # surface errors to the client, then close
            try:
                await ws.send_json({"type": "error", "message": str(exc)})
            except Exception:
                pass
        finally:
            try:
                await ws.close()
            except Exception:
                pass

    @app.websocket("/ws/explore/a2ui")
    async def ws_explore_a2ui(ws: WebSocket) -> None:
        """Stream the golden path as STANDARD A2UI v0.9.1 JSONL messages.

        Sequence:
            createSurface(explore, sendDataModel=true)
            updateComponents(intent input)
            updateDataModel(/intent, {"text": ""})
            ← client sends {intent_text, lat, lng}

            [clarification loop, 0–3 rounds]
            {"a2uiPhase": "clarifying"}
            updateComponents(clarification surface)     # shows question + answer field
            updateDataModel(/clarify, {question, answer})
            ← client sends {answer_text}

            {"a2uiPhase": "negotiating"}
            updateComponents(negotiation skeleton)
            updateDataModel(/broadcast, ...)
            updateDataModel(/bids, [])
            per 地基主 bid: updateDataModel(/bids/<i>, bid_data)
            updateComponents(verdict)
            updateDataModel(/verdict, ...)
            {"a2uiDone": true}
        """
        await ws.accept()
        try:
            await ws.send_json(create_surface(SURFACE_ID, send_data_model=True))
            await ws.send_json(update_components(SURFACE_ID, intent_input_components()))
            await ws.send_json(update_data_model(SURFACE_ID, "/intent", {"text": ""}))

            req_data = await ws.receive_json()
            req = IntentRequest.model_validate(req_data)

            task_id = uuid4().hex
            # ── 五營兵將 clarification loop (max 3 questions) ──────────────────
            # Each round uses a FRESH ADK session but receives the full chat
            # history in the payload — this avoids multi-turn + output_schema
            # instability while still giving the LLM full context.
            history: list[dict] = [{"role": "user", "text": req.intent_text}]
            tb: TaskBroadcast | None = None

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

            await ws.send_json({"a2uiPhase": "negotiating"})
            await ws.send_json(update_components(SURFACE_ID, negotiation_components()))
            await ws.send_json(update_data_model(SURFACE_ID, "/broadcast", broadcast_data(tb)))
            await ws.send_json(update_data_model(SURFACE_ID, "/bids", []))

            # Run the pipeline; append a bid per 地基主, capture the judge verdict.
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
            verdict_text = ""
            pipeline_error: str | None = None
            for _pipeline_attempt in range(3):
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
                                proposal = BiddingProposal.model_validate_json(_extract_json(text))
                            except Exception:
                                continue
                            await ws.send_json(
                                update_data_model(SURFACE_ID, f"/bids/{bid_index}", bid_data(proposal))
                            )
                            bid_index += 1
                        elif author == "tudigong_judge" and event.is_final_response():
                            verdict_text = text
                    break  # pipeline finished without exception
                except Exception as pipeline_exc:
                    if _is_retryable(pipeline_exc) and _pipeline_attempt < 2:
                        wait = 2 ** _pipeline_attempt
                        logger.warning(
                            "Pipeline 503 (attempt %d), retry in %ds: %s",
                            _pipeline_attempt + 1, wait, pipeline_exc,
                        )
                        bid_index = 0
                        verdict_text = ""
                        # Re-create session for clean retry
                        session_id = uuid4().hex
                        await session_service.create_session(
                            app_name="deg", user_id="gateway", session_id=session_id
                        )
                        await asyncio.sleep(wait)
                        continue
                    pipeline_error = str(pipeline_exc)
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
                    pass  # best-effort — don't crash the WS if verdict parse fails

            if pipeline_error and not verdict_text:
                # Pipeline failed with no usable output — surface the error
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

    return app


app = create_app()
