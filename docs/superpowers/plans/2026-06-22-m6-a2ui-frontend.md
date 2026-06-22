# 數位土地公 — M6: A2UI 探索流程 (durable emitter + Divine-Tech reference frontend)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the exploration golden path (流程 A) speak **standard A2UI** end-to-end and render it as a cinematic Divine-Tech "negotiation theater." Two layers, two lifespans:

1. **Durable contract (Tasks 1–2, Python, TDD):** a standard-compliant A2UI message emitter in the backend. The gateway streams `createSurface` / `updateComponents` / `updateDataModel` (A2UI v0.9.1, **basic catalog**) over a WebSocket as the negotiation unfolds. This is the long-lived interface — any future third-party frontend must consume it identically.
2. **Reference frontend (Tasks 3–4, Next.js, replaceable):** a Divine-Tech A2UI renderer + Framer Motion ritual theater + Leaflet result map. Explicitly disposable — a future team may rebuild it. It must consume ONLY the standard A2UI stream, so a replacement renderer works without backend changes.

**Design decisions (locked with the user):**
- A2UI depth = **gateway translates events → standard A2UI surfaces** (option 1), kept renderer-agnostic for a future third-party frontend.
- Map = **Leaflet** (no API token).
- Theater = **full ritual** (incense, sealed bid cards, 擲筊 verdict), but the frontend is built to be heavily revised later.

**A2UI version/catalog:** v0.9.1, basic catalog (`https://a2ui.org/specification/v0_9_1/catalogs/basic/catalog.json`). Flat adjacency list — every component is a top-level object with an `id`; parents reference children **by id string**; exactly one component has `"id": "root"`. Styling/animation is the renderer's job; the emitter only requests standard component types.

---

## ⚠️ Prerequisites

1. M0–M5 complete (commits through `dc9e90f`). 43 non-integration tests pass.
2. `apps/api/gateway.py` has `create_app()`, `_run_wuying()`, `IntentRequest`.
3. `agents/tudigong/agent.py` has `create_pipeline()`; `deg/schemas` exports `TaskBroadcast`, `BiddingProposal`, `JudgmentResult`, `LatLng`, `Poi`.
4. Node v24 + npm v11 available.

---

## File structure (created by this plan)

```
deg/
  a2ui/
    __init__.py            # (NEW) exports builders + constants
    builder.py             # (NEW) low-level: create_surface/update_components/update_data_model + validation
    surfaces.py            # (NEW) domain → A2UI: intent / broadcast / bid card / verdict surfaces
apps/api/
  gateway.py               # (UPDATE) add WS /ws/explore/a2ui streaming standard A2UI JSONL
tests/
  test_a2ui_builder.py     # (NEW) unit: flat list, one root, children-by-id, version, action.event shape
  test_a2ui_surfaces.py    # (NEW) unit: domain objects → valid A2UI surfaces
  test_gateway_a2ui_integration.py  # (NEW) @integration: full A2UI WS transcript
apps/web/                  # (NEW) Next.js reference frontend (Divine-Tech)
  package.json, next.config.*, tsconfig.json, tailwind.config.ts, postcss.config.*
  app/                     # app router: layout, page (live), demo page (canned)
  lib/a2ui/                # renderer: types, surfaceStore, Renderer.tsx, catalog components
  lib/transcript/          # canned A2UI JSONL demo transcript for offline render
  components/theater/      # ritual animation components (incense, seal, jiaobei)
docs/
  a2ui-contract.md         # (NEW) the durable A2UI message contract (so a 3rd-party FE can implement it)
```

---

## Durable layer (Tasks 1–2)

### Task 1: A2UI message builder library (`deg/a2ui/`)

**Files:**
- Create: `deg/a2ui/__init__.py`, `deg/a2ui/builder.py`, `deg/a2ui/surfaces.py`
- Create: `tests/test_a2ui_builder.py`, `tests/test_a2ui_surfaces.py`

- [ ] **Step 1: Write failing tests (TDD)**

