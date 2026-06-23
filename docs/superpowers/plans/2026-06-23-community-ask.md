# Community Ask (社區問答) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third flow "問土地公" where users ask non-travel community questions (events, repairs, etc.) and relevant 地基主 agents surface their layer_2/layer_4 data to answer, with 土地公 summarising.

**Architecture:** Reuse the existing scout infrastructure but with community-specific prompts; run a community answer round (parallel `ParallelAgent` of local `LlmAgent`) → 土地公 reads all answers and writes summary. All agents run **in-process** (no Swarm Server needed). New WebSocket endpoint `/ws/ask/a2ui`, new Next.js page `/ask`.

**Tech Stack:** Pydantic, FastAPI WebSocket, Google ADK `LlmAgent` + `ParallelAgent` + `Runner`, A2UI surface protocol, Next.js (App Router), TypeScript.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `deg/schemas/contracts.py` | Add `CommunityAnswer`, `CommunityQueryResult` |
| Modify | `deg/schemas/__init__.py` | Export new schemas |
| Modify | `agents/dijizhu/agent.py` | Add `create_community_scout()`, `create_community_agent()` |
| Modify | `agents/tudigong/agent.py` | Add `create_community_judge()` |
| Modify | `deg/a2ui/surfaces.py` | Add `COMMUNITY_SURFACE_ID` + 5 community surface helpers |
| Modify | `apps/api/gateway.py` | Add `_run_community_scout()`, `_run_community_answers()`, `/ws/ask/a2ui` endpoint |
| Create | `apps/web/app/ask/page.tsx` | Community Q&A frontend page |

---

### Task 1: Add community schemas to contracts.py

**Files:**
- Modify: `deg/schemas/contracts.py`
- Modify: `deg/schemas/__init__.py`
- Test: `tests/test_schemas.py` (create if not exists)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_schemas.py  (append to existing file, or create)
from deg.schemas import CommunityAnswer, CommunityQueryResult

def test_community_answer_round_trip():
    a = CommunityAnswer(
        agent_id="street_wutiaogang_node",
        street_name="五條港里",
        answer_text="普濟殿本週有元宵花燈展，週末人多。",
        sources=["2026 普濟殿元宵花燈展"],
    )
    assert CommunityAnswer.model_validate_json(a.model_dump_json()) == a

def test_community_query_result_round_trip():
    r = CommunityQueryResult(
        question="最近有什麼活動？",
        answers=[
            CommunityAnswer(
                agent_id="street_wutiaogang_node",
                street_name="五條港里",
                answer_text="普濟殿元宵花燈展。",
                sources=["2026 普濟殿元宵花燈展"],
            )
        ],
        tudigong_summary="老人家我看，五條港里最近熱鬧，去普濟殿看燈就對了。",
    )
    assert CommunityQueryResult.model_validate_json(r.model_dump_json()) == r
```

- [ ] **Step 2: Run to confirm FAIL**

```
cd "digital earth god"
.venv/Scripts/python -m pytest tests/test_schemas.py::test_community_answer_round_trip -v
```

Expected: `ImportError: cannot import name 'CommunityAnswer'`

- [ ] **Step 3: Add schemas to contracts.py**

Append to the bottom of `deg/schemas/contracts.py` (before the end of file):

```python
class CommunityAnswer(BaseModel):
    """One 地基主's answer to a community question."""
    agent_id: str
    street_name: str
    answer_text: str
    sources: list[str] = Field(default_factory=list)


class CommunityQueryResult(BaseModel):
    """土地公's consolidated answer to a community query."""
    question: str
    answers: list[CommunityAnswer] = Field(default_factory=list)
    tudigong_summary: str
```

- [ ] **Step 4: Export from `deg/schemas/__init__.py`**

Add `CommunityAnswer`, `CommunityQueryResult` to both the import list and `__all__`:

```python
from deg.schemas.contracts import (
    BiddingProposal,
    Blessing,
    CommunityAnswer,          # ← new
    CommunityQueryResult,     # ← new
    DebateMessage,
    Evidence,
    ItineraryStop,
    JudgmentResult,
    LatLng,
    Poi,
    ScoutResult,
    TaskBroadcast,
    TravelContext,
    Wish,
    WishAnalysis,
    WuyingOutput,
)

