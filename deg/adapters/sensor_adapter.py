"""巡境使 mock sensor adapter.

Reads from data/seed/sensor.json.
In production, swap this for a real sensor API call.
"""

from __future__ import annotations

import json
from pathlib import Path

_SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "seed" / "sensor.json"
_DATA: dict = {}


def _load() -> dict:
    global _DATA
    if not _DATA:
        _DATA = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    return _DATA


def get_sensor_summary(street_id: str) -> str:
    """Return a human-readable sensor summary for a street.

    Args:
        street_id: One of shennong, haian, zhengxing.

    Returns:
        A string description of current crowd/weather conditions.
    """
    data = _load()
    entry = data.get(street_id)
    if entry is None:
        return f"街廓 '{street_id}' 暫無感測資料（巡境使尚未巡至此處）"
    return entry["summary"]
