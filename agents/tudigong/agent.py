"""???Contract Net 蝺冽? pipeline.

瘚?嚗?  SequentialAgent
    ?? ParallelAgent  ?? 3??啣銝?(shennong / haian / zhengxing)
    ?? tudigong LlmAgent  ?? LLM-as-Judge ??JudgmentResult

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

_MOOD_POOL = [
    "隞敹???嚗??????澈摨衣?閫嚗??賊?銝?鈭箸?瞈?,
    "隞?典??嚗?亦?????撟賬霈犖?Ｖ?靘??唳",
    "隞蟡???隞餅改?銝粥撠虜頝荔??迭?銝?????,
    "隞憭?擐?箇?嚗?瘞?遛皞ｇ????梢洹???急除???,
    "隞敹?甇Ｘ偌嚗???唬犖??瘣駁敺?隞颱???賢?鈭?,
    "隞?唾絲撟渲???啣??末??嚗???瑕?摰Ｚ?閰?",
    "隞?孵甈??撌瑕???雿矽蝝啁?嚗??冽楛??憟賜???蟡?",
    "隞擐?憳?嚗?憌蕭嚗????亥???閬箄粥嚗??詨?臬???,
    "隞??祆憭?潘?銝?征瘣??嚗???撖衣??典靘?",
    "隞?拙??嚗洵鈭??????乩???銋?湔?",
]


def get_random_mood() -> str:
    """Draw a random divine-mood phrase to inject per-request personality into the judge."""
    return random.choice(_MOOD_POOL)


_JUDGE_INSTRUCTION = """雿??穿??啣?銝剛正???霅瑞?嚗ontract Net ??蝯?瘙箄?
雿??蜓??銝?湔?璅?霅啜??銝??啣銝領?颲脰??絲摰楝?迤???歇??漱鈭?BiddingProposal JSON???????貊?典?其??澆???閰梯??葉??
?亙?閰曹葉???亦?????隢?摰凝敺桀椰?喃???憟踝?銝?閬圾?隞暻潑????渲死撠望?渲死??
??瘙箸郊撽?1. ?梯?銝遢 BiddingProposal嚗?頛??啣銝餌? fitness_score?easoning ??candidate_pois??2. ?雿?蟡??箸嚗???隞?”敹?嚗?皞怠漲??唳?鈭?犖嚗??貊餈?嚗?敹??閬箸??游像??3. ?詨??銝血???candidate_pois 銝剜??箸??拙???POI ?曉 recommended_pois??4. 隞亙??啣??鳴???厭暺??箸嚗?皛踹????撖思? recommendation ??reasoning??   recommendation 隢撠?2 ?伐?撣嗡?暺??瘞??靘??犖摰嗆??艾酋摮??艾??憟踝?撠勗?艾?
???扳???摰?嚗?撖犖??隤除憒???嗥?蝚?皛踹??唳?改???啗?隤???銝?鋡遙雿????祆迤雿?皞怠漲嚗??瑟?銋??怨??
???單撘????喳??渡? JudgmentResult JSON嚗?- task_id: 敺?璅銝剖??綽?銝遢???
- winner_agent_id: ?? agent_id
- winner_street: ??銵??迂
- recommendation: ??砍?餌??刻隤??喳? 2 ?伐?蝜?銝剜?嚗?蟡?隤?嚗?- recommended_pois: 敺???candidate_pois ?詨??拙???1~3 ??
- ranked_agent_ids: ???璅???????agent_id ?”嚗?擃雿?
- reasoning: 鋆捱?嚗撠?2 ?伐?蝜?銝剜?嚗?""


def create_pipeline() -> SequentialAgent:
    """Create the full ???Contract Net pipeline.

    Returns a SequentialAgent:
        1. ParallelAgent ??runs all 3 ?啣銝?concurrently
        2. LlmAgent (tudigong judge) ??reads 3 BiddingProposals ??JudgmentResult
    """
    dijizhu_shennong = create_dijizhu("shennong", "蟡噙銵?, "street_shennong_node")
    dijizhu_haian = create_dijizhu("haian", "瘚瑕?頝?, "street_haian_node")
    dijizhu_zhengxing = create_dijizhu("zhengxing", "甇??銵?, "street_zhengxing_node")

    bidding_round = ParallelAgent(
        name="bidding_round",
        sub_agents=[dijizhu_shennong, dijizhu_haian, dijizhu_zhengxing],
    )

    tudigong_judge = LlmAgent(
        name="tudigong_judge",
        model="gemini-2.0-flash",
        description="??穿?Contract Net 鋆捱??敺?隞賣?璅銝剝?箸?雿單?艾?,
        instruction=_JUDGE_INSTRUCTION,
        output_schema=JudgmentResult,
    )

    return SequentialAgent(
        name="tudigong_pipeline",
        description="???Contract Net 蝺冽?嚗蒂銵?璅???LLM-as-Judge ??鋆捱?刻??,
        sub_agents=[bidding_round, tudigong_judge],
    )


def create_pipeline_remote(
    base_urls: dict[str, str] | None = None,
) -> SequentialAgent:
    """Create the ???Contract Net pipeline using remote A2A ?啣銝?servers.

    Args:
        base_urls: Mapping of street_id ??server base URL.
                   Defaults to localhost ports 9001/9002/9003.
                   Example: {"shennong": "http://127.0.0.1:9001", ...}

    Returns a SequentialAgent:
        1. ParallelAgent ??calls all 3 ?啣銝?A2A servers concurrently via RemoteA2aAgent
        2. LlmAgent (tudigong_judge) ??reads 3 BiddingProposals ??JudgmentResult
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
        description="?啣?蟡噙銵??啣銝鳴?remote A2A嚗?,
    )
    remote_haian = RemoteA2aAgent(
        name="dijizhu_haian",
        agent_card=f"{urls['haian']}{agent_card_path}",
        description="?啣?瘚瑕?頝舐??啣銝鳴?remote A2A嚗?,
    )
    remote_zhengxing = RemoteA2aAgent(
        name="dijizhu_zhengxing",
        agent_card=f"{urls['zhengxing']}{agent_card_path}",
        description="?啣?甇??銵??啣銝鳴?remote A2A嚗?,
    )

    bidding_round_remote = ParallelAgent(
        name="bidding_round_remote",
        sub_agents=[remote_shennong, remote_haian, remote_zhengxing],
    )

    tudigong_judge = LlmAgent(
        name="tudigong_judge",
        model="gemini-2.0-flash",
        description="??穿?Contract Net 鋆捱??敺?隞賣?璅銝剝?箸?雿單?艾?,
        instruction=_JUDGE_INSTRUCTION,
        output_schema=JudgmentResult,
    )

    return SequentialAgent(
        name="tudigong_pipeline_remote",
        description="???Contract Net 蝺冽?嚗?蝡?A2A嚗?銝西??? ??LLM-as-Judge ??鋆捱?刻??,
        sub_agents=[bidding_round_remote, tudigong_judge],
    )


# Module-level root_agent required by `adk run tudigong`.
root_agent = create_pipeline()