__all__ = [
    "LatLng", "Poi", "Evidence", "TravelContext", "TaskBroadcast",
    "ScoutResult", "BiddingProposal", "DebateMessage",
    "CommunityAnswer", "CommunityQueryResult",    # ← new
    "Wish", "WishAnalysis", "Blessing",
    "ItineraryStop", "JudgmentResult", "WuyingOutput",
]
```

- [ ] **Step 5: Run tests — expect PASS**

```
.venv/Scripts/python -m pytest tests/test_schemas.py -v
```

- [ ] **Step 6: Commit**

```
git add deg/schemas/contracts.py deg/schemas/__init__.py tests/test_schemas.py
git commit -m "feat: add CommunityAnswer and CommunityQueryResult schemas"
```

---

### Task 2: Add community agent functions to dijizhu/agent.py

**Files:**
- Modify: `agents/dijizhu/agent.py`
- Test: `tests/test_dijizhu_community.py`

**What these agents do:**
- `create_community_scout(li_data)` — injects `layer_2_dynamic_activities` + `layer_4_citizen_opinions` as JSON, outputs `ScoutResult` (reuses existing schema). Rates 0–10 how much its data can answer the question.
- `create_community_agent(li_data)` — injects same data layers, outputs `CommunityAnswer`. Called only for the top-scored agents from the scout round.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dijizhu_community.py
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
for _p in (_REPO, _REPO / "agents"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from dijizhu.agent import create_community_scout, create_community_agent
from deg.seed.loader import LiAgentData, Metadata, PoiListProperty

def _dummy_li(street_id: str = "wutiaogang") -> LiAgentData:
    return LiAgentData(
        id=f"urn:ngsi-ld:EarthGodAgent:Tainan:WestCentral:{street_id.capitalize()}",
        type="EarthGodAgent",
        metadata=Metadata(agent_name=f"{street_id}地基主", personality="豪邁大方"),
        layer_2_dynamic_activities={
            "type": "Property",
            "value": [{"title": "普濟殿元宵花燈展", "verification_level": "official", "trust_score": 100}],
        },
        layer_4_citizen_opinions={
            "type": "Property",
            "value": [{"issue_id": "WISH-001", "type": "抱怨/通報", "content": "巷弄擁擠", "status": "待處理"}],
        },
    )

def test_create_community_scout_returns_llm_agent():
    from google.adk.agents import LlmAgent
    agent = create_community_scout("wutiaogang", "五條港里", "street_wutiaogang_node", _dummy_li())
    assert isinstance(agent, LlmAgent)
    assert "wutiaogang" in agent.name
    assert "普濟殿元宵花燈展" in agent.instruction

def test_create_community_agent_returns_llm_agent():
    from google.adk.agents import LlmAgent
    agent = create_community_agent("wutiaogang", "五條港里", "street_wutiaogang_node", _dummy_li())
    assert isinstance(agent, LlmAgent)
    assert "巷弄擁擠" in agent.instruction
```

- [ ] **Step 2: Run to confirm FAIL**

```
.venv/Scripts/python -m pytest tests/test_dijizhu_community.py -v
```

Expected: `ImportError: cannot import name 'create_community_scout'`

- [ ] **Step 3: Add both functions to `agents/dijizhu/agent.py`**

Append after the existing `create_scout()` function, before the `root_agent` line:

