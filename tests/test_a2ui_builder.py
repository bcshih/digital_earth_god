"""Unit tests for the A2UI message builders — enforce the flat-adjacency-list contract."""

from deg.a2ui.builder import (
    A2UI_VERSION,
    BASIC_CATALOG,
    assert_valid_components,
    create_surface,
    update_components,
    update_data_model,
)


def test_create_surface_shape():
    msg = create_surface("explore")
    assert msg["version"] == A2UI_VERSION
    assert msg["createSurface"]["surfaceId"] == "explore"
    assert msg["createSurface"]["catalogId"] == BASIC_CATALOG


def test_create_surface_send_data_model():
    msg = create_surface("explore", send_data_model=True)
    assert msg["createSurface"]["sendDataModel"] is True


def test_update_components_shape():
    comps = [{"id": "root", "component": "Column", "children": ["t"]},
             {"id": "t", "component": "Text", "text": "hi"}]
    msg = update_components("explore", comps)
    assert msg["version"] == A2UI_VERSION
    assert msg["updateComponents"]["surfaceId"] == "explore"
    assert msg["updateComponents"]["components"] == comps


def test_update_data_model_shape():
    msg = update_data_model("explore", "/broadcast", {"intent": "x"})
    assert msg["updateDataModel"]["surfaceId"] == "explore"
    assert msg["updateDataModel"]["path"] == "/broadcast"
    assert msg["updateDataModel"]["value"] == {"intent": "x"}


def test_assert_valid_components_accepts_good():
    comps = [{"id": "root", "component": "Column", "children": ["t"]},
             {"id": "t", "component": "Text", "text": "hi"}]
    assert_valid_components(comps)  # should not raise


def test_assert_valid_components_requires_one_root():
    comps = [{"id": "t", "component": "Text", "text": "hi"}]
    try:
        assert_valid_components(comps)
        raise AssertionError("expected ValueError for missing root")
    except ValueError:
        pass


def test_assert_valid_components_rejects_nested_child_objects():
    # children must be id strings, not embedded component objects
    comps = [{"id": "root", "component": "Column",
              "children": [{"id": "t", "component": "Text", "text": "hi"}]}]
    try:
        assert_valid_components(comps)
        raise AssertionError("expected ValueError for nested children objects")
    except ValueError:
        pass


def test_assert_valid_components_rejects_unknown_child_id():
    comps = [{"id": "root", "component": "Column", "children": ["missing"]}]
    try:
        assert_valid_components(comps)
        raise AssertionError("expected ValueError for dangling child id")
    except ValueError:
        pass
