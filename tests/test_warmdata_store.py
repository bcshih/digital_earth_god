"""Unit tests for the warm-data SQLite store (temp DB, no LLM, no API key)."""

from deg.schemas import LatLng, Wish
from deg.warmdata.store import WarmDataStore


def _wish(wid="w1", category="交通", lat=22.997, lng=120.201, text="希望路口加裝紅綠燈") -> Wish:
    return Wish(wish_id=wid, raw_text=text, category=category,
                location=LatLng(lat=lat, lng=lng))


def _store(tmp_path) -> WarmDataStore:
    return WarmDataStore(tmp_path / "wd.db")


def test_add_and_get_roundtrip(tmp_path):
    s = _store(tmp_path)
    s.add_wish(_wish())
    got = s.list_wishes()
    assert len(got) == 1
    assert got[0].wish_id == "w1"
    assert got[0].category == "交通"


def test_persists_across_instances(tmp_path):
    db = tmp_path / "wd.db"
    WarmDataStore(db).add_wish(_wish())
    assert len(WarmDataStore(db).list_wishes()) == 1


def test_category_counts(tmp_path):
    s = _store(tmp_path)
    s.add_wish(_wish("w1", "交通"))
    s.add_wish(_wish("w2", "交通"))
    s.add_wish(_wish("w3", "環境清潔"))
    counts = s.category_counts()
    assert counts["交通"] == 2
    assert counts["環境清潔"] == 1


def test_heatmap_points(tmp_path):
    s = _store(tmp_path)
    s.add_wish(_wish("w1", "交通", 22.99, 120.20))
    s.add_wish(_wish("w2", "環境清潔", 22.98, 120.19))
    pts = s.heatmap_points()
    assert len(pts) == 2
    assert {"lat", "lng", "category"} <= pts[0].keys()


def test_summary_shape(tmp_path):
    s = _store(tmp_path)
    s.add_wish(_wish("w1", "交通"))
    summary = s.summary()
    assert summary["total"] == 1
    assert summary["by_category"]["交通"] == 1
    assert len(summary["points"]) == 1
    assert len(summary["recent"]) == 1


def test_list_wishes_limit_and_order(tmp_path):
    s = _store(tmp_path)
    for i in range(5):
        s.add_wish(_wish(f"w{i}", "交通"))
    recent = s.list_wishes(limit=3)
    assert len(recent) == 3  # most recent first
