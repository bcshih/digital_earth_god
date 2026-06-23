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
        recommendation="這是一套為您量身打造的台南跨區行程。",
        reasoning="整合了最好的咖啡與景點。",
    )
    assert jr.recommendation == "這是一套為您量身打造的台南跨區行程。"
    assert jr.itinerary == []
    assert jr.contributing_agent_ids == []


def test_judgment_result_full_with_itinerary():
    from deg.schemas import JudgmentResult, Poi, LatLng, ItineraryStop
    poi = Poi(
        name="舊來發", category="cafe",
        location=LatLng(lat=22.999, lng=120.222),
        tags=["安靜", "老宅"],
        note="好咖啡",
    )
    stop = ItineraryStop(
        poi=poi,
        agent_id="wutiaogang",
        duration_mins=60,
        activity="喝杯老宅咖啡",
        transit_to_next="步行前往下一個景點"
    )
    jr = JudgmentResult(
        task_id="t2",
        recommendation="去台南走走吧。",
        itinerary=[stop],
        contributing_agent_ids=["wutiaogang"],
        reasoning="非常適合安靜品咖啡。",
    )
    assert len(jr.itinerary) == 1
    assert jr.itinerary[0].duration_mins == 60
    assert jr.contributing_agent_ids[0] == "wutiaogang"


def test_judgment_result_serializes_to_json():
    from deg.schemas import JudgmentResult
    jr = JudgmentResult(
        task_id="t3",
        recommendation="海安路藝術氛圍最濃。",
        reasoning="候選地點最多。",
    )
    raw = jr.model_dump_json()
    jr2 = JudgmentResult.model_validate_json(raw)
    assert jr2.task_id == "t3"
    assert jr2.recommendation == "海安路藝術氛圍最濃。"


# ── CommunityAnswer & CommunityQueryResult ──────────────────────────────────

def test_community_answer_round_trip():
    from deg.schemas import CommunityAnswer
    a = CommunityAnswer(
        agent_id="street_wutiaogang_node",
        street_name="五條港里",
        answer_text="普濟殿本週有元宵花燈展，週末人多。",
        sources=["2026 普濟殿元宵花燈展"],
    )
    assert CommunityAnswer.model_validate_json(a.model_dump_json()) == a


def test_community_query_result_round_trip():
    from deg.schemas import CommunityAnswer, CommunityQueryResult
    r = CommunityQueryResult(
        question="最近有什麼活動？",
        answers=[
            CommunityAnswer(
                agent_id="street_wutiaogang_node",
                street_name="五條港里",
                answer_text="普濟殿元宵花燈展。",
                sources=["2026 普濟殿元宵花燈展"],
            )
        ],
        tudigong_summary="老人家我查了一輪，這幾個地方要注意…",
    )
    assert CommunityQueryResult.model_validate_json(r.model_dump_json()) == r