Create `tests/test_a2ui_builder.py`:
```python
"""Unit tests for the A2UI message builders — enforce the flat-adjacency-list contract."""

from deg.a2ui.builder import (
    A2UI_VERSION,
    BASIC_CATALOG,
    assert_valid_components,
    create_surface,
    update_components,
    update_data_model,
)


def test_create_surface_shape():
    msg = create_surface("explore")
    assert msg["version"] == A2UI_VERSION
    assert msg["createSurface"]["surfaceId"] == "explore"
    assert msg["createSurface"]["catalogId"] == BASIC_CATALOG


def test_create_surface_send_data_model():
    msg = create_surface("explore", send_data_model=True)
    assert msg["createSurface"]["sendDataModel"] is True


def test_update_components_shape():
    comps = [{"id": "root", "component": "Column", "children": ["t"]},
             {"id": "t", "component": "Text", "text": "hi"}]
    msg = update_components("explore", comps)
    assert msg["version"] == A2UI_VERSION
    assert msg["updateComponents"]["surfaceId"] == "explore"
    assert msg["updateComponents"]["components"] == comps


def test_update_data_model_shape():
    msg = update_data_model("explore", "/broadcast", {"intent": "x"})
    assert msg["updateDataModel"]["surfaceId"] == "explore"
    assert msg["updateDataModel"]["path"] == "/broadcast"
    assert msg["updateDataModel"]["value"] == {"intent": "x"}


def test_assert_valid_components_accepts_good():
    comps = [{"id": "root", "component": "Column", "children": ["t"]},
             {"id": "t", "component": "Text", "text": "hi"}]
    assert_valid_components(comps)  # should not raise


def test_assert_valid_components_requires_one_root():
    comps = [{"id": "t", "component": "Text", "text": "hi"}]
    try:
        assert_valid_components(comps)
        raise AssertionError("expected ValueError for missing root")
    except ValueError:
        pass


def test_assert_valid_components_rejects_nested_child_objects():
    # children must be id strings, not embedded component objects
    comps = [{"id": "root", "component": "Column",
              "children": [{"id": "t", "component": "Text", "text": "hi"}]}]
    try:
        assert_valid_components(comps)
        raise AssertionError("expected ValueError for nested children objects")
    except ValueError:
        pass


def test_assert_valid_components_rejects_unknown_child_id():
    comps = [{"id": "root", "component": "Column", "children": ["missing"]}]
    try:
        assert_valid_components(comps)
        raise AssertionError("expected ValueError for dangling child id")
    except ValueError:
        pass
```

Create `tests/test_a2ui_surfaces.py`:
```python
"""Unit tests: domain objects → valid A2UI surfaces (basic catalog, flat list)."""

from deg.a2ui.builder import assert_valid_components
from deg.a2ui.surfaces import (
    SURFACE_ID,
    bid_card_components,
    broadcast_data,
    intent_input_components,
    judgment_components,
    judgment_data,
)
from deg.schemas import BiddingProposal, JudgmentResult, LatLng, Poi, TaskBroadcast


def _proposal(agent_id="street_shennong_node", street="神農街") -> BiddingProposal:
    return BiddingProposal(
        agent_id=agent_id,
        task_id="t1",
        fitness_score=8.5,
        reasoning="神農街老宅咖啡氛圍最佳，安靜且有歷史。",
        spatial_data=LatLng(lat=22.999, lng=120.222),
        tags=["安靜", "老宅", "咖啡"],
        candidate_pois=[Poi(name="舊來發", category="cafe",
                            location=LatLng(lat=22.999, lng=120.222),
                            tags=["安靜"], note="好咖啡")],
    )


def test_intent_input_is_valid_flat_list():
    comps = intent_input_components()
    assert_valid_components(comps)
    # has a submit button with an event action named submit_intent
    btns = [c for c in comps if c.get("component") == "Button"]
    assert any(
        b.get("action", {}).get("event", {}).get("name") == "submit_intent" for b in btns
    )


def test_bid_card_is_valid_and_namespaced():
    comps = bid_card_components(_proposal(), index=0)
    assert_valid_components(comps)
    # every id should be namespaced by the agent_id so multiple bid cards coexist
    assert all("street_shennong_node" in c["id"] for c in comps)


def test_two_bid_cards_have_disjoint_ids():
    a = bid_card_components(_proposal("street_shennong_node", "神農街"), 0)
    b = bid_card_components(_proposal("street_haian_node", "海安路"), 1)
    ids_a = {c["id"] for c in a}
    ids_b = {c["id"] for c in b}
    assert ids_a.isdisjoint(ids_b)


def test_broadcast_data_roundtrips():
    tb = TaskBroadcast(task_id="t1", intent="find_quiet_cafe",
                       user_location=LatLng(lat=22.999, lng=120.222),
                       constraints=["安靜", "咖啡"])
    data = broadcast_data(tb)
    assert data["intent"] == "find_quiet_cafe"
    assert data["constraints"] == ["安靜", "咖啡"]


def test_judgment_components_valid():
    result = JudgmentResult(
        task_id="t1", winner_agent_id="street_shennong_node", winner_street="神農街",
        recommendation="土地公推薦神農街老宅咖啡。", reasoning="分數最高且最有人情味。",
        recommended_pois=[Poi(name="舊來發", category="cafe",
                              location=LatLng(lat=22.999, lng=120.222))],
        ranked_agent_ids=["street_shennong_node", "street_haian_node", "street_zhengxing_node"],
    )
    comps = judgment_components(result)
    assert_valid_components(comps)
    data = judgment_data(result)
    assert data["winner_street"] == "神農街"
    assert len(data["recommended_pois"]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python -m pytest tests/test_a2ui_builder.py tests/test_a2ui_surfaces.py -q`
