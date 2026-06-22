# 數位土地公 — M4: 巡境使 + 虎爺 (mock adapters + evidence integration)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 巡境使 (sensor/environment) and 虎爺 (social intel) as A2A servers backed by mock seed data. Update 地基主 to call them via ADK function tools during bidding, populating `BiddingProposal.evidence.sensor` and `evidence.social`. After M4 the full golden-path BiddingProposal carries real evidence from two specialist agents.

**Architecture:**
- `deg/adapters/` — mock adapters (pure Python, no LLM, read from seed JSON)
- `agents/xunjingshi/` — 巡境使: A2A server returning sensor summary string
- `agents/huye/` — 虎爺: A2A server returning social intel summary string
- `agents/dijizhu/agent.py` (updated) — adds two ADK function tools (`get_env_sensor`, `get_social_intel`) that call adapters locally; updates instruction to call them and fill `evidence`
- Seed data: `data/seed/sensor.json` and `data/seed/social.json` (already created)

**Why function tools (not A2A client calls) from 地基主:**
The 地基主 is an ADK LlmAgent. ADK function tools are the clean native way to give it capabilities. For M4 (mock), the tools call local adapter functions. In M5+ they can call real APIs or A2A servers via httpx — the adapter boundary makes this swap transparent to the LLM.

**a2a-sdk version:** v0.3.26 (same as M3). All v0.3 patterns apply.

---

## ⚠️ Prerequisites

1. M0–M3 complete (commits through `3d6da75`). 29 non-integration tests pass.
2. `data/seed/sensor.json` and `data/seed/social.json` already created.
3. a2a-sdk 0.3.26, uvicorn installed.

---

## File structure (created by this plan)

```
data/seed/
  sensor.json          # (ALREADY CREATED) mock environment data per street
  social.json          # (ALREADY CREATED) mock social intel per street
deg/
  adapters/
    __init__.py        # (NEW)
    sensor_adapter.py  # (NEW) get_sensor_summary(street_id) -> str
    social_adapter.py  # (NEW) get_social_summary(street_id) -> str
agents/
  xunjingshi/
    __init__.py        # (NEW)
    a2a_server.py      # (NEW) 巡境使 A2A server (port 9011)
  huye/
    __init__.py        # (NEW)
    a2a_server.py      # (NEW) 虎爺 A2A server (port 9012)
  dijizhu/
    agent.py           # (UPDATE) add get_env_sensor + get_social_intel tools
tests/
  test_adapters.py     # (NEW) unit tests for adapters
  test_xunjingshi_huye_a2a.py  # (NEW) unit tests for server build
  test_dijizhu_evidence_integration.py  # (NEW) @pytest.mark.integration
```

---

### Task 1: Mock adapters + 巡境使 + 虎爺 A2A servers

**Files:**
- Create: `deg/adapters/__init__.py`, `deg/adapters/sensor_adapter.py`, `deg/adapters/social_adapter.py`
- Create: `agents/xunjingshi/__init__.py`, `agents/xunjingshi/a2a_server.py`
- Create: `agents/huye/__init__.py`, `agents/huye/a2a_server.py`
- Create: `tests/test_adapters.py`, `tests/test_xunjingshi_huye_a2a.py`

- [ ] **Step 1: Write failing tests (TDD)**

Create `tests/test_adapters.py`:
```python
"""Unit tests for mock sensor and social adapters."""


def test_sensor_returns_string_for_shennong():
    from deg.adapters.sensor_adapter import get_sensor_summary
    result = get_sensor_summary("shennong")
    assert isinstance(result, str)
    assert len(result) > 5


def test_sensor_returns_string_for_all_streets():
    from deg.adapters.sensor_adapter import get_sensor_summary
    for street_id in ["shennong", "haian", "zhengxing"]:
        result = get_sensor_summary(street_id)
        assert isinstance(result, str) and len(result) > 5


def test_sensor_unknown_street_returns_fallback():
    from deg.adapters.sensor_adapter import get_sensor_summary
    result = get_sensor_summary("nowhere")
    assert isinstance(result, str)


def test_social_returns_string_for_shennong():
    from deg.adapters.social_adapter import get_social_summary
    result = get_social_summary("shennong")
    assert isinstance(result, str)
    assert len(result) > 5


def test_social_returns_string_for_all_streets():
    from deg.adapters.social_adapter import get_social_summary
    for street_id in ["shennong", "haian", "zhengxing"]:
        result = get_social_summary(street_id)
        assert isinstance(result, str) and len(result) > 5


def test_social_unknown_street_returns_fallback():
    from deg.adapters.social_adapter import get_social_summary
    result = get_social_summary("nowhere")
    assert isinstance(result, str)
```

