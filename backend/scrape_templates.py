from __future__ import annotations

import json
import sqlite3
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
        CREATE TABLE IF NOT EXISTS live_scrape_templates (
            domain TEXT PRIMARY KEY,
            page_type TEXT,
            instruction TEXT,
            selectors TEXT,
            confidence_score REAL DEFAULT 0,
            last_successful_scrape TEXT,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def save_scrape_template(template: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    domain = (template.get("domain") or "").lower().strip()
    if not domain:
        return {"status": "skipped", "message": "Template domain is required."}

    row = {
        "domain": domain,
        "page_type": template.get("page_type") or "unknown",
        "instruction": template.get("instruction"),
        "selectors": json.dumps(template.get("selectors") or {}, ensure_ascii=False),
        "confidence_score": float(template.get("confidence_score") or 0),
        "last_successful_scrape": template.get("last_successful_scrape") or now,
        "updated_at": now,
    }

    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO live_scrape_templates (
                domain, page_type, instruction, selectors, confidence_score, last_successful_scrape, updated_at
            )
            VALUES (
                :domain, :page_type, :instruction, :selectors, :confidence_score, :last_successful_scrape, :updated_at
            )
            ON CONFLICT(domain) DO UPDATE SET
                page_type = excluded.page_type,
                instruction = excluded.instruction,
                selectors = CASE
                    WHEN excluded.selectors IS NOT NULL AND excluded.selectors != '{}' THEN excluded.selectors
                    ELSE live_scrape_templates.selectors
                END,
                confidence_score = excluded.confidence_score,
                last_successful_scrape = excluded.last_successful_scrape,
                updated_at = excluded.updated_at
            """,
            row,
        )
        connection.commit()

    saved = get_scrape_template(domain)
    return {"status": "success", "template": saved}


def get_scrape_template(domain: str) -> dict[str, Any] | None:
    normalized = (domain or "").lower().strip()
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT domain, page_type, instruction, selectors, confidence_score, last_successful_scrape, updated_at
            FROM live_scrape_templates
            WHERE domain = ?
            """,
            (normalized,),
        ).fetchone()
    if not row:
        return None
    result = dict(row)
    try:
        result["selectors"] = json.loads(result.get("selectors") or "{}")
    except Exception:
        result["selectors"] = {}
    return result
