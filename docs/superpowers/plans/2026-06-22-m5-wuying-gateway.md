# 數位土地公 — M5: 五營兵將 + FastAPI Gateway (WebSocket streaming)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 五營兵將 (intent extraction → `TaskBroadcast`) and a FastAPI gateway that orchestrates the full exploration golden path end-to-end: receive a citizen's natural-language intent + GPS → 五營兵將 extracts a `TaskBroadcast` → 土地公 in-process pipeline runs 3 地基主 bids + LLM-as-Judge → `JudgmentResult`. The gateway exposes a non-streaming REST endpoint and a WebSocket that streams each negotiation phase to the frontend (M6 will render these as A2UI surfaces).

**Architecture after M5:**
```
HTTP/WS client (curl / future Next.js)
        │  POST /intent  |  WS /ws/explore   {intent_text, lat, lng}
        ▼
FastAPI Gateway (apps/api/gateway.py)
   1. 五營兵將 LlmAgent (output_schema=TaskBroadcast)  ── intent → TaskBroadcast
   2. 土地公 create_pipeline() (in-process)            ── ParallelAgent(3×地基主) → judge
        │  streams phase / bid / judgment events
        ▼
   JudgmentResult JSON
```

**Why in-process pipeline:** The gateway runs everything in one process via `create_pipeline()` (M2), which already includes the M4 evidence tools. The remote A2A pipeline (`create_pipeline_remote`, M3) needs 5 servers started separately — that is a deployment concern, switchable later via a flag. M5's goal is one runnable gateway.

**Why gateway re-injects task_id + location:** 五營兵將 (an LLM) is reliable at *judgment* (classifying intent, extracting constraint keywords) but not at echoing exact floats / generating UUIDs. The gateway pre-generates `task_id` and overwrites `task_id` + `user_location` on the returned `TaskBroadcast` with the known-exact input values. The LLM owns `intent` + `constraints`; the gateway guarantees the data fields.

**a2a-sdk / ADK versions:** unchanged from M4 (a2a-sdk 0.3.26, google-adk 2.3.0). FastAPI 0.138, uvicorn 0.49, websockets 15 already installed transitively.

---

## ⚠️ Prerequisites

1. M0–M4 complete (commits through `a337a2c`). 39 non-integration tests pass.
2. `agents/tudigong/agent.py` has `create_pipeline() -> SequentialAgent`.
3. `deg/schemas` exports `TaskBroadcast`, `LatLng`, `JudgmentResult`.
4. `conftest.py` adds `agents/` to sys.path.

---

## File structure (created by this plan)

```
pyproject.toml                     # (UPDATE) add fastapi, uvicorn, websockets explicitly
agents/
  wuying/
    __init__.py                    # (NEW) from . import agent — required by adk run
    agent.py                       # (NEW) create_wuying() + root_agent
apps/
  __init__.py                      # (NEW)
  api/
    __init__.py                    # (NEW)
    gateway.py                     # (NEW) FastAPI app: GET /health, POST /intent, WS /ws/explore
tests/
  test_wuying_integration.py       # (NEW) @integration: intent → TaskBroadcast
  test_gateway.py                  # (NEW) unit: TestClient, app builds, routes, 422 — no LLM
  test_gateway_integration.py      # (NEW) @integration: full WS exploration flow
```

---

### Task 1: 五營兵將 intent-extraction agent

**Files:**
- Create: `agents/wuying/__init__.py`
- Create: `agents/wuying/agent.py`
- Create: `tests/test_wuying_integration.py`

- [ ] **Step 1: Create `agents/wuying/__init__.py`**

```python
"""五營兵將 ADK agent — 凡人意圖萃取為 TaskBroadcast.

Required by `adk run wuying` (ADK discovers agents through package import).
"""

from . import agent as agent  # noqa: F401 — re-exported for `adk run wuying`
```

- [ ] **Step 2: Create `agents/wuying/agent.py`**

