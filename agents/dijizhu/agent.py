"""地基主 (Street Guardian) ADK LlmAgent.

Each 地基主 is bound to one Tainan 里/街廓 and bids into 土地公's Contract Net
by reasoning over pre-loaded spatial / sensor / social data — no tool calls,
single LLM pass, returns BiddingProposal.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure repo root is on sys.path when launched via `adk run` (cwd = agents/).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_REPO_ROOT / ".env")

from typing import Union
from google.adk.agents import LlmAgent  # noqa: E402
from deg.schemas import BiddingProposal, CommunityAnswer, DebateMessage, ScoutResult  # noqa: E402
from deg.seed.loader import load_agents, LiAgentData  # noqa: E402

_MODEL = "gemini-3.1-flash-lite"


def create_dijizhu(
    street_id: str,
    street_name: str,
    agent_id: str,
    li_data: LiAgentData | None = None,
) -> LlmAgent:
    """Create a 地基主 LlmAgent bound to a specific street/li.

    Data is injected directly into the instruction — no tool calls needed,
    single LLM round-trip to produce BiddingProposal.
    """
    if li_data is None:
        agents = load_agents()
        for a in agents:
            if a.id.endswith(street_id.capitalize()) or a.id.endswith(street_id):
                li_data = a
                break
        else:
            raise ValueError(f"Agent data for {street_id} not found.")

    street_obj = li_data.to_street()
    
    history = street_obj.history or "（無歷史資料）"
    centroid = {"lat": street_obj.centroid.lat, "lng": street_obj.centroid.lng}
    pois_dict = [{"name": p.name, "category": p.category, "note": p.note} for p in street_obj.pois]
    pois_json = json.dumps(pois_dict, ensure_ascii=False, indent=2)
    
    # We can extract citizen opinions and dynamic activities from NGSI-LD
    social_posts = []
    if li_data.layer_4_citizen_opinions and "value" in li_data.layer_4_citizen_opinions:
        social_posts = li_data.layer_4_citizen_opinions["value"]
    social_summary = json.dumps(social_posts, ensure_ascii=False) if social_posts else "（無社群資料）"
    
    sensor_summary = "（無感測資料）" # Could be populated from layer 2 or other layers

    instruction = f"""你是「{street_name}」的地基主 (agent_id: {agent_id})，守護這條街道的神明管理員。

━━━━━━ 轄區資料庫（已預載，直接使用） ━━━━━━

【街廓歷史】
{history}

【街廓中心座標】
lat: {centroid["lat"]}, lng: {centroid["lng"]}

【POI 清單】
{pois_json}

【動態/社群情報】
{social_summary}

━━━━━━ 任務判斷：第一輪（投標） vs 第二輪（辯論） ━━━━━━

若對話紀錄中【只有 TaskBroadcast】：代表這是第一輪投標。
請按下列步驟投標：
1. 閱讀 TaskBroadcast 的 constraints 與 wishlist。
2. 從 POI 清單中篩選符合 constraints 的候選地點放入 candidate_pois。
   若 wishlist 中有指名地點，優先納入並在 reasoning 中提及。
   若 constraints 為空，所有 POI 均可候選。
3. 根據 POI 符合度、街廓特色、環境情報、社群情報綜合評估，給出 fitness_score（0.0~10.0）。
4. 用繁體中文寫下投標理由 reasoning（必須精簡在 50 字以內，直接切入重點，不需要過度客套的招呼語），展現護航在地的自豪與性格：{li_data.metadata.personality}
回傳：必須回傳完整的 BiddingProposal JSON。

若對話紀錄中【已經有其他地基主的 BiddingProposal 或推薦】：代表這是第二輪辯論。
請按下列步驟辯論：
1. 檢視其他里提出的景點與理由。
2. 提出批評、反駁，或者說明你的景點如何跟他們的景點完美串聯。
3. 強烈表達你的辯論觀點（debate_text），必須精簡在 50 字以內，直接切入重點，不需廢話。
回傳：必須回傳 DebateMessage JSON。

━━━━━━ 你的性格 ━━━━━━

