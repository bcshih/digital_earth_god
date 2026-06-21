"""Unit tests for mock sensor and social adapters."""


def test_sensor_returns_string_for_shennong():
    from deg.adapters.sensor_adapter import get_sensor_summary
    result = get_sensor_summary("shennong")
    assert isinstance(result, str)
    assert len(result) > 5


def test_sensor_returns_string_for_all_streets():
    from deg.adapters.sensor_adapter import get_sensor_summary
    for street_id in ["shennong", "haian", "zhengxing"]:
        result = get_sensor_summary(street_id)
        assert isinstance(result, str) and len(result) > 5


def test_sensor_unknown_street_returns_fallback():
    from deg.adapters.sensor_adapter import get_sensor_summary
    result = get_sensor_summary("nowhere")
    assert isinstance(result, str)


def test_social_returns_string_for_shennong():
    from deg.adapters.social_adapter import get_social_summary
    result = get_social_summary("shennong")
    assert isinstance(result, str)
    assert len(result) > 5


def test_social_returns_string_for_all_streets():
    from deg.adapters.social_adapter import get_social_summary
    for street_id in ["shennong", "haian", "zhengxing"]:
        result = get_social_summary(street_id)
        assert isinstance(result, str) and len(result) > 5


def test_social_unknown_street_returns_fallback():
    from deg.adapters.social_adapter import get_social_summary
    result = get_social_summary("nowhere")
    assert isinstance(result, str)
