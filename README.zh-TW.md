# 數位土地公 Digital Earth God

[English](README.md) | 繁體中文

> **以神明為喻的多智能體系統，守護台南中西區的文化探索與社區治理。**
>
> 一套以台灣民間信仰為隱喻的多智能體系統（MAS）——**土地公**統籌 **20 位地基主（街區守護神）**，透過競標、辯論與協商，為你規劃最佳旅遊路線，並回答社區治理的各種問題。

---

## ✨ 功能一覽

| 流程 | 說明 | WebSocket |
|------|------|-----------|
| 🧭 **向土地公問路**（探索） | 輸入旅遊意圖＋GPS → 20 位地基主先後偵察、競標、辯論 → 土地公裁決並產出多日行程＋Leaflet 地圖 | `/ws/explore/a2ui` |
| 🏘️ **問土地公**（社區問答） | 提出社區問題 → 地基主評估相關性並回答 → 土地公整合摘要 | `/ws/ask/a2ui` |
| 🏛️ **里長大會**（議事） | 提出議題 → 多輪自由搶話，每輪地基主可表態（支持／反駁／提問／補充／沉默） → 土地公下裁示，地圖呈現共識 | `/ws/council/a2ui` |
| 🙏 **向土地公許願**（許願） | 向土地公許願，五營兵將分類，土地公賜福 | `/ws/wish/a2ui` |

### 特色亮點

- **Contract Net 協議** — 去中心化任務分配：廣播 → 偵察 → 競標 → 辯論 → 裁決
- **A2UI（Agent-to-UI）** — 伺服器透過 WebSocket 推送元件樹與資料補丁；前端用通用 Renderer 渲染，搭配領域裝飾器（印章動畫、擲筊揭示、香煙背景）
- **5 種 Agent 類型** — 土地公（統籌者）、20× 地基主（街區守護神）、虎爺、巡境使、五營兵將
- **20 個自主街區 Agent** — 每位地基主預載一個台南中西區街里的空間資料（景點、歷史、社區輿情）
- **神明個性** — 每次呼叫隨機抽取今日心情語錄，注入土地公的裁決文字
- **廟宇劇場 UI** — 朱砂印章動畫、擲筊（杯珓）儀式揭示、香煙縹緲背景、對話泡泡式偵察回報

---

## 🏗️ 系統架構

```
┌─────────────────────────────────────────────────────────┐
│                    前端（Next.js）                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │  探索 /  │  │ 問答 /ask│  │議事/council│ │許願/wish│ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘  │
│       │ WS          │ WS          │ WS          │ WS    │
└───────┼─────────────┼─────────────┼─────────────┼───────┘
        ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Gateway（:8080）                    │
│         apps/api/gateway.py                             │
│                                                         │
│  ┌───────────────────────────────────────────┐          │
│  │  土地公 Pipeline（Google ADK）             │          │
│  │  ┌──────────┐ → 前 N 名 Agent             │          │
│  │  │RouterAgent│                            │          │
│  │  └──────────┘                             │          │
│  │  ┌────────────────────────┐               │          │
│  │  │ ParallelAgent（偵察×20）│               │          │
│  │  └────────────────────────┘               │          │
│  │  ┌────────────────────────┐               │          │
│  │  │ ParallelAgent（競標×N） │               │          │
│  │  └────────────────────────┘               │          │
│  │  ┌────────────────────────┐               │          │
│  │  │ ParallelAgent（辯論×N） │               │          │
│  │  └────────────────────────┘               │          │
│  │  ┌────────────────────────┐               │          │
│  │  │ LlmAgent（裁決）        │               │          │
│  │  └────────────────────────┘               │          │
│  └───────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────┘
        │               │               │
        ▼               ▼               ▼
┌──────────────────────────────────────────────────┐
│         Swarm Server（:9000）                     │
│  ┌──────┐  ┌──────┐  ┌──────┐    ┌──────┐        │
│  │五條港│  │光賢里│  │兌悅里│ …  │共20里│        │
│  │:9001 │  │:9002 │  │:9003 │    │      │        │
│  └──────┘  └──────┘  └──────┘    └──────┘        │
│        （A2A JSON-RPC 端點）                       │
└──────────────────────────────────────────────────┘
```

