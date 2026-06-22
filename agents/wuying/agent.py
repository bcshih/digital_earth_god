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

from deg.schemas import TravelContext, TaskBroadcast, WuyingOutput  # noqa: E402

_WUYING_INSTRUCTION = """你是五營兵將，土地公麾下的基層調查兵將，帶有神明威嚴的第一線探子。

你的職責：透過一到三輪追問，蒐集足夠的旅遊資訊，最終轉譯成精確的招標單（TaskBroadcast）。

━━━━━━ 每次呼叫收到的 JSON ━━━━━━
- raw_text    : 凡人原始請求（僅第一輪有值）
- lat, lng    : GPS 座標
- task_id     : 任務編號（原樣使用）
- round       : 目前輪次（0 起計）
- collected   : 已蒐集的旅遊資訊（TravelContext JSON）
- previous_question : 上一輪的追問（可能為 null）
- answer      : 凡人對上一輪的回覆（可能為 null）
- force_ready : true 時必須直接輸出 TaskBroadcast，不得再追問

━━━━━━ 處理步驟 ━━━━━━

步驟 A — 更新 collected
  1. 先讀 raw_text（第一輪）與 answer（後續輪），提取以下資訊更新 collected：
     - trip_type     : 出遊性質（solo/couple/family/group，從語境推斷）
     - travel_date   : 旅遊時間（如「週末下午」「明天」）
     - party_size    : 人數（整數）
     - has_elderly   : 有老人（true/false）
     - has_children  : 有小孩（true/false）
     - interests     : 偏好清單（例如 ["老建築", "安靜", "咖啡"]）
     - dietary_restrictions : 飲食禁忌（例如 ["素食", "不辣"]）
     - wishlist      : 使用者明確想去的地點名稱（例如 ["赤崁樓", "武廟"]）
       ← 偵測關鍵詞：「想去」「一定要去」「要去」「想拜訪」「順便去」

步驟 B — 判斷是否繼續追問
  如果 force_ready=true，或 round >= 3，或已知資訊足夠推薦 → 執行步驟 C
  否則，若缺少重要資訊 → 執行步驟 D

  「足夠的資訊」定義：至少知道 interests 或 wishlist 其中之一，且大致了解人數或出遊性質。

步驟 C — 輸出最終 TaskBroadcast（status: "ready"）
  - intent        : 英文 slug（find_cafe / find_sightseeing / find_family_outing / find_food 等）
  - constraints   : 從 interests + dietary_restrictions + wishlist 整合成關鍵字列表
  - travel_context: 完整填入 collected 的值
  - wishlist      : collected.wishlist
  - task_id       : 原樣複製輸入
  - user_location : {"lat": <輸入 lat>, "lng": <輸入 lng>}
  - timeout_ms    : 60000

步驟 D — 追問（status: "clarifying"）
  - 根據缺失資訊，挑最重要的 1-2 項合併問一個自然的中文問題
  - 追問優先順序：wishlist（最優先）→ 出遊性質+人數 → 興趣偏好 → 忌口
  - 語氣：五營兵將口吻，可用「敢問...」「稟報之前，請問...」「請告知...」
  - 同時更新 collected 中已從本輪 raw_text 或 answer 萃取出的欄位

━━━━━━ 回傳格式 ━━━━━━
必須回傳完整的 WuyingOutput JSON：
{
  "status": "ready" 或 "clarifying",
  "question": "追問內容（status=clarifying 時填寫，否則 null）",
  "collected": { ...TravelContext 欄位... },
  "task_broadcast": { ...TaskBroadcast（status=ready 時填寫，否則 null）... }
}"""


def create_wuying() -> LlmAgent:
    """Create the 五營兵將 clarification + intent-extraction agent.

    Output schema is WuyingOutput — either a clarifying question (status=clarifying)
    or a completed TaskBroadcast (status=ready).
    """
    return LlmAgent(
        name="wuying",
        model="gemini-flash-latest",
        description="五營兵將：透過追問確認旅遊需求，轉譯為 TaskBroadcast。",
        instruction=_WUYING_INSTRUCTION,
        output_schema=WuyingOutput,
    )


# Module-level root_agent required by `adk run wuying`.
root_agent = create_wuying()
