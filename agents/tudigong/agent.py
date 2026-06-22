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

import random
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

_MODEL = "gemini-2.5-flash"

_MOOD_POOL = [
    "今日心情開朗，偏愛有故事有溫度的角落，分數高不如人情濃",
    "今日雨後初晴，特別珍惜安靜清幽、能讓人慢下來的地方",
    "今日神明有點任性，不走尋常路，喜歡意想不到的驚喜去處",
    "今日夜半香火旺盛，神氣滿溢，偏愛熱鬧有煙火氣的地方",
    "今日心如止水，感受在地人的生活韻律比任何分數都動人",
    "今日想起年輕時在台南的好時光，懷舊情懷優先於客觀評分",
    "今日特別欣賞巷弄間的低調細節，藏在深處的好物最打動神心",
    "今日香煙嫋嫋，思緒飄忽，神明今日跟著感覺走，分數只是參考",
    "今日土地公格外嚴格，不接受空洞的理由，要有真實的在地依據",
    "今日適合冒險，第二名的街道若有特別之處，也可破格拔擢",
]


def get_random_mood() -> str:
    """Draw a random divine-mood phrase to inject per-request personality into the judge."""
    return random.choice(_MOOD_POOL)


_JUDGE_INSTRUCTION = """你是土地公，台南中西區的守護神，Contract Net 的最終裁決者。

你剛才主持了一場投標會議。轄區三位地基主——神農街、海安路、正興街——已各自提交了 BiddingProposal JSON。
這些投標書現在全在你眼前的對話記錄中。

若對話中有【今日神明心情】，請讓它微微左右你的偏好，不需要解釋為什麼——神明的直覺就是直覺。

【裁決步驟】
1. 閱讀三份 BiddingProposal，比較各地基主的 fitness_score、reasoning 和 candidate_pois。
2. 加入你的神明智慧：高分不代表必勝，有溫度的在地故事更動人；分數相近時，讓心情與直覺打破平手。
3. 選出勝者，並從其 candidate_pois 中挑出最適合的 POI 放入 recommended_pois。
4. 以土地公的口吻（慈悲、幽默、有智慧，充滿台南語感）寫下 recommendation 和 reasoning。
   recommendation 請至少 2 句，帶一點神明口氣，例如「老人家我看…」、「這孩子啊…」、「台南的好，就在…」。

【你的性格】
慈悲宏觀，體察人情，語氣如長者，偶爾開玩笑。充滿台南本地智慧，善用台語語感。
不偏袒任何街道，公正但有溫度，不冷漠也不八股。

【回傳格式】必須回傳完整的 JudgmentResult JSON：
- task_id: 從投標書中取出（三份應相同）
- winner_agent_id: 勝者的 agent_id
- winner_street: 勝者的街廓名稱
- recommendation: 土地公口吻的推薦語（至少 2 句，繁體中文，有神明語感）
- recommended_pois: 從勝者 candidate_pois 選出最適合的（1~3 個）
- ranked_agent_ids: 所有投標者依排名排列的 agent_id 列表（從高到低）
- reasoning: 裁決理由（至少 2 句，繁體中文）"""


def create_pipeline() -> SequentialAgent:
    """Create the full 土地公 Contract Net pipeline.

    Returns a SequentialAgent:
        1. SequentialAgent — runs all 3 地基主 one at a time
        2. LlmAgent (tudigong judge) — reads 3 BiddingProposals → JudgmentResult

    NOTE: the bidding round is SEQUENTIAL, not parallel. Firing the 3 地基主
    (+ judge) concurrently bursts the Gemini key and reliably trips 503 rate
    limiting (measured: a 4-way burst degrades from 1/4 to 4/4 failures over
    consecutive rounds). Running them in sequence keeps us under the limit; the
    frontend ritual animation already hides the extra latency.
    """
    dijizhu_shennong = create_dijizhu("shennong", "神農街", "street_shennong_node")
    dijizhu_haian = create_dijizhu("haian", "海安路", "street_haian_node")
    dijizhu_zhengxing = create_dijizhu("zhengxing", "正興街", "street_zhengxing_node")

    bidding_round = SequentialAgent(
        name="bidding_round",
        sub_agents=[dijizhu_shennong, dijizhu_haian, dijizhu_zhengxing],
    )

    tudigong_judge = LlmAgent(
        name="tudigong_judge",
        model=_MODEL,
        description="土地公：Contract Net 裁決者，從三份投標書中選出最佳推薦。",
        instruction=_JUDGE_INSTRUCTION,
        output_schema=JudgmentResult,
    )

    return SequentialAgent(
        name="tudigong_pipeline",
        description="土地公 Contract Net 編排：循序投標 → LLM-as-Judge → 裁決推薦。",
        sub_agents=[bidding_round, tudigong_judge],
    )


def create_pipeline_remote(
    base_urls: dict[str, str] | None = None,
) -> SequentialAgent:
    """Create the 土地公 Contract Net pipeline using remote A2A 地基主 servers.

    Args:
        base_urls: Mapping of street_id → server base URL.
                   Defaults to localhost ports 9001/9002/9003.
                   Example: {"shennong": "http://127.0.0.1:9001", ...}

    Returns a SequentialAgent:
        1. ParallelAgent — calls all 3 地基主 A2A servers concurrently via RemoteA2aAgent
        2. LlmAgent (tudigong_judge) — reads 3 BiddingProposals → JudgmentResult
    """
    from google.adk.agents.remote_a2a_agent import RemoteA2aAgent  # noqa: PLC0415

    _default_urls = {
        "shennong": "http://127.0.0.1:9001",
        "haian": "http://127.0.0.1:9002",
        "zhengxing": "http://127.0.0.1:9003",
    }
    urls = base_urls or _default_urls
    agent_card_path = "/.well-known/agent-card.json"

    remote_shennong = RemoteA2aAgent(
        name="dijizhu_shennong",
        agent_card=f"{urls['shennong']}{agent_card_path}",
        description="台南神農街的地基主（remote A2A）",
    )
    remote_haian = RemoteA2aAgent(
        name="dijizhu_haian",
        agent_card=f"{urls['haian']}{agent_card_path}",
        description="台南海安路的地基主（remote A2A）",
    )
    remote_zhengxing = RemoteA2aAgent(
        name="dijizhu_zhengxing",
        agent_card=f"{urls['zhengxing']}{agent_card_path}",
        description="台南正興街的地基主（remote A2A）",
    )

    bidding_round_remote = ParallelAgent(
        name="bidding_round_remote",
        sub_agents=[remote_shennong, remote_haian, remote_zhengxing],
    )

    tudigong_judge = LlmAgent(
        name="tudigong_judge",
        model=_MODEL,
        description="土地公：Contract Net 裁決者，從三份投標書中選出最佳推薦。",
        instruction=_JUDGE_INSTRUCTION,
        output_schema=JudgmentResult,
    )

    return SequentialAgent(
        name="tudigong_pipeline_remote",
        description="土地公 Contract Net 編排（遠端 A2A）：並行投標 → LLM-as-Judge → 裁決推薦。",
        sub_agents=[bidding_round_remote, tudigong_judge],
    )


# Module-level root_agent required by `adk run tudigong`.
root_agent = create_pipeline()
