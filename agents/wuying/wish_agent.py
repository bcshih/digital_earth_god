"""五營兵將 wish categorizer — raw 許願 text → WishAnalysis (no tools).

Input message (JSON): {"raw_text": "...", "lat": ..., "lng": ...}
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import os  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_REPO_ROOT / ".env")

from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.models.lite_llm import LiteLlm  # noqa: E402

from deg.schemas import WishAnalysis  # noqa: E402

_DASHSCOPE_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
_QWEN = LiteLlm(
    model="openai/" + os.environ.get("DASHSCOPE_MODEL", "qwen-plus"),
    api_base=_DASHSCOPE_BASE,
    api_key=os.environ.get("DASHSCOPE_API_KEY", ""),
)

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
        model=_QWEN,
        description="五營兵將：將凡人許願歸納為治理分類 (WishAnalysis)。",
        instruction=_WISH_INSTRUCTION,
        output_schema=WishAnalysis,
    )


root_agent = create_wish_categorizer()