Expected: `ModuleNotFoundError: No module named 'deg.a2ui'`

- [ ] **Step 3: Create `deg/a2ui/builder.py`**

```python
"""Low-level A2UI v0.9.1 message builders + structural validation.

A2UI is a FLAT ADJACENCY LIST: every component is a top-level object with an `id`;
parents reference children BY ID STRING; exactly one component has id "root".
These builders + assert_valid_components keep the emitter honest so any standard
A2UI renderer (including a future third-party frontend) can consume the stream.
"""

from __future__ import annotations

from typing import Any

A2UI_VERSION = "v0.9.1"
BASIC_CATALOG = "https://a2ui.org/specification/v0_9_1/catalogs/basic/catalog.json"

# Basic-catalog component types this system emits. Renderer must support these.
KNOWN_COMPONENTS = {
    "Row", "Column", "List", "Text", "Image", "Icon", "Divider",
    "Button", "TextField", "Card",
}


def create_surface(
    surface_id: str,
    *,
    catalog_id: str = BASIC_CATALOG,
    send_data_model: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"surfaceId": surface_id, "catalogId": catalog_id}
    if send_data_model:
        payload["sendDataModel"] = True
    return {"version": A2UI_VERSION, "createSurface": payload}


def update_components(surface_id: str, components: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": A2UI_VERSION,
        "updateComponents": {"surfaceId": surface_id, "components": components},
    }


def update_data_model(surface_id: str, path: str, value: Any) -> dict[str, Any]:
    return {
        "version": A2UI_VERSION,
        "updateDataModel": {"surfaceId": surface_id, "path": path, "value": value},
    }


def assert_valid_components(components: list[dict[str, Any]]) -> None:
    """Enforce the flat-adjacency-list contract. Raises ValueError on violations."""
    if not isinstance(components, list) or not components:
        raise ValueError("components must be a non-empty list")

    ids: set[str] = set()
    for c in components:
        if not isinstance(c, dict):
            raise ValueError(f"component is not an object: {c!r}")
        cid = c.get("id")
        if not isinstance(cid, str) or not cid:
            raise ValueError(f"component missing string id: {c!r}")
        if cid in ids:
            raise ValueError(f"duplicate component id: {cid!r}")
        ids.add(cid)
        comp_type = c.get("component")
        if comp_type not in KNOWN_COMPONENTS:
            raise ValueError(f"unknown component type {comp_type!r} on {cid!r}")

    root_count = sum(1 for c in components if c["id"] == "root")
    if root_count != 1:
        raise ValueError(f"exactly one component must have id 'root' (found {root_count})")

    # children must be id strings (static array) or a template dict; never nested objects
    for c in components:
        children = c.get("children")
        if children is None:
            continue
        if isinstance(children, dict):
            # template form: {"path": "...", "componentId": "..."}
            if "componentId" in children and children["componentId"] not in ids:
                raise ValueError(
                    f"template componentId {children['componentId']!r} not defined"
                )
            continue
        if not isinstance(children, list):
            raise ValueError(f"children must be a list or template dict on {c['id']!r}")
        for child in children:
            if not isinstance(child, str):
                raise ValueError(
                    f"children must be id strings, got object on {c['id']!r} "
                    "(flat adjacency list — define children as separate components)"
                )
            if child not in ids:
                raise ValueError(f"dangling child id {child!r} on {c['id']!r}")
```

