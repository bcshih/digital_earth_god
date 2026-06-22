"""路由過濾器 Agent.

Analyzes a TaskBroadcast and the list of available Li agents, then selects the top N 
agents that are most relevant to the task constraints.
"""

from __future__ import annotations

import json
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent
from deg.seed.loader import load_agents

_MODEL = "gemini-3.1-flash-lite"

class RouterResult(BaseModel):
    selected_agent_ids: list[str] = Field(description="List of selected agent IDs, exactly 3 to 5 items.")
    reasoning: str = Field(description="Reasoning for why these agents were selected.")

def create_router_agent() -> LlmAgent:
    """Create the router agent that filters 20 agents down to 3-5."""
    
    agents = load_agents()
    candidates_info = []
    for a in agents:
        street = a.to_street()
        candidates_info.append({
            "agent_id": street.agent_id,
            "name": street.name,
            "feature": street.history[:100] + "..." if len(street.history) > 100 else street.history,
        })
        
    candidates_json = json.dumps(candidates_info, ensure_ascii=False, indent=2)

    instruction = f"""你是數位土地公的「選派使者」，負責在發包任務前，從台南市中西區的 20 個里（地基主）中挑選出最合適的里來參與競標。

━━━━━━ 候選名單（20 個里） ━━━━━━
{candidates_json}

━━━━━━ 你的任務 ━━━━━━
使用者會傳入 TaskBroadcast JSON 內容（包含 intent, constraints, wishlist 等）。
1. 請先判斷行程的複雜度：
   - 若是「半天」或「單日」的短行程，請挑選 3 到 5 個里。
   - 若是「兩天一夜」、「三天兩夜」等多天數的長行程，請挑選 5 到 8 個里，以確保有足夠的景點與變化。
2. 分析候選名單中各里的特色（feature），並挑選出「最符合條件」或「最有潛力滿足需求」的 agent_id。

回傳必須是符合 RouterResult Schema 的 JSON：
- selected_agent_ids: 包含選中的 agent_id 字串陣列
- reasoning: 挑選的理由說明（必須提及行程長短判斷）
"""

    return LlmAgent(
        name="router_agent",
        model=_MODEL,
        description="過濾並挑選最合適的 3-5 個地基主 Agent 參與競標。",
        instruction=instruction,
        output_schema=RouterResult,
    )

root_agent = create_router_agent()