Create `tests/test_xunjingshi_huye_a2a.py`:
```python
"""Unit tests for 巡境使 and 虎爺 A2A servers — card and app construction."""
import starlette.applications
from a2a.types import AgentCard


def test_xunjingshi_card_builds():
    from xunjingshi.a2a_server import build_xunjingshi_card
    card = build_xunjingshi_card()
    assert isinstance(card, AgentCard)
    assert card.name == "xunjingshi"
    assert "9011" in card.url


def test_xunjingshi_app_builds():
    from xunjingshi.a2a_server import build_xunjingshi_app
    app = build_xunjingshi_app()
    assert isinstance(app, starlette.applications.Starlette)


def test_huye_card_builds():
    from huye.a2a_server import build_huye_card
    card = build_huye_card()
    assert isinstance(card, AgentCard)
    assert card.name == "huye"
    assert "9012" in card.url


def test_huye_app_builds():
    from huye.a2a_server import build_huye_app
    app = build_huye_app()
    assert isinstance(app, starlette.applications.Starlette)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python -m pytest tests/test_adapters.py tests/test_xunjingshi_huye_a2a.py -q`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create adapter package**

Create `deg/adapters/__init__.py`:
```python
"""Mock adapters for 巡境使 (sensor) and 虎爺 (social) data sources."""
```

Create `deg/adapters/sensor_adapter.py`:
```python
"""巡境使 mock sensor adapter.

Reads from data/seed/sensor.json.
In production, swap this for a real sensor API call.
"""

from __future__ import annotations

import json
from pathlib import Path

_SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "seed" / "sensor.json"
_DATA: dict = {}


def _load() -> dict:
    global _DATA
    if not _DATA:
        _DATA = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    return _DATA


def get_sensor_summary(street_id: str) -> str:
    """Return a human-readable sensor summary for a street.

    Args:
        street_id: One of shennong, haian, zhengxing.

    Returns:
        A string description of current crowd/weather conditions.
    """
    data = _load()
    entry = data.get(street_id)
    if entry is None:
        return f"街廓 '{street_id}' 暫無感測資料（巡境使尚未巡至此處）"
    return entry["summary"]
```

Create `deg/adapters/social_adapter.py`:
```python
"""虎爺 mock social intel adapter.

Reads from data/seed/social.json.
In production, swap this for a real social media API call.
"""

from __future__ import annotations

import json
from pathlib import Path

_SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "seed" / "social.json"
_DATA: dict = {}


def _load() -> dict:
    global _DATA
    if not _DATA:
        _DATA = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    return _DATA


def get_social_summary(street_id: str) -> str:
    """Return a human-readable social intel summary for a street.

    Args:
        street_id: One of shennong, haian, zhengxing.

    Returns:
        A string description of recent social media activity and commercial buzz.
    """
    data = _load()
    entry = data.get(street_id)
    if entry is None:
        return f"街廓 '{street_id}' 暫無社群情報（虎爺尚未偵察到此處）"
    return entry["summary"]
```

- [ ] **Step 4: Create 巡境使 A2A server**

Create `agents/xunjingshi/__init__.py`:
```python
"""巡境使 (Scout) A2A server — real-time environment sensor agent."""

from . import a2a_server as a2a_server  # noqa: F401
```

Create `agents/xunjingshi/a2a_server.py`:
```python
"""巡境使 A2A server (a2a-sdk v0.3, mock sensor data, no LLM).

Returns real-time environment summary (crowd/weather) for a requested street.

Run:
    python -m xunjingshi.a2a_server    # port 9011
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_REPO_ROOT / ".env")

import starlette.applications  # noqa: E402
import uvicorn  # noqa: E402
from a2a.server.agent_execution import AgentExecutor, RequestContext  # noqa: E402
from a2a.server.apps import A2AStarletteApplication  # noqa: E402
from a2a.server.events import EventQueue  # noqa: E402
from a2a.server.request_handlers import DefaultRequestHandler  # noqa: E402
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater  # noqa: E402
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, Part, TextPart  # noqa: E402

from deg.adapters.sensor_adapter import get_sensor_summary  # noqa: E402

_PORT = 9011
_HOST = "127.0.0.1"


def build_xunjingshi_card() -> AgentCard:
    """Build the A2A AgentCard for 巡境使."""
    return AgentCard(
        name="xunjingshi",
        description="巡境使：台南中西區即時環境斥候，回報人流、天氣、交通狀況摘要。",
        version="1.0.0",
        url=f"http://{_HOST}:{_PORT}/",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="env_sensor",
                name="Environment Sensor",
                description="輸入 street_id，回傳該街廓的即時環境摘要（人流/天氣）",
                tags=["sensor", "environment", "tainan"],
                examples=["shennong", "haian", "zhengxing"],
            )
        ],
    )


class XunjingshiExecutor(AgentExecutor):
    """Returns mock sensor data for the requested street_id."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id,
            context_id=context.context_id,
        )
        await updater.submit()
        await updater.start_work()

        street_id = context.get_user_input().strip()
        summary = get_sensor_summary(street_id)

        await updater.add_artifact(
            parts=[Part(root=TextPart(text=summary))],
            name="sensor_summary",
        )
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id or "",
            context_id=context.context_id or "",
        )
        await updater.cancel()


def build_xunjingshi_app() -> starlette.applications.Starlette:
    """Build the Starlette A2A app for 巡境使."""
    card = build_xunjingshi_card()
    handler = DefaultRequestHandler(
        agent_executor=XunjingshiExecutor(),
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(agent_card=card, http_handler=handler).build()


if __name__ == "__main__":
    app = build_xunjingshi_app()
    uvicorn.run(app, host=_HOST, port=_PORT)
```

