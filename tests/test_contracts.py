import pytest
from pydantic import ValidationError

from deg.schemas import (
    LatLng,
    Poi,
    Evidence,
    TaskBroadcast,
    BiddingProposal,
    Wish,
)


def test_task_broadcast_valid():
    tb = TaskBroadcast(
        task_id="req_12345",
        intent="find_cafe_avoid_crowd",
        user_location=LatLng(lat=22.999, lng=120.222),
        constraints=["quiet", "coffee"],
        timeout_ms=3000,
    )
    assert tb.task_id == "req_12345"
    assert tb.user_location.lat == 22.999
    assert tb.constraints == ["quiet", "coffee"]


def test_task_broadcast_defaults():
    tb = TaskBroadcast(
        task_id="req_1",
        intent="explore",
        user_location=LatLng(lat=22.99, lng=120.20),
    )
    assert tb.constraints == []
    assert tb.timeout_ms == 3000


def test_bidding_proposal_valid_and_roundtrip():
    bp = BiddingProposal(
        agent_id="street_shennong_node",
        task_id="req_12345",
        fitness_score=8.5,
        reasoning="MCP檢索到兩家老宅咖啡，巡境使API回報目前人流低於30%。",
        spatial_data=LatLng(lat=22.998, lng=120.220),
        tags=["推薦", "安靜"],
        candidate_pois=[
            Poi(
                name="老宅咖啡・神農38",
                category="cafe",
                location=LatLng(lat=22.9975, lng=120.1968),
                tags=["老宅", "安靜"],
                note="二樓老屋咖啡。",
            )
        ],
        evidence=Evidence(sensor="人流<30%", social="IG 提及度上升"),
        confidence=0.7,
    )
    dumped = bp.model_dump_json()
    restored = BiddingProposal.model_validate_json(dumped)
    assert restored == bp
    assert restored.candidate_pois[0].name == "老宅咖啡・神農38"


def _proposal(**overrides):
    base = dict(
        agent_id="x",
        task_id="t",
        fitness_score=5.0,
        reasoning="r",
        spatial_data=LatLng(lat=0.0, lng=0.0),
    )
    base.update(overrides)
    return BiddingProposal(**base)


@pytest.mark.parametrize("fitness_score", [11.0, -0.1])
def test_bidding_proposal_fitness_score_out_of_range_rejected(fitness_score):
    with pytest.raises(ValidationError):
        _proposal(fitness_score=fitness_score)


@pytest.mark.parametrize("confidence", [1.1, -0.1])
def test_bidding_proposal_confidence_out_of_range_rejected(confidence):
    with pytest.raises(ValidationError):
        _proposal(confidence=confidence)


@pytest.mark.parametrize(
    "lat,lng",
    [(91.0, 0.0), (-91.0, 0.0), (0.0, 181.0), (0.0, -181.0)],
)
def test_latlng_out_of_range_rejected(lat, lng):
    with pytest.raises(ValidationError):
        LatLng(lat=lat, lng=lng)


def test_wish_defaults_and_minimal():
    w = Wish(
        wish_id="wish_1",
        raw_text="希望這條巷子晚上有路燈",
        category="public_safety",
        location=LatLng(lat=22.993, lng=120.201),
    )
    assert w.status == "received"
    assert w.photo_ref is None
    assert w.created_at is not None
    assert w.created_at.tzinfo is not None  # must be timezone-aware (UTC)


# ── JudgmentResult ──────────────────────────────────────────────────────────

def test_judgment_result_minimal():
    from deg.schemas import JudgmentResult
    jr = JudgmentResult(
        task_id="t1",
        winner_agent_id="street_shennong_node",
        winner_street="神農街",
        recommendation="神農街老宅咖啡是最佳選擇。",
        reasoning="fitness_score 最高且最符合安靜需求。",
    )
    assert jr.winner_agent_id == "street_shennong_node"
    assert jr.recommended_pois == []
    assert jr.ranked_agent_ids == []


def test_judgment_result_full_with_pois():
    from deg.schemas import JudgmentResult, Poi, LatLng
    poi = Poi(
        name="舊來發", category="cafe",
        location=LatLng(lat=22.999, lng=120.222),
        tags=["安靜", "老宅"],
        note="好咖啡",
    )
    jr = JudgmentResult(
        task_id="t2",
        winner_agent_id="street_shennong_node",
        winner_street="神農街",
        recommendation="去神農街找老宅咖啡吧。",
        recommended_pois=[poi],
        ranked_agent_ids=["street_shennong_node", "street_haian_node", "street_zhengxing_node"],
        reasoning="神農街歷史最豐富，非常適合安靜品咖啡。",
    )
    assert len(jr.recommended_pois) == 1
    assert jr.ranked_agent_ids[0] == "street_shennong_node"


def test_judgment_result_serializes_to_json():
    from deg.schemas import JudgmentResult
    jr = JudgmentResult(
        task_id="t3",
        winner_agent_id="street_haian_node",
        winner_street="海安路",
        recommendation="海安路藝術氛圍最濃。",
        reasoning="候選地點最多。",
    )
    raw = jr.model_dump_json()
    jr2 = JudgmentResult.model_validate_json(raw)
    assert jr2.task_id == "t3"
    assert jr2.winner_street == "海安路"
