from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


EXPORT_DIR = Path(__file__).resolve().parents[1] / "exports"
EXPORT_DIR.mkdir(exist_ok=True)


class ExportError(RuntimeError):
    pass


def export_records(task_id: int, records: list[dict[str, Any]], export_format: str) -> Path:
    normalized = "xlsx" if export_format == "excel" else export_format.lower()
    if normalized not in {"csv", "json", "xlsx"}:
        raise ExportError("Unsupported format. Use csv, excel, xlsx, or json.")

    path = EXPORT_DIR / f"task_{task_id}.{normalized}"

    try:
        if normalized == "json":
            path.write_text(json.dumps(records, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        elif normalized == "csv":
            pd.DataFrame(records).to_csv(path, index=False)
        elif normalized == "xlsx":
            pd.DataFrame(records).to_excel(path, index=False)
    except Exception as exc:
        raise ExportError(f"Export failed: {exc}") from exc

    return path


def media_type_for(export_format: str) -> str:
    normalized = "xlsx" if export_format == "excel" else export_format.lower()
    return {
        "json": "application/json",
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }[normalized]
