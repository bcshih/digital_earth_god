"""Integration test: 五營兵將 intent extraction → TaskBroadcast.

Skips if GOOGLE_API_KEY is not set / is the placeholder.
Run: pytest tests/test_wuying_integration.py -v -m integration -s
"""

from __future__ import annotations

import json
import os

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import ValidationError

from deg.schemas import TaskBroadcast


def _require_api_key() -> None:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "paste_your_real_key_here":
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


@pytest.mark.integration
async def test_wuying_extracts_task_broadcast():
    _require_api_key()

    from wuying.agent import create_wuying  # noqa: PLC0415

    agent = create_wuying()
    payload = json.dumps(
        {
            "raw_text": "我想找一間安靜的老宅咖啡，可以待整個下午",
            "lat": 22.999,
            "lng": 120.222,
            "task_id": "wuying_test_001",
        },
        ensure_ascii=False,
    )

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="deg", user_id="test_user", session_id="wy_s_001"
    )
    runner = Runner(agent=agent, app_name="deg", session_service=session_service)
    msg = types.Content(role="user", parts=[types.Part(text=payload)])

    final_text = ""
    async for event in runner.run_async(
        user_id="test_user", session_id="wy_s_001", new_message=msg
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text
            break

    assert final_text, "五營兵將 produced no response"

    try:
        tb = TaskBroadcast.model_validate_json(final_text)
    except ValidationError as exc:
        pytest.fail(f"Not a valid TaskBroadcast.\nRaw:\n{final_text}\nError:\n{exc}")

    assert tb.task_id == "wuying_test_001"
    assert len(tb.intent) > 0
    assert len(tb.constraints) >= 1, "should extract at least one constraint keyword"
