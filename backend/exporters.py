from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BACKEND_DIR / "static" / "downloads"


def _stringify(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value if value is not None else "")


def to_markdown_table(columns: list[str], rows: list[dict[str, Any]]) -> str:
    if not columns or not rows:
        return ""

    def cell(value: Any) -> str:
        return _stringify(value).replace("|", "\\|").replace("\n", " ")

    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = ["| " + " | ".join(cell(row.get(col, "")) for col in columns) + " |" for row in rows]
    return "\n".join([header, separator] + body)


def export_data(rows: list[dict[str, Any]], columns: list[str], output_format: str) -> dict[str, Any]:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4().hex
    normalized = (output_format or "json").lower().replace("plain_text", "text").replace("plain text", "text")
    markdown = to_markdown_table(columns, rows)

    if normalized == "json":
        file_path = DOWNLOAD_DIR / f"scrape_{file_id}.json"
        file_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    elif normalized == "csv":
        file_path = DOWNLOAD_DIR / f"scrape_{file_id}.csv"
        pd.DataFrame(rows, columns=columns or None).to_csv(file_path, index=False)
    elif normalized in {"excel", "xlsx"}:
        file_path = DOWNLOAD_DIR / f"scrape_{file_id}.xlsx"
        pd.DataFrame(rows, columns=columns or None).to_excel(file_path, index=False)
    elif normalized in {"markdown", "md"}:
        file_path = DOWNLOAD_DIR / f"scrape_{file_id}.md"
        file_path.write_text(markdown, encoding="utf-8")
    else:
        file_path = DOWNLOAD_DIR / f"scrape_{file_id}.txt"
        if rows:
            lines = []
            for row in rows:
                lines.append("\n".join(f"{column}: {_stringify(row.get(column, ''))}" for column in columns or row.keys()))
            file_path.write_text("\n\n".join(lines), encoding="utf-8")
        else:
            file_path.write_text("No records were extracted.", encoding="utf-8")

    relative = f"static/downloads/{file_path.name}"
    return {
        "download_url": f"/{relative}",
        "file_name": file_path.name,
        "file_path": relative,
        "markdown_table": markdown,
    }
