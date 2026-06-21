# 數位土地公 — M1: MCP Spatial-DB + 地基主 ADK Agent

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the FastMCP spatial-db server that serves the Tainan seed data, create the 地基主 ADK `LlmAgent` (神農街) that reads from it via `McpToolset`, and verify end-to-end that a `TaskBroadcast` JSON produces a valid `BiddingProposal` JSON.

**Architecture:** The MCP server (`deg/mcp/spatial_db/server.py`, inside the installed `deg` package) exposes three tools over stdio. The 地基主 (`agents/dijizhu/`) is an ADK `LlmAgent` with `McpToolset` that spawns the server as a subprocess. M1 is fully single-machine — no A2A networking yet (M3). `ParallelAgent` / 土地公 orchestration is M2. The `create_dijizhu(street_id, ...)` factory is written now and reused in M2 for all three streets.

**Tech Stack:** Python 3.11+, `mcp>=1.0` (FastMCP), `google-adk>=2.0`, `pytest-asyncio>=0.23`. Model: `gemini-flash-latest` via Google AI Studio (needs `GOOGLE_API_KEY`).

---

## ⚠️ Prerequisites

1. **API key:** Get a `GOOGLE_API_KEY` from [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
2. **`.env` file** at repo root (already gitignored): create it with the two lines shown in Task 1 Step 9.
3. The integration tests in Task 3 skip automatically if `GOOGLE_API_KEY` is missing — no API key is needed to complete Tasks 1 and 3's non-integration suite.

## ⚠️ McpToolset API surface — verify before Task 2

ADK's McpToolset API changes between patch releases. Before writing `agent.py`, run the import-check step at the start of Task 2 to confirm the exact class path and whether async context management is required. The plan shows the direct-assignment pattern from the ADK reference; if `async with McpToolset(...) as toolset:` is required, follow the adk.dev docs and report DONE_WITH_CONCERNS with what you changed.

---

## File structure (created by this plan)

```
.env                               # (NEW, gitignored) GOOGLE_API_KEY + GOOGLE_GENAI_USE_VERTEXAI
.env.example                       # (UPDATE) replace with ADK-compatible content
pyproject.toml                     # (UPDATE) add mcp, google-adk; add pytest-asyncio dev dep + asyncio_mode
conftest.py                        # (NEW, repo root) sys.path setup for agents/ + dotenv load
deg/
  mcp/
    __init__.py                    # (NEW)
    spatial_db/
      __init__.py                  # (NEW)
      server.py                    # (NEW) FastMCP: get_street_info, get_street_pois, search_pois_by_constraints
agents/
  dijizhu/
    __init__.py                    # (NEW) from . import agent  — required by adk run
    agent.py                       # (NEW) create_dijizhu() factory + root_agent = create_dijizhu("shennong")
tests/
  test_mcp_spatial_db.py           # (NEW) unit tests: tool functions, no LLM, no subprocess
  test_dijizhu_integration.py      # (NEW) @pytest.mark.integration: TaskBroadcast → BiddingProposal
```

**Responsibilities**
- `deg/mcp/spatial_db/server.py` — FastMCP server, pure read of seed data. Launched as subprocess by McpToolset. Also directly importable for unit tests.
- `agents/dijizhu/agent.py` — `create_dijizhu()` factory (parameterizable by street, reused in M2) + `root_agent` for `adk run`.
- `conftest.py` — adds `agents/` to `sys.path` so pytest imports `dijizhu.agent` the same way `adk run dijizhu` does.
- `tests/test_mcp_spatial_db.py` — calls tool functions directly (no subprocess, no API key).
- `tests/test_dijizhu_integration.py` — end-to-end with real LLM; skips without API key.

---

### Task 1: Dependencies + MCP spatial-db server

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env.example`
- Create: `.env` (gitignored — needs your real API key)
- Create: `conftest.py`
- Create: `deg/mcp/__init__.py`, `deg/mcp/spatial_db/__init__.py`, `deg/mcp/spatial_db/server.py`
- Test: `tests/test_mcp_spatial_db.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_mcp_spatial_db.py`:
```python
"""Unit tests for MCP spatial-db tool functions.

Call tool functions directly — no MCP subprocess, no LLM, no API key needed.
FastMCP's @mcp.tool() returns the original callable, so direct calls work.
"""

from deg.mcp.spatial_db.server import (
    get_street_info,
    get_street_pois,
    search_pois_by_constraints,
)


def test_get_street_info_shennong():
    result = get_street_info("shennong")
    assert result["street_id"] == "shennong"
    assert result["name"] == "神農街"
    assert result["agent_id"] == "street_shennong_node"
    assert "history" in result
    assert result["poi_count"] == 3


def test_get_street_info_unknown_returns_error():
    result = get_street_info("nowhere")
    assert "error_message" in result


def test_get_street_pois_structure():
    result = get_street_pois("shennong")
    pois = result["pois"]
    assert len(pois) == 3
    for p in pois:
        assert {"name", "category", "location", "tags", "note"} <= p.keys()
        assert {"lat", "lng"} <= p["location"].keys()


def test_search_pois_cafe_constraint():
    result = search_pois_by_constraints("shennong", ["cafe"])
    assert result["matching_count"] >= 1
    for p in result["matching_pois"]:
        text = " ".join([p["name"], p["category"], p.get("note", "")] + p.get("tags", []))
        assert "cafe" in text.lower() or "咖啡" in text


def test_search_pois_empty_constraints_returns_all():
    result = search_pois_by_constraints("haian", [])
    assert result["matching_count"] == result["total_pois"]


def test_all_three_streets_have_pois():
    for street_id in ["shennong", "haian", "zhengxing"]:
        result = get_street_pois(street_id)
        assert len(result["pois"]) >= 1, f"{street_id} has no POIs"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_mcp_spatial_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'deg.mcp'`

- [ ] **Step 3: Update `pyproject.toml`**

Replace the `[project]`, `[project.optional-dependencies]`, and `[tool.pytest.ini_options]` sections. All other sections remain unchanged.

```toml
[project]
name = "digital-earth-god"
version = "0.1.0"
description = "數位土地公 — MAS 微觀治理系統"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.6",
    "python-dotenv>=1.0",
    "mcp>=1.0",
    "google-adk>=2.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.4", "pytest-asyncio>=0.23"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
asyncio_mode = "auto"
markers = [
    "integration: requires GOOGLE_API_KEY and makes live LLM calls (slow)",
]
```

- [ ] **Step 4: Install updated deps**

Run: `.\.venv\Scripts\python -m pip install -e ".[dev]"`
Expected: `mcp`, `google-adk`, `google-genai`, `pytest-asyncio` all install cleanly.

- [ ] **Step 5: Create package markers**

Create `deg/mcp/__init__.py`:
```python
"""MCP servers for 數位土地公."""
```

Create `deg/mcp/spatial_db/__init__.py`:
```python
"""FastMCP spatial-db server package."""
```

- [ ] **Step 6: Create `deg/mcp/spatial_db/server.py`**

```python
"""FastMCP spatial-db server for 數位土地公.

Exposes the Tainan seed dataset as MCP tools for 地基主 agents.

Run standalone (blocks on stdio):
    python -m deg.mcp.spatial_db.server

Connect via ADK:
    McpToolset(connection_params=StdioServerParameters(
        command=sys.executable, args=["-m", "deg.mcp.spatial_db.server"]
    ))
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from deg.seed.loader import load_streets

mcp = FastMCP("deg-spatial-db", instructions="台南中西區空間資料庫 MCP 服務")  # mcp>=1.28 uses instructions=

# Index seed data once at import time (small, read-only, constant).
_STREETS = {s.street_id: s for s in load_streets()}


def _poi_to_dict(p) -> dict:
    return {
        "name": p.name,
        "category": p.category,
        "location": {"lat": p.location.lat, "lng": p.location.lng},
        "tags": p.tags,
        "note": p.note,
    }


@mcp.tool()
def get_street_info(street_id: str) -> dict:
    """Returns historical context and metadata for a street.

    Args:
        street_id: One of: shennong, haian, zhengxing.
    """
    st = _STREETS.get(street_id)
    if st is None:
        return {"error_message": f"Unknown street_id '{street_id}'. Valid: {list(_STREETS)}"}
    return {
        "street_id": st.street_id,
        "name": st.name,
        "agent_id": st.agent_id,
        "centroid": {"lat": st.centroid.lat, "lng": st.centroid.lng},
        "history": st.history,
        "poi_count": len(st.pois),
    }


@mcp.tool()
def get_street_pois(street_id: str) -> dict:
    """Returns all points of interest in a street.

    Args:
        street_id: One of: shennong, haian, zhengxing.
    """
    st = _STREETS.get(street_id)
    if st is None:
        return {"error_message": f"Unknown street_id '{street_id}'. Valid: {list(_STREETS)}"}
    return {"pois": [_poi_to_dict(p) for p in st.pois]}


@mcp.tool()
def search_pois_by_constraints(street_id: str, constraints: list[str]) -> dict:
    """Finds POIs in a street that match keyword constraints.

    Args:
        street_id: One of: shennong, haian, zhengxing.
        constraints: Keywords to match against name/category/note/tags (e.g. ["quiet", "安靜"]).
                     Empty list returns all POIs.
    """
    st = _STREETS.get(street_id)
    if st is None:
        return {"error_message": f"Unknown street_id '{street_id}'. Valid: {list(_STREETS)}"}

    lower = [c.lower() for c in constraints]

    def _matches(poi) -> bool:
        if not lower:
            return True
        haystack = " ".join([poi.name, poi.category, poi.note] + poi.tags).lower()
        return any(kw in haystack for kw in lower)

    matching = [p for p in st.pois if _matches(p)]
    return {
        "total_pois": len(st.pois),
        "matching_count": len(matching),
        "matching_pois": [_poi_to_dict(p) for p in matching],
    }


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `.\.venv\Scripts\python -m pytest tests/test_mcp_spatial_db.py -v`
Expected: PASS — all 6 tests green.

- [ ] **Step 8: Smoke-test standalone server start**

Run: `.\.venv\Scripts\python -m deg.mcp.spatial_db.server`
Expected: Server starts (blocks waiting for stdio). No import errors visible before it blocks. Press Ctrl+C to stop.

- [ ] **Step 9: Update `.env.example` and create `.env`**

Replace `.env.example` contents entirely:
```dotenv
# Google AI Studio — used by Google ADK (adk run, Runner, adk web)
# Get your key at: https://aistudio.google.com/apikey
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your-google-api-key-here

# LiteLLM model strings — for future switchable model config
DEG_MODEL=gemini/gemini-2.0-flash
DEG_FALLBACK_MODEL=ollama_chat/llama3.1
```

Create `.env` at repo root (gitignored — do NOT commit):
```dotenv
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=paste_your_real_key_here
```

Confirm it's gitignored: `git check-ignore .env` should print `.env`.

- [ ] **Step 10: Create `conftest.py` at repo root**

```python
"""Pytest configuration for 數位土地公.

Adds agents/ to sys.path so `from dijizhu.agent import ...` works the same
way as `adk run dijizhu` (which runs from agents/ directory).
Loads .env so GOOGLE_API_KEY is available to integration tests.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).parent
_AGENTS = _ROOT / "agents"