- [ ] **Step 4: Create `deg/a2ui/surfaces.py`**

```python
"""Domain objects (TaskBroadcast / BiddingProposal / JudgmentResult) → A2UI surfaces.

All components use the basic catalog so any A2UI renderer can draw them. Data lives
in the data model (bound by path); components carry presentation intent only.
"""

from __future__ import annotations

from typing import Any

from deg.schemas import BiddingProposal, JudgmentResult, Poi, TaskBroadcast

SURFACE_ID = "explore"


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
         "text": "向土地公稟報你的心願", "variant": "h1"},
        {"id": "intent-sub", "component": "Text",
         "text": "五營兵將會將你的凡人語言轉成招標令", "variant": "caption"},
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


# ── Task broadcast (招標令) ───────────────────────────────────────────────────

def broadcast_data(tb: TaskBroadcast) -> dict[str, Any]:
    return {
        "task_id": tb.task_id,
        "intent": tb.intent,
        "constraints": tb.constraints,
        "lat": tb.user_location.lat,
        "lng": tb.user_location.lng,
    }


def broadcast_components() -> list[dict[str, Any]]:
    """The negotiation surface root + broadcast card + empty bids row."""
    return [
        {"id": "root", "component": "Column",
         "children": ["broadcast-card", "bids-row"]},
        {"id": "broadcast-card", "component": "Card", "child": "broadcast-body"},
        {"id": "broadcast-body", "component": "Column",
         "children": ["broadcast-title", "broadcast-intent"]},
        {"id": "broadcast-title", "component": "Text", "text": "土地公發出招標令", "variant": "h2"},
        {"id": "broadcast-intent", "component": "Text", "text": {"path": "/broadcast/intent"}},
        {"id": "bids-row", "component": "Row", "children": []},
    ]


# ── Bid card (地基主投標) ─────────────────────────────────────────────────────

def bid_data(proposal: BiddingProposal) -> dict[str, Any]:
    ev = proposal.evidence
    return {
        "agent_id": proposal.agent_id,
        "fitness_score": proposal.fitness_score,
        "reasoning": proposal.reasoning,
        "tags": proposal.tags,
        "sensor": (ev.sensor if ev else None),
        "social": (ev.social if ev else None),
        "candidate_pois": [_poi_dict(p) for p in proposal.candidate_pois],
    }


def bid_card_components(proposal: BiddingProposal, index: int) -> list[dict[str, Any]]:
    """Components for ONE bid card. Ids are namespaced by agent_id so cards coexist.

    NOTE: the caller must also resend `bids-row` with this card's root id appended
    to its children, and call update_data_model('/bids/<agent_id>', bid_data(...)).
    """
    aid = proposal.agent_id
    card = f"bid-{aid}"
    body = f"bid-body-{aid}"
    score = f"bid-score-{aid}"
    reason = f"bid-reason-{aid}"
    path = f"/bids/{aid}"
    return [
        {"id": card, "component": "Card", "child": body},
        {"id": body, "component": "Column", "children": [score, reason]},
        {"id": score, "component": "Text",
         "text": {"path": f"{path}/fitness_score"}, "variant": "h2"},
        {"id": reason, "component": "Text", "text": {"path": f"{path}/reasoning"}},
    ]


def bid_card_root_id(proposal: BiddingProposal) -> str:
    return f"bid-{proposal.agent_id}"


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


def judgment_components(result: JudgmentResult) -> list[dict[str, Any]]:
    """Full surface incl. verdict card. Root now includes verdict-card last."""
    return [
        {"id": "root", "component": "Column",
         "children": ["broadcast-card", "bids-row", "verdict-card"]},
        {"id": "verdict-card", "component": "Card", "child": "verdict-body"},
        {"id": "verdict-body", "component": "Column",
         "children": ["verdict-title", "verdict-street", "verdict-text"]},
        {"id": "verdict-title", "component": "Text", "text": "土地公的裁決", "variant": "h1"},
        {"id": "verdict-street", "component": "Text",
         "text": {"path": "/verdict/winner_street"}, "variant": "h2"},
        {"id": "verdict-text", "component": "Text", "text": {"path": "/verdict/recommendation"}},
    ]
```

