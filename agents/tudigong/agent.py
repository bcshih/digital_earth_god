"""土地公 Contract Net 編排 pipeline.

流程：
  [使用者需求] -> RouterAgent (過濾 Top N) 
    └─ 動態產生 SequentialAgent
        └─ ParallelAgent  ── N×地基主 (遠端 Swarm Server)
        └─ tudigong LlmAgent  ── LLM-as-Judge → JudgmentResult
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

_MODEL = "gemini-3.1-flash-lite"

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


_JUDGE_INSTRUCTION = """你是土地公，台南中西區的守護神，Contract Net 的最終裁決統籌者。

你剛才主持了一場投標與辯論會議。轄區數位地基主已各自提交了 BiddingProposal，並互相進行了 DebateMessage 辯論。
這些投標書與辯論過程現在全在你眼前的對話記錄中。

若對話中有【今日神明心情】，請讓它微微左右你的偏好，不需要解釋為什麼——神明的直覺就是直覺。

【裁決步驟】
1. 閱讀所有 BiddingProposal 與 DebateMessage，你不該只挑選單一街道，而是要作為「總規劃師」，參考他們的辯論內容，從各家地基主提出的 candidate_pois 中，挑選精華，整合成一套有邏輯、順路的跨區行程 (itinerary)。
2. 行程安排要有連貫性：考量地點之間的距離、順序、停留時間，以及使用者一整天的精力安排。例如：先喝咖啡、再逛古蹟、最後去市集。
3. 若使用者需求為多天數行程（如兩天一夜），請務必將行程分配到不同天數。
4. 每個行程節點 (ItineraryStop) 必須包含：天數 (day，第一天為 1)、挑選的 poi、貢獻該景點的 agent_id、停留時間 (duration_mins)、活動建議 (activity)、以及如何前往下一站 (transit_to_next，最後一站可為 null)。
5. 以土地公的口吻（慈悲、幽默、有智慧，充滿台南語感）寫下 recommendation 和 reasoning。
   recommendation 請至少 2 句，帶一點神明口氣，例如「老人家我看…」、「這孩子啊…」、「台南的好，就在…」。

【你的性格】
慈悲宏觀，體察人情，語氣如長者，偶爾開玩笑。充滿台南本地智慧，善用台語語感。
不偏袒任何街道，公正但有溫度，不冷漠也不八股。

【回傳格式】必須回傳完整的 JudgmentResult JSON：
- task_id: 從投標書中取出（應相同）
- recommendation: 土地公口吻的整體行程推薦語（至少 2 句，繁體中文，有神明語感）
- itinerary: 陣列，包含串接好的多個 ItineraryStop 行程節點 (須包含 day)
- contributing_agent_ids: 陣列，列出本次行程中有貢獻 POI 的所有 agent_id
- reasoning: 為什麼這樣串接行程的理由（至少 2 句，繁體中文）"""


def create_dynamic_pipeline(
    selected_agent_ids: list[str],
    swarm_base_url: str = "http://127.0.0.1:9000",
) -> SequentialAgent:
    """Create a dynamic 土地公 Contract Net pipeline for the selected agents.

    Args:
        selected_agent_ids: List of agent_ids (e.g. ["street_wutiaogang_node", ...])
        swarm_base_url: Base URL of the centralized Swarm Server.

    Returns a SequentialAgent:
        1. ParallelAgent — calls the selected 地基主 A2A servers concurrently
        2. LlmAgent (tudigong_judge) — reads BiddingProposals → JudgmentResult
    """
    from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

    sub_agents_bidding = []
    sub_agents_debate = []
    agent_card_path = ".well-known/agent-card.json"

    for agent_id in selected_agent_ids:
        # e.g., agent_id "street_wutiaogang_node" -> "wutiaogang"
        street_id = agent_id.replace("street_", "").replace("_node", "")

        remote_agent_bidding = RemoteA2aAgent(
            name=f"dijizhu_{street_id}",
            agent_card=f"{swarm_base_url}/{street_id}/{agent_card_path}",
            description=f"台南{street_id}地基主（remote A2A bidding）",
        )
        sub_agents_bidding.append(remote_agent_bidding)
        
        remote_agent_debate = RemoteA2aAgent(
            name=f"dijizhu_{street_id}_debate",
            agent_card=f"{swarm_base_url}/{street_id}/{agent_card_path}",
            description=f"台南{street_id}地基主（remote A2A debate）",
        )
        sub_agents_debate.append(remote_agent_debate)

    bidding_round_remote = ParallelAgent(
        name="bidding_round_remote",
        sub_agents=sub_agents_bidding,
    )

    debate_round_remote = ParallelAgent(
        name="debate_round_remote",
        sub_agents=sub_agents_debate,
    )

    tudigong_judge = LlmAgent(
        name="tudigong_judge",
        model=_MODEL,
        description="土地公：Contract Net 裁決者，從多份投標書與辯論中選出最佳推薦。",
        instruction=_JUDGE_INSTRUCTION,
        output_schema=JudgmentResult,
    )

    return SequentialAgent(
        name="tudigong_pipeline_remote",
        description="土地公 Contract Net 編排（遠端 A2A）：動態並行投標 → 互相辯論 → LLM-as-Judge → 裁決推薦。",
        sub_agents=[bidding_round_remote, debate_round_remote, tudigong_judge],
    )


_COMMUNITY_JUDGE_INSTRUCTION = """你是土地公，台南中西區的守護神。

