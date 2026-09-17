from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import ScrapingTask
from schemas import HistoryResponse
from services.export_service import ExportError, export_records, media_type_for


router = APIRouter(prefix="/api", tags=["exports-history"])


@router.get("/history", response_model=list[HistoryResponse])
async def get_history(db: Session = Depends(get_db)) -> list[HistoryResponse]:
    tasks = db.scalars(select(ScrapingTask).order_by(ScrapingTask.created_at.desc()).limit(100)).all()
    return [HistoryResponse.model_validate(task) for task in tasks]


@router.get("/export/{task_id}")
async def export_task(
    task_id: int,
    format: str = Query("csv", pattern="^(csv|json|excel|xlsx)$"),
    db: Session = Depends(get_db),
) -> FileResponse:
    task = db.get(ScrapingTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Scraping task not found.")
    if not task.data_json:
        raise HTTPException(status_code=400, detail="This task has no data to export.")

    try:
        path = export_records(task.id, task.data_json, format)
    except ExportError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    normalized = "xlsx" if format == "excel" else format
    return FileResponse(
        path,
        media_type=media_type_for(format),
        filename=f"jasons-web-scraper-task-{task.id}.{normalized}",
    )
