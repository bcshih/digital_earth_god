"""Integration tests: 土地公 Contract Net pipeline end-to-end.

Runs the full SequentialAgent(ParallelAgent([3×地基主]) → tudigong LLM-as-Judge).
Skips automatically if GOOGLE_API_KEY is not set / is still the placeholder.
Expect 60–120 seconds (3 parallel LLM+MCP calls + 1 judge call).

Run explicitly:
    pytest tests/test_tudigong_integration.py -v -m integration -s
"""

from __future__ import annotations

import os

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import ValidationError

from deg.schemas import JudgmentResult, LatLng, TaskBroadcast


def _require_api_key():
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "paste_your_real_key_here":
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


@pytest.mark.integration
async def test_full_contract_net_returns_judgment():
    """End-to-end: TaskBroadcast → 3 parallel 地基主 → 土地公 judge → JudgmentResult."""
    _require_api_key()

    # Import inside test so pipeline (and its 3 McpToolsets) isn't built at collection
    from tudigong.agent import create_pipeline  # noqa: PLC0415

    pipeline = create_pipeline()

    task = TaskBroadcast(
        task_id="m2_integration_001",
        intent="find_cafe_avoid_crowd",
        user_location=LatLng(lat=22.999, lng=120.222),
        constraints=["咖啡", "安靜"],
        timeout_ms=60000,
    )

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="deg", user_id="test_user", session_id="m2_s_001"
    )
    runner = Runner(agent=pipeline, app_name="deg", session_service=session_service)

    msg = types.Content(role="user", parts=[types.Part(text=task.model_dump_json())])
    final_text = ""
    async for event in runner.run_async(
        user_id="test_user", session_id="m2_s_001", new_message=msg
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text
            break

    assert final_text, "Pipeline produced no final response"

    try:
        result = JudgmentResult.model_validate_json(final_text)
    except ValidationError as exc:
        pytest.fail(
            f"Response is not a valid JudgmentResult.\n"
            f"Raw response:\n{final_text}\n"
            f"Validation error:\n{exc}"
        )

    assert result.task_id == "m2_integration_001"
    assert len(result.contributing_agent_ids) >= 1
    assert len(result.recommendation) > 10
    assert len(result.reasoning) > 10


@pytest.mark.integration
async def test_judgment_returns_itinerary_with_pois():
    """Verify the judge included POIs in the itinerary (MCP data flowed through)."""
    _require_api_key()

    from tudigong.agent import create_pipeline  # noqa: PLC0415

    pipeline = create_pipeline()

    task = TaskBroadcast(
        task_id="m2_integration_002",
        intent="find_local_food",
        user_location=LatLng(lat=22.999, lng=120.222),
        constraints=["小吃", "在地"],
    )

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="deg", user_id="test_user", session_id="m2_s_002"
    )
    runner = Runner(agent=pipeline, app_name="deg", session_service=session_service)
    msg = types.Content(role="user", parts=[types.Part(text=task.model_dump_json())])

    final_text = ""
    async for event in runner.run_async(
        user_id="test_user", session_id="m2_s_002", new_message=msg
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text
            break

    result = JudgmentResult.model_validate_json(final_text)
    assert len(result.itinerary) >= 1, (
        "Expected ≥1 itinerary stop — judge may not have included POI data. "
        f"Raw response:\n{final_text}"
    )
