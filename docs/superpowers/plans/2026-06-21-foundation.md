# 數位土地公 — M0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap the monorepo and ship the shared data-contract layer (Pydantic schemas) plus the Tainan seed spatial dataset and its validated loader — the foundation every agent and the MCP server will import.

**Architecture:** A single Python package `deg` (importable as `deg.schemas`, `deg.seed`, later `deg.agents`, `deg.mcp`) installed editable at the repo root, with the Next.js frontend kept separate under `apps/web/` (built in a later plan). The approved structure's `packages/schemas`, `agents/…`, `mcp/…` are realized as subpackages of `deg/` for clean imports; `data/seed` and `apps/web` stay top-level. M0 delivers only `deg.schemas` + `deg.seed` + project config — no LLM, no network, fully unit-testable.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, ruff, python-dotenv, setuptools, git. (ADK / a2a-sdk / mcp deps are added in later plans, not here.)

---

## File Structure (created by this plan)

```
digital-earth-god/
  .gitignore                       # python + node + env ignores
  .env.example                     # GEMINI_API_KEY + LiteLLM model strings
  README.md                        # one-paragraph project + dev bootstrap
  pyproject.toml                   # project metadata, deps, pytest config
  deg/
    __init__.py
    schemas/
      __init__.py                  # re-exports the public contracts
      contracts.py                 # LatLng, Poi, Evidence, TaskBroadcast, BiddingProposal, Wish
    seed/
      __init__.py
      loader.py                    # Street model + load_streets()
  data/
    seed/
      streets.json                 # 神農街 / 海安路 / 正興街 seed (illustrative demo data)
  tests/
    __init__.py
    test_contracts.py              # validation + JSON round-trip
    test_seed_loader.py            # loads real seed file, validates shape
  docs/superpowers/plans/2026-06-21-foundation.md   # (this file, already present)
```

**Responsibilities**
- `deg/schemas/contracts.py` — the *only* source of truth for A2A wire shapes (Schema A/B) and the Warm-data Wish. Pure Pydantic, no I/O.
- `deg/seed/loader.py` — reads + validates `data/seed/streets.json` into typed `Street` objects. Pure read, no LLM.
- `data/seed/streets.json` — the three Tainan 中西區 街廓 the 地基主 will represent. Clearly illustrative seed data.

---

### Task 1: Repo scaffold + tooling

**Files:**
- Create: `.gitignore`, `.env.example`, `README.md`, `pyproject.toml`
- Create: `deg/__init__.py`, `deg/schemas/__init__.py`, `deg/seed/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Initialize git and create the package directories**

Run (PowerShell, from repo root `C:\Users\User\Desktop\digital earth god`):
```powershell
git init
New-Item -ItemType Directory -Force deg\schemas, deg\seed, data\seed, tests | Out-Null
```
Expected: `Initialized empty Git repository …`; the directories exist.

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[project]
name = "digital-earth-god"
version = "0.1.0"
description = "數位土地公 — MAS 微觀治理系統"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.6",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.4"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["deg*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.ruff]
line-length = 100
```

- [ ] **Step 3: Create `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.ruff_cache/
*.egg-info/
build/
dist/

# Env / secrets
.env
.env.local

# Node (frontend, later)
node_modules/
.next/
out/

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 4: Create `.env.example`**

```dotenv
# App LLM provider (LiteLLM model strings — see ADK LiteLlm wrapper)
# Primary: Gemini. Keep the abstraction so DEG_MODEL can swap to other/local models later.
GEMINI_API_KEY=your-gemini-api-key-here
DEG_MODEL=gemini/gemini-2.0-flash
DEG_FALLBACK_MODEL=ollama_chat/llama3.1
```

- [ ] **Step 5: Create `README.md`**

```markdown
# 數位土地公 (Digital Earth God)

MAS 微觀治理系統 — 在地 Agent 動態協商（Contract Net）+ 神學科技 A2UI + Warm Data。
詳見 `docs/superpowers/specs/` 設計與 `docs/superpowers/plans/` 實作計畫。

## Dev bootstrap (Windows / PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
```

## 資料說明
`data/seed/streets.json` 為**示意用 seed 資料**（台南中西區三條街），非真實營業資訊。
```

- [ ] **Step 6: Create empty package markers**

Create `deg/__init__.py` with:
```python
"""數位土地公 — MAS 微觀治理系統 core package."""
```
Create empty files: `deg/schemas/__init__.py`, `deg/seed/__init__.py`, `tests/__init__.py` (each with a single line `"""(package marker)"""` is fine, or leave empty).

