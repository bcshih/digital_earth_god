"""Integration: POST /wish full flow (categorize → persist → blessing). Skips without key."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


def _require_api_key() -> None:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "paste_your_real_key_here":
        pytest.skip("GOOGLE_API_KEY not set — skipping integration test")


@pytest.mark.integration
def test_post_wish_returns_blessing_and_persists(tmp_path, monkeypatch):
    _require_api_key()
    monkeypatch.setenv("DEG_WARMDATA_DB", str(tmp_path / "wd.db"))
    from apps.api.gateway import create_app

    client = TestClient(create_app())
    resp = client.post("/wish", json={
        "wish_text": "希望神農街的老房子可以被好好保存下來",
        "lat": 22.9971, "lng": 120.2010,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["analysis"]["category"]
    assert len(body["blessing"]["blessing"]) > 5
    assert body["wish"]["wish_id"]

    summary = client.get("/dashboard/summary").json()
    assert summary["total"] >= 1