- [ ] **Step 5: Run tests, then full suite + ruff**

```powershell
.\.venv\Scripts\python -m pytest tests/test_a2ui_builder.py tests/test_a2ui_surfaces.py -v
.\.venv\Scripts\python -m pytest -q -m "not integration"
.\.venv\Scripts\python -m ruff check deg tests agents apps conftest.py
```
Expected: new tests pass; full suite now 43 + (builder ~7 + surfaces ~5) ≈ 55 pass; ruff clean. (Report the exact count.)

Create `deg/a2ui/__init__.py`:
```python
"""Standard A2UI v0.9.1 message emitter for 數位土地公 (durable contract)."""

from deg.a2ui.builder import (
    A2UI_VERSION,
    BASIC_CATALOG,
    assert_valid_components,
    create_surface,
    update_components,
    update_data_model,
)

__all__ = [
    "A2UI_VERSION",
    "BASIC_CATALOG",
    "assert_valid_components",
    "create_surface",
    "update_components",
    "update_data_model",
]
```

- [ ] **Step 6: Commit Task 1**

```powershell
git add deg/a2ui tests/test_a2ui_builder.py tests/test_a2ui_surfaces.py
git commit -m "feat(a2ui): add standard A2UI v0.9.1 message emitter (builder + domain surfaces)"
```

---

### Task 2: Gateway A2UI WebSocket endpoint

**Files:**
- Modify: `apps/api/gateway.py`
- Create: `tests/test_gateway_a2ui_integration.py`
- Create: `docs/a2ui-contract.md`

- [ ] **Step 1: Add an A2UI streaming endpoint to `apps/api/gateway.py`**

Add these imports near the others (use the `# noqa: E402` block already present):
```python
from deg.a2ui import create_surface, update_components, update_data_model  # noqa: E402
from deg.a2ui.surfaces import (  # noqa: E402
    SURFACE_ID,
    bid_card_components,
    bid_card_root_id,
    bid_data,
    broadcast_components,
    broadcast_data,
    intent_input_components,
    judgment_components,
    judgment_data,
)
from deg.schemas import BiddingProposal  # noqa: E402  (if not already imported)
```

Add a pipeline runner helper that yields per-agent proposals. Inside `create_app()`, after the existing endpoints, add:

```python
    @app.websocket("/ws/explore/a2ui")
    async def ws_explore_a2ui(ws: WebSocket) -> None:
        """Stream the golden path as STANDARD A2UI JSONL messages.

        Sequence:
            createSurface(explore, sendDataModel=true)
            updateComponents(intent input)            # initial prompt surface
            ← client sends {intent_text, lat, lng}
            updateComponents(broadcast surface) + updateDataModel(/broadcast)
            per 地基主 bid: updateComponents(bid card + grown bids-row) + updateDataModel(/bids/<id>)
            updateComponents(verdict surface) + updateDataModel(/verdict)
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
            await ws.send_json(update_components(SURFACE_ID, broadcast_components()))
            await ws.send_json(update_data_model(SURFACE_ID, "/broadcast", broadcast_data(tb)))
            await ws.send_json(update_data_model(SURFACE_ID, "/bids", {}))

            # Run the pipeline; emit a bid card per 地基主, verdict at the end.
            session_id = uuid4().hex
            await session_service.create_session(
                app_name="deg", user_id="gateway", session_id=session_id
            )
            msg = genai_types.Content(
                role="user", parts=[genai_types.Part(text=tb.model_dump_json())]
            )
            bid_order: list[str] = []
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
                    comps = bid_card_components(proposal, len(bid_order))
                    bid_order.append(bid_card_root_id(proposal))
                    grown_row = {"id": "bids-row", "component": "Row", "children": bid_order}
                    await ws.send_json(update_components(SURFACE_ID, [*comps, grown_row]))
                    await ws.send_json(
                        update_data_model(SURFACE_ID, f"/bids/{proposal.agent_id}",
                                          bid_data(proposal))
                    )
                elif author == "tudigong_judge" and event.is_final_response():
                    verdict_text = text

            if verdict_text:
                result = JudgmentResult.model_validate_json(verdict_text)
                await ws.send_json(update_components(SURFACE_ID, judgment_components(result)))
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
```

