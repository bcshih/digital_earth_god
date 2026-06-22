"""Low-level A2UI v0.9.1 message builders + structural validation.

A2UI is a FLAT ADJACENCY LIST: every component is a top-level object with an `id`;
parents reference children BY ID STRING; exactly one component has id "root".
These builders + assert_valid_components keep the emitter honest so any standard
A2UI renderer (including a future third-party frontend) can consume the stream.
"""

from __future__ import annotations

from typing import Any

A2UI_VERSION = "v0.9.1"
BASIC_CATALOG = "https://a2ui.org/specification/v0_9_1/catalogs/basic/catalog.json"

# Basic-catalog component types this system emits. Renderer must support these.
KNOWN_COMPONENTS = {
    "Row", "Column", "List", "Text", "Image", "Icon", "Divider",
    "Button", "TextField", "Card",
}

# Container components that may legitimately be the single root of a surface/fragment.
ROOT_COMPONENTS = {"Row", "Column", "List", "Card"}


def create_surface(
    surface_id: str,
    *,
    catalog_id: str = BASIC_CATALOG,
    send_data_model: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"surfaceId": surface_id, "catalogId": catalog_id}
    if send_data_model:
        payload["sendDataModel"] = True
    return {"version": A2UI_VERSION, "createSurface": payload}


def update_components(surface_id: str, components: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": A2UI_VERSION,
        "updateComponents": {"surfaceId": surface_id, "components": components},
    }


def update_data_model(surface_id: str, path: str, value: Any) -> dict[str, Any]:
    return {
        "version": A2UI_VERSION,
        "updateDataModel": {"surfaceId": surface_id, "path": path, "value": value},
    }


def assert_valid_components(components: list[dict[str, Any]]) -> None:
    """Enforce the flat-adjacency-list contract. Raises ValueError on violations."""
    if not isinstance(components, list) or not components:
        raise ValueError("components must be a non-empty list")

    ids: set[str] = set()
    referenced: set[str] = set()
    for c in components:
        if not isinstance(c, dict):
            raise ValueError(f"component is not an object: {c!r}")
        cid = c.get("id")
        if not isinstance(cid, str) or not cid:
            raise ValueError(f"component missing string id: {c!r}")
        if cid in ids:
            raise ValueError(f"duplicate component id: {cid!r}")
        ids.add(cid)
        comp_type = c.get("component")
        if comp_type not in KNOWN_COMPONENTS:
            raise ValueError(f"unknown component type {comp_type!r} on {cid!r}")

    # children must be id strings (static array) or a template dict; never nested objects.
    # `child` (single-child containers like Card/Button) must also be an id string.
    for c in components:
        single = c.get("child")
        if single is not None:
            if not isinstance(single, str):
                raise ValueError(
                    f"child must be an id string, got object on {c['id']!r} "
                    "(flat adjacency list — define children as separate components)"
                )
            if single not in ids:
                raise ValueError(f"dangling child id {single!r} on {c['id']!r}")
            referenced.add(single)

        children = c.get("children")
        if children is None:
            continue
        if isinstance(children, dict):
            # template form: {"path": "...", "componentId": "..."}
            cref = children.get("componentId")
            if cref is not None:
                if cref not in ids:
                    raise ValueError(f"template componentId {cref!r} not defined")
                referenced.add(cref)
            continue
        if not isinstance(children, list):
            raise ValueError(f"children must be a list or template dict on {c['id']!r}")
        for child in children:
            if not isinstance(child, str):
                raise ValueError(
                    f"children must be id strings, got object on {c['id']!r} "
                    "(flat adjacency list — define children as separate components)"
                )
            if child not in ids:
                raise ValueError(f"dangling child id {child!r} on {c['id']!r}")
            referenced.add(child)

    # Exactly one root: the unique component not referenced as any other's child.
    # It must be a container (a bare leaf like Text cannot be a surface root). This
    # admits both literal id="root" surfaces and namespaced fragments (e.g. bid cards).
    roots = [c for c in components if c["id"] not in referenced]
    if len(roots) != 1:
        raise ValueError(
            f"exactly one unreferenced root component required (found {len(roots)})"
        )
    if roots[0].get("component") not in ROOT_COMPONENTS:
        raise ValueError(
            f"root component {roots[0]['id']!r} must be a container "
            f"(one of {sorted(ROOT_COMPONENTS)}), got {roots[0].get('component')!r}"
        )
