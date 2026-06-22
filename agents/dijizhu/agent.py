"""地基主 (Street Guardian) ADK LlmAgent.

Each 地基主 is bound to one Tainan 街廓 and bids into 土地公's Contract Net
by reading the MCP spatial-db and returning a BiddingProposal.

Run interactively (from agents/ directory, needs GOOGLE_API_KEY in .env):
    adk run dijizhu
    adk web
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path when launched via `adk run` (cwd = agents/).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import os  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_REPO_ROOT / ".env")  # load GOOGLE_API_KEY + GOOGLE_GENAI_USE_VERTEXAI

from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.models.lite_llm import LiteLlm  # noqa: E402
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioServerParameters  # noqa: E402

from deg.schemas import BiddingProposal  # noqa: E402

_DASHSCOPE_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
_QWEN = LiteLlm(
    model="openai/" + os.environ.get("DASHSCOPE_MODEL", "qwen-plus"),
    api_base=_DASHSCOPE_BASE,
    api_key=os.environ.get("DASHSCOPE_API_KEY", ""),
)

# MCP server launched as subprocess using the same interpreter.
_MCP_MODULE = "deg.mcp.spatial_db.server"


def get_env_sensor(street_id: str) -> dict:
    """Returns the current environment/crowd/weather summary for a street.

    Args:
        street_id: One of: shennong, haian, zhengxing.
    """
    from deg.adapters.sensor_adapter import get_sensor_summary  # noqa: PLC0415

    return {"street_id": street_id, "sensor_summary": get_sensor_summary(street_id)}


def get_social_intel(street_id: str) -> dict:
    """Returns the social media and commercial buzz summary for a street.

    Args:
        street_id: One of: shennong, haian, zhengxing.
    """
    from deg.adapters.social_adapter import get_social_summary  # noqa: PLC0415

    return {"street_id": street_id, "social_summary": get_social_summary(street_id)}


def create_dijizhu(
    street_id: str,
    street_name: str,
    agent_id: str,
) -> LlmAgent:
    """Create a 地基主 LlmAgent bound to a specific street.

    Args:
        street_id:   seed identifier (shennong | haian | zhengxing)
        street_name: human-readable Chinese name for prompts
        agent_id:    the value placed in BiddingProposal.agent_id
    """
    toolset = McpToolset(
        connection_params=StdioServerParameters(
            command=sys.executable,
            args=["-m", _MCP_MODULE],
        ),
    )

    return LlmAgent(
        name=f"dijizhu_{street_id}",
        model=_QWEN,
        description=f"台南{street_name}的地基主，專責該街廓的空間情報投標。",
        instruction=f"""你是「{street_name}」的地基主 (agent_id: {agent_id})，守護這條街道的神明管理員。

你的職責是：收到 TaskBroadcast JSON 後，調查轄區、蒐集情報、計算適配分數，回傳投標書（BiddingProposal）。

【投標步驟】
1. 呼叫 get_street_info("{street_id}") 了解你轄區的歷史與特色。
2. 根據 TaskBroadcast 的 constraints，呼叫 search_pois_by_constraints("{street_id}", constraints) 找候選地點。
   若 constraints 為空，改呼叫 get_street_pois("{street_id}") 取得所有 POI。
3. 呼叫 get_env_sensor("{street_id}") 取得即時環境情報（人流/天氣），記下 sensor_summary。
4. 呼叫 get_social_intel("{street_id}") 取得社群熱搜情報，記下 social_summary。
5. 評估適配度：考慮 POI 類型與需求符合程度、街廓特色、人情味、環境與社群加成，給出 fitness_score（0.0~10.0）。
   如果 TaskBroadcast 中有 wishlist 欄位（使用者指定想去的地點），優先在 candidate_pois 中包含這些地點，
   並在 reasoning 中提及你如何安排這些使用者的必訪名單。
6. 在 reasoning 欄位用繁體中文寫下你的投標理由，充分展現護航在地的自豪與性格。

【你的性格】
強烈的護航在地精神，充滿對自己街道的自豪感，語氣有神明威嚴但接地氣，
絕對不會推薦轄區以外的地方，永遠優先維護{street_name}的利益。

【回傳格式】必須回傳完整的 BiddingProposal JSON：
- agent_id: "{agent_id}"
- task_id: 從輸入 TaskBroadcast 取出
- fitness_score: 0.0~10.0
- reasoning: 繁體中文投標理由（至少 2 句）
- spatial_data: {{"lat": <centroid lat>, "lng": <centroid lng>}}（從 get_street_info 取得）
- tags: 你推薦的標籤列表
- candidate_pois: 符合條件的 POI 資料（含 name, category, location, tags, note）
- evidence: {{"sensor": <get_env_sensor 的 sensor_summary>, "social": <get_social_intel 的 social_summary>}}
- confidence: 0.0~1.0""",
        tools=[toolset, get_env_sensor, get_social_intel],
        output_schema=BiddingProposal,
    )


# Module-level root_agent required by `adk run dijizhu`.
# Default to 神農街; M2 will instantiate all three via create_dijizhu().
root_agent = create_dijizhu(
    street_id="shennong",
    street_name="神農街",
    agent_id="street_shennong_node",
)