- [ ] **Step 5: Create 虎爺 A2A server**

Create `agents/huye/__init__.py`:
```python
"""虎爺 (Tiger General) A2A server — social & commercial intel agent."""

from . import a2a_server as a2a_server  # noqa: F401
```

Create `agents/huye/a2a_server.py`:
```python
"""虎爺 A2A server (a2a-sdk v0.3, mock social data, no LLM).

Returns social media / commercial intel summary for a requested street.

Run:
    python -m huye.a2a_server    # port 9012
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_REPO_ROOT / ".env")

import starlette.applications  # noqa: E402
import uvicorn  # noqa: E402
from a2a.server.agent_execution import AgentExecutor, RequestContext  # noqa: E402
from a2a.server.apps import A2AStarletteApplication  # noqa: E402
from a2a.server.events import EventQueue  # noqa: E402
from a2a.server.request_handlers import DefaultRequestHandler  # noqa: E402
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater  # noqa: E402
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, Part, TextPart  # noqa: E402

from deg.adapters.social_adapter import get_social_summary  # noqa: E402

_PORT = 9012
_HOST = "127.0.0.1"


def build_huye_card() -> AgentCard:
    """Build the A2A AgentCard for 虎爺."""
    return AgentCard(
        name="huye",
        description="虎爺：社群商機靈通者，整理社群媒體熱搜、打卡數與商業活力情報。",
        version="1.0.0",
        url=f"http://{_HOST}:{_PORT}/",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="social_intel",
                name="Social Intel",
                description="輸入 street_id，回傳該街廓的社群熱搜與商機摘要",
                tags=["social", "commercial", "tainan"],
                examples=["shennong", "haian", "zhengxing"],
            )
        ],
    )


class HuyeExecutor(AgentExecutor):
    """Returns mock social intel data for the requested street_id."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id,
            context_id=context.context_id,
        )
        await updater.submit()
        await updater.start_work()

        street_id = context.get_user_input().strip()
        summary = get_social_summary(street_id)

        await updater.add_artifact(
            parts=[Part(root=TextPart(text=summary))],
            name="social_summary",
        )
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id or "",
            context_id=context.context_id or "",
        )
        await updater.cancel()


def build_huye_app() -> starlette.applications.Starlette:
    """Build the Starlette A2A app for 虎爺."""
    card = build_huye_card()
    handler = DefaultRequestHandler(
        agent_executor=HuyeExecutor(),
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(agent_card=card, http_handler=handler).build()


if __name__ == "__main__":
    app = build_huye_app()
    uvicorn.run(app, host=_HOST, port=_PORT)
```

- [ ] **Step 6: Run all new unit tests**

```powershell
.\.venv\Scripts\python -m pytest tests/test_adapters.py tests/test_xunjingshi_huye_a2a.py -v
```
Expected: 10 tests pass (6 adapter + 4 A2A server).

- [ ] **Step 7: Run full non-integration suite + ruff**

```powershell
.\.venv\Scripts\python -m pytest -q -m "not integration"
.\.venv\Scripts\python -m ruff check deg tests agents conftest.py
```
Expected: 39 tests pass (29 + 10 new); ruff clean.

- [ ] **Step 8: Commit Task 1**

```powershell
git add data/seed/sensor.json data/seed/social.json deg/adapters agents/xunjingshi agents/huye tests/test_adapters.py tests/test_xunjingshi_huye_a2a.py
git commit -m "feat(adapters): add 巡境使+虎爺 mock adapters and A2A servers (sensor + social intel)"
```