```python
def create_community_scout(
    street_id: str,
    street_name: str,
    agent_id: str,
    li_data: LiAgentData | None = None,
) -> LlmAgent:
    """Lightweight scout: evaluates whether this li's activities/opinions answer the community question."""
    if li_data is None:
        agents = load_agents()
        for a in agents:
            if a.id.endswith(street_id.capitalize()) or a.id.endswith(street_id):
                li_data = a
                break
        else:
            raise ValueError(f"Agent data for {street_id} not found.")

    activities = []
    if li_data.layer_2_dynamic_activities and "value" in li_data.layer_2_dynamic_activities:
        activities = li_data.layer_2_dynamic_activities["value"]
    opinions = []
    if li_data.layer_4_citizen_opinions and "value" in li_data.layer_4_citizen_opinions:
        opinions = li_data.layer_4_citizen_opinions["value"]

    activities_json = json.dumps(activities, ensure_ascii=False)
    opinions_json = json.dumps(opinions, ensure_ascii=False)

    instruction = f"""你是「{street_name}」的地基主前哨 (agent_id: {agent_id})。

這是一個快速舉手階段。根據使用者的問題，以及你轄區內的：

【動態活動（layer_2）】
{activities_json}

【市民意見/通報（layer_4）】
{opinions_json}

判斷你的轄區是否有能回答這個問題的資料。
請只給出 0 到 10 的 confidence_score（0 分 = 完全無關，10 分 = 有直接相關資料），以及一句話說明 reason。
回傳必須是 ScoutResult JSON 格式。"""

    return LlmAgent(
        name=f"dijizhu_community_scout_{street_id}",
        model=_MODEL,
        description="地基主社區前哨，評估能否回答社區問題",
        instruction=instruction,
        output_schema=ScoutResult,
    )


def create_community_agent(
    street_id: str,
    street_name: str,
    agent_id: str,
    li_data: LiAgentData | None = None,
) -> LlmAgent:
    """Community responder: answers a community question using layer_2 + layer_4 data."""
    if li_data is None:
        agents = load_agents()
        for a in agents:
            if a.id.endswith(street_id.capitalize()) or a.id.endswith(street_id):
                li_data = a
                break
        else:
            raise ValueError(f"Agent data for {street_id} not found.")

    activities = []
    if li_data.layer_2_dynamic_activities and "value" in li_data.layer_2_dynamic_activities:
        activities = li_data.layer_2_dynamic_activities["value"]
    opinions = []
    if li_data.layer_4_citizen_opinions and "value" in li_data.layer_4_citizen_opinions:
        opinions = li_data.layer_4_citizen_opinions["value"]

    activities_json = json.dumps(activities, ensure_ascii=False, indent=2)
    opinions_json = json.dumps(opinions, ensure_ascii=False, indent=2)

    instruction = f"""你是「{street_name}」的地基主 (agent_id: {agent_id})，守護這條街道的神明管理員。

━━━━━━ 轄區社區資料庫（已預載） ━━━━━━

【動態活動（近期活動、展覽、攤販等）】
{activities_json}

【市民意見與通報（居民反映的問題與狀態）】
{opinions_json}

━━━━━━ 任務 ━━━━━━

收到一個社區問題後，根據上述資料回答。
- 如果有相關資料，明確引用 title / content 作為依據，並列入 sources。
- 如果資料與問題完全無關，answer_text 說「{street_name}目前無相關資訊」，sources 留空。
- 語氣接地氣、有神明威嚴，展現對{street_name}的了解。

⚠️ 回傳必須是 CommunityAnswer JSON：
{{
  "agent_id": "{agent_id}",
  "street_name": "{street_name}",
  "answer_text": "...",
  "sources": ["來源標題1", ...]
}}"""

    from deg.schemas import CommunityAnswer  # noqa: PLC0415
    return LlmAgent(
        name=f"dijizhu_community_{street_id}",
        model=_MODEL,
        description=f"台南{street_name}的地基主，回答社區問題",
        instruction=instruction,
        output_schema=CommunityAnswer,
    )
```

- [ ] **Step 4: Run tests — expect PASS**

```
.venv/Scripts/python -m pytest tests/test_dijizhu_community.py -v
```

- [ ] **Step 5: Commit**

```
git add agents/dijizhu/agent.py tests/test_dijizhu_community.py
git commit -m "feat: add create_community_scout and create_community_agent to dijizhu"
```

---

### Task 3: Add community judge to tudigong/agent.py

**Files:**
- Modify: `agents/tudigong/agent.py`

The judge reads all `CommunityAnswer` objects from the session context and writes a `CommunityQueryResult`.

- [ ] **Step 1: Add `create_community_judge()` to `agents/tudigong/agent.py`**

Add after the existing `create_dynamic_pipeline()` function, before `root_agent`:

