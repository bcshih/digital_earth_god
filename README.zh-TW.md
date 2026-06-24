# 數位土地公 Digital Earth God

繁體中文 | [English](README.md)

> **以神明為喻的多智能體系統，守護台南中西區的文化探索與社區治理。**
>
> 數位土地公是一個多智能體系統（MAS），它透過台灣民間信仰的隱喻來重新詮釋台南市的文化探索與治理——在這裡，**土地公**作為統籌者，指揮 20 位**地基主**（各里守護神）為您進行競標、辯論，並協商出最佳的旅遊行程與社區洞察。

**🌐 線上展示：** [https://digital-earth-god.netlify.app](https://digital-earth-god.netlify.app)  
*(後端部署於 Railway · 前端部署於 Netlify)*

---

## ✨ 核心功能

| 流程 | 描述 | WebSocket 節點 |
|------|-------------|-----------|
| 🧭 **向土地公問路** (探索) | 輸入您的旅遊意圖與 GPS 位置 → 20 位地基主進行探勘、競標、辯論 → 土地公進行評判，並產出多日遊行程與地圖 | `/ws/explore/a2ui` |
| 🏘️ **問土地公** (社區問答) | 詢問社區相關問題 → 地基主評估相關性並提供解答 → 土地公匯總出總結報告 | `/ws/ask/a2ui` |
| 🏛️ **里長大會** (議會) | 提出社區議題 → 地基主進行多輪審議，表達支持/反對/質疑立場 → 土地公給出最終裁定 | `/ws/council/a2ui` |
| 🙏 **向土地公許願** (祈願) | 向土地公提交您的祈願或訴求 | `/ws/wish` |

### 亮點特色

- **合約網協定 (Contract Net)** — 去中心化任務分配：廣播 → 探勘 → 競標 → 辯論 → 評判。
- **A2UI (Agent-to-UI)** — 伺服器透過 WebSocket 推送元件樹與資料補丁；前端使用通用渲染器搭配領域專屬裝飾器（如印章、擲筊、線香背景）進行渲染。
- **五大神明代理人 (5 Agent Types)** — 土地公（統籌者）、20× 地基主（街道守護神）、虎爺（社群情資）、巡境使（環境感測）、五營兵將（意圖解析）。
- **20 個自治街道代理人** — 每位地基主皆載入真實 NLSC 村里界多邊形（臺灣國土測繪中心官方 shapefile），以及台南中西區各里的空間資料（POI、歷史、社群貼文）。
- **里長大會最多 15 位出席** — 多輪自由討論；地圖保持靜態總覽（不隨發言縮放）；發言以緊湊行內格式串流顯示。
- **神明性格系統** — 土地公每日的「神明心情」會隨機改變，並反映在最終的評判語氣中。
- **劇場式使用者介面** — 朱印蓋章動畫、擲筊揭曉、線香煙霧背景、聊天室風格的探勘回報，以及手機友善的側滑抽屜面板。
- **雲端部署** — 後端部署於 Railway（Docker/FastAPI）、前端部署於 Netlify（Next.js 靜態輸出）。

---

## 🏗️ 系統架構

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────┐ │
│  │ 探索問路 │  │ 社區問答 │  │ 里長大會 │  │祈願 │ │
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
│  │  │RouterAgent│ → 篩選前 N 名    │                │
│  │  └───────────┘                  │                │
│  │  ┌──────────────────────────┐   │                │
│  │  │ParallelAgent (探勘 ×20)  │   │                │
│  │  └──────────────────────────┘   │                │
│  │  ┌──────────────────────────┐   │                │
│  │  │ParallelAgent (競標 ×N)   │   │                │
│  │  └──────────────────────────┘   │                │
│  │  ┌──────────────────────────┐   │                │
│  │  │ParallelAgent (辯論 ×N)   │   │                │
│  │  └──────────────────────────┘   │                │
│  │  ┌──────────────────────────┐   │                │
│  │  │LlmAgent (評判法官)       │   │                │
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

### 技術堆疊

| 階層 | 技術 |
|-------|-----------|
| LLM | Google Gemini 3.1 Flash Lite |
| 代理人框架 | [Google ADK](https://google.github.io/adk-docs/) (Agent Development Kit) |
| 通訊協定 | [A2A Protocol](https://github.com/google/A2A) (Agent-to-Agent) |
| 後端 | FastAPI + WebSocket |
| 前端 | Next.js 16 (Turbopack) + Motion (Framer Motion) + Leaflet |
| 資料 | 靈感來自 NGSI-LD 的五層資料架構（空間、動態、歷史、市民意見、元資料） |

---

## 📁 專案目錄結構

```
digital-earth-god/
├── agents/
│   ├── tudigong/            # 土地公 — 統籌者、評判者、大會主席、賜福
│   ├── dijizhu/             # 地基主 — 20 個里級代理人（探勘、競標、辯論、大會發言）
│   ├── huye/                # 虎爺 — 模擬社群情資適配器、A2A 伺服器
│   ├── wuying/              # 五營兵將 — 意圖解析與祈願分類代理人
│   └── xunjingshi/          # 巡境使 — 模擬感測器資料適配器、A2A 伺服器
│
├── apps/
│   ├── api/
│   │   └── gateway.py       # FastAPI 閘道器 — 管理 WebSocket 與工作流編排
│   └── web/                 # Next.js 16 前端
│       ├── app/             # 各頁面路由（探索、問事、大會、許願、儀表板）
│       ├── components/      # 共用元件、地圖與劇場式特效（印章、擲筊等）
│       └── lib/a2ui/        # A2UI 通用渲染器
│
├── deg/                       # 核心函式庫 (pip install -e .)
│   ├── schemas/             # Pydantic 資料模型
│   ├── a2ui/                # A2UI 協定（狀態、補丁、建構器）
│   ├── adapters/            # 虎爺/巡境使等資料適配器
│   ├── warmdata/            # 溫資料 (SQLite 祈願儲存庫)
│   ├── mcp/spatial_db/      # MCP 空間資料庫
│   └── seed/loader.py       # NGSI-LD 代理人資料載入器
│
├── dijizu_agent/              # 20 個里的 JSON 資料檔（每份為 5 層 NGSI-LD 架構）
├── data/seed/                 # 種子資料（街道 POI、感測器、社群資料）
├── tests/                     # 80+ 單元與整合測試
├── docs/                      # 設計文件與開發計畫
├── start.ps1                  # 一鍵啟動腳本 (Windows)
└── .env.example               # 環境變數範例檔
```

---

## 🚀 快速開始

### 系統需求

- **Python** ≥ 3.11
- **Node.js** ≥ 20
- **Google Gemini API Key** ([在此取得](https://aistudio.google.com/apikey))

### 1. 複製專案與安裝依賴

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
# 編輯 .env 檔案並加入您的 Gemini API 金鑰：
#   GOOGLE_API_KEY=your-gemini-api-key-here
```

### 3. 啟動系統

**選項 A：一鍵啟動 (Windows PowerShell)**

```powershell
.\start.ps1
```

這將依序啟動 Swarm Server、FastAPI Gateway 以及 Next.js 前端，並在 10 秒後開啟瀏覽器。

**選項 B：手動啟動 (需開啟 3 個終端機)**

```bash
# 終端機 1 — Swarm Server (20 個地基主 A2A 伺服器)
python agents/dijizhu/swarm_server.py

# 終端機 2 — FastAPI Gateway
uvicorn apps.api.gateway:app --host 127.0.0.1 --port 8080 --reload

# 終端機 3 — Next.js 前端
cd apps/web && npm run dev
```

### 4. 開啟瀏覽器

前往 **http://localhost:3000** 開始體驗數位土地公！

---

## 🛠️ 開發工具 (Utilities)

本專案提供了一個視覺化的 **Agent 編輯器 (Agent Editor)**，方便您直接修改 20 個里的 JSON-LD NGSI-LD 資料。

1. 在終端機執行：`python scripts/agent_editor.py`
2. 開啟瀏覽器進入 [http://localhost:8081](http://localhost:8081)
3. 您可以在左側選擇任意一個里，右側會帶出表單供您編輯地基主性格、邊界座標以及無限新增「在地觀察」。點擊儲存後會自動覆寫本地檔案。

---

## 📐 資料模型

本系統採用基於 NGSI-LD 標準的 JSON-LD 圖形架構。每個里的資料集包含多個實體：

1. **VillageAgent (里代理人)**：代表該街區的核心實體，包含元資料（性格設定、名稱）、空間邊界（GeoJSON Polygon）與歷史脈絡。
2. **LocalObservation (在地觀察)**：代表該街區內各項事件、地點或市民反饋的細粒度資料節點。這些節點會被動態載入 Agent 的五層知識庫中：
   * `daily_activity` (日常活動), `weather` (天氣), `new_shop` (新店) → Layer 2 (動態活動)
   * `poi` (景點), `local_history` (在地歷史) → Layer 3 (空間與 POI)
   * `citizen_feedback` (市民回饋) → Layer 4 (市民意見)

> **注意**：為防止平行執行時 LLM 發生 Token 溢出，資料載入器 (`deg/seed/loader.py`) 會自動將每個 Agent 載入的觀察節點截斷，僅保留前 15 筆最重要的實體。

---

## 📜 授權條款

本專案為智慧城市多智能體系統（MAS）學術研究計畫之一部分。

---

<p align="center">
  <strong>🏯 台南・中西區・數位土地公 🏯</strong><br/>
  <em>Built with Google ADK · A2A Protocol · Gemini · Next.js</em>
</p>