---

### Task 2: Update 地基主 with evidence tools + integration test

**Files:**
- Modify: `agents/dijizhu/agent.py`
- Create: `tests/test_dijizhu_evidence_integration.py`

- [ ] **Step 1: Update `agents/dijizhu/agent.py`**

Read the current file first. Then make two changes:

**Change A: Add two function tools before `create_dijizhu()`.**

Add these functions after the `_MCP_MODULE` constant:
```python
def get_env_sensor(street_id: str) -> dict:
    """Returns the current environment/crowd/weather summary for a street.

    Args:
        street_id: One of: shennong, haian, zhengxing.
    """
    from deg.adapters.sensor_adapter import get_sensor_summary  # noqa: PLC0415
    return {"street_id": street_id, "sensor_summary": get_sensor_summary(street_id)}


def get_social_intel(street_id: str) -> dict:
    """Returns the social media and commercial buzz summary for a street.

    Args:
        street_id: One of: shennong, haian, zhengxing.
    """
    from deg.adapters.social_adapter import get_social_summary  # noqa: PLC0415
    return {"street_id": street_id, "social_summary": get_social_summary(street_id)}
```

**Change B: Update `create_dijizhu()` to add the new tools and extend the instruction.**

In `create_dijizhu()`:
1. Add `get_env_sensor` and `get_social_intel` to `tools=[toolset, get_env_sensor, get_social_intel]`.
2. Extend the instruction `【投標步驟】` — add steps 3 and 4, renumber the original 3-4 to 5-6:

Replace the instruction string inside `create_dijizhu()` with:
```
f"""你是「{street_name}」的地基主 (agent_id: {agent_id})，守護這條街道的神明管理員。

你的職責是：收到 TaskBroadcast JSON 後，調查轄區、蒐集情報、計算適配分數，回傳投標書（BiddingProposal）。

【投標步驟】
1. 呼叫 get_street_info("{street_id}") 了解你轄區的歷史與特色。
2. 根據 TaskBroadcast 的 constraints，呼叫 search_pois_by_constraints("{street_id}", constraints) 找候選地點。
   若 constraints 為空，改呼叫 get_street_pois("{street_id}") 取得所有 POI。
3. 呼叫 get_env_sensor("{street_id}") 取得即時環境情報（人流/天氣），放入 evidence.sensor。
4. 呼叫 get_social_intel("{street_id}") 取得社群熱搜情報，放入 evidence.social。
5. 評估適配度：考慮 POI 類型與需求符合程度、街廓特色、人情味、環境與社群加成，給出 fitness_score（0.0~10.0）。
6. 在 reasoning 欄位用繁體中文寫下你的投標理由，充分展現護航在地的自豪與性格。

【你的性格】
強烈的護航在地精神，充滿對自己街道的自豪感，語氣有神明威嚴但接地氣，
絕對不會推薦轄區以外的地方，永遠優先維護{street_name}的利益。

【回傳格式】必須回傳完整的 BiddingProposal JSON：
- agent_id: "{agent_id}"
- task_id: 從輸入 TaskBroadcast 取出
- fitness_score: 0.0~10.0
- reasoning: 繁體中文投標理由（至少 2 句）
- spatial_data: {{"lat": <centroid lat>, "lng": <centroid lng>}}（從 get_street_info 取得）
- tags: 你推薦的標籤列表
- candidate_pois: 符合條件的 POI 資料（含 name, category, location, tags, note）
- evidence: {{"sensor": <get_env_sensor 的 sensor_summary>, "social": <get_social_intel 的 social_summary>}}
- confidence: 0.0~1.0"""
```

- [ ] **Step 2: Verify import still works**

```powershell
.\.venv\Scripts\python -c "
import sys; sys.path.insert(0, 'agents')
from dijizhu.agent import create_dijizhu, root_agent
print(root_agent.name)
tools = [t.__name__ if callable(t) else type(t).__name__ for t in root_agent.tools]
print('tools:', tools)
"
```
Expected:
```
dijizhu_shennong
tools: ['get_env_sensor', 'get_social_intel', 'McpToolset']
```
(Order may vary; all three should appear.)

- [ ] **Step 3: Run full non-integration suite + ruff**

```powershell
.\.venv\Scripts\python -m pytest -q -m "not integration"
.\.venv\Scripts\python -m ruff check deg tests agents conftest.py
```
Expected: 39 tests pass; ruff clean.

- [ ] **Step 4: Create integration test**

