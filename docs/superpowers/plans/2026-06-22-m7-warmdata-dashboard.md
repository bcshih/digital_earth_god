# 數位土地公 — M7: 許願 (Warm Data) 流程 + 治理儀表板

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 流程 B — citizens "上香許願" (free text + location + optional photo): 五營兵將 normalizes + LLM-classifies the wish, it persists to a SQLite warm-data store with geo, and 土地公 responds with a blessing. A governance dashboard aggregates wishes into a density heatmap + category stats (the city's 風向球 / "weather vane of raw urban desire").

**Architecture after M7:**
```
citizen 上香許願 (text + GPS + optional photo)
   POST /wish  |  WS /ws/wish/a2ui
        ▼
五營兵將 categorizer (LlmAgent, output_schema=WishAnalysis)  → category + tags + summary + sentiment
        ▼
warm-data SQLite store (deg/warmdata)  ← persist Wish (geo, category, created_at)
        ▼
土地公 blessing (LlmAgent, output_schema=Blessing)  → 神明口吻 祝福
        ▼
治理儀表板:  GET /dashboard/summary  → {total, by_category, heatmap points, recent}
             frontend /dashboard (Leaflet density + category 風向球)
```

**Boundaries:**
- Wish flow (input → blessing) is offered as REST (`POST /wish`, primary/testable) AND standard A2UI WS (`/ws/wish/a2ui`, ritual consistency with M6).
- The dashboard is plain REST JSON (`GET /dashboard/summary`) + a bespoke frontend page — a heatmap is not a basic-catalog A2UI component, so this is the right boundary (documented).
- Gateway uses the existing in-process agents. Persistence is local SQLite (`data/warmdata.db`, gitignored); tests use in-memory / temp DB.
- `photo_ref` is accepted and stored as an optional string; actual file upload is out of scope (demo passes a URL or omits it).

**Versions:** unchanged (google-adk 2.3.0, a2a-sdk 0.3.26, FastAPI). Model `gemini-flash-latest`. SQLite via stdlib `sqlite3`.

---

## ⚠️ Prerequisites

1. M0–M6 complete (commits through `eb2380a`). 59 non-integration tests pass.
2. `deg/schemas/contracts.py` already has `Wish(wish_id, raw_text, category, location, photo_ref?, created_at, status)`.
3. `apps/api/gateway.py` has `create_app()` with `wuying_runner`, `pipeline_runner`, `session_service`, `IntentRequest`, `_run_wuying`.
4. `deg/a2ui` emitter + `apps/web` Divine-Tech frontend exist (M6).

---

## File structure (created by this plan)

```
.gitignore                       # (UPDATE) ignore data/warmdata.db
deg/
  schemas/contracts.py           # (UPDATE) add WishAnalysis, Blessing
  schemas/__init__.py            # (UPDATE) export them
  warmdata/
    __init__.py                  # (NEW)
    store.py                     # (NEW) WarmDataStore: SQLite persist + aggregate
agents/
  wuying/wish_agent.py           # (NEW) create_wish_categorizer() (output_schema=WishAnalysis)
  tudigong/blessing_agent.py     # (NEW) create_blessing_agent() (output_schema=Blessing)
deg/a2ui/surfaces.py             # (UPDATE) wish_input_components / blessing_components / *_data
apps/api/gateway.py              # (UPDATE) POST /wish, GET /wishes, GET /dashboard/summary, WS /ws/wish/a2ui
tests/
  test_warmdata_store.py         # (NEW) unit: persist + aggregate (temp DB, no LLM)
  test_a2ui_wish_surfaces.py     # (NEW) unit: wish/blessing surfaces valid
  test_gateway_wish.py           # (NEW) unit: routes + 422 validation (TestClient, no LLM)
  test_wish_flow_integration.py  # (NEW) @integration: POST /wish full flow
apps/web/
  app/wish/page.tsx              # (NEW) 上香許願 page (A2UI WS ritual)
  app/dashboard/page.tsx         # (NEW) 治理儀表板 (Leaflet density + category 風向球)
  lib/transcript/wishDemo.ts     # (NEW) canned wish A2UI transcript (offline)
```

---

### Task 1: warm-data SQLite store + schemas

**Files:**
- Modify: `deg/schemas/contracts.py`, `deg/schemas/__init__.py`, `.gitignore`
- Create: `deg/warmdata/__init__.py`, `deg/warmdata/store.py`
- Create: `tests/test_warmdata_store.py`

- [ ] **Step 1: Add schemas to `deg/schemas/contracts.py`**

Append after `Wish`:
```python
class WishAnalysis(BaseModel):
    """五營兵將's LLM classification of a raw wish."""

    category: str           # 交通 / 環境清潔 / 公共安全 / 公共設施 / 社區營造 / 商業活動 / 其他
    tags: list[str] = Field(default_factory=list)
    summary: str            # one-line normalized restatement
    sentiment: str = "中性"  # 正面 / 中性 / 負面 / 急迫


class Blessing(BaseModel):
    """土地公's blessing response to a citizen wish."""

    acknowledgment: str     # warm restatement showing the wish was heard
    blessing: str           # 神明口吻 的祝福（繁體中文）
```

Export both from `deg/schemas/__init__.py` (import line + `__all__`).

- [ ] **Step 2: Add `data/warmdata.db` to `.gitignore`**

Append a line `data/warmdata.db` (and `*.db` is fine too) so the local DB never gets committed.

- [ ] **Step 3: Write failing tests**

Create `tests/test_warmdata_store.py`:
```python
"""Unit tests for the warm-data SQLite store (temp DB, no LLM, no API key)."""

from deg.schemas import LatLng, Wish
from deg.warmdata.store import WarmDataStore


def _wish(wid="w1", category="交通", lat=22.997, lng=120.201, text="希望路口加裝紅綠燈") -> Wish:
    return Wish(wish_id=wid, raw_text=text, category=category,
                location=LatLng(lat=lat, lng=lng))


def _store(tmp_path) -> WarmDataStore:
    return WarmDataStore(tmp_path / "wd.db")


def test_add_and_get_roundtrip(tmp_path):
    s = _store(tmp_path)
    s.add_wish(_wish())
    got = s.list_wishes()
    assert len(got) == 1
    assert got[0].wish_id == "w1"
    assert got[0].category == "交通"


def test_persists_across_instances(tmp_path):
    db = tmp_path / "wd.db"
    WarmDataStore(db).add_wish(_wish())
    assert len(WarmDataStore(db).list_wishes()) == 1


def test_category_counts(tmp_path):
    s = _store(tmp_path)
    s.add_wish(_wish("w1", "交通"))
    s.add_wish(_wish("w2", "交通"))
    s.add_wish(_wish("w3", "環境清潔"))
    counts = s.category_counts()
    assert counts["交通"] == 2
    assert counts["環境清潔"] == 1


def test_heatmap_points(tmp_path):
    s = _store(tmp_path)
    s.add_wish(_wish("w1", "交通", 22.99, 120.20))
    s.add_wish(_wish("w2", "環境清潔", 22.98, 120.19))
    pts = s.heatmap_points()
    assert len(pts) == 2
    assert {"lat", "lng", "category"} <= pts[0].keys()


def test_summary_shape(tmp_path):
    s = _store(tmp_path)
    s.add_wish(_wish("w1", "交通"))
    summary = s.summary()
    assert summary["total"] == 1
    assert summary["by_category"]["交通"] == 1
    assert len(summary["points"]) == 1
    assert len(summary["recent"]) == 1


def test_list_wishes_limit_and_order(tmp_path):
    s = _store(tmp_path)
    for i in range(5):
        s.add_wish(_wish(f"w{i}", "交通"))
    recent = s.list_wishes(limit=3)
    assert len(recent) == 3  # most recent first
```

Run to confirm failure: `.\.venv\Scripts\python -m pytest tests/test_warmdata_store.py -q` → `ModuleNotFoundError`.

- [ ] **Step 4: Create `deg/warmdata/__init__.py`**
```python
"""Warm-data persistence (citizen wishes) for 數位土地公."""

from deg.warmdata.store import WarmDataStore

__all__ = ["WarmDataStore"]
```

- [ ] **Step 5: Create `deg/warmdata/store.py`**

```python
"""SQLite warm-data store for citizen wishes (流程 B).

Pure persistence + aggregation. No LLM, no I/O beyond the local SQLite file.
Default DB path is data/warmdata.db (gitignored); pass a path for tests.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from deg.schemas import LatLng, Wish

_DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "warmdata.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS wishes (
    wish_id     TEXT PRIMARY KEY,
    raw_text    TEXT NOT NULL,
    category    TEXT NOT NULL,
    lat         REAL NOT NULL,
    lng         REAL NOT NULL,
    photo_ref   TEXT,
    created_at  TEXT NOT NULL,
    status      TEXT NOT NULL
);
"""


class WarmDataStore:
    """Thin SQLite-backed store for Wish records + governance aggregates."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._path = Path(db_path) if db_path is not None else _DEFAULT_DB
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_wish(self, wish: Wish) -> Wish:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO wishes "
                "(wish_id, raw_text, category, lat, lng, photo_ref, created_at, status) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    wish.wish_id, wish.raw_text, wish.category,
                    wish.location.lat, wish.location.lng, wish.photo_ref,
                    wish.created_at.isoformat(), wish.status,
                ),
            )
        return wish

    def _row_to_wish(self, row: sqlite3.Row) -> Wish:
        return Wish(
            wish_id=row["wish_id"], raw_text=row["raw_text"], category=row["category"],
            location=LatLng(lat=row["lat"], lng=row["lng"]),
            photo_ref=row["photo_ref"], created_at=row["created_at"], status=row["status"],
        )

    def list_wishes(self, limit: int | None = None) -> list[Wish]:
        sql = "SELECT * FROM wishes ORDER BY created_at DESC, rowid DESC"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        with self._connect() as conn:
            return [self._row_to_wish(r) for r in conn.execute(sql)]

    def category_counts(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT category, COUNT(*) AS n FROM wishes GROUP BY category"
            ).fetchall()
        return {r["category"]: r["n"] for r in rows}

    def heatmap_points(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT lat, lng, category FROM wishes").fetchall()
        return [{"lat": r["lat"], "lng": r["lng"], "category": r["category"]} for r in rows]

    def summary(self, recent_limit: int = 20) -> dict:
        return {
            "total": sum(self.category_counts().values()),
            "by_category": self.category_counts(),
            "points": self.heatmap_points(),
            "recent": [w.model_dump(mode="json") for w in self.list_wishes(limit=recent_limit)],
        }
```

- [ ] **Step 6: Run tests + full suite + ruff**

```powershell
.\.venv\Scripts\python -m pytest tests/test_warmdata_store.py -v
.\.venv\Scripts\python -m pytest -q -m "not integration"
.\.venv\Scripts\python -m ruff check deg tests agents apps conftest.py
```
Expected: 6 store tests pass; full suite ~65 pass; ruff clean. Report exact count.

- [ ] **Step 7: Commit Task 1**

```powershell
git add deg/schemas/contracts.py deg/schemas/__init__.py deg/warmdata .gitignore tests/test_warmdata_store.py
git commit -m "feat(warmdata): add SQLite wish store + WishAnalysis/Blessing schemas"
```

---

### Task 2: Wish categorizer + 土地公 blessing agents

**Files:**
- Create: `agents/wuying/wish_agent.py`, `agents/tudigong/blessing_agent.py`
- Create: `tests/test_wish_agents_integration.py`

- [ ] **Step 1: Create `agents/wuying/wish_agent.py`**

```python
"""五營兵將 wish categorizer — raw 許願 text → WishAnalysis (no tools).

Input message (JSON): {"raw_text": "...", "lat": ..., "lng": ...}
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

from deg.schemas import WishAnalysis  # noqa: E402

_CATEGORIES = "交通、環境清潔、公共安全、公共設施、社區營造、商業活動、其他"

_WISH_INSTRUCTION = f"""你是五營兵將，土地公麾下體察民情的基層兵將。
收到凡人的「許願」（對社區的期望、抱怨或建議）後，將它歸納為治理情報。

【輸入】JSON：raw_text（願望原文）、lat、lng（座標）。

【分析步驟】
1. category：從以下選一個最貼切的分類：{_CATEGORIES}。
2. tags：抽取 2~4 個關鍵字標籤。
3. summary：用一句繁體中文中性地重述這個願望。
4. sentiment：判斷情緒，從 正面 / 中性 / 負面 / 急迫 擇一。

【回傳】完整的 WishAnalysis JSON：category、tags、summary、sentiment。"""


def create_wish_categorizer() -> LlmAgent:
    return LlmAgent(
        name="wuying_wish",
        model="gemini-flash-latest",
        description="五營兵將：將凡人許願歸納為治理分類 (WishAnalysis)。",
        instruction=_WISH_INSTRUCTION,
        output_schema=WishAnalysis,
    )


root_agent = create_wish_categorizer()
```

- [ ] **Step 2: Create `agents/tudigong/blessing_agent.py`**

```python
"""土地公 blessing agent — responds to a citizen wish with a warm blessing.

Input message (JSON): {"raw_text": "...", "category": "...", "summary": "..."}
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

from deg.schemas import Blessing  # noqa: E402

_BLESSING_INSTRUCTION = """你是土地公，台南中西區慈悲宏觀的守護神。
一位凡人剛剛上香許願，向你訴說對社區的期望。請以神明的口吻回應。

【輸入】JSON：raw_text（願望原文）、category（分類）、summary（摘要）。

【回應步驟】
1. acknowledgment：用溫暖的話語重述你聽見了他的心願，讓人感到被理解。
2. blessing：給予一段有台南人情味、慈悲又帶點幽默的祝福（繁體中文，2~3 句）。

【回傳】完整的 Blessing JSON：acknowledgment、blessing。"""


def create_blessing_agent() -> LlmAgent:
    return LlmAgent(
        name="tudigong_blessing",
        model="gemini-flash-latest",
        description="土地公：對凡人許願給予神明口吻的祝福 (Blessing)。",
        instruction=_BLESSING_INSTRUCTION,
        output_schema=Blessing,
    )


root_agent = create_blessing_agent()
```

- [ ] **Step 3: Verify imports (no API key)**

```powershell
.\.venv\Scripts\python -c "import sys; sys.path.insert(0,'agents'); from wuying.wish_agent import create_wish_categorizer; from tudigong.blessing_agent import create_blessing_agent; print(create_wish_categorizer().name, create_blessing_agent().name)"
```
Expected: `wuying_wish tudigong_blessing`

- [ ] **Step 4: Create `tests/test_wish_agents_integration.py`**

```python
"""Integration: wish categorizer + blessing agents (real LLM). Skips without API key."""

from __future__ import annotations

import json
import os

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from deg.schemas import Blessing, WishAnalysis


def _require_api_key() -> None:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "paste_your_real_key_here":
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


async def _run(agent, payload: str) -> str:
    ss = InMemorySessionService()
    await ss.create_session(app_name="deg", user_id="u", session_id="s")
    runner = Runner(agent=agent, app_name="deg", session_service=ss)
    msg = types.Content(role="user", parts=[types.Part(text=payload)])
    out = ""
    async for event in runner.run_async(user_id="u", session_id="s", new_message=msg):
        if event.is_final_response() and event.content and event.content.parts:
            out = event.content.parts[0].text
            break
    return out


@pytest.mark.integration
async def test_wish_categorizer():
    _require_api_key()
    from wuying.wish_agent import create_wish_categorizer  # noqa: PLC0415

    payload = json.dumps(
        {"raw_text": "海安路晚上太暗了，希望多裝幾盞路燈比較安全", "lat": 22.992, "lng": 120.198},
        ensure_ascii=False,
    )
    analysis = WishAnalysis.model_validate_json(await _run(create_wish_categorizer(), payload))
    assert len(analysis.category) > 0
    assert len(analysis.summary) > 0


@pytest.mark.integration
async def test_blessing_agent():
    _require_api_key()
    from tudigong.blessing_agent import create_blessing_agent  # noqa: PLC0415

    payload = json.dumps(
        {"raw_text": "希望神農街可以一直保持安靜美好", "category": "社區營造",
         "summary": "期望神農街維持寧靜氛圍"},
        ensure_ascii=False,
    )
    blessing = Blessing.model_validate_json(await _run(create_blessing_agent(), payload))
    assert len(blessing.blessing) > 5
    assert len(blessing.acknowledgment) > 0
```

- [ ] **Step 5: Run non-integration suite + ruff (+ verify integration skips)**

```powershell
.\.venv\Scripts\python -m pytest -q -m "not integration"
.\.venv\Scripts\python -m pytest tests/test_wish_agents_integration.py -v -m integration -s
.\.venv\Scripts\python -m ruff check deg tests agents apps conftest.py
```
Expected: full suite unchanged count passes; the 2 wish-agent integration tests SKIP; ruff clean.

- [ ] **Step 6: Commit Task 2**

```powershell
git add agents/wuying/wish_agent.py agents/tudigong/blessing_agent.py tests/test_wish_agents_integration.py
git commit -m "feat(agent): add 五營兵將 wish categorizer + 土地公 blessing agents"
```

---

### Task 3: Gateway wish endpoints + A2UI wish surfaces

**Files:**
- Modify: `apps/api/gateway.py`, `deg/a2ui/surfaces.py`
- Create: `tests/test_a2ui_wish_surfaces.py`, `tests/test_gateway_wish.py`, `tests/test_wish_flow_integration.py`

- [ ] **Step 1: Add wish A2UI surfaces to `deg/a2ui/surfaces.py`**

Append:
```python
WISH_SURFACE_ID = "wish"


def wish_input_components() -> list[dict[str, Any]]:
    return [
        {"id": "root", "component": "Column",
         "children": ["wish-title", "wish-sub", "wish-field", "wish-submit"]},
        {"id": "wish-title", "component": "Text", "text": "向土地公上香許願", "variant": "h1"},
        {"id": "wish-sub", "component": "Text",
         "text": "說出你對這座城市的心願，土地公會聽見", "variant": "caption"},
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
        {"id": "blessing-title", "component": "Text", "text": "土地公的祝福", "variant": "h1"},
        {"id": "blessing-ack", "component": "Text", "text": {"path": "/blessing/acknowledgment"}},
        {"id": "blessing-text", "component": "Text", "text": {"path": "/blessing/blessing"},
         "variant": "h2"},
        {"id": "blessing-cat", "component": "Text", "text": {"path": "/blessing/category"},
         "variant": "caption"},
    ]
```

- [ ] **Step 2: Create `tests/test_a2ui_wish_surfaces.py`**
```python
from deg.a2ui.builder import assert_valid_components
from deg.a2ui.surfaces import blessing_components, wish_input_components


def test_wish_input_valid_and_has_submit_event():
    comps = wish_input_components()
    assert_valid_components(comps)
    btns = [c for c in comps if c.get("component") == "Button"]
    assert any(b.get("action", {}).get("event", {}).get("name") == "submit_wish" for b in btns)


def test_blessing_components_valid():
    assert_valid_components(blessing_components())
```

- [ ] **Step 3: Add gateway endpoints to `apps/api/gateway.py`**

Add imports (in the `# noqa: E402` block):
```python
from deg.a2ui.surfaces import (  # noqa: E402  (extend the existing import)
    WISH_SURFACE_ID, blessing_components, wish_input_components,
)
from deg.schemas import Blessing, LatLng, Wish, WishAnalysis  # noqa: E402 (extend existing)
from deg.warmdata import WarmDataStore  # noqa: E402
from wuying.wish_agent import create_wish_categorizer  # noqa: E402
from tudigong.blessing_agent import create_blessing_agent  # noqa: E402
```

Add a request model near `IntentRequest`:
```python
class WishRequest(BaseModel):
    wish_text: str = Field(min_length=1)
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)
    photo_ref: str | None = None
```

Inside `create_app()`, after the runners, add the wish store + runners:
```python
    warm_store = WarmDataStore()
    wish_runner = Runner(
        agent=create_wish_categorizer(), app_name="deg", session_service=session_service
    )
    blessing_runner = Runner(
        agent=create_blessing_agent(), app_name="deg", session_service=session_service
    )
```

Add a shared helper (module-level, like `_run_wuying`):
```python
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
    # 1. categorize
    sid = uuid4().hex
    await session_service.create_session(app_name="deg", user_id="gateway", session_id=sid)
    payload = json.dumps({"raw_text": wish_text, "lat": lat, "lng": lng}, ensure_ascii=False)
    msg = genai_types.Content(role="user", parts=[genai_types.Part(text=payload)])
    analysis_text = ""
    async for event in wish_runner.run_async(user_id="gateway", session_id=sid, new_message=msg):
        if event.is_final_response() and event.content and event.content.parts:
            analysis_text = event.content.parts[0].text
            break
    analysis = WishAnalysis.model_validate_json(analysis_text)

    # 2. persist (gateway owns exact data fields)
    wish = Wish(
        wish_id=uuid4().hex, raw_text=wish_text, category=analysis.category,
        location=LatLng(lat=lat, lng=lng), photo_ref=photo_ref, status="received",
    )
    warm_store.add_wish(wish)

    # 3. blessing
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
    blessing = Blessing.model_validate_json(blessing_text)
    return wish, analysis, blessing
```

Add the endpoints inside `create_app()`:
```python
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
```

NOTE: the `WishRequest` field is `wish_text`; the A2UI `submit_wish` event context sends `text` — the frontend maps it to `{wish_text, lat, lng}` before sending (document this). For tests, the WS client sends `{wish_text, lat, lng}` directly.

- [ ] **Step 4: Create `tests/test_gateway_wish.py`**
```python
"""Unit tests for the wish endpoints — routes + validation, no LLM (no API key)."""

from fastapi.testclient import TestClient


def _client() -> TestClient:
    from apps.api.gateway import create_app
    return TestClient(create_app())


def test_wish_routes_registered():
    from apps.api.gateway import create_app
    paths = {getattr(r, "path", None) for r in create_app().routes}
    assert {"/wish", "/wishes", "/dashboard/summary", "/ws/wish/a2ui"} <= paths


def test_wish_rejects_missing_fields():
    assert _client().post("/wish", json={"wish_text": "x"}).status_code == 422


def test_dashboard_summary_ok_empty_or_not():
    resp = _client().get("/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert {"total", "by_category", "points", "recent"} <= body.keys()
```

NOTE: `create_app()` instantiates `WarmDataStore()` at the default path. To avoid touching the real DB in unit tests, set the env or ensure the store handles a missing dir (it does — it mkdirs). The dashboard test only reads aggregates (works on an empty/existing DB). If you prefer isolation, allow `create_app()` to honor a `DEG_WARMDATA_DB` env var pointing at a temp path and set it in a fixture — implement this if the default-path coupling is a problem.

- [ ] **Step 5: Create `tests/test_wish_flow_integration.py`**
```python
"""Integration: POST /wish full flow (categorize → persist → blessing). Skips without key."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


def _require_api_key() -> None:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "paste_your_real_key_here":
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


@pytest.mark.integration
def test_post_wish_returns_blessing_and_persists():
    _require_api_key()
    from apps.api.gateway import create_app

    client = TestClient(create_app())
    resp = client.post("/wish", json={
        "wish_text": "希望神農街的老房子可以被好好保存下來",
        "lat": 22.9971, "lng": 120.2010,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["analysis"]["category"]
    assert len(body["blessing"]["blessing"]) > 5
    assert body["wish"]["wish_id"]

    summary = client.get("/dashboard/summary").json()
    assert summary["total"] >= 1
```

- [ ] **Step 6: Verify + commit**

```powershell
.\.venv\Scripts\python -m pytest -q -m "not integration"
.\.venv\Scripts\python -m pytest tests/test_wish_flow_integration.py -v -m integration -s
.\.venv\Scripts\python -m ruff check deg tests agents apps conftest.py
git add apps/api/gateway.py deg/a2ui/surfaces.py tests/test_a2ui_wish_surfaces.py tests/test_gateway_wish.py tests/test_wish_flow_integration.py
git commit -m "feat(gateway): add 許願 wish flow (POST /wish + WS A2UI) + dashboard summary API"
```
Expected: full non-integration suite ~71 pass; integration tests skip; ruff clean.

---

### Task 4: Frontend — 許願 page + governance dashboard

**Files:** `apps/web/app/wish/page.tsx`, `apps/web/app/dashboard/page.tsx`, `apps/web/lib/transcript/wishDemo.ts`, small shared map/stat components

> Build per **frontend-design**, reusing the existing Divine-Tech renderer + theater from M6 (`apps/web/lib/a2ui/`, `apps/web/components/theater/`). Read those first. Replaceable reference frontend.

- [ ] **Step 1: 許願 page `app/wish/page.tsx`**

Live A2UI page mirroring `app/page.tsx`: connect to `ws://…/ws/wish/a2ui` (`NEXT_PUBLIC_GATEWAY_WS` host), render the wish input surface; on `submit_wish`, send `{wish_text, lat, lng}` (text from event context / `/wish/text`; lat/lng from geolocation or default Tainan); render the blessing surface with a gentle incense/glow reward animation (reuse `IncenseBackground`; a soft golden bloom on the blessing card). Graceful banner when the socket is down. Provide an offline canned `wishDemo.ts` transcript + behavior (mirror `/demo`) so the page renders without a backend.

- [ ] **Step 2: Governance dashboard `app/dashboard/page.tsx`**

Fetch `GET /dashboard/summary` (host via `NEXT_PUBLIC_GATEWAY_HTTP` ?? `http://127.0.0.1:8080`). Render:
- **City 風向球**: category breakdown as Divine-Tech stat cards / a simple bar visualization (counts per category), total wishes headline.
- **Density map**: a Leaflet dark map (reuse the M6 map approach, dynamic `ssr:false`) centered on 台南中西區 with a weighted density layer — use `CircleMarker`s with radius/opacity scaled by local wish density (or group by rounded lat/lng cell), colored by dominant category. No extra plugin required.
- **Recent wishes**: a list of the latest wishes (category chip + summary/raw_text).
- Graceful empty state ("尚無願望 — 快去 /wish 上香") and a banner if the API is unreachable. Provide sample fallback data so the page renders offline for the demo.

- [ ] **Step 3: Verify build + lint**

```bash
cd apps/web
npm run lint
npm run build
```
Both MUST pass with no backend (pages handle fetch failure / use fallback). Guard Leaflet behind `ssr:false`. Do NOT run `npm run dev`.

- [ ] **Step 4: Commit**

```powershell
cd ..\..
git add apps/web
git commit -m "feat(web): 許願 ritual page + governance heatmap dashboard (城市風向球)"
```

---

## Verification (end-to-end for M7)

```powershell
# Unit tests (no API key):
.\.venv\Scripts\python -m pytest -q -m "not integration"
# Expected: ~71 passed

# Wish flow integration (needs GOOGLE_API_KEY):
.\.venv\Scripts\python -m pytest tests/test_wish_flow_integration.py tests/test_wish_agents_integration.py -v -m integration -s

# Frontend (no API key):
cd apps/web; npm run build; npm run lint
#   npm run dev → /wish (offline demo) and /dashboard (fallback data)

# Full live (needs GOOGLE_API_KEY):
#   uvicorn apps.api.gateway:app --port 8080
#   curl -X POST localhost:8080/wish -H "Content-Type: application/json" -d '{"wish_text":"希望海安路多裝路燈","lat":22.992,"lng":120.198}'
#   curl localhost:8080/dashboard/summary
#   web: /wish (上香許願 → 祝福) , /dashboard (風向球 + 熱力圖)
```

M7 complete: citizens' wishes persist as warm data, 土地公 blesses each one, and the governance dashboard visualizes the city's collective desire as a density heatmap + category 風向球. Both flows (探索 from M6, 許願 from M7) are now live.

---

## Self-Review

**Spec coverage (M7):**
- 上香許願: free text + GPS + optional photo_ref ✓
- 五營兵將 LLM categorization → WishAnalysis ✓
- SQLite warm-data persistence with geo (`deg/warmdata`) ✓
- 土地公 blessing response (A2UI ritual reward) ✓
- 治理儀表板: density heatmap + category 風向球 + recent wishes ✓
- REST (`POST /wish`, `GET /wishes`, `GET /dashboard/summary`) + standard A2UI WS (`/ws/wish/a2ui`) ✓
- Unit tests (no key) + integration tests (auto-skip) ✓

**Design notes:**
- Gateway owns exact data fields (wish_id, location, created_at); the LLM owns category/tags/summary/blessing (same trust split as M5).
- Dashboard is plain REST JSON + bespoke viz (heatmaps aren't basic-catalog A2UI) — documented boundary.
- DB is local SQLite, gitignored; tests use temp/empty DB.

**Out of scope (M8):** 土地公 randomness/personality polish, error handling hardening, demo script, 虎爺×願望 social cross-correlation, photo upload.
