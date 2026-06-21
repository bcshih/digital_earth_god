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


def test_bidding_proposal_score_out_of_range_rejected():
    with pytest.raises(ValidationError):
        BiddingProposal(
            agent_id="x",
            task_id="t",
            fitness_score=11.0,  # > 10 not allowed
            reasoning="r",
            spatial_data=LatLng(lat=0.0, lng=0.0),
        )


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
