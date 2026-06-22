"""Integration: wish categorizer + blessing agents (real LLM). Skips without API key."""

from __future__ import annotations

import json
import os

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from deg.schemas import Blessing, WishAnalysis


def _require_api_key() -> None:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "paste_your_real_key_here":
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


async def _run(agent, payload: str) -> str:
    ss = InMemorySessionService()
    await ss.create_session(app_name="deg", user_id="u", session_id="s")
    runner = Runner(agent=agent, app_name="deg", session_service=ss)
    msg = types.Content(role="user", parts=[types.Part(text=payload)])
    out = ""
    async for event in runner.run_async(user_id="u", session_id="s", new_message=msg):
        if event.is_final_response() and event.content and event.content.parts:
            out = event.content.parts[0].text
            break
    return out


@pytest.mark.integration
async def test_wish_categorizer():
    _require_api_key()
    from wuying.wish_agent import create_wish_categorizer  # noqa: PLC0415

    payload = json.dumps(
        {"raw_text": "海安路晚上太暗了，希望多裝幾盞路燈比較安全", "lat": 22.992, "lng": 120.198},
        ensure_ascii=False,
    )
    analysis = WishAnalysis.model_validate_json(await _run(create_wish_categorizer(), payload))
    assert len(analysis.category) > 0
    assert len(analysis.summary) > 0


@pytest.mark.integration
async def test_blessing_agent():
    _require_api_key()
    from tudigong.blessing_agent import create_blessing_agent  # noqa: PLC0415

    payload = json.dumps(
        {"raw_text": "希望神農街可以一直保持安靜美好", "category": "社區營造",
         "summary": "期望神農街維持寧靜氛圍"},
        ensure_ascii=False,
    )
    blessing = Blessing.model_validate_json(await _run(create_blessing_agent(), payload))
    assert len(blessing.blessing) > 5
    assert len(blessing.acknowledgment) > 0
