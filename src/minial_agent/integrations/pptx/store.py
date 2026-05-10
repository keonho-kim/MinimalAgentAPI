from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from minial_agent.integrations.pptx.model import PptxDeck


def pptx_store_dir(cache_dir: Path, source_path: Path) -> Path:
    key = hashlib.sha256(str(source_path.resolve()).encode("utf-8")).hexdigest()[:24]
    path = cache_dir / "pptx_decks" / key
    path.mkdir(parents=True, exist_ok=True)
    return path


def pptx_db_path(cache_dir: Path, source_path: Path) -> Path:
    return pptx_store_dir(cache_dir, source_path) / "deck.sqlite3"


class PptxDeckStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def load(self) -> tuple[PptxDeck | None, dict[str, Any] | None]:
        with self._connect() as db:
            row = db.execute(
                "SELECT deck_json, source_stat_json FROM decks LIMIT 1"
            ).fetchone()
        if row is None:
            return None, None
        return PptxDeck.model_validate_json(row["deck_json"]), json.loads(
            row["source_stat_json"]
        )

    def save(
        self,
        deck: PptxDeck,
        *,
        source_stat: dict[str, Any],
        revision: int | None = None,
    ) -> None:
        if revision is not None:
            deck = deck.model_copy(update={"revision": revision})
        deck_json = deck.model_dump_json()
        with self._connect() as db:
            db.execute("DELETE FROM elements")
            db.execute("DELETE FROM slides")
            db.execute("DELETE FROM slide_text_fts")
            db.execute("DELETE FROM decks")
            db.execute(
                """
                INSERT INTO decks(id, title, revision, source_stat_json, deck_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    deck.id,
                    deck.title,
                    deck.revision,
                    json.dumps(source_stat, ensure_ascii=False),
                    deck_json,
                ),
            )
            for slide in deck.slides:
                raw_text = "\n".join(
                    [slide.title, slide.notes, *[element.content for element in slide.elements]]
                ).strip()
                db.execute(
                    """
                    INSERT INTO slides(id, deck_id, slide_index, title, raw_text, slide_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        slide.id,
                        deck.id,
                        slide.index,
                        slide.title,
                        raw_text,
                        slide.model_dump_json(),
                    ),
                )
                db.execute(
                    "INSERT INTO slide_text_fts(slide_id, title, body, notes) VALUES (?, ?, ?, ?)",
                    (slide.id, slide.title, raw_text, slide.notes),
                )
                for element in slide.elements:
                    db.execute(
                        """
                        INSERT INTO elements(
                            id, slide_id, element_type, role, content, x, y, width, height,
                            z_index, pptx_shape_id, element_json
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            element.id,
                            slide.id,
                            element.type,
                            element.role,
                            element.content,
                            element.x,
                            element.y,
                            element.width,
                            element.height,
                            element.zIndex,
                            element.pptxShapeId,
                            element.model_dump_json(),
                        ),
                    )

    def record_edit(
        self,
        *,
        deck_id: str,
        revision: int,
        origin: str,
        operations: list[dict[str, Any]],
        changed_slide_ids: list[str],
    ) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO edit_history(deck_id, revision, origin, operations_json, changed_slide_ids_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    deck_id,
                    revision,
                    origin,
                    json.dumps(operations, ensure_ascii=False),
                    json.dumps(changed_slide_ids, ensure_ascii=False),
                ),
            )

    def search(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT s.id, s.slide_index, s.title, snippet(slide_text_fts, 2, '', '', '...', 12) AS snippet
                FROM slide_text_fts
                JOIN slides s ON s.id = slide_text_fts.slide_id
                WHERE slide_text_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        return [
            {
                "slideId": row["id"],
                "slideIndex": row["slide_index"],
                "title": row["title"],
                "snippet": row["snippet"],
            }
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def _init_schema(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS decks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    source_stat_json TEXT NOT NULL,
                    deck_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS slides (
                    id TEXT PRIMARY KEY,
                    deck_id TEXT NOT NULL,
                    slide_index INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    raw_text TEXT NOT NULL,
                    slide_json TEXT NOT NULL,
                    FOREIGN KEY(deck_id) REFERENCES decks(id)
                );

                CREATE TABLE IF NOT EXISTS elements (
                    id TEXT PRIMARY KEY,
                    slide_id TEXT NOT NULL,
                    element_type TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    z_index INTEGER NOT NULL,
                    pptx_shape_id INTEGER,
                    element_json TEXT NOT NULL,
                    FOREIGN KEY(slide_id) REFERENCES slides(id)
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS slide_text_fts USING fts5(
                    slide_id UNINDEXED,
                    title,
                    body,
                    notes
                );

                CREATE TABLE IF NOT EXISTS edit_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    deck_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    origin TEXT NOT NULL,
                    operations_json TEXT NOT NULL,
                    changed_slide_ids_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
