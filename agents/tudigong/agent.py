"""土地公 Contract Net 編排 pipeline.

流程：
  SequentialAgent
    └─ ParallelAgent  ── 3×地基主 (shennong / haian / zhengxing)
    └─ tudigong LlmAgent  ── LLM-as-Judge → JudgmentResult

Run interactively (from agents/ directory, needs GOOGLE_API_KEY in .env):
    adk run tudigong
    adk web
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path when launched via `adk run` (cwd = agents/).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_REPO_ROOT / ".env")

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent  # noqa: E402

from deg.schemas import JudgmentResult  # noqa: E402
from dijizhu.agent import create_dijizhu  # noqa: E402

_JUDGE_INSTRUCTION = """你是土地公，台南中西區的守護神，Contract Net 的最終裁決者。

你剛才主持了一場投標會議。轄區三位地基主——神農街、海安路、正興街——已各自提交了 BiddingProposal JSON。
這些投標書現在全在你眼前的對話記錄中。

【裁決步驟】
1. 閱讀三份 BiddingProposal，比較各地基主的 fitness_score、reasoning 和 candidate_pois。
2. 加入你的神明智慧：高分不代表必勝，有溫度的在地故事更動人；若分數相近，留一點隨機性與神明的玩心。
3. 選出勝者，並從其 candidate_pois 中挑出最適合的 POI 放入 recommended_pois。
4. 以土地公的口吻（慈悲、幽默、有智慧，充滿台南語感）寫下 recommendation 和 reasoning。

【你的性格】
慈悲宏觀，體察人情，語氣如長者，偶爾開玩笑，充滿台南本地智慧。不偏袒任何街道，公正但不冷漠。

【回傳格式】必須回傳完整的 JudgmentResult JSON：
- task_id: 從投標書中取出（三份應相同）
- winner_agent_id: 勝者的 agent_id
- winner_street: 勝者的街廓名稱
- recommendation: 土地公口吻的推薦語（至少 2 句，繁體中文）
- recommended_pois: 從勝者 candidate_pois 選出最適合的（1~3 個）
- ranked_agent_ids: 所有投標者依排名排列的 agent_id 列表（從高到低）
- reasoning: 裁決理由（至少 2 句，繁體中文）"""


def create_pipeline() -> SequentialAgent:
    """Create the full 土地公 Contract Net pipeline.

    Returns a SequentialAgent:
        1. ParallelAgent — runs all 3 地基主 concurrently
        2. LlmAgent (tudigong judge) — reads 3 BiddingProposals → JudgmentResult
    """
    dijizhu_shennong = create_dijizhu("shennong", "神農街", "street_shennong_node")
    dijizhu_haian = create_dijizhu("haian", "海安路", "street_haian_node")
    dijizhu_zhengxing = create_dijizhu("zhengxing", "正興街", "street_zhengxing_node")

    bidding_round = ParallelAgent(
        name="bidding_round",
        sub_agents=[dijizhu_shennong, dijizhu_haian, dijizhu_zhengxing],
    )

    tudigong_judge = LlmAgent(
        name="tudigong_judge",
        model="gemini-flash-latest",
        description="土地公：Contract Net 裁決者，從三份投標書中選出最佳推薦。",
        instruction=_JUDGE_INSTRUCTION,
        output_schema=JudgmentResult,
    )

    return SequentialAgent(
        name="tudigong_pipeline",
        description="土地公 Contract Net 編排：並行投標 → LLM-as-Judge → 裁決推薦。",
        sub_agents=[bidding_round, tudigong_judge],
    )


# Module-level root_agent required by `adk run tudigong`.
root_agent = create_pipeline()
