"""Integration: full A2UI transcript over /ws/explore/a2ui.

Skips if GOOGLE_API_KEY is not set / is the placeholder. Expect 60–120s.
Validates the durable A2UI contract end-to-end: every updateComponents message is a
valid flat adjacency list, and the transcript reaches a verdict surface.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from deg.a2ui.builder import assert_valid_components


def _require_api_key() -> None:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "paste_your_real_key_here":
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


@pytest.mark.integration
def test_a2ui_transcript_is_valid_and_reaches_verdict():
    _require_api_key()

    from apps.api.gateway import create_app

    client = TestClient(create_app())
    msgs: list[dict] = []
    with client.websocket_connect("/ws/explore/a2ui") as ws:
        first = ws.receive_json()
        assert "createSurface" in first
        ws.send_json({"intent_text": "找一間安靜的老宅咖啡", "lat": 22.999, "lng": 120.222})
        while True:
            m = ws.receive_json()
            msgs.append(m)
            if m.get("a2uiDone") or m.get("a2uiError"):
                break

    assert not any(m.get("a2uiError") for m in msgs), [m for m in msgs if m.get("a2uiError")]
    for m in msgs:
        if "updateComponents" in m:
            assert_valid_components(m["updateComponents"]["components"])
    verdicts = [m for m in msgs if m.get("updateDataModel", {}).get("path") == "/verdict"]
    assert verdicts, "no verdict surface emitted"
    assert len(verdicts[-1]["updateDataModel"]["value"]["itinerary"]) >= 1
    bid_updates = [
        m for m in msgs
        if m.get("updateDataModel", {}).get("path", "").startswith("/bids/")
    ]
    assert bid_updates, "no bid cards emitted"