- [ ] **Step 2: Add a route-registration assertion to `tests/test_gateway.py`**

Append a test:
```python
def test_a2ui_route_registered():
    from apps.api.gateway import create_app
    app = create_app()
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/ws/explore/a2ui" in paths
```

- [ ] **Step 3: Run non-integration suite + ruff**

```powershell
.\.venv\Scripts\python -m pytest -q -m "not integration"
.\.venv\Scripts\python -m ruff check deg tests agents apps conftest.py
```
Expected: count goes up by 1 (the new gateway route test); ruff clean.

- [ ] **Step 4: Create `tests/test_gateway_a2ui_integration.py`**

```python
"""Integration: full A2UI transcript over /ws/explore/a2ui.

Skips if GOOGLE_API_KEY is not set / is the placeholder. Expect 60–120s.
Validates the durable A2UI contract end-to-end: every component message is a valid
flat adjacency list, and the transcript reaches a verdict surface.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from deg.a2ui.builder import assert_valid_components


def _require_api_key() -> None:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "paste_your_real_key_here":
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


@pytest.mark.integration
def test_a2ui_transcript_is_valid_and_reaches_verdict():
    _require_api_key()

    from apps.api.gateway import create_app

    client = TestClient(create_app())
    msgs: list[dict] = []
    with client.websocket_connect("/ws/explore/a2ui") as ws:
        # drain the initial intent surface
        first = ws.receive_json()
        assert "createSurface" in first
        # send the citizen intent
        ws.send_json({"intent_text": "找一間安靜的老宅咖啡", "lat": 22.999, "lng": 120.222})
        while True:
            m = ws.receive_json()
            msgs.append(m)
            if m.get("a2uiDone") or m.get("a2uiError"):
                break

    assert not any(m.get("a2uiError") for m in msgs), [m for m in msgs if m.get("a2uiError")]
    # every updateComponents must be a valid flat adjacency list
    for m in msgs:
        if "updateComponents" in m:
            assert_valid_components(m["updateComponents"]["components"])
    # a verdict data model update must appear
    verdicts = [m for m in msgs if m.get("updateDataModel", {}).get("path") == "/verdict"]
    assert verdicts, "no verdict surface emitted"
    assert verdicts[-1]["updateDataModel"]["value"]["winner_street"]
    # at least one bid card surfaced
    bid_updates = [
        m for m in msgs
        if m.get("updateDataModel", {}).get("path", "").startswith("/bids/")
    ]
    assert bid_updates, "no bid cards emitted"
```

- [ ] **Step 5: Write `docs/a2ui-contract.md`**

Document the message sequence, surface id, data-model paths (`/intent`, `/broadcast`, `/bids/<agent_id>`, `/verdict`), the client→server intent message shape, and the `submit_intent` event — so a future third-party frontend can implement the renderer from this doc alone. Include one captured example of each message type (copy from a real run or from the builder output).

- [ ] **Step 6: Verify integration test skips cleanly + commit**

```powershell
.\.venv\Scripts\python -m pytest tests/test_gateway_a2ui_integration.py -v -m integration -s
.\.venv\Scripts\python -m ruff check deg tests agents apps conftest.py
git add apps/api/gateway.py tests/test_gateway.py tests/test_gateway_a2ui_integration.py docs/a2ui-contract.md
git commit -m "feat(gateway): stream standard A2UI surfaces over /ws/explore/a2ui + contract doc"
```

---

## Reference frontend (Tasks 3–4) — Divine-Tech, replaceable

> Build per the **frontend-design** skill. Aesthetic is committed below; execute the visual craft with precision. The frontend must consume ONLY the standard A2UI stream from Task 2 (and the canned transcript), so a future replacement renderer is a drop-in.