```python
"""五營兵將 (Five Camp Soldiers) — 基層調查員 intent-extraction agent.

Takes a citizen's natural-language request and turns it into a TaskBroadcast
(Schema A) for 土地公 to broadcast in the Contract Net. No tools — pure extraction
with output_schema=TaskBroadcast.

Input message (JSON): {"raw_text": "...", "lat": 22.99, "lng": 120.22, "task_id": "..."}

Run interactively (from agents/ directory, needs GOOGLE_API_KEY in .env):
    adk run wuying
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_REPO_ROOT / ".env")

from google.adk.agents import LlmAgent  # noqa: E402

from deg.schemas import TaskBroadcast  # noqa: E402

_WUYING_INSTRUCTION = """你是五營兵將，土地公麾下的基層調查兵將，帶有神明威嚴的第一線探子。

你的職責：收到凡人的請求（自由文字 + GPS + task_id）後，將模糊的凡人語言翻譯成精確的招標單（TaskBroadcast）。

【輸入】一段 JSON，包含：
- raw_text: 凡人的自然語言請求（例如「找間安靜的老宅咖啡」）
- lat, lng: GPS 座標
- task_id: 預先產生的任務編號

【萃取步驟】
1. 從 raw_text 判斷使用者的核心意圖，歸納成一個簡短的英文 slug（例如 find_quiet_cafe、find_local_food、find_night_view）。
2. 從 raw_text 抽取所有約束關鍵字，放入 constraints 列表（中英混合皆可，例如 ["安靜", "老宅", "咖啡"]）。
3. task_id 與 user_location 必須原樣複製輸入值（不要自行更改數字）。
4. timeout_ms 設為 60000。

【回傳格式】必須回傳完整的 TaskBroadcast JSON：
- task_id: 原樣複製輸入的 task_id
- intent: 你歸納的英文 slug
- user_location: {"lat": <輸入 lat>, "lng": <輸入 lng>}
- constraints: 抽取的關鍵字列表
- timeout_ms: 60000"""


def create_wuying() -> LlmAgent:
    """Create the 五營兵將 intent-extraction agent."""
    return LlmAgent(
        name="wuying",
        model="gemini-flash-latest",
        description="五營兵將：基層調查兵將，將凡人語言意圖萃取為 TaskBroadcast。",
        instruction=_WUYING_INSTRUCTION,
        output_schema=TaskBroadcast,
    )


# Module-level root_agent required by `adk run wuying`.
root_agent = create_wuying()
```

- [ ] **Step 3: Verify import (no API key)**

```powershell
.\.venv\Scripts\python -c "import sys; sys.path.insert(0, 'agents'); from wuying.agent import create_wuying, root_agent; print(root_agent.name)"
```
Expected: `wuying`

- [ ] **Step 4: Create `tests/test_wuying_integration.py`**

```python
"""Integration test: 五營兵將 intent extraction → TaskBroadcast.

Skips if GOOGLE_API_KEY is not set / is the placeholder.
Run: pytest tests/test_wuying_integration.py -v -m integration -s
"""

from __future__ import annotations

import json
import os

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import ValidationError

from deg.schemas import TaskBroadcast


def _require_api_key() -> None:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "paste_your_real_key_here":
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


@pytest.mark.integration
async def test_wuying_extracts_task_broadcast():
    _require_api_key()

    from wuying.agent import create_wuying  # noqa: PLC0415

    agent = create_wuying()
    payload = json.dumps(
        {
            "raw_text": "我想找一間安靜的老宅咖啡，可以待整個下午",
            "lat": 22.999,
            "lng": 120.222,
            "task_id": "wuying_test_001",
        },
        ensure_ascii=False,
    )

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="deg", user_id="test_user", session_id="wy_s_001"
    )
    runner = Runner(agent=agent, app_name="deg", session_service=session_service)
    msg = types.Content(role="user", parts=[types.Part(text=payload)])

    final_text = ""
    async for event in runner.run_async(
        user_id="test_user", session_id="wy_s_001", new_message=msg
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text
            break

    assert final_text, "五營兵將 produced no response"

    try:
        tb = TaskBroadcast.model_validate_json(final_text)
    except ValidationError as exc:
        pytest.fail(f"Not a valid TaskBroadcast.\nRaw:\n{final_text}\nError:\n{exc}")

    assert tb.task_id == "wuying_test_001"
    assert len(tb.intent) > 0
    assert len(tb.constraints) >= 1, "should extract at least one constraint keyword"
```