- [ ] **Step 7: Create venv and install editable**

Run:
```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
```
Expected: install succeeds, ending with `Successfully installed … digital-earth-god-0.1.0 …`.

- [ ] **Step 8: Verify pytest runs (no tests yet)**

Run:
```powershell
.\.venv\Scripts\python -m pytest
```
Expected: `no tests ran` (exit code 5 is acceptable here — there are no tests yet).

- [ ] **Step 9: Commit**

```powershell
git add .gitignore .env.example README.md pyproject.toml deg tests
git commit -m "chore: scaffold monorepo, tooling, and package skeleton"
```

---

### Task 2: Data contracts (Schema A/B + Wish)

**Files:**
- Create: `deg/schemas/contracts.py`
- Modify: `deg/schemas/__init__.py`
- Test: `tests/test_contracts.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_contracts.py`:
```python
import pytest
from pydantic import ValidationError

from deg.schemas import (
    LatLng,
    Poi,
    Evidence,
    TaskBroadcast,
    BiddingProposal,
    Wish,
)


def test_task_broadcast_valid():
    tb = TaskBroadcast(
        task_id="req_12345",
        intent="find_cafe_avoid_crowd",
        user_location=LatLng(lat=22.999, lng=120.222),
        constraints=["quiet", "coffee"],
        timeout_ms=3000,
    )
    assert tb.task_id == "req_12345"
    assert tb.user_location.lat == 22.999
    assert tb.constraints == ["quiet", "coffee"]


def test_task_broadcast_defaults():
    tb = TaskBroadcast(
        task_id="req_1",
        intent="explore",
        user_location=LatLng(lat=22.99, lng=120.20),
    )
    assert tb.constraints == []
    assert tb.timeout_ms == 3000


def test_bidding_proposal_valid_and_roundtrip():
    bp = BiddingProposal(
        agent_id="street_shennong_node",
        task_id="req_12345",
        fitness_score=8.5,
        reasoning="MCP檢索到兩家老宅咖啡，巡境使API回報目前人流低於30%。",
        spatial_data=LatLng(lat=22.998, lng=120.220),
        tags=["推薦", "安靜"],
        candidate_pois=[
            Poi(
                name="老宅咖啡・神農38",
                category="cafe",
                location=LatLng(lat=22.9975, lng=120.1968),
                tags=["老宅", "安靜"],
                note="二樓老屋咖啡。",
            )
        ],
        evidence=Evidence(sensor="人流<30%", social="IG 提及度上升"),
        confidence=0.7,
    )
    dumped = bp.model_dump_json()
    restored = BiddingProposal.model_validate_json(dumped)
    assert restored == bp
    assert restored.candidate_pois[0].name == "老宅咖啡・神農38"


def test_bidding_proposal_score_out_of_range_rejected():
    with pytest.raises(ValidationError):
        BiddingProposal(
            agent_id="x",
            task_id="t",
            fitness_score=11.0,  # > 10 not allowed
            reasoning="r",
            spatial_data=LatLng(lat=0.0, lng=0.0),
        )


def test_wish_defaults_and_minimal():
    w = Wish(
        wish_id="wish_1",
        raw_text="希望這條巷子晚上有路燈",
        category="public_safety",
        location=LatLng(lat=22.993, lng=120.201),
    )
    assert w.status == "received"
    assert w.photo_ref is None
    assert w.created_at is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```powershell
.\.venv\Scripts\python -m pytest tests/test_contracts.py -v
```
Expected: FAIL — `ModuleNotFoundError` / `ImportError: cannot import name 'LatLng' from 'deg.schemas'`.

- [ ] **Step 3: Implement `deg/schemas/contracts.py`**

```python
"""Wire-level data contracts for 數位土地公.

These models are the single source of truth for the A2A payloads (Contract Net
Schema A/B) and the Warm-data Wish. They are pure Pydantic — no I/O, no LLM.
The JSON they serialize is what gets carried inside A2A message DataParts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class LatLng(BaseModel):
    lat: float
    lng: float


class Poi(BaseModel):
    """A point of interest a 地基主 can recommend."""

    name: str
    category: str
    location: LatLng
    tags: list[str] = Field(default_factory=list)
    note: str = ""


class Evidence(BaseModel):
    """Supporting evidence a 地基主 cites in its bid."""

    sensor: str | None = None  # 巡境使: traffic/weather/crowd summary
    social: str | None = None  # 虎爺: social/IG intel summary


class TaskBroadcast(BaseModel):
    """Schema A — the call-for-proposals 土地公 broadcasts to all 地基主."""

    task_id: str
    intent: str
    user_location: LatLng
    constraints: list[str] = Field(default_factory=list)
    timeout_ms: int = 3000  # soft preference hint; real-LLM bidding uses a wider window


class BiddingProposal(BaseModel):
    """Schema B — a 地基主's bid back to 土地公."""

    agent_id: str
    task_id: str
    fitness_score: float = Field(ge=0.0, le=10.0)
    reasoning: str
    spatial_data: LatLng
    tags: list[str] = Field(default_factory=list)
    candidate_pois: list[Poi] = Field(default_factory=list)
    evidence: Evidence | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class Wish(BaseModel):
    """Warm-data — a citizen wish made via 上香許願."""

    wish_id: str
    raw_text: str
    category: str
    location: LatLng
    photo_ref: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "received"
