"""Integration test: full exploration golden path over WebSocket.

Drives the gateway with FastAPI TestClient's WebSocket support.
Skips if GOOGLE_API_KEY is not set / is the placeholder. Expect 60–120s.
Run: pytest tests/test_gateway_integration.py -v -m integration -s
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


def _require_api_key() -> None:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "paste_your_real_key_here":
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


@pytest.mark.integration
def test_ws_exploration_full_flow():
    _require_api_key()

    from apps.api.gateway import create_app

    client = TestClient(create_app())
    seen_types: list[str] = []
    judgment = None

    with client.websocket_connect("/ws/explore") as ws:
        ws.send_json(
            {"intent_text": "找一間安靜的老宅咖啡", "lat": 22.999, "lng": 120.222}
        )
        while True:
            msg = ws.receive_json()
            seen_types.append(msg["type"])
            if msg["type"] == "judgment":
                judgment = msg["data"]
            if msg["type"] in ("done", "error"):
                break

    assert "error" not in seen_types, f"gateway errored; events={seen_types}"
    assert "task_broadcast" in seen_types
    assert "judgment" in seen_types
    assert "done" in seen_types
    assert judgment is not None
    assert judgment["winner_agent_id"] in {
        "street_shennong_node",
        "street_haian_node",
        "street_zhengxing_node",
    }
    assert len(judgment["ranked_agent_ids"]) == 3
