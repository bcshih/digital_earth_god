"""Integration tests: 地基主 → MCP + sensor + social → BiddingProposal with evidence.

Skips automatically if GOOGLE_API_KEY is not set / is the placeholder.
Run explicitly:
    pytest tests/test_dijizhu_evidence_integration.py -v -m integration -s
"""

from __future__ import annotations

import os

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import ValidationError

from deg.schemas import BiddingProposal, LatLng, TaskBroadcast


def _require_api_key() -> None:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "paste_your_real_key_here":
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


@pytest.mark.integration
async def test_dijizhu_returns_evidence_in_proposal():
    """地基主 should call env_sensor + social_intel and populate BiddingProposal.evidence."""
    _require_api_key()

    from dijizhu.agent import create_dijizhu  # noqa: PLC0415

    agent = create_dijizhu("wutiaogang", "五條港里", "street_wutiaogang_node")
    task = TaskBroadcast(
        task_id="evidence_test_001",
        intent="find_quiet_cafe",
        user_location=LatLng(lat=22.999, lng=120.222),
        constraints=["咖啡", "安靜"],
    )

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="deg", user_id="test_user", session_id="ev_s_001"
    )
    runner = Runner(agent=agent, app_name="deg", session_service=session_service)
    msg = types.Content(role="user", parts=[types.Part(text=task.model_dump_json())])

    final_text = ""
    async for event in runner.run_async(
        user_id="test_user", session_id="ev_s_001", new_message=msg
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text
            break

    assert final_text, "Agent produced no response"

    try:
        proposal = BiddingProposal.model_validate_json(final_text)
    except ValidationError as exc:
        pytest.fail(
            f"Response is not a valid BiddingProposal.\n"
            f"Raw response:\n{final_text}\n"
            f"Validation error:\n{exc}"
        )

    assert proposal.agent_id == "street_wutiaogang_node"
    assert 0.0 <= proposal.fitness_score <= 10.0

    # Evidence should now be populated (sensor + social)
    assert proposal.evidence is not None, "evidence should be set — agent should call sensor + social tools"
    assert proposal.evidence.sensor is not None, "evidence.sensor should be populated by get_env_sensor"
    assert proposal.evidence.social is not None, "evidence.social should be populated by get_social_intel"
    assert len(proposal.evidence.sensor) > 5
    assert len(proposal.evidence.social) > 5