```

- [ ] **Step 4: Re-export from `deg/schemas/__init__.py`**

Replace the contents of `deg/schemas/__init__.py` with:
```python
"""Public data contracts for 數位土地公."""

from deg.schemas.contracts import (
    BiddingProposal,
    Evidence,
    LatLng,
    Poi,
    TaskBroadcast,
    Wish,
)

__all__ = [
    "LatLng",
    "Poi",
    "Evidence",
    "TaskBroadcast",
    "BiddingProposal",
    "Wish",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```powershell
.\.venv\Scripts\python -m pytest tests/test_contracts.py -v
```
Expected: PASS — all 5 tests green.

- [ ] **Step 6: Commit**

```powershell
git add deg/schemas tests/test_contracts.py
git commit -m "feat(schemas): add Contract Net + Wish data contracts"
```

---

### Task 3: Tainan seed dataset + validated loader

**Files:**
- Create: `data/seed/streets.json`
- Create: `deg/seed/loader.py`
- Test: `tests/test_seed_loader.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_seed_loader.py`:
```python
from deg.schemas import Poi
from deg.seed.loader import Street, load_streets


def test_loads_three_streets():
    streets = load_streets()
    assert len(streets) == 3
    assert all(isinstance(s, Street) for s in streets)


def test_agent_ids_are_unique():
    streets = load_streets()
    agent_ids = [s.agent_id for s in streets]
    assert len(agent_ids) == len(set(agent_ids))


def test_every_street_has_pois_typed_as_schema():
    streets = load_streets()
    for s in streets:
        assert len(s.pois) >= 1
        assert all(isinstance(p, Poi) for p in s.pois)


def test_expected_streets_present():
    names = {s.name for s in load_streets()}
    assert {"神農街", "海安路", "正興街"} <= names
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```powershell
.\.venv\Scripts\python -m pytest tests/test_seed_loader.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'deg.seed.loader'`.

- [ ] **Step 3: Create the seed data file `data/seed/streets.json`**

```json
{
  "_note": "示意用 seed 資料（台南中西區），非真實營業資訊。Illustrative demo data only.",
  "streets": [
    {
      "street_id": "shennong",
      "name": "神農街",
      "agent_id": "street_shennong_node",
      "centroid": {"lat": 22.9974, "lng": 120.1966},
      "history": "清代五條港之一，老屋與街屋林立，近年成為老宅咖啡與文創聚落，夜間靜謐。",
      "pois": [
        {"name": "老宅咖啡・神農38", "category": "cafe", "location": {"lat": 22.9975, "lng": 120.1968}, "tags": ["老宅", "安靜", "手沖"], "note": "改建自清代街屋的二樓咖啡，座位少、氛圍靜。"},
        {"name": "巷弄手沖", "category": "cafe", "location": {"lat": 22.9972, "lng": 120.1963}, "tags": ["手沖", "獨立"], "note": "單品手沖小店，常有在地常客。"},
        {"name": "永川工藝街屋", "category": "culture", "location": {"lat": 22.9976, "lng": 120.1969}, "tags": ["文化", "老工藝"], "note": "傳統神轎工藝，文化導覽點。"}
      ]
    },
    {
      "street_id": "haian",
      "name": "海安路",
      "agent_id": "street_haian_node",
      "centroid": {"lat": 22.9958, "lng": 120.1992},
      "history": "藝術造街後成為夜生活與餐酒聚落，入夜人流高、氣氛熱鬧。",
      "pois": [
        {"name": "海安餐酒館", "category": "bar", "location": {"lat": 22.9960, "lng": 120.1994}, "tags": ["熱鬧", "餐酒"], "note": "夜間人氣餐酒館。"},
        {"name": "街角麵攤", "category": "food", "location": {"lat": 22.9955, "lng": 120.1990}, "tags": ["小吃", "在地"], "note": "在地老麵攤，宵夜首選。"},
        {"name": "海安路藝術牆", "category": "culture", "location": {"lat": 22.9959, "lng": 120.1993}, "tags": ["文化", "拍照"], "note": "造街藝術裝置，打卡點。"}
      ]
    },
    {
      "street_id": "zhengxing",
      "name": "正興街",
      "agent_id": "street_zhengxing_node",
      "centroid": {"lat": 22.9931, "lng": 120.2008},
      "history": "文青小店與冰品聚集的窄街，假日人潮多、巷弄藏有小咖啡。",
      "pois": [
        {"name": "正興冰舖", "category": "dessert", "location": {"lat": 22.9932, "lng": 120.2009}, "tags": ["冰品", "排隊"], "note": "假日排隊名店。"},
        {"name": "窄巷咖啡", "category": "cafe", "location": {"lat": 22.9929, "lng": 120.2006}, "tags": ["老宅", "安靜", "巷弄"], "note": "藏在巷弄的小宅咖啡，平日清靜。"},
        {"name": "正興選物店", "category": "shop", "location": {"lat": 22.9933, "lng": 120.2010}, "tags": ["文創", "選物"], "note": "在地文創選物。"}
      ]
    }
  ]
}
```

- [ ] **Step 4: Implement `deg/seed/loader.py`**

```python
"""Load and validate the Tainan seed spatial dataset into typed objects.

Pure read — no LLM, no network. The MCP spatial-db server (later plan) will
serve queries over these same Street objects.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from deg.schemas import LatLng, Poi

# repo root: deg/seed/loader.py -> parents[2]
_DEFAULT_SEED = Path(__file__).resolve().parents[2] / "data" / "seed" / "streets.json"


class Street(BaseModel):
    """A 街廓 represented by one 地基主 agent."""

    street_id: str
    name: str
    agent_id: str
    centroid: LatLng
    history: str
    pois: list[Poi]


def load_streets(path: Path | str | None = None) -> list[Street]:
    """Read the seed file and return validated Street objects."""
    seed_path = Path(path) if path is not None else _DEFAULT_SEED
    raw = json.loads(seed_path.read_text(encoding="utf-8"))
    return [Street.model_validate(item) for item in raw["streets"]]
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```powershell
.\.venv\Scripts\python -m pytest tests/test_seed_loader.py -v
```
Expected: PASS — all 4 tests green.

- [ ] **Step 6: Run the full suite + ruff**

Run:
```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check deg tests
```
Expected: all tests pass; ruff reports no errors (or auto-fixable only — fix with `ruff check --fix` if needed, then re-run).

- [ ] **Step 7: Commit**

```powershell
git add data/seed/streets.json deg/seed/loader.py tests/test_seed_loader.py
git commit -m "feat(seed): add Tainan three-street seed data + validated loader"
```

---

## Verification (end-to-end for M0)

After all tasks, from repo root:
```powershell
.\.venv\Scripts\python -m pytest -v
.\.venv\Scripts\python -c "from deg.seed.loader import load_streets; s=load_streets(); print([(x.name, len(x.pois)) for x in s])"
```
Expected:
- All 9 tests pass.
- The one-liner prints: `[('神農街', 3), ('海安路', 3), ('正興街', 3)]`.

This proves the shared contract layer and seed data are importable and valid — the foundation M1 (MCP spatial-db + first 地基主 ADK agent) will build on.

---

## Self-Review notes
- **Spec coverage (M0 slice):** schemas package ✓ (Schema A/B + Wish), Tainan seed for 3 街廓 ✓, LiteLLM/Gemini config placeholder in `.env.example` ✓, monorepo scaffold ✓. ADK/A2A/MCP/A2UI/frontend are intentionally out of scope for M0 (later plans).
- **No placeholders:** every code/file/command step shows full content. ✓
- **Type consistency:** `Poi`/`LatLng` defined in `contracts.py` are reused by both `BiddingProposal.candidate_pois` and `Street.pois`; loader imports them rather than redefining. `load_streets()` / `Street` names match across loader and tests. ✓
- **Out of scope (next plan):** `deg/mcp/spatial_db` MCP server and `deg/agents/dijizhu` ADK bidding agent — to be written after consulting the `using-google-adk` skill for ADK 2.0 / MCPToolset / LiteLlm exact APIs.
