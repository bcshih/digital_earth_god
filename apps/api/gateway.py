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

import json
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable
from uuid import uuid4

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

from deg.schemas import BiddingProposal, JudgmentResult, LatLng, TaskBroadcast  # noqa: E402
from tudigong.agent import create_pipeline  # noqa: E402
from wuying.agent import create_wuying  # noqa: E402

from deg.a2ui import create_surface, update_components, update_data_model  # noqa: E402
from deg.a2ui.surfaces import (  # noqa: E402
    SURFACE_ID,
    bid_data,
    broadcast_data,
    intent_input_components,
    judgment_components,
    judgment_data,
    negotiation_components,
)

# Event callback type for streaming negotiation phases.
EventSink = Callable[[dict[str, Any]], Awaitable[None]]


class IntentRequest(BaseModel):
    """A citizen's exploration request."""

    intent_text: str = Field(min_length=1)
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)


async def _run_wuying(
    wuying_runner: Runner,
    session_service: InMemorySessionService,
    intent_text: str,
    lat: float,
    lng: float,
    task_id: str,
) -> TaskBroadcast:
    """Run 五營兵將 to extract a TaskBroadcast, then guarantee exact task_id + location."""
    session_id = uuid4().hex
    await session_service.create_session(
        app_name="deg", user_id="gateway", session_id=session_id
    )
    payload = json.dumps(
        {"raw_text": intent_text, "lat": lat, "lng": lng, "task_id": task_id},
        ensure_ascii=False,
    )
    msg = genai_types.Content(role="user", parts=[genai_types.Part(text=payload)])

    final_text = ""
    async for event in wuying_runner.run_async(
        user_id="gateway", session_id=session_id, new_message=msg
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text
            break

    tb = TaskBroadcast.model_validate_json(final_text)
    # Trust the LLM for intent/constraints; guarantee the exact data fields.
    tb.task_id = task_id
    tb.user_location = LatLng(lat=lat, lng=lng)
    return tb


async def _run_pipeline(
    pipeline_runner: Runner,
    session_service: InMemorySessionService,
    task: TaskBroadcast,
    on_event: EventSink | None,
) -> JudgmentResult:
    """Run the 土地公 pipeline, streaming intermediate agent events; return the judgment."""
    session_id = uuid4().hex
    await session_service.create_session(
        app_name="deg", user_id="gateway", session_id=session_id
    )
    msg = genai_types.Content(
        role="user", parts=[genai_types.Part(text=task.model_dump_json())]
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

    return JudgmentResult.model_validate_json(final_text)


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
            updateComponents(intent input)              # prompt surface
            updateDataModel(/intent, {"text": ""})
            ← client sends {intent_text, lat, lng}
            updateComponents(negotiation skeleton)      # broadcast + bids List + verdict placeholder
            updateDataModel(/broadcast, ...)
            updateDataModel(/bids, [])
            per 地基主 bid: updateDataModel(/bids/<i>, bid_data)   # data append, no component msg
            updateComponents(verdict)                   # redefines verdict-card subtree in place
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
            tb = await _run_wuying(
                wuying_runner, session_service, req.intent_text, req.lat, req.lng, task_id
            )
            await ws.send_json(update_components(SURFACE_ID, negotiation_components()))
            await ws.send_json(update_data_model(SURFACE_ID, "/broadcast", broadcast_data(tb)))
            await ws.send_json(update_data_model(SURFACE_ID, "/bids", []))

            # Run the pipeline; append a bid per 地基主, capture the judge verdict.
            session_id = uuid4().hex
            await session_service.create_session(
                app_name="deg", user_id="gateway", session_id=session_id
            )
            msg = genai_types.Content(
                role="user", parts=[genai_types.Part(text=tb.model_dump_json())]
            )
            bid_index = 0
            verdict_text = ""
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
                        proposal = BiddingProposal.model_validate_json(text)
                    except Exception:
                        continue
                    await ws.send_json(
                        update_data_model(SURFACE_ID, f"/bids/{bid_index}", bid_data(proposal))
                    )
                    bid_index += 1
                elif author == "tudigong_judge" and event.is_final_response():
                    verdict_text = text

            if verdict_text:
                result = JudgmentResult.model_validate_json(verdict_text)
                await ws.send_json(update_components(SURFACE_ID, judgment_components()))
                await ws.send_json(update_data_model(SURFACE_ID, "/verdict", judgment_data(result)))

            await ws.send_json({"a2uiDone": True})
        except WebSocketDisconnect:
            return
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
