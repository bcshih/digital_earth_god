"""虎爺 mock social intel adapter.

Reads from data/seed/social.json.
In production, swap this for a real social media API call.
"""

from __future__ import annotations

import json
from pathlib import Path

_SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "seed" / "social.json"
_DATA: dict = {}


def _load() -> dict:
    global _DATA
    if not _DATA:
        _DATA = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    return _DATA


def get_social_summary(street_id: str) -> str:
    """Return a human-readable social intel summary for a street.

    Args:
        street_id: One of shennong, haian, zhengxing.

    Returns:
        A string description of recent social media activity and commercial buzz.
    """
    data = _load()
    entry = data.get(street_id)
    if entry is None:
        return f"街廓 '{street_id}' 暫無社群情報（虎爺尚未偵察到此處）"
    return entry["summary"]
