"""Unit tests: domain objects → valid A2UI surfaces (basic catalog, flat list)."""

from deg.a2ui.builder import assert_valid_components
from deg.a2ui.surfaces import (
    SURFACE_ID,
    bid_card_components,
    broadcast_data,
    intent_input_components,
    judgment_components,
    judgment_data,
)
from deg.schemas import BiddingProposal, JudgmentResult, LatLng, Poi, TaskBroadcast


def _proposal(agent_id="street_shennong_node", street="神農街") -> BiddingProposal:
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
    )


def test_intent_input_is_valid_flat_list():
    comps = intent_input_components()
    assert_valid_components(comps)
    # has a submit button with an event action named submit_intent
    btns = [c for c in comps if c.get("component") == "Button"]
    assert any(
        b.get("action", {}).get("event", {}).get("name") == "submit_intent" for b in btns
    )


def test_bid_card_is_valid_and_namespaced():
    comps = bid_card_components(_proposal(), index=0)
    assert_valid_components(comps)
    # every id should be namespaced by the agent_id so multiple bid cards coexist
    assert all("street_shennong_node" in c["id"] for c in comps)


def test_two_bid_cards_have_disjoint_ids():
    a = bid_card_components(_proposal("street_shennong_node", "神農街"), 0)
    b = bid_card_components(_proposal("street_haian_node", "海安路"), 1)
    ids_a = {c["id"] for c in a}
    ids_b = {c["id"] for c in b}
    assert ids_a.isdisjoint(ids_b)


def test_broadcast_data_roundtrips():
    tb = TaskBroadcast(task_id="t1", intent="find_quiet_cafe",
                       user_location=LatLng(lat=22.999, lng=120.222),
                       constraints=["安靜", "咖啡"])
    data = broadcast_data(tb)
    assert data["intent"] == "find_quiet_cafe"
    assert data["constraints"] == ["安靜", "咖啡"]


def test_judgment_components_valid():
    result = JudgmentResult(
        task_id="t1", winner_agent_id="street_shennong_node", winner_street="神農街",
        recommendation="土地公推薦神農街老宅咖啡。", reasoning="分數最高且最有人情味。",
        recommended_pois=[Poi(name="舊來發", category="cafe",
                              location=LatLng(lat=22.999, lng=120.222))],
        ranked_agent_ids=["street_shennong_node", "street_haian_node", "street_zhengxing_node"],
    )
    comps = judgment_components(result)
    assert_valid_components(comps)
    data = judgment_data(result)
    assert data["winner_street"] == "神農街"
    assert len(data["recommended_pois"]) == 1