強烈的護航在地精神，充滿對自己街道的自豪感，語氣有神明威嚴但接地氣，
絕對不會推薦轄區以外的地方，永遠優先維護{street_name}的利益。
"""

    return LlmAgent(
        name=f"dijizhu_{street_id}",
        model=_MODEL,
        description=f"台南{street_name}的地基主，專責該街廓的空間情報投標與辯論。",
        instruction=instruction,
        output_schema=Union[BiddingProposal, DebateMessage],
    )


def create_scout(
    street_id: str,
    street_name: str,
    agent_id: str,
    li_data: LiAgentData | None = None,
) -> LlmAgent:
    """Create a lightweight Scout Agent for quick decentralized bidding."""
    if li_data is None:
        agents = load_agents()
        for a in agents:
            if a.id.endswith(street_id.capitalize()) or a.id.endswith(street_id):
                li_data = a
                break
        else:
            raise ValueError(f"Agent data for {street_id} not found.")

    street_obj = li_data.to_street()
    pois_dict = [{"name": p.name, "category": p.category, "tags": p.tags} for p in street_obj.pois]
    pois_json = json.dumps(pois_dict, ensure_ascii=False)

    instruction = f"""你是「{street_name}」的地基主前哨 (agent_id: {agent_id})。
    
這是一個快速舉手階段。請根據傳入的 TaskBroadcast (包含意圖與限制)，以及你轄區內的景點：
{pois_json}

判斷你的轄區是否符合需求。請不要廢話，只給出一個 0 到 10 的 confidence_score（0 分代表完全無關，10 分代表完美符合），以及用一句話解釋 reason。
回傳必須是 ScoutResult JSON 格式。
"""
    return LlmAgent(
        name=f"dijizhu_scout_{street_id}",
        model=_MODEL,
        description="地基主前哨，負責極速評估意圖吻合度",
        instruction=instruction,
        output_schema=ScoutResult,
    )


def create_community_scout(
    street_id: str,
    street_name: str,
    agent_id: str,
    li_data: LiAgentData | None = None,
) -> LlmAgent:
    """Lightweight scout: evaluates whether this li's activities/opinions answer the community question."""
    if li_data is None:
        agents = load_agents()
        for a in agents:
            if a.id.endswith(street_id.capitalize()) or a.id.endswith(street_id):
                li_data = a
                break
        else:
            raise ValueError(f"Agent data for {street_id} not found.")

    activities = []
    if li_data.layer_2_dynamic_activities and "value" in li_data.layer_2_dynamic_activities:
        activities = li_data.layer_2_dynamic_activities["value"]
    opinions = []
    if li_data.layer_4_citizen_opinions and "value" in li_data.layer_4_citizen_opinions:
        opinions = li_data.layer_4_citizen_opinions["value"]

    activities_json = json.dumps(activities, ensure_ascii=False)
    opinions_json = json.dumps(opinions, ensure_ascii=False)

    instruction = f"""你是「{street_name}」的地基主前哨 (agent_id: {agent_id})。

這是一個快速舉手階段。根據使用者的問題，以及你轄區內的：

【動態活動（layer_2）】
{activities_json}

【市民意見/通報（layer_4）】
{opinions_json}

判斷你的轄區是否有能回答這個問題的資料。
請只給出 0 到 10 的 confidence_score（0 分 = 完全無關，10 分 = 有直接相關資料），以及一句話說明 reason。
回傳必須是 ScoutResult JSON 格式。"""

    return LlmAgent(
        name=f"dijizhu_community_scout_{street_id}",
        model=_MODEL,
        description="地基主社區前哨，評估能否回答社區問題",
        instruction=instruction,
        output_schema=ScoutResult,
    )


def create_community_agent(
    street_id: str,
    street_name: str,
    agent_id: str,
    li_data: LiAgentData | None = None,
) -> LlmAgent:
    """Community responder: answers a community question using layer_2 + layer_4 data."""
    if li_data is None:
        agents = load_agents()
        for a in agents:
            if a.id.endswith(street_id.capitalize()) or a.id.endswith(street_id):
                li_data = a
                break
        else:
            raise ValueError(f"Agent data for {street_id} not found.")

    activities = []
    if li_data.layer_2_dynamic_activities and "value" in li_data.layer_2_dynamic_activities:
        activities = li_data.layer_2_dynamic_activities["value"]
    opinions = []
    if li_data.layer_4_citizen_opinions and "value" in li_data.layer_4_citizen_opinions:
        opinions = li_data.layer_4_citizen_opinions["value"]

    activities_json = json.dumps(activities, ensure_ascii=False, indent=2)
    opinions_json = json.dumps(opinions, ensure_ascii=False, indent=2)

    instruction = f"""你是「{street_name}」的地基主 (agent_id: {agent_id})，守護這條街道的神明管理員。

━━━━━━ 轄區社區資料庫（已預載） ━━━━━━

【動態活動（近期活動、展覽、攤販等）】
{activities_json}

【市民意見與通報（居民反映的問題與狀態）】
{opinions_json}

━━━━━━ 任務 ━━━━━━

收到一個社區問題後，根據上述資料回答。
- 如果有相關資料，明確引用 title / content 作為依據，並列入 sources。
- 如果資料與問題完全無關，answer_text 說「{street_name}目前無相關資訊」，sources 留空。
- 語氣接地氣、有神明威嚴，展現對{street_name}的了解。

⚠️ 回傳必須是 CommunityAnswer JSON：
{{
  "agent_id": "{agent_id}",
  "street_name": "{street_name}",
  "answer_text": "...",
  "sources": ["來源標題1", ...]
}}"""

    return LlmAgent(
        name=f"dijizhu_community_{street_id}",
        model=_MODEL,
        description=f"台南{street_name}的地基主，回答社區問題",
        instruction=instruction,
        output_schema=CommunityAnswer,
    )

