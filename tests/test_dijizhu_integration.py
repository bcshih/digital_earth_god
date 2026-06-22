"""Integration tests: 地基主 (神農街) → MCP server subprocess → Gemini → BiddingProposal.

Skips automatically if GOOGLE_API_KEY is not set in environment / .env.
Uses real LLM calls — expect 20–45 seconds per test.

Run explicitly:
    pytest tests/test_dijizhu_integration.py -v -m integration -s
"""

from __future__ import annotations

import os

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import ValidationError

from deg.schemas import BiddingProposal, LatLng, TaskBroadcast


def _require_api_key():
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "paste_your_real_key_here":
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


@pytest.mark.integration
async def test_wutiaogang_returns_valid_bidding_proposal():
    """End-to-end: TaskBroadcast → 地基主 → Gemini + MCP tools → BiddingProposal."""
    _require_api_key()

    # Import inside test so McpToolset isn't constructed during collection
    from dijizhu.agent import create_dijizhu  # noqa: PLC0415

    agent = create_dijizhu(
        street_id="wutiaogang",
        street_name="五條港里",
        agent_id="street_wutiaogang_node",
    )

    task = TaskBroadcast(
        task_id="integration_001",
        intent="find_cafe_avoid_crowd",
        user_location=LatLng(lat=22.999, lng=120.222),
        constraints=["咖啡", "安靜"],
        timeout_ms=30000,
    )

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="deg", user_id="test_user", session_id="s_001"
    )
    runner = Runner(agent=agent, app_name="deg", session_service=session_service)

    msg = types.Content(role="user", parts=[types.Part(text=task.model_dump_json())])
    final_text = ""
    async for event in runner.run_async(
        user_id="test_user", session_id="s_001", new_message=msg
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
    assert proposal.task_id == "integration_001"
    assert 0.0 <= proposal.fitness_score <= 10.0
    assert len(proposal.reasoning) > 10, "reasoning should be a meaningful sentence"
    assert proposal.spatial_data is not None


@pytest.mark.integration
async def test_mcp_tools_actually_called():
    """Verify the agent retrieved POIs from MCP (candidate_pois non-empty)."""
    _require_api_key()

    from dijizhu.agent import create_dijizhu  # noqa: PLC0415

    agent = create_dijizhu(
        street_id="wutiaogang",
        street_name="五條港里",
        agent_id="street_wutiaogang_node",
    )

    task = TaskBroadcast(
        task_id="integration_002",
        intent="find_cafe",
        user_location=LatLng(lat=22.999, lng=120.222),
        constraints=["cafe"],
    )

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="deg", user_id="test_user", session_id="s_002"
    )
    runner = Runner(agent=agent, app_name="deg", session_service=session_service)
    msg = types.Content(role="user", parts=[types.Part(text=task.model_dump_json())])

    final_text = ""
    async for event in runner.run_async(
        user_id="test_user", session_id="s_002", new_message=msg
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text
            break

    proposal = BiddingProposal.model_validate_json(final_text)
    assert len(proposal.candidate_pois) >= 1, (
        "Expected ≥1 candidate_poi — agent may not have called MCP tools. "
        f"Raw response:\n{final_text}"
    )
