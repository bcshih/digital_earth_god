"""?啣銝?(Street Guardian) ADK LlmAgent.

Each ?啣銝?is bound to one Tainan 銵? and bids into ???s Contract Net
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

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_REPO_ROOT / ".env")  # load GOOGLE_API_KEY + GOOGLE_GENAI_USE_VERTEXAI

from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioServerParameters  # noqa: E402

from deg.schemas import BiddingProposal  # noqa: E402

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
    """Create a ?啣銝?LlmAgent bound to a specific street.

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
        model="gemini-2.0-flash",
        description=f"?啣?{street_name}??箔蜓嚗?鞎祈府銵??征???望?璅?,
        instruction=f"""雿?street_name}???啣銝?(agent_id: {agent_id})嚗?霅琿?銵????恣???
雿??瑁痊?荔??嗅 TaskBroadcast JSON 敺?隤踵頧??????晞?蝞???賂?????賂?BiddingProposal嚗?
??璅郊撽?1. ?澆 get_street_info("{street_id}") 鈭圾雿???風?脰??寡??2. ?寞? TaskBroadcast ??constraints嚗??search_pois_by_constraints("{street_id}", constraints) ?曉?圈???   ??constraints ?箇征嚗?澆 get_street_pois("{street_id}") ?????POI??3. ?澆 get_env_sensor("{street_id}") ???單??啣??嚗犖瘚?憭拇除嚗?閮? sensor_summary??4. ?澆 get_social_intel("{street_id}") ??蝷曄黎?望??嚗?銝?social_summary??5. 閰摯?拚?摨佗?? POI 憿???瘙泵??摨艾?撱?脯犖??憓?蝷曄黎??嚗策??fitness_score嚗?.0~10.0嚗?   憒? TaskBroadcast 銝剜? wishlist 甈?嚗蝙?刻?摰?餌??圈?嚗??芸???candidate_pois 銝剖??恍??圈?嚗?   銝血 reasoning 銝剜???憒?摰???雿輻??敹赤???6. ??reasoning 甈??函?擃葉?神銝???璅??梧???撅霅瑁?典?鞊芾??扳??
???扳??撘瑞??風?芸?啁移蟡??遛撠撌梯????芾悸??隤除?????港??亙瘞??
蝯?銝??刻頧?隞亙???對?瘞賊??芸?蝬剛風{street_name}???
???單撘????喳??渡? BiddingProposal JSON嚗?- agent_id: "{agent_id}"
- task_id: 敺撓??TaskBroadcast ?
- fitness_score: 0.0~10.0
- reasoning: 蝜?銝剜????嚗撠?2 ?伐?
- spatial_data: {{"lat": <centroid lat>, "lng": <centroid lng>}}嚗? get_street_info ??嚗?- tags: 雿?衣?璅惜?”
- candidate_pois: 蝚血?璇辣??POI 鞈?嚗 name, category, location, tags, note嚗?- evidence: {{"sensor": <get_env_sensor ??sensor_summary>, "social": <get_social_intel ??social_summary>}}
- confidence: 0.0~1.0""",
        tools=[toolset, get_env_sensor, get_social_intel],
        output_schema=BiddingProposal,
    )


# Module-level root_agent required by `adk run dijizhu`.
# Default to 蟡噙銵? M2 will instantiate all three via create_dijizhu().
root_agent = create_dijizhu(
    street_id="shennong",
    street_name="蟡噙銵?,
    agent_id="street_shennong_node",
)
