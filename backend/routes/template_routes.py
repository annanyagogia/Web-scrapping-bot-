from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.db import get_db
from schemas import SaveTemplateRequest, SaveTemplateResponse, TemplateResponse
from services.memory_service import list_templates, save_or_update_template
from utils.url_tools import domain_from_url


router = APIRouter(prefix="/api", tags=["templates"])


@router.post("/save-template", response_model=SaveTemplateResponse)
async def save_template(payload: SaveTemplateRequest, db: Session = Depends(get_db)) -> SaveTemplateResponse:
    domain = payload.website_domain or (domain_from_url(str(payload.website_url)) if payload.website_url else "global")
    template = save_or_update_template(
        db,
        template_name=payload.template_name,
        website_domain=domain,
        website_type=payload.website_type,
        preferred_fields=payload.fields,
        last_successful_selectors=payload.last_successful_selectors,
    )
    return SaveTemplateResponse(status="success", template=TemplateResponse.model_validate(template))


@router.get("/templates", response_model=list[TemplateResponse])
async def get_templates(db: Session = Depends(get_db)) -> list[TemplateResponse]:
    return [TemplateResponse.model_validate(template) for template in list_templates(db)]