# agents/ on sys.path → `import dijizhu.agent` (consistent with adk run)
if str(_AGENTS) not in sys.path:
    sys.path.insert(0, str(_AGENTS))

load_dotenv(_ROOT / ".env")
```

- [ ] **Step 11: Run full non-integration suite**

Run:
```powershell
.\.venv\Scripts\python -m pytest -q -m "not integration"
.\.venv\Scripts\python -m ruff check deg tests
```
Expected: 22 tests pass (16 M0 + 6 MCP unit tests); ruff clean.

- [ ] **Step 12: Commit Task 1**

```powershell
git add pyproject.toml .env.example conftest.py deg/mcp tests/test_mcp_spatial_db.py
git commit -m "feat(mcp): add FastMCP spatial-db server + M1 deps + test config"
```
(Do NOT `git add .env`.)

---

### Task 2: 地基主 ADK agent (神農街)

**Files:**
- Create: `agents/dijizhu/__init__.py`
- Create: `agents/dijizhu/agent.py`

- [ ] **Step 1: Verify McpToolset import before writing agent code**

Run:
```powershell
.\.venv\Scripts\python -c "from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioServerParameters; print('McpToolset import OK')"
```
Expected: `McpToolset import OK`.

If import fails, the class path changed in your installed version — check `adk.dev/tools-custom/mcp-tools/index.md` for the correct import and adapt Steps 2–3 accordingly before continuing. Report this as DONE_WITH_CONCERNS.

- [ ] **Step 2: Create `agents/dijizhu/__init__.py`**

Create the directory `agents/dijizhu/` then create `agents/dijizhu/__init__.py`:
```python
"""地基主 ADK agent — 台南街廓微觀管理員.

Required by `adk run dijizhu` (ADK discovers agents through package import).
"""

