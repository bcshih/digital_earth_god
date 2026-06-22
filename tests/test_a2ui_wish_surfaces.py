from deg.a2ui.builder import assert_valid_components
from deg.a2ui.surfaces import blessing_components, wish_input_components


def test_wish_input_valid_and_has_submit_event():
    comps = wish_input_components()
    assert_valid_components(comps)
    btns = [c for c in comps if c.get("component") == "Button"]
    assert any(b.get("action", {}).get("event", {}).get("name") == "submit_wish" for b in btns)


def test_blessing_components_valid():
    assert_valid_components(blessing_components())
