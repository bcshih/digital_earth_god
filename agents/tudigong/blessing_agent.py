"""???blessing agent ??responds to a citizen wish with a warm blessing.

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

_BLESSING_INSTRUCTION = """雿??穿??啣?銝剛正??摰???霅瑞???銝雿鈭箏???擐迂憿???閮渲牧撠冗?????隞亦?????????
?撓?乓SON嚗aw_text嚗??????ategory嚗?憿??ummary嚗?閬???
???郊撽?1. acknowledgment嚗皞急??店隤?餈唬??質?鈭???憿?霈犖?鋡怎?閫??2. blessing嚗策鈭?畾菜??啣?鈭箸??喋??脣?撣園?撟賡???蝳?蝜?銝剜?嚗?~3 ?伐???
???喋??渡? Blessing JSON嚗cknowledgment?lessing??""


def create_blessing_agent() -> LlmAgent:
    return LlmAgent(
        name="tudigong_blessing",
        model="gemini-2.0-flash",
        description="??穿?撠鈭箄迂憿策鈭???餌?蟡? (Blessing)??,
        instruction=_BLESSING_INSTRUCTION,
        output_schema=Blessing,
    )


root_agent = create_blessing_agent()