from . import agent
```

- [ ] **Step 3: Create `agents/dijizhu/agent.py`**

```python
"""地基主 (Street Guardian) ADK LlmAgent.

Each 地基主 is bound to one Tainan 街廓 and bids into 土地公's Contract Net
by reading the MCP spatial-db and returning a BiddingProposal.

Run interactively:
    cd agents
    adk run dijizhu      (starts 神農街 地基主 by default)
    adk web              (browser dev UI)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path when launched via `adk run` (cwd = agents/).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(_REPO_ROOT / ".env")  # load GOOGLE_API_KEY + GOOGLE_GENAI_USE_VERTEXAI

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioServerParameters

from deg.schemas import BiddingProposal

# Launch the MCP server as a subprocess using the same interpreter.
_MCP_MODULE = "deg.mcp.spatial_db.server"


def create_dijizhu(
    street_id: str,
    street_name: str,
    agent_id: str,
) -> LlmAgent:
    """Create a 地基主 LlmAgent bound to a specific street.

    Args:
        street_id:   seed identifier (shennong | haian | zhengxing)
        street_name: human-readable Chinese name for prompts
        agent_id:    the value placed in BiddingProposal.agent_id
    """
    toolset = McpToolset(
        connection_params=StdioServerParameters(
            command=sys.executable,
            args=["-m", _MCP_MODULE],
        ),
    )

    return LlmAgent(
        name=f"dijizhu_{street_id}",
        model="gemini-flash-latest",
        description=f"台南{street_name}的地基主，專責該街廓的空間情報投標。",
        instruction=f"""你是「{street_name}」的地基主 (agent_id: {agent_id})，守護這條街道的神明管理員。

