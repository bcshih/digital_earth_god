"""Unit tests for the FastAPI gateway — app/route construction, no LLM calls.

Uses TestClient. Agent construction at app-build time does NOT call the LLM,
so these run without an API key.
"""

from fastapi.testclient import TestClient


def _client() -> TestClient:
    from apps.api.gateway import create_app
    return TestClient(create_app())


def test_health_ok():
    client = _client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_intent_rejects_missing_fields():
    client = _client()
    resp = client.post("/intent", json={"intent_text": "找咖啡"})  # missing lat/lng
    assert resp.status_code == 422


def test_intent_rejects_bad_latlng():
    client = _client()
    resp = client.post(
        "/intent", json={"intent_text": "找咖啡", "lat": 999.0, "lng": 0.0}
    )
    assert resp.status_code == 422


def test_routes_registered():
    from apps.api.gateway import create_app
    app = create_app()
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/health" in paths
    assert "/intent" in paths
    assert "/ws/explore" in paths


def test_a2ui_route_registered():
    from apps.api.gateway import create_app
    app = create_app()
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/ws/explore/a2ui" in paths
