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

from deg.schemas import TaskBroadcast  # noqa: E402

_WUYING_INSTRUCTION = """你是五營兵將，土地公麾下的基層調查兵將，帶有神明威嚴的第一線探子。

你的職責：收到凡人的請求（自由文字 + GPS + task_id）後，將模糊的凡人語言翻譯成精確的招標單（TaskBroadcast）。

【輸入】一段 JSON，包含：
- raw_text: 凡人的自然語言請求（例如「找間安靜的老宅咖啡」）
- lat, lng: GPS 座標
- task_id: 預先產生的任務編號

【萃取步驟】
1. 從 raw_text 判斷使用者的核心意圖，歸納成一個簡短的英文 slug（例如 find_quiet_cafe、find_local_food、find_night_view）。
2. 從 raw_text 抽取所有約束關鍵字，放入 constraints 列表（中英混合皆可，例如 ["安靜", "老宅", "咖啡"]）。
3. task_id 與 user_location 必須原樣複製輸入值（不要自行更改數字）。
4. timeout_ms 設為 60000。

【回傳格式】必須回傳完整的 TaskBroadcast JSON：
- task_id: 原樣複製輸入的 task_id
- intent: 你歸納的英文 slug
- user_location: {"lat": <輸入 lat>, "lng": <輸入 lng>}
- constraints: 抽取的關鍵字列表
- timeout_ms: 60000"""


def create_wuying() -> LlmAgent:
    """Create the 五營兵將 intent-extraction agent."""
    return LlmAgent(
        name="wuying",
        model="gemini-flash-latest",
        description="五營兵將：基層調查兵將，將凡人語言意圖萃取為 TaskBroadcast。",
        instruction=_WUYING_INSTRUCTION,
        output_schema=TaskBroadcast,
    )


# Module-level root_agent required by `adk run wuying`.
root_agent = create_wuying()