### 技術棧

| 層級 | 技術 |
|------|------|
| LLM | Google Gemini 3.1 Flash Lite |
| Agent 框架 | [Google ADK](https://google.github.io/adk-docs/)（Agent Development Kit） |
| Agent 通訊 | [A2A Protocol](https://github.com/google/A2A)（Agent-to-Agent） v0.3 |
| 後端 | FastAPI + WebSocket |
| 前端 | Next.js 16（Turbopack）+ Motion（Framer Motion）+ Leaflet |
| 資料 | NGSI-LD 啟發的 5 層資料模型（空間、動態、歷史、民情、元資料） |

---

## 📁 專案結構

```
digital-earth-god/
├── agents/
│   ├── tudigong/            # 土地公（Earth God）— 統籌者、裁決者、里長大會主席、賜福
│   │   ├── agent.py         #   Contract Net pipeline、心情池、社區/議事裁決
│   │   └── blessing_agent.py#   許願賜福 agent
│   ├── dijizhu/             # 地基主（街區守護神）— 20 個街區 agent
│   │   ├── agent.py         #   偵察、競標、辯論、社區、議事發言 agent
│   │   ├── a2a_server.py    #   每個街區的 A2A HTTP 伺服器
│   │   └── swarm_server.py  #   同時啟動全部 20 個 A2A 伺服器
│   ├── huye/                # 虎爺 — 感測器證據 mock 轉接器，A2A 伺服器
│   ├── wuying/              # 五營兵將 — 意圖 agent + 許願分類器
│   └── xunjingshi/          # 巡境使 — 社群輿情 mock 轉接器，A2A 伺服器
│
├── apps/
│   ├── api/
│   │   └── gateway.py       # FastAPI gateway — 4 個 WS 端點、pipeline 統籌
│   └── web/                 # Next.js 16 前端
│       ├── app/
│       │   ├── page.tsx           #   探索（向土地公問路）
│       │   ├── ask/page.tsx       #   社區問答（問土地公）
│       │   ├── council/page.tsx   #   里長大會
│       │   ├── wish/page.tsx      #   許願（上香）
│       │   └── dashboard/page.tsx #   儀表板（城市風向球）
│       ├── components/
│       │   ├── theater/           #   SealStamp、Jiaobei、IncenseBackground
│       │   ├── NegotiationBoard.tsx   # 競標/辯論緊湊檢視器（含分頁）
│       │   ├── ChatBubble.tsx         # 偵察報告對話泡泡
│       │   ├── CouncilMap.tsx         # 響應式里界地圖（Leaflet，SSR-safe）
│       │   └── ResultMap.tsx          # Leaflet 行程地圖
│       └── lib/a2ui/          # 通用 A2UI 渲染器
│           └── Renderer.tsx
│
├── deg/                       # 核心函式庫（pip install -e .）
│   ├── schemas/
│   │   └── contracts.py       #   Pydantic 資料模型（TaskBroadcast → CouncilVerdict）
│   ├── a2ui/
│   │   ├── __init__.py        #   A2UI 協議（狀態、補丁、建構器）
│   │   └── surfaces.py        #   各流程的元件樹建構器（探索/問答/議事/許願）
│   ├── adapters/              #   感測器與社群資料轉接器（虎爺/巡境使證據）
│   ├── warmdata/              #   SQLite 許願資料庫（store.py）
│   ├── mcp/spatial_db/        #   MCP 空間資料庫（景點查詢）
│   └── seed/loader.py         #   從 JSON 載入 5 層 NGSI-LD agent 資料
│
├── dijizu_agent/              # 20 個里的 JSON 資料檔（每個里一份 5 層資料）
│   ├── 五條港里.json           # … （共 20 個檔案）
│   └── …
│
├── data/seed/
│   ├── streets.json           # 街道 / 景點種子資料
│   ├── sensor.json            # 感測器讀數種子資料
│   └── social.json            # 社群 / 民情種子資料
│
├── tests/                     # 80+ 單元測試（整合測試需 API 金鑰）
├── docs/                      # 設計文件與功能計畫
├── scripts/demo.py            # CLI 示範腳本
├── start.ps1                  # 一鍵啟動腳本（Windows）
├── pyproject.toml             # Python 專案設定
└── .env.example               # 環境變數範本
```

---

## 🚀 快速開始

### 前置需求

- **Python** ≥ 3.11
- **Node.js** ≥ 20
- **Google Gemini API 金鑰**（[在此申請](https://aistudio.google.com/apikey)）

### 1. 複製與安裝

```bash
git clone https://github.com/bcshih/digital_earth_god.git
cd digital_earth_god

# Python 依賴
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -e ".[dev]"

# 前端依賴
cd apps/web
npm install
cd ../..
```

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env，填入你的 Gemini API 金鑰：
#   GOOGLE_API_KEY=your-gemini-api-key-here
```

### 3. 啟動服務

**選項 A：一鍵啟動（Windows PowerShell）**

```powershell
.\start.ps1
```

會自動啟動 Swarm Server、FastAPI Gateway、Next.js 前端並開啟瀏覽器。

**選項 B：手動啟動（3 個終端機）**

```bash
# 終端機 1 — Swarm Server（20 個地基主 A2A agent）
python agents/dijizhu/swarm_server.py

# 終端機 2 — FastAPI Gateway
uvicorn apps.api.gateway:app --host 127.0.0.1 --port 8080 --reload

# 終端機 3 — Next.js 前端
cd apps/web && npm run dev
```

### 4. 開啟瀏覽器

前往 **http://localhost:3000**，開始探索台南！

---

## 🎮 運作原理

### 探索流程（向土地公問路）

1. **你** 輸入旅遊意圖（例如「我想找老巷弄裡的文青咖啡廳」）並分享 GPS 位置
2. **土地公** 向全部 20 位地基主廣播 `TaskBroadcast`
3. **20 位偵察員** 快速評估相關性（0–10 信心分數）—— 結果以對話泡泡即時串流
4. **前 N 名** 被選中，提交完整 `BiddingProposal`（含景點、適切度分數、理由）
5. **辯論輪** —— 地基主互相批評提案並為自己的街區辯護
6. **土地公裁決** —— 土地公讀取所有競標＋辯論，加入今日神明心情，產出 `JudgmentResult`（多日行程）
7. **擲筊揭示** —— 裁決以擲筊動畫揭曉，接著顯示互動式 Leaflet 地圖

### 社區問答流程（問土地公）

1. 提出社區問題（例如「最近中西區有什麼活動？」）
2. 偵察員評估哪些街里有相關資料
3. 入選的地基主從各自的在地資料庫提供詳細回答，以對話泡泡呈現
4. 土地公整合所有回答，輸出統一摘要

### 里長大會流程（Council）

1. 提出議題（例如「海安路應不應該辦共同夜市？」）
2. 多輪自由搶話：每輪地基主可看完前面的逐字稿後決定表態——
   - 🟢 **支持**（附議）
   - 🔴 **反駁**（有意見）
   - 🔵 **提問**（發問）
   - 🟡 **補充**（中性補充）
   - ⬛ **沉默**（本輪不發言）
3. 每則發言以 0.6 秒間隔串流，地圖同步反應：
   - 發言中的里界閃金色光暈＋鏡頭飛移
   - 各里依最新立場著色
   - 回應對象之間連虛線
4. 整輪無人發言則提前結束討論
5. 土地公下裁示，地圖重新著色呈現最終共識

### 許願流程（Wish）

1. 向土地公許願（輸入心願文字）
2. 五營兵將分類許願主題（健康、工作、感情、祈平安…）
3. 土地公閱覽許願，以神明口吻賜福回覆
4. 許願資料存入 SQLite 暖資料庫，儀表板顯示城市整體心願分布

---

## 🧪 測試

```bash
# 執行所有測試
pytest

# 執行特定測試檔
pytest tests/test_contracts.py
pytest tests/test_gateway.py
pytest tests/test_council_schemas.py

# 整合測試（需要真實 Gemini API 金鑰）
pytest -m integration
```

> 整合測試標有 `@pytest.mark.integration`，沒有設定 `GOOGLE_API_KEY` 時會自動跳過。

---

## 📐 資料模型

系統對每個街里採用 5 層 NGSI-LD 啟發式資料模型：

| 層級 | 內容 | 範例 |
|------|------|------|
| Layer 1 | 空間（景點、邊界、質心） | 咖啡廳、廟宇、公園（附經緯度） |
| Layer 2 | 動態活動 | 當前活動、展覽、市集 |
| Layer 3 | 歷史脈絡 | 街道歷史、文化意義 |
| Layer 4 | 民情輿論 | 居民回報、意見、建議 |
| Layer 5 | 元資料 | Agent 個性、街名、行政區 |

### 主要 Pydantic 資料模型

- `TaskBroadcast` — 意圖 + GPS + 限制條件廣播給所有 agent
- `ScoutResult` — 快速信心評分（0–10）+ 一行理由
- `BiddingProposal` — 完整提案（候選景點、適切度分數、理由）
- `DebateMessage` — Agent 間辯論文字
- `JudgmentResult` — 最終行程（含 `ItineraryStop[]`、推薦理由）
- `CommunityAnswer` / `CommunityQueryResult` — 社區問答模型
- `CouncilStatement` / `CouncilAlignment` / `CouncilVerdict` — 里長大會議事模型（立場：support/oppose/question/inform/silent）

---

## 🎨 A2UI 協議

**Agent-to-UI（A2UI）** 協議將 agent pipeline 與前端完全解耦：

1. **伺服器**推送一棵元件樹（JSON），定義 UI 結構
2. **伺服器**隨 agent 結果到達，持續推送資料模型補丁
3. **前端**用通用 `Renderer` 元件渲染整棵樹
4. **Decorator**在上層疊加領域特定的呈現方式（動畫、地圖、泡泡）

這讓同一個 agent pipeline 可以驅動不同前端（網頁、行動裝置、語音）而無須修改 agent 程式碼。A2UI 合約文件詳見 `docs/a2ui-contract.md`。

---

## 🌐 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `GOOGLE_API_KEY` | Google Gemini API 金鑰 | （必填） |
| `GOOGLE_GENAI_USE_VERTEXAI` | 改用 Vertex AI | `FALSE` |
| `NEXT_PUBLIC_GATEWAY_WS` | 探索流程 WS URL | `ws://127.0.0.1:8080/ws/explore/a2ui` |
| `NEXT_PUBLIC_GATEWAY_WS_COMMUNITY` | 問答流程 WS URL | `ws://127.0.0.1:8080/ws/ask/a2ui` |
| `NEXT_PUBLIC_GATEWAY_WS_COUNCIL` | 里長大會 WS URL | `ws://127.0.0.1:8080/ws/council/a2ui` |
| `DEG_WARMDATA_DB` | SQLite 許願資料庫路徑 | `data/warmdata.db` |

---

## 📜 授權

本專案為智慧城市多智能體系統的學術研究成果。

---

<p align="center">
  <strong>🏯 台南・中西區・數位土地公 🏯</strong><br/>
  <em>以 Google ADK · A2A Protocol · Gemini · Next.js 建構</em>
</p>
