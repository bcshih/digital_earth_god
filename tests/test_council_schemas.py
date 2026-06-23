from deg.schemas import CouncilAlignment, CouncilStatement, CouncilVerdict


def test_council_statement_round_trip():
    s = CouncilStatement(
        agent_id="street_wutiaogang_node",
        street_name="五條港里",
        round=2,
        stance="oppose",
        responds_to="street_chikan_node",
        statement_text="赤嵌里的夜市會把人潮全吸過去，五條港里反對。",
        sources=["WISH-001 巷弄擁擠"],
    )
    assert CouncilStatement.model_validate_json(s.model_dump_json()) == s


def test_council_statement_defaults():
    s = CouncilStatement(agent_id="a", street_name="甲里")
    assert s.round == 1
    assert s.stance == "inform"
    assert s.responds_to is None
    assert s.statement_text == ""
    assert s.sources == []


def test_council_verdict_round_trip():
    v = CouncilVerdict(
        topic="中西區要不要辦共同夜市？",
        tudigong_summary="老人家我看，這事兒得各里協調，免得人潮全擠一處。",
        alignments=[
            CouncilAlignment(agent_id="a", street_name="甲里", final_stance="support"),
            CouncilAlignment(agent_id="b", street_name="乙里", final_stance="oppose"),
        ],
    )
    assert CouncilVerdict.model_validate_json(v.model_dump_json()) == v