- [ ] **Step 5: Run non-integration suite + ruff (integration auto-skips)**

```powershell
.\.venv\Scripts\python -m pytest -q -m "not integration"
.\.venv\Scripts\python -m ruff check deg tests agents conftest.py
```
Expected: 39 tests pass (the new integration test is deselected); ruff clean.

- [ ] **Step 6: Commit Task 1**

```powershell
git add agents/wuying tests/test_wuying_integration.py
git commit -m "feat(agent): add 五營兵將 intent-extraction agent (raw text -> TaskBroadcast)"
```

---

### Task 2: FastAPI Gateway (REST + WebSocket)

**Files:**
- Modify: `pyproject.toml`
- Create: `apps/__init__.py`, `apps/api/__init__.py`, `apps/api/gateway.py`
- Create: `tests/test_gateway.py`
- Create: `tests/test_gateway_integration.py`

- [ ] **Step 1: Update `pyproject.toml` — add web deps and include apps in test path**

Add to `[project]` `dependencies` (after `a2a-sdk`):
```toml
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "websockets>=12",
```
(All already installed transitively; this records them explicitly.)

- [ ] **Step 2: Write failing unit tests (TDD)**

Create `tests/test_gateway.py`:
```python
"""Unit tests for the FastAPI gateway — app/route construction, no LLM calls.

Uses TestClient. Agent construction at app-build time does NOT call the LLM,
so these run without an API key.
"""

from fastapi.testclient import TestClient


def _client() -> TestClient:
    from apps.api.gateway import create_app
    return TestClient(create_app())


def test_health_ok():
    client = _client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_intent_rejects_missing_fields():
    client = _client()
    resp = client.post("/intent", json={"intent_text": "找咖啡"})  # missing lat/lng
    assert resp.status_code == 422


def test_intent_rejects_bad_latlng():
    client = _client()
    resp = client.post(
        "/intent", json={"intent_text": "找咖啡", "lat": 999.0, "lng": 0.0}
    )
    assert resp.status_code == 422


def test_routes_registered():
    from apps.api.gateway import create_app
    app = create_app()
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/health" in paths
    assert "/intent" in paths
    assert "/ws/explore" in paths
```

Run to confirm failure: `.\.venv\Scripts\python -m pytest tests/test_gateway.py -q`
Expected: `ModuleNotFoundError: No module named 'apps'` (or import error).

- [ ] **Step 3: Create `apps/__init__.py` and `apps/api/__init__.py`**

`apps/__init__.py`:
```python
"""數位土地公 application layer (gateway, future workers)."""
```

`apps/api/__init__.py`:
```python
"""FastAPI gateway package."""
```

- [ ] **Step 4: Create `apps/api/gateway.py`**

```python
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

from deg.schemas import JudgmentResult, LatLng, TaskBroadcast  # noqa: E402
from tudigong.agent import create_pipeline  # noqa: E402
from wuying.agent import create_wuying  # noqa: E402

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

    return app


app = create_app()
```

- [ ] **Step 5: Run unit tests**

```powershell
.\.venv\Scripts\python -m pytest tests/test_gateway.py -v
```
Expected: 4 tests pass. No API key needed (app build + validation only).

If a test fails because app construction triggers an LLM call or a route path differs, fix the gateway. (Construction of LlmAgent / Runner does not call the LLM — verified throughout M1–M4.)

- [ ] **Step 6: Create `tests/test_gateway_integration.py`**

