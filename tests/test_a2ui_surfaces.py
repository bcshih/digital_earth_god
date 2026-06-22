"""Unit tests: domain objects → valid A2UI surfaces (basic catalog, flat list)."""

from deg.a2ui.builder import assert_valid_components
from deg.a2ui.surfaces import (
    bid_data,
    broadcast_data,
    intent_input_components,
    judgment_components,
    judgment_data,
    negotiation_components,
)
from deg.schemas import BiddingProposal, Evidence, JudgmentResult, LatLng, Poi, TaskBroadcast


def _proposal(agent_id="street_shennong_node") -> BiddingProposal:
    return BiddingProposal(
        agent_id=agent_id,
        task_id="t1",
        fitness_score=8.5,
        reasoning="神農街老宅咖啡氛圍最佳，安靜且有歷史。",
        spatial_data=LatLng(lat=22.999, lng=120.222),
        tags=["安靜", "老宅", "咖啡"],
        candidate_pois=[Poi(name="舊來發", category="cafe",
                            location=LatLng(lat=22.999, lng=120.222),
                            tags=["安靜"], note="好咖啡")],
        evidence=Evidence(sensor="人流稀少，晴天", social="#老宅日系 熱搜"),
    )


def test_intent_input_is_valid_flat_list():
    comps = intent_input_components()
    assert_valid_components(comps)
    btns = [c for c in comps if c.get("component") == "Button"]
    assert any(
        b.get("action", {}).get("event", {}).get("name") == "submit_intent" for b in btns
    )


def test_negotiation_skeleton_is_valid():
    comps = negotiation_components()
    assert_valid_components(comps)
    ids = {c["id"] for c in comps}
    # stable skeleton exposes broadcast, bids list, and a verdict placeholder
    assert {"root", "broadcast-card", "bids-row", "verdict-card"} <= ids


def test_bids_row_is_a_list_template_bound_to_bids():
    comps = negotiation_components()
    bids_row = next(c for c in comps if c["id"] == "bids-row")
    assert bids_row["component"] == "List"
    assert bids_row["children"] == {"path": "/bids", "componentId": "bid-card"}


def test_broadcast_data_roundtrips():
    tb = TaskBroadcast(task_id="t1", intent="find_quiet_cafe",
                       user_location=LatLng(lat=22.999, lng=120.222),
                       constraints=["安靜", "咖啡"])
    data = broadcast_data(tb)
    assert data["intent"] == "find_quiet_cafe"
    assert data["constraints"] == ["安靜", "咖啡"]


def test_bid_data_carries_street_label_and_evidence():
    data = bid_data(_proposal("street_wutiaogang_node"))
    assert data["street"] == "五條港里"
    assert data["fitness_score"] == 8.5
    assert data["sensor"] is not None
    assert data["social"] is not None
    assert len(data["candidate_pois"]) == 1


def test_judgment_components_valid_and_self_contained():
    comps = judgment_components()
    assert_valid_components(comps)
    # redefines the verdict-card subtree in place; does NOT touch root
    ids = {c["id"] for c in comps}
    assert "verdict-card" in ids
    assert "root" not in ids


def test_judgment_data_roundtrips():
    from deg.schemas import JudgmentResult, ItineraryStop, Poi, LatLng
    stop = ItineraryStop(
        poi=Poi(name="舊來發", category="cafe", location=LatLng(lat=22.999, lng=120.222)),
        agent_id="wutiaogang",
        duration_mins=60,
        activity="喝咖啡",
        transit_to_next="步行"
    )
    result = JudgmentResult(
        task_id="t1",
        recommendation="土地公推薦神農街老宅咖啡。", reasoning="分數最高且最有人情味。",
        itinerary=[stop],
        contributing_agent_ids=["wutiaogang"],
    )
    data = judgment_data(result)
    assert len(data["itinerary"]) == 1
    assert data["itinerary"][0]["stop_activity"] == "喝咖啡"
    assert data["itinerary"][0]["stop_duration"] == "停留 60 分鐘"
