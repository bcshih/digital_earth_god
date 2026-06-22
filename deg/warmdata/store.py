"""SQLite warm-data store for citizen wishes (流程 B).

Pure persistence + aggregation. No LLM, no I/O beyond the local SQLite file.
Default DB path is data/warmdata.db (gitignored); pass a path for tests.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from deg.schemas import LatLng, Wish

_DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "warmdata.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS wishes (
    wish_id     TEXT PRIMARY KEY,
    raw_text    TEXT NOT NULL,
    category    TEXT NOT NULL,
    lat         REAL NOT NULL,
    lng         REAL NOT NULL,
    photo_ref   TEXT,
    created_at  TEXT NOT NULL,
    status      TEXT NOT NULL
);
"""


class WarmDataStore:
    """Thin SQLite-backed store for Wish records + governance aggregates."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._path = Path(db_path) if db_path is not None else _DEFAULT_DB
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_wish(self, wish: Wish) -> Wish:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO wishes "
                "(wish_id, raw_text, category, lat, lng, photo_ref, created_at, status) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    wish.wish_id, wish.raw_text, wish.category,
                    wish.location.lat, wish.location.lng, wish.photo_ref,
                    wish.created_at.isoformat(), wish.status,
                ),
            )
        return wish

    def _row_to_wish(self, row: sqlite3.Row) -> Wish:
        return Wish(
            wish_id=row["wish_id"], raw_text=row["raw_text"], category=row["category"],
            location=LatLng(lat=row["lat"], lng=row["lng"]),
            photo_ref=row["photo_ref"], created_at=row["created_at"], status=row["status"],
        )

    def list_wishes(self, limit: int | None = None) -> list[Wish]:
        sql = "SELECT * FROM wishes ORDER BY created_at DESC, rowid DESC"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        with self._connect() as conn:
            return [self._row_to_wish(r) for r in conn.execute(sql)]

    def category_counts(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT category, COUNT(*) AS n FROM wishes GROUP BY category"
            ).fetchall()
        return {r["category"]: r["n"] for r in rows}

    def heatmap_points(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT lat, lng, category FROM wishes").fetchall()
        return [{"lat": r["lat"], "lng": r["lng"], "category": r["category"]} for r in rows]

    def summary(self, recent_limit: int = 20) -> dict:
        return {
            "total": sum(self.category_counts().values()),
            "by_category": self.category_counts(),
            "points": self.heatmap_points(),
            "recent": [w.model_dump(mode="json") for w in self.list_wishes(limit=recent_limit)],
        }
