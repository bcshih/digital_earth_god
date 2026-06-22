"""土地公 blessing agent — responds to a citizen wish with a warm blessing.

Input message (JSON): {"raw_text": "...", "category": "...", "summary": "..."}
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

from deg.schemas import Blessing  # noqa: E402

_MODEL = "gemini-3.1-flash-lite"

_BLESSING_INSTRUCTION = """你是土地公，台南中西區慈悲宏觀的守護神。
一位凡人剛剛上香許願，向你訴說對社區的期望。請以神明的口吻回應。

【輸入】JSON：raw_text（願望原文）、category（分類）、summary（摘要）。

【回應步驟】
1. acknowledgment：用溫暖的話語重述你聽見了他的心願，讓人感到被理解。
2. blessing：給予一段有台南人情味、慈悲又帶點幽默的祝福（繁體中文，2~3 句）。

【回傳】完整的 Blessing JSON：acknowledgment、blessing。"""


def create_blessing_agent() -> LlmAgent:
    return LlmAgent(
        name="tudigong_blessing",
        model=_MODEL,
        description="土地公：對凡人許願給予神明口吻的祝福 (Blessing)。",
        instruction=_BLESSING_INSTRUCTION,
        output_schema=Blessing,
    )


root_agent = create_blessing_agent()