你的職責是：收到 TaskBroadcast JSON 後，調查轄區、計算適配分數，回傳投標書（BiddingProposal）。

【投標步驟】
1. 呼叫 get_street_info("{street_id}") 了解你轄區的歷史與特色。
2. 根據 TaskBroadcast 的 constraints，呼叫 search_pois_by_constraints("{street_id}", constraints) 找候選地點。
   若 constraints 為空，改呼叫 get_street_pois("{street_id}") 取得所有 POI。
3. 評估適配度：考慮 POI 類型與需求符合程度、街廓特色、人情味，給出 fitness_score（0.0~10.0）。
4. 在 reasoning 欄位用繁體中文寫下你的投標理由，充分展現護航在地的自豪與性格。

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
- evidence: {{"sensor": null, "social": null}}（巡境使/虎爺情報 M4 後填入）
- confidence: 0.0~1.0""",
        tools=[toolset],
        output_schema=BiddingProposal,
    )


# Module-level root_agent required by `adk run dijizhu`.
# Default to 神農街; M2 will instantiate all three via create_dijizhu().
root_agent = create_dijizhu(
    street_id="shennong",
    street_name="神農街",
    agent_id="street_shennong_node",
)
```

- [ ] **Step 4: Manually verify via `adk run`**

From the `agents/` directory (not repo root):
```powershell
cd agents
adk run dijizhu
```
When prompted, paste this TaskBroadcast:
```
{"task_id": "manual_test_01", "intent": "find_cafe_avoid_crowd", "user_location": {"lat": 22.999, "lng": 120.222}, "constraints": ["咖啡", "安靜"], "timeout_ms": 30000}
```
Expected (15–30 sec response time):
- The agent calls `get_street_info` and `search_pois_by_constraints` via the MCP server.
- The final response is a JSON string conforming to `BiddingProposal`.
- `agent_id` = `"street_shennong_node"`.
- `reasoning` is in Chinese and praises 神農街.
- `candidate_pois` contains at least one café POI.

Press Ctrl+C to exit. Return to repo root: `cd ..`

- [ ] **Step 5: Commit Task 2**

```powershell
git add agents/dijizhu
git commit -m "feat(agent): add 地基主 ADK LlmAgent for 神農街 (create_dijizhu factory + adk run)"
```

---

### Task 3: Integration test

**Files:**
- Create: `tests/test_dijizhu_integration.py`

- [ ] **Step 1: Write the integration test**

Create `tests/test_dijizhu_integration.py`:
```python
"""Integration tests: 地基主 (神農街) → MCP server subprocess → Gemini → BiddingProposal.

