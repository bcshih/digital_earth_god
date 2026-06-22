"""Unit tests for 地基主 A2A server — card and app construction, no LLM needed."""

from a2a.types import AgentCard


def test_build_dijizhu_card_wutiaogang():
    from dijizhu.a2a_server import build_dijizhu_card
    card = build_dijizhu_card("wutiaogang", "五條港里", 9001)
    assert isinstance(card, AgentCard)
    assert card.name == "dijizhu_wutiaogang"
    assert "五條港里" in card.description
    assert card.url == "http://127.0.0.1:9001/"
    assert len(card.skills) >= 1


def test_build_dijizhu_card_all_streets():
    from dijizhu.a2a_server import build_dijizhu_card
    for street_id, street_name, port in [
        ("wutiaogang", "五條港里", 9001),
        ("guangxian", "光賢里", 9002),
    ]:
        card = build_dijizhu_card(street_id, street_name, port)
        assert card.url == f"http://127.0.0.1:{port}/"


def test_build_dijizhu_app_returns_starlette():
    from dijizhu.a2a_server import build_dijizhu_app
    import starlette.applications
    app = build_dijizhu_app("wutiaogang", "五條港里", "street_wutiaogang_node", 9001)
    assert isinstance(app, starlette.applications.Starlette)