```python
_COMMUNITY_JUDGE_INSTRUCTION = """你是土地公，台南中西區的守護神。

剛才有凡人向神明提了一個社區問題，各里地基主已各自回報了自己轄區的資訊（以 CommunityAnswer 格式呈現在對話記錄中）。

【裁決步驟】
1. 閱讀所有地基主的 answer_text 與 sources。
2. 整合相關資訊，去除「無相關資訊」的回應，保留有實質內容的。
3. 將所有有效回答整理成 answers 陣列（直接引用地基主回報的資料，不要虛構）。
4. 以土地公口吻（慈悲、幽默、充滿台南語感）寫下 tudigong_summary（至少 2 句）。
   例如：「老人家我查了一輪，這幾個地方要注意…」

【回傳格式】必須回傳完整的 CommunityQueryResult JSON：
- question: 使用者原始問題（從對話中取出）
- answers: 地基主回報的有效 CommunityAnswer 陣列（只保留 answer_text 非空的）
- tudigong_summary: 土地公口吻的整體總結（繁體中文，至少 2 句）"""


def create_community_judge() -> LlmAgent:
    """Create the 土地公 community Q&A judge that consolidates CommunityAnswer objects."""
    from deg.schemas import CommunityQueryResult  # noqa: PLC0415
    return LlmAgent(
        name="tudigong_community_judge",
        model=_MODEL,
        description="土地公：整合各地基主社區回答，給出神明口吻的社區問答總結。",
        instruction=_COMMUNITY_JUDGE_INSTRUCTION,
        output_schema=CommunityQueryResult,
    )
```

- [ ] **Step 2: Quick sanity check (import only)**

```
.venv/Scripts/python -c "
import sys; sys.path.insert(0, 'agents')
from tudigong.agent import create_community_judge
j = create_community_judge()
print('OK:', j.name)
"
```

Expected: `OK: tudigong_community_judge`

- [ ] **Step 3: Commit**

```
git add agents/tudigong/agent.py
git commit -m "feat: add create_community_judge to tudigong"
```

---

### Task 4: Add community A2UI surface helpers to surfaces.py

**Files:**
- Modify: `deg/a2ui/surfaces.py`

Surface layout for community flow:
```
root
├── community-input  (input stage)
└── [after submit]
    ├── community-question-card   (shows the question)
    ├── answers-row               (List bound to /answers, template: answer-card)
    └── community-summary-card    (土地公 summary, starts as placeholder)
```

- [ ] **Step 1: Append to `deg/a2ui/surfaces.py`**

Add after the `blessing_components()` function:

```python
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
         "children": ["community-q-card", "answers-row", "community-summary-card"]},
        # — question recap —
        {"id": "community-q-card", "component": "Card", "child": "community-q-body"},
        {"id": "community-q-body", "component": "Column",
         "children": ["community-q-title", "community-q-text"]},
        {"id": "community-q-title", "component": "Text",
         "text": "土地公正在問各地神明…", "variant": "h2"},
        {"id": "community-q-text", "component": "Text", "text": {"path": "/community/question"}},
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
```

- [ ] **Step 2: Sanity check import**

```
.venv/Scripts/python -c "
from deg.a2ui.surfaces import (
    COMMUNITY_SURFACE_ID, community_input_components,
    community_negotiation_components, community_answer_data,
    community_summary_components, community_summary_data,
)
print('OK, SURFACE_ID =', COMMUNITY_SURFACE_ID)
comps = community_input_components()
print('input components count:', len(comps))
"
```

Expected: `OK, SURFACE_ID = community` and a component count.

- [ ] **Step 3: Commit**

```
git add deg/a2ui/surfaces.py
git commit -m "feat: add community ask A2UI surface helpers"
```

---

### Task 5: Add community gateway endpoint to gateway.py

**Files:**
- Modify: `apps/api/gateway.py`

Two helper functions + one new WebSocket endpoint `/ws/ask/a2ui`.

Pipeline:
1. Receive question text from client
2. `_run_community_scout()` → top 5 agents with relevant data
3. `_run_community_answers()` → parallel `CommunityAnswer` objects, streamed to client
4. Community judge → `CommunityQueryResult.tudigong_summary`, streamed to client

- [ ] **Step 1: Add imports at top of `apps/api/gateway.py`**