**Divine-Tech aesthetic (神・科技):** dark night-temple sanctum; divine negotiation as a luminous ritual; agent telemetry as incense-lit terminal readouts.
- **Color (CSS vars):** ink `#0B0E14`, sanctum panel `#12161F`, 科技金 gold `#E8B04B` (glow `#F5D78E`), 硃砂紅 vermillion `#C8442E` (seal `#E5533D`), jade `#4FA88B` (online), ash text `#C9CCD6`, smoke `#6B7180`.
- **Type:** Noto Serif TC (divine voice / headings, weighty + tracked), Noto Sans TC (body), Space Mono (Contract Net telemetry, scores, agent ids). Load via `next/font/google`.
- **Atmosphere:** layered radial gold/vermillion glows on near-black, faint noise/grain overlay, gold filigree borders that draw on (stroke-dashoffset), drifting incense smoke particles.
- **Avoid AI slop:** no Inter/Roboto/system fonts, no purple-on-white gradients, no generic card grids.

### Task 3: Next.js scaffold + A2UI renderer + canned demo

**Files:** `apps/web/**`

- [ ] **Step 1: Scaffold Next.js (TypeScript, App Router, Tailwind) in `apps/web/`**

From repo root:
```powershell
npx create-next-app@latest apps/web --typescript --tailwind --app --eslint --src-dir=false --import-alias "@/*" --use-npm --no-turbopack
cd apps/web
npm install motion leaflet react-leaflet
npm install -D @types/leaflet
```
(If `create-next-app` prompts, accept these defaults. `motion` is the current Framer Motion package for React.)

- [ ] **Step 2: Define the A2UI renderer contract in `apps/web/lib/a2ui/`**

Create TypeScript types mirroring the durable contract:
- `types.ts` — `A2uiMessage` (createSurface | updateComponents | updateDataModel | done | error), `Component` (flat: `{id, component, ...props}`), `Binding = {path: string}`.
- `surfaceStore.ts` — a reducer/store holding `{components: Record<id, Component>, dataModel: object}`. Applies messages: createSurface resets; updateComponents merges by id; updateDataModel sets value at JSON Pointer path (implement a small RFC-6901 setter). Resolve bindings: a prop value `{path}` reads from dataModel.
- `Renderer.tsx` — given the store, render the component whose id is `root`, recursing through `children` (id strings) and `child`. Map each basic-catalog `component` type to a Divine-Tech React component (see Step 3). Unknown types render a labelled fallback (never crash).

Pin the renderer contract: **children are id strings; resolve them from the components map. Never expect nested objects.** Binding resolution: if a prop is an object with a `path` key, read `dataModel` at that pointer; else use the literal.

- [ ] **Step 3: Divine-Tech catalog components in `apps/web/lib/a2ui/catalog/`**

One React component per basic-catalog type, styled Divine-Tech: `Column`, `Row`, `List`, `Text` (variant → h1/h2/caption/body type styles in Noto Serif TC for headings, Space Mono for numeric/score-like), `Image`, `Icon`, `Divider`, `Button` (vermillion seal styling, fires `submit_intent` via the live socket), `TextField` (writes back to dataModel path), `Card` (sanctum panel + gold filigree border). Each reads props/bindings via the store helpers.

- [ ] **Step 4: Canned demo transcript + offline demo page**

Create `apps/web/lib/transcript/exploreDemo.ts` exporting an array of A2UI messages (a hand-authored transcript matching the Task 2 contract: createSurface → intent input → broadcast → 3 bid cards (神農街/海安路/正興街 with sample scores+reasoning) → verdict). Use realistic Tainan content.

Create `apps/web/app/demo/page.tsx`: a client page that replays the transcript through the store with a timed delay between messages (so the theater animates), no backend needed. This is the **verifiable, API-key-free demo**.

- [ ] **Step 5: Verify build + lint**

```powershell
cd apps/web
npm run lint
npm run build
```
Expected: lint clean, production build succeeds. (No backend/API key needed — the demo page uses the canned transcript.)

- [ ] **Step 6: Commit Task 3**

```powershell
cd ..\..
git add apps/web
git commit -m "feat(web): Next.js Divine-Tech A2UI renderer + canned offline demo page"
```

### Task 4: Negotiation theater (ritual animation) + Leaflet map + live mode

**Files:** `apps/web/components/theater/**`, `apps/web/app/page.tsx`, map component

- [ ] **Step 1: Ritual animation components (Framer Motion via `motion`)**

