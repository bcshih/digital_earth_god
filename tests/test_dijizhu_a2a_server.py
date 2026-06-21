"""Unit tests for 地基主 A2A server — card and app construction, no LLM needed."""

from a2a.types import AgentCard


def test_build_dijizhu_card_shennong():
    from dijizhu.a2a_server import build_dijizhu_card
    card = build_dijizhu_card("shennong", "神農街", 9001)
    assert isinstance(card, AgentCard)
    assert card.name == "dijizhu_shennong"
    assert "神農街" in card.description
    assert card.url == "http://127.0.0.1:9001/"
    assert len(card.skills) >= 1


def test_build_dijizhu_card_all_streets():
    from dijizhu.a2a_server import build_dijizhu_card
    for street_id, street_name, port in [
        ("shennong", "神農街", 9001),
        ("haian", "海安路", 9002),
        ("zhengxing", "正興街", 9003),
    ]:
        card = build_dijizhu_card(street_id, street_name, port)
        assert card.url == f"http://127.0.0.1:{port}/"


def test_build_dijizhu_app_returns_starlette():
    from dijizhu.a2a_server import build_dijizhu_app
    import starlette.applications
    app = build_dijizhu_app("shennong", "神農街", "street_shennong_node", 9001)
    assert isinstance(app, starlette.applications.Starlette)


def test_street_configs_complete():
    from dijizhu.a2a_server import STREET_CONFIGS
    assert "shennong" in STREET_CONFIGS
    assert "haian" in STREET_CONFIGS
    assert "zhengxing" in STREET_CONFIGS
    for street_id, (name, agent_id, port) in STREET_CONFIGS.items():
        assert isinstance(port, int)
        assert 9000 < port < 9100