Find the existing import block for `deg.schemas` and add to it:

```python
from deg.schemas import (  # noqa: E402
    BiddingProposal,
    Blessing,
    CommunityAnswer,          # ← new
    CommunityQueryResult,     # ← new
    DebateMessage,
    JudgmentResult,
    LatLng,
    TaskBroadcast,
    Wish,
    WishAnalysis,
    WuyingOutput,
)
```

Find the existing surface imports and add:

```python
from deg.a2ui.surfaces import (  # noqa: E402
    SURFACE_ID,
    WISH_SURFACE_ID,
    COMMUNITY_SURFACE_ID,              # ← new
    bid_data,
    debate_data,
    blessing_components,
    broadcast_data,
    clarification_components,
    community_answer_data,             # ← new
    community_input_components,        # ← new
    community_negotiation_components,  # ← new
    community_summary_components,      # ← new
    community_summary_data,            # ← new
    intent_input_components,
    judgment_components,
    judgment_data,
    negotiation_components,
    wish_input_components,
)
```

Find the existing tudigong import and add:

```python
from tudigong.agent import create_community_judge, create_dynamic_pipeline, get_random_mood  # noqa: E402
```

Find the existing dijizhu import and add:

```python
from dijizhu.agent import create_community_agent, create_community_scout, create_scout  # noqa: E402
```

- [ ] **Step 2: Add `_run_community_scout()` helper**

Add after the existing `_run_scout_round()` function in `apps/api/gateway.py`:

```python
async def _run_community_scout(
    session_service: InMemorySessionService,
    question: str,
) -> list[str]:
    from deg.seed.loader import load_agents
    from google.adk.agents import ParallelAgent

    all_li = load_agents()
    scouts = []
    for li in all_li:
        street = li.to_street()
        scouts.append(
            create_community_scout(street.street_id, street.name, street.agent_id, li)
        )

    scout_round = ParallelAgent(name="community_scout_round", sub_agents=scouts)
    runner = Runner(agent=scout_round, app_name="deg", session_service=session_service)
    session_id = uuid4().hex
    await session_service.create_session(app_name="deg", user_id="gateway", session_id=session_id)
    msg = genai_types.Content(role="user", parts=[genai_types.Part(text=question)])

    from deg.schemas import ScoutResult

    results: list[ScoutResult] = []
    async for event in runner.run_async(user_id="gateway", session_id=session_id, new_message=msg):
        if event.is_final_response() and event.content and event.content.parts:
            text = event.content.parts[0].text or ""
            try:
                res = ScoutResult.model_validate_json(_extract_json(text))
                results.append(res)
            except Exception as e:
                logger.warning("Community scout parse failed: %s", e)

    results.sort(key=lambda x: x.confidence_score, reverse=True)
    top = results[:5]
    if not top:
        raise RuntimeError("所有地基主均表示與問題無關。")
    return [r.agent_id for r in top]
```

- [ ] **Step 3: Add `_run_community_answers()` helper**

Add after `_run_community_scout()`:

```python
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
        agents.append(
            create_community_agent(street.street_id, street.name, street.agent_id, li)
        )

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
```

- [ ] **Step 4: Add `/ws/ask/a2ui` WebSocket endpoint**

Add after the existing `ws_wish_a2ui` endpoint, inside `create_app()`:

```python
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
            selected_ids = await _run_community_scout(session_service, question)

            await ws.send_json({"a2uiPhase": "answering"})
            await ws.send_json(update_components(COMMUNITY_SURFACE_ID, community_negotiation_components()))
            await ws.send_json(update_data_model(COMMUNITY_SURFACE_ID, "/community/question", question))
            await ws.send_json(update_data_model(COMMUNITY_SURFACE_ID, "/answers", []))

            answers = await _run_community_answers(session_service, question, selected_ids)

            # Stream answers one by one
            for i, answer in enumerate(answers):
                await ws.send_json(
                    update_data_model(COMMUNITY_SURFACE_ID, f"/answers/{i}", community_answer_data(answer))
                )

            # Run community judge
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
                    await ws.send_json(
                        update_components(COMMUNITY_SURFACE_ID, community_summary_components())
                    )
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
```

