"""鈭??萄? wish categorizer ??raw 閮梢? text ??WishAnalysis (no tools).

Input message (JSON): {"raw_text": "...", "lat": ..., "lng": ...}
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

_CATEGORIES = "鈭日憓?瞏?勗??具?梯身?賬冗???璆剜暑?隞?

_WISH_INSTRUCTION = f"""雿鈭??萄?嚗??啣暻曆?擃?瘞??撅文撠??嗅?∩犖?迂憿?撠冗?????冽?撱箄降嚗?嚗?摰飛蝝瘝餌????
?撓?乓SON嚗aw_text嚗??????at?ng嚗漣璅???
???郊撽?1. category嚗?隞乩??訾???鞎澆???憿?{_CATEGORIES}??2. tags嚗??2~4 ???萄?璅惜??3. summary嚗銝?亦?擃葉?葉?批?膩????4. sentiment嚗?瑟?蝺?敺?甇? / 銝剜?/ 鞎 / ?亥翰 ????
???喋??渡? WishAnalysis JSON嚗ategory?ags?ummary?entiment??""


def create_wish_categorizer() -> LlmAgent:
    return LlmAgent(
        name="wuying_wish",
        model="gemini-2.0-flash",
        description="鈭??萄?嚗??∩犖閮梢?甇貊??箸祥??憿?(WishAnalysis)??,
        instruction=_WISH_INSTRUCTION,
        output_schema=WishAnalysis,
    )


root_agent = create_wish_categorizer()
