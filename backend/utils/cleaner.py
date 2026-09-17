from __future__ import annotations

import html
import json
import re
from typing import Any


WHITESPACE_RE = re.compile(r"\s+")


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = html.unescape(str(value))
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text or None


def clean_record(record: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, str):
            cleaned[key] = clean_text(value)
        elif isinstance(value, list):
            cleaned[key] = [clean_text(item) if isinstance(item, str) else item for item in value if item not in (None, "")]
        else:
            cleaned[key] = value
    return {key: value for key, value in cleaned.items() if value not in (None, "", [], {})}


def remove_duplicate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for record in records:
        signature = json.dumps(record, sort_keys=True, default=str)
        if signature in seen:
            continue
        seen.add(signature)
        unique.append(record)
    return unique