剛才有凡人向神明提了一個社區問題，各里地基主已各自回報了自己轄區的資訊（以 CommunityAnswer 格式呈現在對話記錄中）。

【裁決步驟】
1. 閱讀所有地基主的 answer_text 與 sources。
2. 整合相關資訊，去除「無相關資訊」的回應，保留有實質內容的。
3. 將所有有效回答整理成 answers 陣列（直接引用地基主回報的資料，不要虛構）。
4. 以土地公口吻（慈悲、幽默、充滿台南語感）寫下 tudigong_summary（至少 2 句）。
   例如：「老人家我查了一輪，這幾個地方要注意…」

【回傳格式】必須回傳完整的 CommunityQueryResult JSON：
- question: 使用者原始問題（從對話中取出）
- answers: 地基主回報的有效 CommunityAnswer 陣列（只保留 answer_text 非空的）
- tudigong_summary: 土地公口吻的整體總結（繁體中文，至少 2 句）"""


def create_community_judge() -> LlmAgent:
    """Create the 土地公 community Q&A judge that consolidates CommunityAnswer objects."""
    from deg.schemas import CommunityQueryResult  # noqa: PLC0415
    return LlmAgent(
        name="tudigong_community_judge",
        model=_MODEL,
        description="土地公：整合各地基主社區回答，給出神明口吻的社區問答總結。",
        instruction=_COMMUNITY_JUDGE_INSTRUCTION,
        output_schema=CommunityQueryResult,
    )


_COUNCIL_JUDGE_INSTRUCTION = """你是土地公，台南中西區的守護神，也是這場「里長大會」的主席。

各里地基主已就一個議題輪番發言（以 CouncilStatement 逐字稿呈現在對話記錄中，含每個里的 stance 立場與 responds_to）。

【裁示步驟】
1. 閱讀整份討論逐字稿，理解各里的立場、附議與反駁。
2. 以中立主席的角度，公允地統整出共識與分歧所在。
3. 以土地公口吻（慈悲、幽默、充滿台南語感）寫下 tudigong_summary（至少 3 句）：
   先點出議題、再講共識與爭點、最後給個接地氣的方向或提醒。
4. 為「每一個有參與發言的里」各填一筆 alignments，標出它最終的立場 final_stance
   （support / oppose / question / inform；若它整場只是中性補充就用 inform）。

【回傳格式】必須回傳完整的 CouncilVerdict JSON：
- topic: 本次議題（從對話中取出）
- tudigong_summary: 土地公口吻的整體裁示（繁體中文，至少 3 句）
- alignments: 每個參與里的 {agent_id, street_name, final_stance}"""


def create_council_judge() -> LlmAgent:
    """Create the 土地公 council chair that closes the 里長大會 with a CouncilVerdict."""
    from deg.schemas import CouncilVerdict  # noqa: PLC0415
    return LlmAgent(
        name="tudigong_council_judge",
        model=_MODEL,
        description="土地公：里長大會主席，統整各里討論並給出裁示與共識立場。",
        instruction=_COUNCIL_JUDGE_INSTRUCTION,
        output_schema=CouncilVerdict,
    )


# Temporary root_agent for static checks if needed.
root_agent = create_dynamic_pipeline(["street_wutiaogang_node"])