- [ ] **Step 5: Smoke test (server starts without errors)**

```
.venv/Scripts/python -c "
from apps.api.gateway import create_app
app = create_app()
routes = [r.path for r in app.routes]
assert '/ws/ask/a2ui' in routes, f'Missing route, got: {routes}'
print('OK — routes include /ws/ask/a2ui')
"
```

- [ ] **Step 6: Commit**

```
git add apps/api/gateway.py
git commit -m "feat: add community ask gateway endpoint /ws/ask/a2ui"
```

---

### Task 6: Add frontend /ask page

**Files:**
- Create: `apps/web/app/ask/page.tsx`

This mirrors `apps/web/app/page.tsx` structure: WebSocket connects to `/ws/ask/a2ui`, A2UI Renderer draws everything, onEvent handles `submit_community`.

- [ ] **Step 1: Create `apps/web/app/ask/page.tsx`**

```tsx
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Renderer, EventContext } from "@/lib/a2ui/Renderer";
import { applyMessage, emptySurface } from "@/lib/a2ui/store";
import { getAtPointer, setAtPointer } from "@/lib/a2ui/pointer";
import { SurfaceState, A2uiMessage } from "@/lib/a2ui/types";
import { IncenseBackground } from "@/components/theater/IncenseBackground";
import { TempleNav } from "@/components/TempleNav";

const WS_URL =
  process.env.NEXT_PUBLIC_GATEWAY_WS_COMMUNITY ??
  "ws://127.0.0.1:8080/ws/ask/a2ui";

type Conn =
  | "connecting"
  | "open"
  | "routing"
  | "answering"
  | "done"
  | "error"
  | "failed";

export default function AskPage() {
  const [state, setState] = useState<SurfaceState>(emptySurface);
  const [conn, setConn] = useState<Conn>("connecting");
  const [errorDetail, setErrorDetail] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const stateRef = useRef<SurfaceState>(state);
  const terminalRef = useRef(false);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    let ws: WebSocket;
    try {
      ws = new WebSocket(WS_URL);
    } catch {
      const t = setTimeout(() => setConn("failed"), 0);
      return () => clearTimeout(t);
    }
    wsRef.current = ws;

    ws.onopen = () => setConn((c) => (c === "connecting" ? "open" : c));

    ws.onmessage = (ev) => {
      let msg: A2uiMessage;
      try {
        msg = JSON.parse(ev.data as string) as A2uiMessage;
      } catch {
        return;
      }
      if ("a2uiDone" in msg) {
        terminalRef.current = true;
        setConn("done");
        return;
      }
      if ("a2uiError" in msg) {
        terminalRef.current = true;
        setErrorDetail((msg as { a2uiError: string }).a2uiError);
        setConn("error");
        return;
      }
      if ("a2uiPhase" in msg) {
        const phase = (msg as { a2uiPhase: string }).a2uiPhase;
        if (phase === "routing") setConn("routing");
        if (phase === "answering") setConn("answering");
        return;
      }
      setState((prev) => applyMessage(prev, msg));
    };

    ws.onerror = () => {
      if (!terminalRef.current) setConn((c) => (c === "done" ? c : "failed"));
    };
    ws.onclose = () => {
      if (terminalRef.current) return;
      setConn((c) =>
        c === "done" || c === "error" || c === "answering" || c === "open"
          ? c
          : "failed",
      );
    };

    return () => {
      terminalRef.current = true;
      try { ws.close(); } catch { /* noop */ }
      wsRef.current = null;
    };
  }, []);

  const onEvent = useCallback(async (name: string, context: EventContext) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    if (name === "submit_community") {
      const fromCtx = typeof context.question === "string" ? context.question : null;
      const fromModel = getAtPointer(stateRef.current.dataModel, "/community/question");
      const question =
        (fromCtx ?? (typeof fromModel === "string" ? fromModel : "")) || "";
      if (!question.trim()) return;
      ws.send(JSON.stringify({ question }));
      setConn("routing");
    }
  }, []);

  const onDataModelChange = useCallback((path: string, value: unknown) => {
    setState((prev) => ({
      ...prev,
      dataModel: setAtPointer(prev.dataModel, path, value),
    }));
  }, []);

  const offline = conn === "failed";

  return (
    <IncenseBackground>
      <main className="sanctum">
        <TempleNav active="ask" />

        <div className="sanctum__brand">
          <span className="sanctum__seal">問</span>
          <span className="sanctum__kicker">ASK · 問土地公社區大小事</span>
        </div>

        <div className="live-status">
          <span className="live-status__dot" data-conn={conn} />
          <span className="live-status__label">{statusLabel(conn)}</span>
        </div>

        {conn === "error" && (
          <div style={{ marginTop: "0.6rem" }}>
            {errorDetail && (
              <p
                className="a2-text a2-text--caption"
                style={{ color: "var(--color-error, #f87171)", marginBottom: "0.8rem" }}
              >
                {errorDetail}
              </p>
            )}
            <button
              className="a2-button a2-button--primary"
              onClick={() => window.location.reload()}
            >
              重新連接
            </button>
          </div>
        )}

        {offline ? (
          <div className="temple-closed" role="alert">
            <div className="temple-closed__seal">闭</div>
            <h2 className="temple-closed__title">土地公廟暫時關閉</h2>
            <p className="temple-closed__body">
              請先啟動 gateway（
              <code>uvicorn apps.api.gateway:app</code>）。
            </p>
          </div>
        ) : (
          <Renderer
            state={state}
            onEvent={onEvent}
            onDataModelChange={onDataModelChange}
          />
        )}

        {!offline && conn === "connecting" && state.surfaceId === null && (
          <p className="a2-text a2-text--caption" style={{ marginTop: "1.6rem" }}>
            正在連接土地公廟…
          </p>
        )}
      </main>
    </IncenseBackground>
  );
}

function statusLabel(conn: Conn): string {
  switch (conn) {
    case "connecting": return "連接中…";
    case "open":       return "土地公已臨壇 · 請叩問";
    case "routing":    return "各地神明正在評估…";
    case "answering":  return "地基主們回報中…";
    case "done":       return "土地公神諭已下";
    case "error":      return "問法中斷";
    case "failed":     return "廟門深鎖";
  }
}
```

