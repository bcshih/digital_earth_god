"""Unit tests for the wish endpoints — routes + validation, no LLM (no API key)."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DEG_WARMDATA_DB", str(tmp_path / "test_wd.db"))
    from apps.api.gateway import create_app
    return TestClient(create_app())


def test_wish_routes_registered(client):
    paths = {getattr(r, "path", None) for r in client.app.routes}
    assert {"/wish", "/wishes", "/dashboard/summary", "/ws/wish/a2ui"} <= paths


def test_wish_rejects_missing_fields(client):
    assert client.post("/wish", json={"wish_text": "x"}).status_code == 422


def test_dashboard_summary_ok(client):
    resp = client.get("/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert {"total", "by_category", "points", "recent"} <= body.keys()
    assert body["total"] == 0  # isolated empty DB


def test_wishes_empty(client):
    resp = client.get("/wishes")
    assert resp.status_code == 200
    assert resp.json()["wishes"] == []