In `apps/web/components/theater/`:
- `IncenseBackground.tsx` — drifting smoke particles + layered gold/vermillion radial glows on ink (CSS + light motion).
- `SealStamp.tsx` — wraps a bid card; on mount, a vermillion seal stamps down (scale 1.4→1 + rotate + opacity, spring) with a glow flash. Stagger across the 3 cards by index.
- `Jiaobei.tsx` — two crescent 擲筊 blocks that toss (rotate/translate, spring) and land 聖筊 to reveal the verdict card; gold burst on settle.
Hook these into the catalog `Card`/renderer so that when a `bid-*` card or `verdict-card` first appears, the corresponding ritual plays. Respect `prefers-reduced-motion` (fall back to fades).

- [ ] **Step 2: Leaflet result map**

`apps/web/components/ResultMap.tsx` — a Leaflet map (dark tiles, e.g. CARTO dark_all) centered on 台南中西區, dropping gold markers for `/verdict/recommended_pois`. Dynamically import with `ssr: false` (Leaflet needs `window`). Render inside the verdict card.

- [ ] **Step 3: Live mode page `apps/web/app/page.tsx`**

A client page that: shows the intent input surface; on `submit_intent`, opens a WebSocket to `ws://127.0.0.1:8080/ws/explore/a2ui` (configurable via `NEXT_PUBLIC_GATEWAY_WS`), sends `{intent_text, lat, lng}` (use a default Tainan location or browser geolocation), and feeds incoming A2UI messages into the same store/renderer/theater as the demo. Graceful banner if the socket can't connect ("土地公廟暫時關閉 — 請啟動 gateway 或看 /demo").

- [ ] **Step 4: Verify build + lint (+ optional live smoke)**

```powershell
cd apps/web
npm run lint
npm run build
```
Expected: lint clean, build succeeds. Optionally, with the gateway running + a real API key, manually load `/` and submit an intent to watch the live ritual; load `/demo` for the offline ritual.

- [ ] **Step 5: Commit Task 4**

```powershell
cd ..\..
git add apps/web
git commit -m "feat(web): negotiation theater (incense/seal/jiaobei) + Leaflet result map + live WS mode"
```

---

## Verification (end-to-end for M6)

```powershell
# Backend durable contract (no API key):
.\.venv\Scripts\python -m pytest -q -m "not integration"
# Expected: ~56 passed (43 + ~12 a2ui + 1 route)

# A2UI transcript integration (needs GOOGLE_API_KEY):
.\.venv\Scripts\python -m pytest tests/test_gateway_a2ui_integration.py -v -m integration -s

# Frontend (no API key — canned demo):
cd apps/web; npm run build; npm run lint
# Then `npm run dev` and open http://localhost:3000/demo to watch the ritual offline.

# Full live demo (needs GOOGLE_API_KEY):
#   Terminal A: .\.venv\Scripts\python -m uvicorn apps.api.gateway:app --port 8080
#   Terminal B: cd apps/web; npm run dev  → open http://localhost:3000 , submit an intent
```

M6 complete: the exploration golden path speaks **standard A2UI** (durable, schema-validated, documented in `docs/a2ui-contract.md`), and a Divine-Tech reference frontend renders it as a full ritual theater — both live (via the gateway WS) and offline (canned transcript). A future third-party frontend can replace `apps/web/` by consuming the same A2UI stream.

---

## Self-Review

**Spec coverage (M6):**
- Gateway emits standard A2UI v0.9.1 basic-catalog surfaces (flat adjacency list, validated) ✓
- WebSocket streaming of the negotiation (intent → broadcast → bids → verdict) ✓
- Durable, documented contract (`docs/a2ui-contract.md`) for a future third-party frontend ✓
- Next.js + Tailwind + Framer Motion (`motion`) Divine-Tech reference renderer ✓
- Full ritual theater (incense / vermillion seal / 擲筊) ✓
- Leaflet result map (no token) ✓
- Offline canned-transcript demo (verifiable without API key) ✓

**Durable vs replaceable:** Tasks 1–2 (Python, TDD, schema-validated) are the long-lived contract. Tasks 3–4 (`apps/web/`) are a reference renderer, intentionally swappable; they consume only standard A2UI.

**Out of scope (next plans):**
- 許願 (Warm Data) flow + governance heatmap dashboard (M7)
- Personality/randomness polish, error handling, demo script (M8)
- A2UI v1.0 features (synchronous actionResponse, server→client callFunction)
```