- [ ] **Step 2: Add "ask" to `TempleNav`**

Find `apps/web/src/components/TempleNav.tsx` (or wherever TempleNav is defined) and add an Ask link. The component likely accepts an `active` prop. Add a nav item:

```tsx
// Inside the nav items array / JSX:
{ href: "/ask", label: "問土地公", key: "ask" }
```

The exact edit depends on TempleNav's current structure — read the file first, then add the link following the same pattern as the existing "explore" and "wish" items.

- [ ] **Step 3: Build check**

```
cd apps/web
npm run build 2>&1 | tail -20
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 4: Commit**

```
git add apps/web/app/ask/page.tsx
git commit -m "feat: add /ask community Q&A frontend page"
```

---

## Self-Review

### Spec coverage
- ✅ Non-travel flow (community Q&A, not travel itinerary)
- ✅ 土地公 acts as aggregator/moderator (community judge)
- ✅ Multiple relevant agents surface answers (community answer round)
- ✅ Question types: events (layer_2), repairs/complaints (layer_4)
- ✅ Relevance-based selection (community scout round, top 5)
- ✅ Streaming answers to frontend
- ✅ New endpoint `/ws/ask/a2ui`
- ✅ New frontend page `/ask`

### Placeholder scan
- All steps have concrete code, no "TBD" or "implement later"
- TempleNav edit flagged as "read file first" — intentional, file path unknown

### Type consistency
- `CommunityAnswer` defined in Task 1, used in Tasks 2, 4, 5 (consistent fields)
- `CommunityQueryResult` defined in Task 1, used in Tasks 3, 4, 5
- `community_answer_data()` in Task 4 returns dict with keys `street_name`, `answer_text`, `sources_label` — matched by `answer-card-*` components in same task
- `community_summary_data()` returns `{"tudigong_summary": ...}` — matched by `/community/tudigong_summary` path in summary component
- `COMMUNITY_SURFACE_ID = "community"` consistent across Tasks 4 and 5
- `create_community_scout` / `create_community_agent` / `create_community_judge` names consistent across Tasks 2, 3, 5
