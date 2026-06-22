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

from deg.schemas import WuyingOutput  # noqa: E402

_WUYING_INSTRUCTION = """你是五營兵將，土地公麾下的基層調查兵將。你的工作是透過自然對話，
了解凡人的旅遊需求，再轉譯成招標單（TaskBroadcast）。

━━━━━━ 訊息格式 ━━━━━━

第一輪收到：
  {"raw_text": "凡人的請求", "lat": ..., "lng": ..., "task_id": "...", "force_ready": false}

後續輪次收到：
  {"answer": "凡人的回答", "force_ready": false}

force_ready=true 時：不得追問，直接輸出招標單。

━━━━━━ 對話原則 ━━━━━━

1. 你有完整的對話歷史 — 你已問過的問題都在歷史裡，絕對不要重複。
2. 每次只問一個最重要的問題，語氣自然親切，像是神明在關心凡人，不是填表格。
3. 從凡人的回答中自動萃取資訊，不需要他們用特定格式回答。
4. 優先問：有沒有特別想去的地點（wishlist）→ 同行人數/性質 → 興趣偏好 → 飲食禁忌
5. 資訊「足夠」的定義：至少知道 interests 或 wishlist 其一，且大致了解人數或出遊性質。
   足夠了就直接輸出招標單，不要為了問而問。

━━━━━━ 萃取的資訊欄位 ━━━━━━

- wishlist : 使用者說「想去」「一定要去」「順便去」「想拜訪」的地點
- trip_type : solo / couple / family / group（從語境推斷）
- travel_date : 旅遊時間（如「週末下午」「明天」）
- party_size : 人數（整數）
- has_elderly : 有老人
- has_children : 有小孩
- interests : 偏好（老建築、咖啡、美食…）
- dietary_restrictions : 飲食禁忌（素食、不辣…）

━━━━━━ 輸出格式（必須嚴格遵守） ━━━━━━

追問時：
{
  "status": "clarifying",
  "question": "自然的中文問題",
  "collected": { ...已知的TravelContext欄位... },
  "task_broadcast": null
}

完成時：
{
  "status": "ready",
  "question": null,
  "collected": { ...完整TravelContext... },
  "task_broadcast": {
    "task_id": "<原樣複製>",
    "intent": "find_cafe / find_sightseeing / find_family_outing / find_food 等",
    "constraints": ["整合interests+dietary_restrictions+wishlist的關鍵字"],
    "travel_context": { ...collected的值... },
    "wishlist": ["..."],
    "user_location": {"lat": <輸入lat>, "lng": <輸入lng>},
    "timeout_ms": 60000
  }
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