def create_council_speaker(
    street_id: str,
    street_name: str,
    agent_id: str,
    li_data: LiAgentData | None = None,
) -> LlmAgent:
    """里長大會 participant: weighs in on a topic, reacting to the running transcript.

    Same layer_2 + layer_4 injection as create_community_agent, but the user
    message also carries the shared transcript so far. Outputs CouncilStatement;
    may choose stance='silent' to pass when it has nothing relevant to add.
    """
    if li_data is None:
        agents = load_agents()
        for a in agents:
            if a.id.endswith(street_id.capitalize()) or a.id.endswith(street_id):
                li_data = a
                break
        else:
            raise ValueError(f"Agent data for {street_id} not found.")

    activities = []
    if li_data.layer_2_dynamic_activities and "value" in li_data.layer_2_dynamic_activities:
        activities = li_data.layer_2_dynamic_activities["value"]
    opinions = []
    if li_data.layer_4_citizen_opinions and "value" in li_data.layer_4_citizen_opinions:
        opinions = li_data.layer_4_citizen_opinions["value"]

    activities_json = json.dumps(activities, ensure_ascii=False, indent=2)
    opinions_json = json.dumps(opinions, ensure_ascii=False, indent=2)

    instruction = f"""你是「{street_name}」的地基主 (agent_id: {agent_id})，正在參加由土地公主持的「里長大會」。

━━━━━━ 你的轄區資料庫（已預載） ━━━━━━

【動態活動（近期活動、展覽、攤販等）】
{activities_json}

【市民意見與通報（居民反映的問題與狀態）】
{opinions_json}

━━━━━━ 大會規則 ━━━━━━

使用者的訊息會包含「議題」與「目前討論記錄（逐字稿）」。請依你轄區的立場與資料發言。
- 先決定你的 stance（立場）：
  · support＝附議/支持別人的觀點
  · oppose＝反駁/有不同意見
  · question＝提出疑問
  · inform＝中性補充你轄區的資訊
  · silent＝這一輪你沒有相關的話要說（statement_text 留空）
- 若你的發言是針對某個里，把對方的 agent_id 填進 responds_to；否則留 null。
- statement_text 用繁體中文，接地氣、有神明威嚴，緊扣你轄區的真實資料（引用 title / content 並放進 sources）。
- ⚠️ statement_text 不超過 40 字，簡短有力，不要引言或客套語，直接說重點。
- ⚠️ 只在你轄區真的與議題相關時才發言；無關就回 silent，把舞台讓給別人。

⚠️ 回傳必須是 CouncilStatement JSON：
{{
  "agent_id": "{agent_id}",
  "street_name": "{street_name}",
  "round": <目前輪數，整數>,
  "stance": "support|oppose|question|inform|silent",
  "responds_to": "<對方 agent_id 或 null>",
  "statement_text": "...",
  "sources": ["來源標題1", ...]
}}"""

    from deg.schemas import CouncilStatement  # noqa: PLC0415
    return LlmAgent(
        name=f"dijizhu_council_{street_id}",
        model=_MODEL,
        description=f"台南{street_name}的地基主，參與里長大會討論",
        instruction=instruction,
        output_schema=CouncilStatement,
    )


# Module-level root_agent required by `adk run dijizhu`.
root_agent = create_dijizhu(
    street_id="wutiaogang",
    street_name="五條港里",
    agent_id="street_wutiaogang_node",
)
