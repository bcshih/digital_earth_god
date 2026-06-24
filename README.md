# 數位土地公 Digital Earth God

[繁體中文](README.zh-TW.md) | English

> **以神明為喻的多智能體系統，守護台南中西區的文化探索與社區治理。**
>
> A Multi-Agent System (MAS) that reimagines Tainan City's cultural heritage exploration through the metaphor of Taiwanese folk religion — where a **土地公 (Earth God)** orchestrates **20 地基主 (Street Guardians)** to bid, debate, and negotiate the best travel itineraries and community insights for you.

**🌐 Live Demo:** [https://digital-earth-god.netlify.app](https://digital-earth-god.netlify.app)  
*(Backend on Railway · Frontend on Netlify)*

---

## ✨ Features

| Flow | Description | WebSocket |
|------|-------------|-----------|
| 🧭 **向土地公問路** (Explore) | Input your travel intent + GPS → 20 street guardians scout, bid, debate → Earth God judges and produces a multi-day itinerary with a Leaflet map | `/ws/explore/a2ui` |
| 🏘️ **問土地公** (Community Ask) | Ask a community question → guardians evaluate relevance, provide answers → Earth God consolidates a summary | `/ws/ask/a2ui` |
| 🏛️ **里長大會** (Council) | Raise a community topic → multi-round deliberation among guardians with support/oppose/question stances → Earth God delivers a verdict | `/ws/council/a2ui` |
| 🙏 **向土地公許願** (Wish) | Submit a prayer/wish to the Earth God | `/ws/wish` |

### Key Highlights

- **Contract Net Protocol** — Decentralized task allocation: broadcast → scout → bid → debate → judge
- **A2UI (Agent-to-UI)** — Server pushes component trees + data patches over WebSocket; the frontend renders them with a generic renderer + domain-specific decorators (seal stamps, jiaobei divination, incense backgrounds)
- **5 Agent Types** — 土地公 (orchestrator), 20× 地基主 (street guardians), 虎爺 (Tiger God), 巡境使 (Patrol Officer), 五營兵將 (Five Camps)
- **20 Autonomous Street Agents** — Each guardian has real NLSC village boundary polygons (from official 臺灣國土測繪中心 shapefiles) and pre-loaded spatial data (POIs, history, social posts) for one neighborhood in Tainan's West Central District
- **Council: up to 15 participants** — Multi-round deliberation across the most relevant guardians; map stays at static overview (no per-statement zoom); compact inline transcript
- **Divine Personality** — Random "mood of the day" phrases inject personality into the Earth God's judgments
- **Theatrical UI** — Vermillion seal-stamp animations, jiaobei (擲筊) divination reveals, incense smoke backgrounds, chat-room-style scout reports, and mobile-friendly slide-out panels
- **Cloud Deployed** — Backend on Railway (Docker/FastAPI), Frontend on Netlify (Next.js static export)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────┐ │
│  │ Explore  │  │   Ask    │  │ Council  │  │Wish │ │
│  │ /        │  │ /ask     │  │ /council │  │/wish│ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──┬──┘ │
│       │ WS          │ WS          │ WS         │ WS │
└───────┼─────────────┼─────────────┼────────────┼────┘
        ▼             ▼             ▼            ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Gateway (:8080)                 │
│         apps/api/gateway.py                         │
│                                                     │
│  ┌─────────────────────────────────┐                │
│  │  土地公 Pipeline (ADK)          │                │
│  │  ┌───────────┐                  │                │
│  │  │RouterAgent│ → Top N agents   │                │
│  │  └───────────┘                  │                │
│  │  ┌──────────────────────────┐   │                │
│  │  │ParallelAgent (Scout ×20) │   │                │
│  │  └──────────────────────────┘   │                │
│  │  ┌──────────────────────────┐   │                │
│  │  │ParallelAgent (Bid ×N)   │   │                │
│  │  └──────────────────────────┘   │                │
│  │  ┌──────────────────────────┐   │                │
│  │  │ParallelAgent (Debate ×N)│   │                │
│  │  └──────────────────────────┘   │                │
│  │  ┌──────────────────────────┐   │                │
│  │  │LlmAgent (Judge)         │   │                │
│  │  └──────────────────────────┘   │                │
│  └─────────────────────────────────┘                │
└─────────────────────────────────────────────────────┘
        │               │               │
        ▼               ▼               ▼
┌──────────────────────────────────────────────┐
│         Swarm Server (:9000)                 │
│   ┌──────┐  ┌──────┐  ┌──────┐    ┌──────┐  │
│   │神農街│  │海安路│  │正興街│ …  │共20里│  │
│   │:9001 │  │:9002 │  │:9003 │    │      │  │
│   └──────┘  └──────┘  └──────┘    └──────┘  │
│        (A2A JSON-RPC endpoints)              │
└──────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Google Gemini 3.1 Flash Lite |
| Agent Framework | [Google ADK](https://google.github.io/adk-docs/) (Agent Development Kit) |
| Agent Communication | [A2A Protocol](https://github.com/google/A2A) (Agent-to-Agent) |
| Backend | FastAPI + WebSocket · deployed on **Railway** (Docker) |
| Frontend | Next.js 16 (Turbopack) + Motion (Framer Motion) + Leaflet · deployed on **Netlify** (static export) |
| Boundary Data | Official NLSC shapefiles (國土測繪中心) — real village polygon coordinates |
| Data | NGSI-LD inspired 5-layer model (spatial, dynamic, historical, citizen opinions, metadata) |

---

## 📁 Project Structure

```
digital-earth-god/
├── agents/
│   ├── tudigong/            # 土地公 (Earth God) — orchestrator, judge, council chair, blessing
│   │   ├── agent.py         #   Contract Net pipeline, mood pool, community/council judge
│   │   └── blessing_agent.py#   Wish blessing agent
│   ├── dijizhu/             # 地基主 (Street Guardians) — 20 per-street agents
│   │   ├── agent.py         #   Scout, bidding, debate, community, council speaker agents
│   │   ├── a2a_server.py    #   A2A HTTP server (per street)
│   │   └── swarm_server.py  #   Launch all 20 A2A servers in parallel
│   ├── huye/                # 虎爺 (Tiger God) — mock evidence adapter, A2A server
│   ├── wuying/              # 五營兵將 (Five Camps) — intent + wish categorizer agents
│   └── xunjingshi/          # 巡境使 (Patrol Officer) — mock evidence adapter, A2A server
│
├── apps/
│   ├── api/
│   │   └── gateway.py       # FastAPI gateway — 4 WS endpoints, pipeline orchestration
│   └── web/                 # Next.js 16 frontend
│       ├── app/
│       │   ├── page.tsx           #   Explore (向土地公問路)
│       │   ├── ask/page.tsx       #   Community Ask (問土地公)
│       │   ├── council/page.tsx   #   Council (里長大會)
│       │   ├── wish/page.tsx      #   Wish (許願)
│       │   └── dashboard/page.tsx #   Dashboard (城市風向球)
│       ├── components/
│       │   ├── theater/           #   SealStamp, Jiaobei, IncenseBackground
│       │   ├── NegotiationBoard.tsx   # Compact bid/debate viewer with pagination
│       │   ├── ChatBubble.tsx         # Scout chat-room bubbles
│       │   ├── CouncilMap.tsx         # Reactive 里 boundary map (Leaflet, SSR-safe wrapper)
│       │   └── ResultMap.tsx          # Leaflet itinerary map
│       └── lib/a2ui/          # Generic A2UI renderer
│           └── Renderer.tsx
│
├── deg/                       # Core library (pip install -e .)
│   ├── schemas/
│   │   └── contracts.py       #   Pydantic models (TaskBroadcast → CouncilVerdict)
│   ├── a2ui/
│   │   ├── __init__.py        #   A2UI protocol (state, patches, builder)
│   │   └── surfaces.py        #   Component tree builders per flow (explore/ask/council/wish)
│   ├── adapters/              #   Sensor + social data adapters (虎爺/巡境使 evidence)
│   ├── warmdata/              #   SQLite wish store (deg/warmdata/store.py)
│   ├── mcp/spatial_db/        #   MCP spatial database for POI queries
│   └── seed/loader.py         #   Load 5-layer NGSI-LD agent data from JSON
│
├── dijizu_agent/              # 20 li JSON data files (5-layer NGSI-LD per neighborhood)
│   ├── 五條港里.json           # … (20 files total)
│   └── …
│
├── data/seed/
│   ├── streets.json           # Street / POI seed data
│   ├── sensor.json            # Sensor readings seed data
│   └── social.json            # Social / citizen opinion seed data
│
├── tests/                     # 80+ unit tests (integration tests skip without API key)
├── docs/                      # Design documents & feature plans
├── scripts/demo.py            # CLI demo script
├── start.ps1                  # One-click startup script (Windows)
├── pyproject.toml             # Python project config
└── .env.example               # Environment variable template
```

---

## 🚀 Quick Start

### Prerequisites

- **Python** ≥ 3.11
- **Node.js** ≥ 20
- **Google Gemini API Key** ([Get one here](https://aistudio.google.com/apikey))

### 1. Clone & Install

```bash
git clone https://github.com/bcshih/digital_earth_god.git
cd digital_earth_god

# Python dependencies
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -e ".[dev]"

# Frontend dependencies
cd apps/web
npm install
cd ../..
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your Gemini API key:
#   GOOGLE_API_KEY=your-gemini-api-key-here
```

### 3. Start Everything

**Option A: One-click (Windows PowerShell)**

```powershell
.\start.ps1
```

This will start the Swarm Server, FastAPI Gateway, and Next.js frontend, then open your browser.

**Option B: Manual (3 terminals)**

```bash
# Terminal 1 — Swarm Server (20 地基主 A2A agents)
python agents/dijizhu/swarm_server.py

# Terminal 2 — FastAPI Gateway
uvicorn apps.api.gateway:app --host 127.0.0.1 --port 8080 --reload

# Terminal 3 — Next.js Frontend
cd apps/web && npm run dev
```

### 4. Open Browser

Navigate to **http://localhost:3000** and start exploring Tainan!

---

## 🎮 How It Works

### Explore Flow (向土地公問路)

1. **You** type a travel intent (e.g., "我想找老巷弄裡的文青咖啡廳") and share your GPS location
2. **土地公** broadcasts a `TaskBroadcast` to all 20 street guardians
3. **20 Scouts** quickly evaluate relevance (0-10 confidence score) — results stream in real-time as chat bubbles
4. **Top N Guardians** are selected and submit full `BiddingProposal` with POIs, fitness scores, and reasoning
5. **Debate Round** — Guardians critique each other's proposals and defend their streets
6. **土地公 Judge** — The Earth God reads all bids + debates, applies today's divine mood, and produces a `JudgmentResult` with a curated multi-day itinerary
7. **擲筊 (Jiaobei)** — The verdict is revealed with a divination animation, followed by an interactive Leaflet map

### Community Ask Flow (問土地公)

1. Ask a community question (e.g., "最近中西區有什麼活動？")
2. Scouts evaluate which neighborhoods have relevant data
3. Selected guardians provide detailed answers from their local data
4. Earth God consolidates all answers into a unified summary

### Council Flow (里長大會)

1. Raise a topic for discussion (e.g., "海安路的交通改善")
2. Up to 15 most relevant guardians join; up to 3 deliberation rounds
3. Each guardian picks a stance (support / oppose / question / inform / silent) and speaks in ≤ 40 characters — compact statements stream in real-time
4. The council map highlights the speaking boundary in gold; stance colors update as the debate unfolds; response lines connect who is replying to whom
5. Earth God delivers a final verdict summarizing consensus and disagreements

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test files
pytest tests/test_schemas.py
pytest tests/test_gateway.py
```

> **Note**: Gateway tests require `google-adk` to be installed. Schema tests run independently.

---

## 🛠️ Utilities

The project includes a visual **Agent Editor** to easily manage and edit the JSON-LD NGSI-LD files of the 20 street guardians.

1. Run the local backend: `python scripts/agent_editor.py`
2. Open your browser to [http://localhost:8081](http://localhost:8081)
3. Select any neighborhood from the left sidebar to edit the agent's persona, boundaries, and add infinite "Local Observations". Changes are saved directly to the local files.

---

## 📐 Data Model

The system uses a standard JSON-LD graph structure based on NGSI-LD. Each neighborhood contains a dataset with multiple entities:

1. **VillageAgent**: The core entity representing the neighborhood. Contains metadata (personality, name), spatial boundaries (GeoJSON polygons), and historical context.
2. **LocalObservation**: Granular data points representing events, locations, or citizen feedback within the neighborhood. These are dynamically loaded into the agent's 5-layer knowledge base:
   - `daily_activity`, `weather`, `new_shop` → Layer 2 (Dynamic Activities)
   - `poi`, `local_history` → Layer 3 (Spatial & POIs)
   - `citizen_feedback` → Layer 4 (Citizen Opinions)

> **Note**: To prevent LLM context overflow during parallel execution, the data loader (`deg/seed/loader.py`) intelligently truncates observations to the Top 15 most relevant entities per agent.

### Key Schemas (Pydantic)

- `TaskBroadcast` — Intent + GPS + constraints broadcast to all agents
- `ScoutResult` — Quick confidence score (0-10) + one-line reason
- `BiddingProposal` — Full proposal with candidate POIs, fitness score, reasoning
- `DebateMessage` — Inter-agent debate text
- `JudgmentResult` — Final itinerary with `ItineraryStop[]`, recommendation, reasoning
- `CommunityAnswer` / `CommunityQueryResult` — Community Q&A models
- `CouncilStatement` / `CouncilAlignment` / `CouncilVerdict` — Council deliberation models (stance: support/oppose/question/inform/silent)

---

## 🎨 A2UI Protocol

The **Agent-to-UI (A2UI)** protocol decouples the agent pipeline from the frontend:

1. **Server** pushes a component tree (JSON) defining the UI structure
2. **Server** pushes data model patches as agent results arrive
3. **Frontend** renders the tree with a generic `Renderer` component
4. **Decorators** layer domain-specific presentation (animations, maps) on top

This allows the same agent pipeline to power different frontends (web, mobile, voice) without changing agent code.

---

## 🌐 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key | (required) |
| `GOOGLE_GENAI_USE_VERTEXAI` | Use Vertex AI instead of AI Studio | `FALSE` |
| `NEXT_PUBLIC_GATEWAY_WS` | WebSocket URL for frontend | `ws://127.0.0.1:8080/ws/explore/a2ui` |

---

## 📜 License

This project is part of an academic research initiative on multi-agent systems for smart city applications.

---

<p align="center">
  <strong>🏯 台南・中西區・數位土地公 🏯</strong><br/>
  <em>Built with Google ADK · A2A Protocol · Gemini · Next.js</em>
</p>
