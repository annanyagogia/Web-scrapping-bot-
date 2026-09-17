from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import ScrapingTemplate
from utils.url_tools import domain_from_url


def get_template_for_domain(db: Session, url: str) -> ScrapingTemplate | None:
    domain = domain_from_url(url)
    return db.scalars(
        select(ScrapingTemplate)
        .where(ScrapingTemplate.website_domain == domain)
        .order_by(ScrapingTemplate.updated_at.desc())
    ).first()


def list_templates(db: Session) -> list[ScrapingTemplate]:
    return list(db.scalars(select(ScrapingTemplate).order_by(ScrapingTemplate.updated_at.desc())).all())


def save_or_update_template(
    db: Session,
    *,
    template_name: str,
    website_domain: str,
    website_type: str,
    preferred_fields: list[str],
    last_successful_selectors: dict[str, str] | None = None,
) -> ScrapingTemplate:
    existing = db.scalars(
        select(ScrapingTemplate)
        .where(ScrapingTemplate.website_domain == website_domain)
        .where(ScrapingTemplate.website_type == website_type)
        .order_by(ScrapingTemplate.updated_at.desc())
    ).first()

    if existing:
        existing.template_name = template_name
        existing.preferred_fields = preferred_fields
        if last_successful_selectors:
            existing.last_successful_selectors = last_successful_selectors
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    template = ScrapingTemplate(
        template_name=template_name,
        website_domain=website_domain,
        website_type=website_type,
        preferred_fields=preferred_fields,
        last_successful_selectors=last_successful_selectors or {},
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template
