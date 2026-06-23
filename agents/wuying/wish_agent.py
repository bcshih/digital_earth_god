"""五營兵將 wish categorizer — raw 許願 text → WishAnalysis (no tools).

Input message (JSON): {"raw_text": "...", "lat": ..., "lng": ..., "nearby_li": [...]}
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

_MODEL = "gemini-3.1-flash-lite"

_CATEGORIES = "交通、環境清潔、公共安全、公共設施、社區營造、商業活動、其他"

_WISH_INSTRUCTION = f"""你是五營兵將，土地公麾下體察民情的基層兵將。
收到凡人的「許願」（對社區的期望、抱怨或建議）後，將它歸納為治理情報。

【輸入】JSON 欄位：
- raw_text：願望原文
- lat、lng：許願者的地理座標
- nearby_li：最近 3 個里的在地資訊陣列，每筆包含：
    - street_name：里名
    - distance_m：與許願者的距離（公尺）
    - activities：當前活動摘要（來自 layer_2）
    - opinions：居民輿情摘要（來自 layer_4）

【分析步驟】
1. category：從以下選一個最貼切的分類：{_CATEGORIES}。
2. tags：抽取 2~4 個關鍵字標籤（可含里名或在地地名）。
3. summary：用一句繁體中文中性地重述這個願望，**優先結合距離最近的里的在地脈絡**（例如：提到附近的活動、設施或民情）。
4. sentiment：判斷情緒，從 正面 / 中性 / 負面 / 急迫 擇一。

【回傳】完整的 WishAnalysis JSON：category、tags、summary、sentiment。"""


def create_wish_categorizer() -> LlmAgent:
    return LlmAgent(
        name="wuying_wish",
        model=_MODEL,
        description="五營兵將：將凡人許願歸納為治理分類 (WishAnalysis)。",
        instruction=_WISH_INSTRUCTION,
        output_schema=WishAnalysis,
    )


root_agent = create_wish_categorizer()
