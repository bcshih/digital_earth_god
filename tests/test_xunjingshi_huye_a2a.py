"""Unit tests for 巡境使 and 虎爺 A2A servers — card and app construction."""
import starlette.applications
from a2a.types import AgentCard


def test_xunjingshi_card_builds():
    from xunjingshi.a2a_server import build_xunjingshi_card
    card = build_xunjingshi_card()
    assert isinstance(card, AgentCard)
    assert card.name == "xunjingshi"
    assert "9011" in card.url


def test_xunjingshi_app_builds():
    from xunjingshi.a2a_server import build_xunjingshi_app
    app = build_xunjingshi_app()
    assert isinstance(app, starlette.applications.Starlette)


def test_huye_card_builds():
    from huye.a2a_server import build_huye_card
    card = build_huye_card()
    assert isinstance(card, AgentCard)
    assert card.name == "huye"
    assert "9012" in card.url


def test_huye_app_builds():
    from huye.a2a_server import build_huye_app
    app = build_huye_app()
    assert isinstance(app, starlette.applications.Starlette)
