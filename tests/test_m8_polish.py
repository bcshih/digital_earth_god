"""M8 polish unit tests — randomness, error handling, copy."""



# ── 1. Randomness pool ───────────────────────────────────────────────────────

def test_mood_pool_has_items():
    from tudigong.agent import _MOOD_POOL
    assert len(_MOOD_POOL) >= 8


def test_get_random_mood_returns_nonempty_string():
    from tudigong.agent import get_random_mood
    mood = get_random_mood()
    assert isinstance(mood, str) and len(mood) > 5


def test_get_random_mood_draws_from_pool():
    from tudigong.agent import _MOOD_POOL, get_random_mood
    # Run 30 draws; each result must be a pool member.
    for _ in range(30):
        assert get_random_mood() in _MOOD_POOL


# ── 2. Gateway error handling (no LLM) ──────────────────────────────────────

def test_gateway_wish_rejects_missing_text():
    from fastapi.testclient import TestClient
    from apps.api.gateway import create_app
    client = TestClient(create_app())
    resp = client.post("/wish", json={"lat": 22.9, "lng": 120.2})  # missing wish_text
    assert resp.status_code == 422


def test_gateway_wish_rejects_bad_latlng():
    from fastapi.testclient import TestClient
    from apps.api.gateway import create_app
    client = TestClient(create_app())
    resp = client.post("/wish", json={"wish_text": "測試", "lat": 200.0, "lng": 0.0})
    assert resp.status_code == 422


def test_gateway_pipeline_timeout_constants():
    from apps.api.gateway import _PIPELINE_TIMEOUT, _WISH_TIMEOUT
    assert _PIPELINE_TIMEOUT >= 60
    assert _WISH_TIMEOUT >= 30


# ── 3. Copy polish ───────────────────────────────────────────────────────────

def test_intent_title_is_concise():
    from deg.a2ui.surfaces import intent_input_components
    comps = intent_input_components()
    title = next(c for c in comps if c["id"] == "intent-title")
    assert "土地公" in title["text"]


def test_blessing_title_has_warmth():
    from deg.a2ui.surfaces import blessing_components
    comps = blessing_components()
    title = next(c for c in comps if c["id"] == "blessing-title")
    assert "土地公" in title["text"]


def test_verdict_title_updated():
    from deg.a2ui.surfaces import judgment_components
    comps = judgment_components()
    title = next(c for c in comps if c["id"] == "verdict-title")
    assert "裁決" in title["text"]


# ── 4. Demo script importable ────────────────────────────────────────────────

def test_demo_script_imports():
    import importlib.util
    import pathlib
    spec = importlib.util.spec_from_file_location(
        "demo",
        pathlib.Path(__file__).parent.parent / "scripts" / "demo.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.demo_explore)
    assert callable(mod.demo_wish)
    assert callable(mod.demo_dashboard)
