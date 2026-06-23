import os
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _p in (_REPO, _REPO / "agents"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from dijizhu.agent import create_community_scout, create_community_agent
from deg.seed.loader import LiAgentData, Metadata


def _require_api_key() -> None:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "paste_your_real_key_here":
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


def _dummy_li(street_id: str = "wutiaogang") -> LiAgentData:
    return LiAgentData(
        id=f"urn:ngsi-ld:EarthGodAgent:Tainan:WestCentral:{street_id.capitalize()}",
        type="EarthGodAgent",
        metadata=Metadata(agent_name=f"{street_id}地基主", personality="豪邁大方"),
        layer_2_dynamic_activities={
            "type": "Property",
            "value": [{"title": "普濟殿元宵花燈展", "verification_level": "official", "trust_score": 100}],
        },
        layer_4_citizen_opinions={
            "type": "Property",
            "value": [{"issue_id": "WISH-001", "type": "抱怨/通報", "content": "巷弄擁擠", "status": "待處理"}],
        },
    )

@pytest.mark.integration
def test_create_community_scout_returns_llm_agent():
    _require_api_key()
    from google.adk.agents import LlmAgent
    agent = create_community_scout("wutiaogang", "五條港里", "street_wutiaogang_node", _dummy_li())
    assert isinstance(agent, LlmAgent)
    assert "wutiaogang" in agent.name
    assert "普濟殿元宵花燈展" in agent.instruction


@pytest.mark.integration
def test_create_community_agent_returns_llm_agent():
    _require_api_key()
    from google.adk.agents import LlmAgent
    agent = create_community_agent("wutiaogang", "五條港里", "street_wutiaogang_node", _dummy_li())
    assert isinstance(agent, LlmAgent)
    assert "巷弄擁擠" in agent.instruction
