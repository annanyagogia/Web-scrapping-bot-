from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BACKEND_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "scraper.db"


def _connect() -> sqlite3.Connection:
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS live_scrape_history (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            domain TEXT,
            page_title TEXT,
            page_type TEXT,
            instruction TEXT,
            output_format TEXT,
            records_found INTEGER DEFAULT 0,
            confidence REAL DEFAULT 0,
            download_file TEXT,
            screenshot TEXT,
            summary TEXT,
            status TEXT DEFAULT 'success',
            created_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def save_scrape_history(response: dict[str, Any], request_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    explanation = response.get("scrape_explanation", {}) or {}
    request_payload = request_payload or {}
    history_id = response.get("history_id") or uuid.uuid4().hex
    created_at = response.get("created_at") or datetime.now(timezone.utc).isoformat()

    row = {
        "id": history_id,
        "url": response.get("url") or request_payload.get("url") or "",
        "domain": response.get("domain"),
        "page_title": response.get("page_title"),
        "page_type": response.get("page_type"),
        "instruction": request_payload.get("instruction"),
        "output_format": request_payload.get("output_format"),
        "records_found": explanation.get("records_found", len(response.get("data", []) or [])),
        "confidence": explanation.get("confidence", 0),
        "download_file": (response.get("download_url") or "").split("/")[-1] or None,
        "screenshot": (response.get("screenshot_url") or "").split("/")[-1] or None,
        "summary": response.get("summary") or response.get("message"),
        "status": "success" if response.get("success") else "failed",
        "created_at": created_at,
    }

    with _connect() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO live_scrape_history (
                id, url, domain, page_title, page_type, instruction, output_format,
                records_found, confidence, download_file, screenshot, summary, status, created_at
            )
            VALUES (
                :id, :url, :domain, :page_title, :page_type, :instruction, :output_format,
                :records_found, :confidence, :download_file, :screenshot, :summary, :status, :created_at
            )
            """,
            row,
        )
        connection.commit()
    return row


def get_scrape_history(limit: int = 100) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, url, domain, page_title, page_type, instruction, output_format,
                   records_found, confidence, download_file, screenshot, summary, status, created_at
            FROM live_scrape_history
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
