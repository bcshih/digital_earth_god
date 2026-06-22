"""Tests: 五營兵將 clarification feature — schemas, surfaces, gateway."""

from deg.a2ui.builder import assert_valid_components
from deg.a2ui.surfaces import clarification_components
from deg.schemas import LatLng, TaskBroadcast, TravelContext, WuyingOutput


# ── TravelContext schema ──────────────────────────────────────────────────────


def test_travel_context_defaults():
    ctx = TravelContext()
    assert ctx.trip_type is None
    assert ctx.party_size is None
    assert ctx.has_elderly is None
    assert ctx.has_children is None
    assert ctx.interests == []
    assert ctx.dietary_restrictions == []
    assert ctx.wishlist == []


def test_travel_context_full():
    ctx = TravelContext(
        trip_type="family",
        travel_date="週末下午",
        party_size=4,
        has_elderly=True,
        has_children=True,
        interests=["老建築", "咖啡"],
        dietary_restrictions=["素食"],
        wishlist=["赤崁樓", "武廟"],
    )
    assert ctx.party_size == 4
    assert "赤崁樓" in ctx.wishlist
    assert "素食" in ctx.dietary_restrictions


def test_travel_context_roundtrip():
    ctx = TravelContext(interests=["老宅"], wishlist=["神農街"])
    dumped = ctx.model_dump()
    restored = TravelContext(**dumped)
    assert restored.wishlist == ["神農街"]


# ── TaskBroadcast now carries travel_context + wishlist ─────────────────────


def test_task_broadcast_travel_context():
    ctx = TravelContext(trip_type="couple", wishlist=["窄門咖啡"])
    tb = TaskBroadcast(
        task_id="t-clarify-1",
        intent="find_cafe",
        user_location=LatLng(lat=22.9971, lng=120.201),
        constraints=["安靜", "老宅"],
        travel_context=ctx,
        wishlist=["窄門咖啡"],
    )
    assert tb.travel_context is not None
    assert tb.travel_context.trip_type == "couple"
    assert tb.wishlist == ["窄門咖啡"]


def test_task_broadcast_no_travel_context():
    tb = TaskBroadcast(
        task_id="t-plain",
        intent="find_cafe",
        user_location=LatLng(lat=22.9971, lng=120.201),
    )
    assert tb.travel_context is None
    assert tb.wishlist == []


# ── WuyingOutput schema ──────────────────────────────────────────────────────


def test_wuying_output_clarifying():
    out = WuyingOutput(
        status="clarifying",
        question="敢問此行是家庭出遊還是兩人同行？",
        collected=TravelContext(),
        task_broadcast=None,
    )
    assert out.status == "clarifying"
    assert out.question is not None
    assert out.task_broadcast is None


def test_wuying_output_ready():
    tb = TaskBroadcast(
        task_id="t-ready",
        intent="find_sightseeing",
        user_location=LatLng(lat=22.9971, lng=120.201),
        constraints=["老建築"],
        wishlist=["赤崁樓"],
    )
    out = WuyingOutput(
        status="ready",
        question=None,
        collected=TravelContext(trip_type="family", wishlist=["赤崁樓"]),
        task_broadcast=tb,
    )
    assert out.status == "ready"
    assert out.question is None
    assert out.task_broadcast is not None
    assert out.task_broadcast.wishlist == ["赤崁樓"]


def test_wuying_output_defaults():
    out = WuyingOutput(status="clarifying", question="請問幾人同行？")
    assert out.collected.wishlist == []
    assert out.task_broadcast is None


# ── clarification_components A2UI surface ────────────────────────────────────


def test_clarification_components_valid_flat_list():
    comps = clarification_components("請問幾位同行？", round_n=0)
    assert_valid_components(comps)


def test_clarification_components_submit_event():
    comps = clarification_components("敢問此行的出遊性質？", round_n=1)
    btns = [c for c in comps if c.get("component") == "Button"]
    assert any(
        b.get("action", {}).get("event", {}).get("name") == "submit_clarify"
        for b in btns
    ), "clarification surface must fire submit_clarify event"


def test_clarification_components_round_label():
    comps = clarification_components("問題", round_n=2)
    texts = [c.get("text", "") for c in comps if c.get("component") == "Text"]
    assert any("第 3 問" in str(t) for t in texts)


def test_clarification_components_answer_binding():
    comps = clarification_components("有無忌口？", round_n=0)
    fields = [c for c in comps if c.get("component") == "TextField"]
    assert any(
        isinstance(f.get("value"), dict) and f["value"].get("path") == "/clarify/answer"
        for f in fields
    ), "answer field must bind to /clarify/answer"


def test_clarification_components_self_contained():
    comps = clarification_components("test question", round_n=0)
    ids = {c["id"] for c in comps}
    root = next(c for c in comps if c["id"] == "root")
    for child_id in root["children"]:
        assert child_id in ids, f"{child_id} referenced from root but not defined"
