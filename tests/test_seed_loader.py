from deg.schemas import Poi
from deg.seed.loader import Street, load_streets


def test_loads_three_streets():
    streets = load_streets()
    assert len(streets) == 20
    assert all(isinstance(s, Street) for s in streets)


def test_agent_ids_are_unique():
    streets = load_streets()
    agent_ids = [s.agent_id for s in streets]
    assert len(agent_ids) == len(set(agent_ids))


def test_every_street_has_pois_typed_as_schema():
    streets = load_streets()
    for s in streets:
        assert len(s.pois) >= 1
        assert all(isinstance(p, Poi) for p in s.pois)


def test_expected_streets_present():
    names = {s.name for s in load_streets()}
    assert {"五條港里", "赤嵌里", "郡王里"} <= names