Skips automatically if GOOGLE_API_KEY is not set in environment / .env.
Uses real LLM calls — expect 20–45 seconds per test.

Run explicitly:
    pytest tests/test_dijizhu_integration.py -v -m integration -s
"""

from __future__ import annotations

import os

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import ValidationError

from deg.schemas import BiddingProposal, LatLng, TaskBroadcast


def _require_api_key():
    if not os.environ.get("GOOGLE_API_KEY"):
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


@pytest.mark.integration
async def test_shennong_returns_valid_bidding_proposal():
    """End-to-end: TaskBroadcast → 地基主 → Gemini + MCP tools → BiddingProposal."""
    _require_api_key()

    # Import inside test so McpToolset isn't constructed during collection
    from dijizhu.agent import create_dijizhu  # noqa: PLC0415

    agent = create_dijizhu(
        street_id="shennong",
        street_name="神農街",
        agent_id="street_shennong_node",
    )

    task = TaskBroadcast(
        task_id="integration_001",
        intent="find_cafe_avoid_crowd",
        user_location=LatLng(lat=22.999, lng=120.222),
        constraints=["咖啡", "安靜"],
        timeout_ms=30000,
    )

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="deg", user_id="test_user", session_id="s_001"
    )
    runner = Runner(agent=agent, app_name="deg", session_service=session_service)

    msg = types.Content(role="user", parts=[types.Part(text=task.model_dump_json())])
    final_text = ""
    async for event in runner.run_async(
        user_id="test_user", session_id="s_001", new_message=msg
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
    assert proposal.task_id == "integration_001"
    assert 0.0 <= proposal.fitness_score <= 10.0
    assert len(proposal.reasoning) > 10, "reasoning should be a meaningful sentence"
    assert proposal.spatial_data is not None


@pytest.mark.integration
async def test_mcp_tools_actually_called():
    """Verify the agent retrieved POIs from MCP (candidate_pois non-empty)."""
    _require_api_key()

    from dijizhu.agent import create_dijizhu  # noqa: PLC0415

    agent = create_dijizhu(
        street_id="shennong",
        street_name="神農街",
        agent_id="street_shennong_node",
    )

    task = TaskBroadcast(
        task_id="integration_002",
        intent="find_cafe",
        user_location=LatLng(lat=22.999, lng=120.222),
        constraints=["cafe"],
    )

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="deg", user_id="test_user", session_id="s_002"
    )
    runner = Runner(agent=agent, app_name="deg", session_service=session_service)
    msg = types.Content(role="user", parts=[types.Part(text=task.model_dump_json())])

    final_text = ""
    async for event in runner.run_async(
        user_id="test_user", session_id="s_002", new_message=msg
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text
            break

    proposal = BiddingProposal.model_validate_json(final_text)
    assert len(proposal.candidate_pois) >= 1, (
        "Expected ≥1 candidate_poi — agent may not have called MCP tools. "
        f"Raw response:\n{final_text}"
    )
```

- [ ] **Step 2: Verify non-integration suite still passes**

Run: `.\.venv\Scripts\python -m pytest -q -m "not integration"`
Expected: 22 tests pass; 2 integration tests auto-skipped (or not collected since they're marked). Ruff: `.\.venv\Scripts\python -m ruff check deg tests agents conftest.py` → clean.

- [ ] **Step 3: Run integration tests with real API key**

Run (with `GOOGLE_API_KEY` in `.env` — expect 30–60 sec total):
```powershell
.\.venv\Scripts\python -m pytest tests/test_dijizhu_integration.py -v -m integration -s
```
Expected:
- `test_shennong_returns_valid_bidding_proposal` — PASS. Output shows agent reasoning and MCP tool calls (with `-s`).
- `test_mcp_tools_actually_called` — PASS. `candidate_pois` list is non-empty.

If `test_mcp_tools_actually_called` fails with empty `candidate_pois`, the agent responded without calling the MCP tools. Debug by checking if `McpToolset` started the server subprocess (add `-s` to see tool call logs). Verify the McpToolset async lifecycle if needed per `adk.dev/tools-custom/mcp-tools/index.md`.

- [ ] **Step 4: Commit Task 3**

```powershell
git add tests/test_dijizhu_integration.py
git commit -m "test(agent): add 地基主 integration tests (TaskBroadcast → BiddingProposal via real LLM)"
```

---

## Verification (end-to-end for M1)

```powershell
# Unit tests only (no API key needed):
.\.venv\Scripts\python -m pytest -q -m "not integration"
# Expected: 22 passed

# Integration tests (needs GOOGLE_API_KEY in .env):
.\.venv\Scripts\python -m pytest tests/test_dijizhu_integration.py -v -m integration -s
# Expected: 2 passed — valid BiddingProposal JSON with candidate_pois

# Manual CLI demo (from agents/ directory):
cd agents
adk run dijizhu
# Paste: {"task_id":"demo","intent":"find_cafe","user_location":{"lat":22.999,"lng":120.222},"constraints":["安靜","咖啡"],"timeout_ms":30000}
# Expected: 神農街 地基主 responds in Chinese with BiddingProposal JSON, praises 神農街
cd ..
```

M1 complete: the MCP server serves seed data, the 地基主 reads it via MCPToolset, Gemini reasons with the 地基主 persona in Chinese, and the output validates as `BiddingProposal`. The `create_dijizhu()` factory is ready for M2 to instantiate all three streets in parallel.

---

## Self-Review

**Spec coverage (M1):** FastMCP spatial-db server ✓, three tool functions ✓, unit tests (no API key) ✓, single 地基主 ADK LlmAgent ✓ (神農街), `create_dijizhu()` factory parameterized for M2 reuse ✓, `output_schema=BiddingProposal` ✓, `adk run dijizhu` CLI verification ✓, integration tests ✓. `GOOGLE_API_KEY` / ADK env config ✓ (`.env` + `.env.example`).

**No placeholders:** Every file has complete code. The McpToolset import-check step in Task 2 is a deliberate verify-before-code gate (documented API instability), not a placeholder.

**Type consistency:** `BiddingProposal`, `TaskBroadcast`, `LatLng` all imported from `deg.schemas` — the M0 contracts are the single source of truth. `create_dijizhu()` is defined once in `agent.py` and imported in integration tests as `from dijizhu.agent import create_dijizhu` (via conftest.py sys.path setup). `_STREETS` in `server.py` uses `Street.street_id` as the key, matching the `street_id` parameter passed to every tool function.

**Out of scope (next plans):** ParallelAgent + 土地公 LLM-as-Judge (M2), A2A server wrapping for 地基主 / 虎爺 / 巡境使 (M3), 巡境使 + 虎爺 live data integration (M4), FastAPI gateway + WebSocket (M5), Next.js Divine-Tech frontend (M6).