```python
"""Integration test: full exploration golden path over WebSocket.

Drives the gateway with FastAPI TestClient's WebSocket support.
Skips if GOOGLE_API_KEY is not set / is the placeholder. Expect 60–120s.
Run: pytest tests/test_gateway_integration.py -v -m integration -s
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


def _require_api_key() -> None:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "paste_your_real_key_here":
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


@pytest.mark.integration
def test_ws_exploration_full_flow():
    _require_api_key()

    from apps.api.gateway import create_app

    client = TestClient(create_app())
    seen_types: list[str] = []
    judgment = None

    with client.websocket_connect("/ws/explore") as ws:
        ws.send_json(
            {"intent_text": "找一間安靜的老宅咖啡", "lat": 22.999, "lng": 120.222}
        )
        while True:
            msg = ws.receive_json()
            seen_types.append(msg["type"])
            if msg["type"] == "judgment":
                judgment = msg["data"]
            if msg["type"] in ("done", "error"):
                break

    assert "error" not in seen_types, f"gateway errored; events={seen_types}"
    assert "task_broadcast" in seen_types
    assert "judgment" in seen_types
    assert "done" in seen_types
    assert judgment is not None
    assert judgment["winner_agent_id"] in {
        "street_shennong_node",
        "street_haian_node",
        "street_zhengxing_node",
    }
    assert len(judgment["ranked_agent_ids"]) == 3
```

- [ ] **Step 7: Verify non-integration suite + integration skips cleanly + ruff**

```powershell
.\.venv\Scripts\python -m pytest -q -m "not integration"
.\.venv\Scripts\python -m pytest tests/test_gateway_integration.py tests/test_wuying_integration.py -v -m integration -s
.\.venv\Scripts\python -m ruff check deg tests agents apps conftest.py
```
Expected:
- First: 43 tests pass (39 + 4 gateway unit tests).
- Second: both integration tests SKIP with "GOOGLE_API_KEY not set".
- Third: ruff clean.

- [ ] **Step 8: Commit Task 2**

```powershell
git add pyproject.toml apps tests/test_gateway.py tests/test_gateway_integration.py
git commit -m "feat(gateway): add FastAPI gateway (五營兵將 -> 土地公 pipeline) with REST + WebSocket streaming"
```

---

## Verification (end-to-end for M5)

```powershell
# Unit tests (no API key):
.\.venv\Scripts\python -m pytest -q -m "not integration"
# Expected: 43 passed

# Run the gateway (needs GOOGLE_API_KEY in .env):
.\.venv\Scripts\python -m uvicorn apps.api.gateway:app --port 8080
# Then in another shell:
#   curl http://127.0.0.1:8080/health
#   curl -X POST http://127.0.0.1:8080/intent -H "Content-Type: application/json" \
#        -d '{"intent_text":"找一間安靜的老宅咖啡","lat":22.999,"lng":120.222}'

# Integration tests (needs GOOGLE_API_KEY):
.\.venv\Scripts\python -m pytest tests/test_wuying_integration.py tests/test_gateway_integration.py -v -m integration -s
```

M5 complete: a citizen's natural-language intent flows through 五營兵將 → 土地公 pipeline → JudgmentResult, exposed over REST and a streaming WebSocket. The golden path is now reachable from a single HTTP entrypoint — ready for the M6 Next.js A2UI frontend to consume.

---

## Self-Review

**Spec coverage (M5):**
- 五營兵將 `LlmAgent` with `output_schema=TaskBroadcast` ✓
- FastAPI gateway: REST `POST /intent` (non-streaming) + WebSocket `/ws/explore` (streaming) ✓
- Full golden path wired in-process: intent → TaskBroadcast → 3 bids + judge → JudgmentResult ✓
- CORS enabled for the future frontend ✓
- Phase / task_broadcast / agent_event / judgment / done streaming envelope ✓
- Unit tests (no API key): health, 422 validation, route registration ✓
- Integration tests (auto-skip): 五營兵將 extraction + full WS flow ✓

**Design notes:**
- Gateway uses the **in-process** `create_pipeline()` (M2 + M4 evidence tools). Switching to `create_pipeline_remote()` (M3) is a future flag — not needed for a single runnable gateway.
- Gateway overwrites `task_id` + `user_location` post-extraction: the LLM owns intent/constraints judgment; the gateway guarantees exact data fields.

**Out of scope (next plans):**
- A2UI surface JSON instead of raw event envelopes (M6)
- Next.js Divine-Tech frontend + negotiation theater animation (M6)
- 許願 (Warm Data) flow + governance dashboard (M7)