Create `tests/test_dijizhu_evidence_integration.py`:
```python
"""Integration tests: 地基主 → MCP + sensor + social → BiddingProposal with evidence.

Skips automatically if GOOGLE_API_KEY is not set / is the placeholder.
Run explicitly:
    pytest tests/test_dijizhu_evidence_integration.py -v -m integration -s
"""

from __future__ import annotations

import os

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import ValidationError

from deg.schemas import BiddingProposal, LatLng, TaskBroadcast


def _require_api_key() -> None:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "paste_your_real_key_here":
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


@pytest.mark.integration
async def test_dijizhu_returns_evidence_in_proposal():
    """地基主 should call env_sensor + social_intel and populate BiddingProposal.evidence."""
    _require_api_key()

    from dijizhu.agent import create_dijizhu  # noqa: PLC0415

    agent = create_dijizhu("shennong", "神農街", "street_shennong_node")
    task = TaskBroadcast(
        task_id="evidence_test_001",
        intent="find_quiet_cafe",
        user_location=LatLng(lat=22.999, lng=120.222),
        constraints=["咖啡", "安靜"],
    )

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="deg", user_id="test_user", session_id="ev_s_001"
    )
    runner = Runner(agent=agent, app_name="deg", session_service=session_service)
    msg = types.Content(role="user", parts=[types.Part(text=task.model_dump_json())])

    final_text = ""
    async for event in runner.run_async(
        user_id="test_user", session_id="ev_s_001", new_message=msg
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text
            break

    assert final_text, "Agent produced no response"

    try:
        proposal = BiddingProposal.model_validate_json(final_text)
    except ValidationError as exc:
        pytest.fail(
            f"Response is not a valid BiddingProposal.\n"
            f"Raw response:\n{final_text}\n"
            f"Validation error:\n{exc}"
        )

    assert proposal.agent_id == "street_shennong_node"
    assert 0.0 <= proposal.fitness_score <= 10.0

    # Evidence should now be populated (sensor + social)
    assert proposal.evidence is not None, "evidence should be set — agent should call sensor + social tools"
    assert proposal.evidence.sensor is not None, "evidence.sensor should be populated by get_env_sensor"
    assert proposal.evidence.social is not None, "evidence.social should be populated by get_social_intel"
    assert len(proposal.evidence.sensor) > 5
    assert len(proposal.evidence.social) > 5
```

- [ ] **Step 5: Verify non-integration suite still passes and integration test skips cleanly**

```powershell
.\.venv\Scripts\python -m pytest -q -m "not integration"
.\.venv\Scripts\python -m pytest tests/test_dijizhu_evidence_integration.py -v -m integration -s
```
Expected:
- First: 39 passed (6 integration deselected).
- Second: SKIP with "GOOGLE_API_KEY not set".

- [ ] **Step 6: Ruff check**

```powershell
.\.venv\Scripts\python -m ruff check deg tests agents conftest.py
```
Expected: clean.

- [ ] **Step 7: Commit Task 2**

```powershell
git add agents/dijizhu/agent.py tests/test_dijizhu_evidence_integration.py
git commit -m "feat(agent): add env_sensor + social_intel tools to 地基主, populate BiddingProposal.evidence"
```

---

## Verification (end-to-end for M4)

```powershell
# Unit tests (no API key):
.\.venv\Scripts\python -m pytest -q -m "not integration"
# Expected: 39 passed

# Run 巡境使/虎爺 servers manually:
python -m xunjingshi.a2a_server   # port 9011
python -m huye.a2a_server         # port 9012

# Integration test (needs GOOGLE_API_KEY):
.\.venv\Scripts\python -m pytest tests/test_dijizhu_evidence_integration.py -v -m integration -s
# Expected: proposal.evidence.sensor and .social are non-empty strings
```

M4 complete: the golden-path BiddingProposal now carries `evidence.sensor` (巡境使 crowd/weather) and `evidence.social` (虎爺 social buzz). The 土地公's JudgmentResult can factor in this richer data.

---

## Self-Review

**Spec coverage (M4):**
- 巡境使 A2A server + mock sensor adapter ✓
- 虎爺 A2A server + mock social adapter ✓
- 地基主 gets `get_env_sensor` + `get_social_intel` ADK function tools ✓
- `BiddingProposal.evidence.sensor` and `.social` populated ✓
- Adapter boundary: swap to real APIs without changing LLM instruction ✓
- Unit tests: adapters + server builds, no API key ✓
- Integration test: evidence populated in real proposal ✓

**Out of scope (next plans):**
- 五營兵將 intent extraction (M5)
- FastAPI gateway + WebSocket (M5)
- Next.js Divine-Tech frontend (M6)
