"""Integration tests: 土地公 → 3 remote 地基主 A2A servers → JudgmentResult.

Starts 3 A2A HTTP servers in-process, then runs the remote pipeline.
Skips if GOOGLE_API_KEY is not set / is the placeholder.
Expect 90–180 seconds (3 parallel A2A round trips with real LLM).

Run explicitly:
    pytest tests/test_tudigong_remote_integration.py -v -m integration -s
"""

from __future__ import annotations

import asyncio
import os

import httpx
import pytest
import uvicorn
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import ValidationError

from deg.schemas import JudgmentResult, LatLng, TaskBroadcast


def _require_api_key() -> None:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "paste_your_real_key_here":
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


async def _wait_for_server(url: str, timeout: float = 30.0) -> None:
    """Poll GET on url until HTTP 200 or timeout."""
    deadline = asyncio.get_event_loop().time() + timeout
    async with httpx.AsyncClient() as client:
        while asyncio.get_event_loop().time() < deadline:
            try:
                resp = await client.get(url, timeout=2.0)
                if resp.status_code == 200:
                    return
            except Exception:
                pass
            await asyncio.sleep(0.5)
    raise TimeoutError(f"Server at {url} did not become ready within {timeout}s")


@pytest.mark.integration
async def test_remote_pipeline_returns_judgment():
    """Full remote A2A pipeline: 3 地基主 servers + 土地公 judge → JudgmentResult."""
    _require_api_key()

    from dijizhu.a2a_server import STREET_CONFIGS, build_dijizhu_app
    from tudigong.agent import create_pipeline_remote

    # Start 3 地基主 A2A servers as asyncio background tasks.
    servers: list[tuple[uvicorn.Server, asyncio.Task]] = []
    base_urls: dict[str, str] = {}

    try:
        for street_id, (street_name, agent_id, port) in STREET_CONFIGS.items():
            app = build_dijizhu_app(street_id, street_name, agent_id, port)
            config = uvicorn.Config(
                app, host="127.0.0.1", port=port, log_level="error"
            )
            server = uvicorn.Server(config)
            task = asyncio.create_task(server.serve())
            servers.append((server, task))
            base_urls[street_id] = f"http://127.0.0.1:{port}"

        # Wait for all servers to be ready (health check via agent card endpoint).
        card_urls = [f"{url}/.well-known/agent-card.json" for url in base_urls.values()]
        await asyncio.gather(*[_wait_for_server(u) for u in card_urls])

        # Run the remote pipeline.
        pipeline = create_pipeline_remote(base_urls)
        task_broadcast = TaskBroadcast(
            task_id="m3_integration_001",
            intent="find_cafe_avoid_crowd",
            user_location=LatLng(lat=22.999, lng=120.222),
            constraints=["咖啡", "安靜"],
            timeout_ms=90000,
        )
        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name="deg", user_id="test_user", session_id="m3_s_001"
        )
        runner = Runner(
            agent=pipeline, app_name="deg", session_service=session_service
        )
        msg = types.Content(
            role="user",
            parts=[types.Part(text=task_broadcast.model_dump_json())],
        )

        final_text = ""
        async for event in runner.run_async(
            user_id="test_user", session_id="m3_s_001", new_message=msg
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text
                break

        assert final_text, "Remote pipeline produced no final response"

        try:
            result = JudgmentResult.model_validate_json(final_text)
        except ValidationError as exc:
            pytest.fail(
                f"Response is not a valid JudgmentResult.\n"
                f"Raw:\n{final_text}\n"
                f"Validation error:\n{exc}"
            )

        assert result.task_id == "m3_integration_001"
        assert len(result.contributing_agent_ids) >= 1
        assert len(result.recommendation) > 10
        assert len(result.itinerary) >= 1

    finally:
        # Graceful shutdown of all A2A servers.
        for server, srv_task in servers:
            server.should_exit = True
        await asyncio.gather(
            *[srv_task for _, srv_task in servers], return_exceptions=True
        )
