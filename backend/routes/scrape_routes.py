from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import ErrorLog, ScrapingTask
from schemas import (
    AnalyzeUrlRequest,
    AnalyzeUrlResponse,
    AgentRunRequest,
    AgentRunResponse,
    ChatCommandRequest,
    ChatCommandResponse,
    ScrapeRequest,
    ScrapeResponse,
)
from services.ai_planner import plan_scrape
from services.compliance_guard import (
    PROTECTED_SITE_MESSAGE,
    compliance_warning_for_terms,
    evaluate_url_compliance,
)
from services.export_service import export_records
from services.html_analyzer import analyze_html
from services.memory_service import get_template_for_domain
from services.page_loader import load_page
from services.robots_checker import check_robots_txt
from services.scraper_engine import scrape_url
from utils.url_tools import normalize_url
from utils.validators import URLValidationError, validate_public_url


router = APIRouter(prefix="/api", tags=["scraping"])


def _log_error(db: Session, *, task_id: int | None, url: str | None, error_type: str, message: str) -> None:
    db.add(ErrorLog(task_id=task_id, url=url, error_type=error_type, message=message))
    db.commit()


async def _analyze_url_for_agent(url: str, db: Session) -> AnalyzeUrlResponse:
    try:
        validate_public_url(url)
    except URLValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    url_policy = evaluate_url_compliance(url)
    if not url_policy.allowed:
        return AnalyzeUrlResponse(
            website_type="unknown",
            suggested_fields=[],
            detected_sections=[],
            confidence_score=0,
            clarifying_question=url_policy.warning,
            compliance_allowed=False,
            compliance_warning=url_policy.warning,
            compliance_reasons=url_policy.reasons,
        )

    terms_warning = compliance_warning_for_terms(url)
    robots = check_robots_txt(url)
    if not robots.allowed:
        return AnalyzeUrlResponse(
            website_type="unknown",
            suggested_fields=[],
            detected_sections=[],
            confidence_score=0,
            clarifying_question=robots.warning,
            compliance_allowed=False,
            compliance_warning=robots.warning,
            compliance_reasons=["robots_txt_disallow"],
        )

    page = await load_page(url)
    if page.error:
        _log_error(db, task_id=None, url=url, error_type="page_load", message=page.error)
        raise HTTPException(status_code=502, detail=page.error)
    if page.blocked:
        return AnalyzeUrlResponse(
            website_type="unknown",
            suggested_fields=[],
            detected_sections=[],
            confidence_score=0,
            clarifying_question=PROTECTED_SITE_MESSAGE,
            compliance_allowed=False,
            compliance_warning=PROTECTED_SITE_MESSAGE,
            compliance_reasons=page.security_reasons,
        )

    context = analyze_html(page.final_url, page.html)
    plan = await plan_scrape(context)
    template = get_template_for_domain(db, url)
    warnings = [item for item in [terms_warning, robots.warning, *page.warnings] if item]

    return AnalyzeUrlResponse(
        website_type=plan["website_category"],
        suggested_fields=plan["recommended_fields"],
        detected_sections=context["detected_sections"],
        confidence_score=plan["confidence_score"],
        clarifying_question=plan["clarifying_question"],
        possible_scraping_strategy=plan["possible_scraping_strategy"],
        compliance_allowed=True,
        compliance_warning=" ".join(warnings) if warnings else None,
        compliance_reasons=[],
        template_available=template is not None,
        page_title=context.get("page_title"),
    )


async def _run_scrape_with_task(
    db: Session,
    *,
    url: str,
    fields: list[str],
    export_format: str = "json",
    manual_selectors: dict[str, str] | None = None,
    update_template: bool = True,
) -> ScrapeResponse:
    if not fields:
        raise HTTPException(status_code=400, detail="Please select at least one field to scrape.")

    try:
        validate_public_url(url)
    except URLValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    url_policy = evaluate_url_compliance(url)
    if not url_policy.allowed:
        raise HTTPException(status_code=403, detail=url_policy.warning)

    terms_warning = compliance_warning_for_terms(url)
    robots = check_robots_txt(url)
    if not robots.allowed:
        raise HTTPException(status_code=403, detail=robots.warning)

    task = ScrapingTask(
        url=url,
        status="running",
        selected_fields=fields,
        compliance_warning=" ".join(item for item in [terms_warning, robots.warning] if item) or None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    try:
        result = await scrape_url(
            db,
            url=url,
            fields=fields,
            manual_selectors=manual_selectors,
            update_template=update_template,
        )
        task.status = "success" if result.records else "empty"
        task.website_type = result.website_type
        task.total_records = len(result.records)
        task.data_json = result.records
        task.selected_fields = fields
        task.compliance_warning = " ".join(item for item in [task.compliance_warning, *result.warnings] if item) or None
        db.add(task)
        db.commit()
        db.refresh(task)

        export_url = None
        if export_format != "json":
            export_records(task.id, result.records, export_format)
            export_url = f"/api/export/{task.id}?format={export_format}"

        return ScrapeResponse(
            status=task.status,
            total_records=len(result.records),
            data=result.records,
            task_id=task.id,
            export_url=export_url,
            warnings=[item for item in [terms_warning, robots.warning, *result.warnings] if item],
            compliance_reasons=[],
            reused_template=result.reused_template,
        )
    except Exception as exc:
        message = str(exc)
        task.status = "failed"
        task.error_message = message
        db.add(task)
        db.commit()
        _log_error(db, task_id=task.id, url=url, error_type="scrape_failure", message=message)
        if "block automated scraping" in message:
            raise HTTPException(status_code=403, detail=message) from exc
        raise HTTPException(status_code=500, detail=message) from exc


@router.post("/analyze-url", response_model=AnalyzeUrlResponse)
async def analyze_url(payload: AnalyzeUrlRequest, db: Session = Depends(get_db)) -> AnalyzeUrlResponse:
    return await _analyze_url_for_agent(normalize_url(str(payload.url)), db)


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape(payload: ScrapeRequest, db: Session = Depends(get_db)) -> ScrapeResponse:
    url = normalize_url(str(payload.url))
    fields = [field.strip() for field in payload.fields if field.strip()]
    return await _run_scrape_with_task(
        db,
        url=url,
        fields=fields,
        export_format=payload.format,
        manual_selectors=payload.manual_selectors,
        update_template=payload.update_template,
    )


def _fields_from_command(command: str, available_fields: list[str]) -> list[str]:
    lower = command.lower()
    aliases = {
        "name": "product_name",
        "names": "product_name",
        "title": "title",
        "price": "price",
        "discount": "discount",
        "discounted": "discount",
        "image": "image_url",
        "images": "image_url",
        "link": "product_url",
        "links": "product_url",
        "url": "product_url",
        "rating": "rating",
        "reviews": "reviews_count",
        "brand": "brand",
        "shade": "shade",
        "company": "company",
        "location": "location",
        "salary": "salary",
    }
    fields = []
    for token, field in aliases.items():
        if re.search(rf"\b{re.escape(token)}\b", lower) and field not in fields:
            fields.append(field)
    if "all products" in lower and available_fields:
        return available_fields
    if not fields and available_fields:
        return available_fields[:5]
    return fields


def _agent_message_for_clarification(analysis: AnalyzeUrlResponse) -> str:
    if analysis.clarifying_question:
        return analysis.clarifying_question
    return "I found several scrapeable sections. Choose the fields you want, then I can scrape only those public fields."


@router.post("/agent-run", response_model=AgentRunResponse)
async def agent_run(payload: AgentRunRequest, db: Session = Depends(get_db)) -> AgentRunResponse:
    url = normalize_url(str(payload.url))
    analysis = await _analyze_url_for_agent(url, db)

    if not analysis.compliance_allowed:
        return AgentRunResponse(
            mode="blocked",
            message=analysis.compliance_warning or PROTECTED_SITE_MESSAGE,
            analysis=analysis,
            selected_fields=[],
            clarification_options=[],
            decision_reason="compliance_guard_blocked_autonomous_scraping",
        )

    instruction = payload.user_instruction or ""
    approved_fields = [field.strip() for field in payload.approved_fields if field.strip()]
    requested_fields = _fields_from_command(instruction, analysis.suggested_fields)
    selected_fields = approved_fields or requested_fields or analysis.suggested_fields[:5]

    needs_clarification = False
    if approved_fields:
        reason = "user_approved_fields_after_clarification"
    elif requested_fields:
        reason = "user_instruction_identified_fields"
    else:
        reason = "confidence_high_enough_to_scrape_recommended_fields"
    if not approved_fields and analysis.confidence_score < payload.confidence_threshold:
        needs_clarification = True
        reason = "confidence_below_threshold"
    if not approved_fields and analysis.clarifying_question:
        needs_clarification = True
        reason = "planner_requested_user_clarification"
    if not selected_fields:
        needs_clarification = True
        reason = "no_fields_selected"

    if needs_clarification:
        return AgentRunResponse(
            mode="needs_clarification",
            message=_agent_message_for_clarification(analysis),
            analysis=analysis,
            selected_fields=selected_fields,
            clarification_options=analysis.suggested_fields,
            decision_reason=reason,
        )

    scrape_result = await _run_scrape_with_task(
        db,
        url=url,
        fields=selected_fields,
        export_format=payload.format,
        manual_selectors=None,
        update_template=True,
    )
    mode = "scraped" if scrape_result.total_records else "empty"
    return AgentRunResponse(
        mode=mode,
        message=(
            f"I scraped {scrape_result.total_records} records using: {', '.join(selected_fields)}."
            if scrape_result.total_records
            else "I made an autonomous scrape attempt, but no matching public records were found."
        ),
        analysis=analysis,
        selected_fields=selected_fields,
        clarification_options=[],
        scrape_result=scrape_result,
        decision_reason=reason,
    )


@router.post("/chat-command", response_model=ChatCommandResponse)
async def chat_command(payload: ChatCommandRequest) -> ChatCommandResponse:
    command = payload.command.strip()
    lower = command.lower()

    if not command:
        return ChatCommandResponse(action="noop", message="Type a scraping command and I will map it to an action.")

    prohibited_terms = [
        "bypass",
        "captcha",
        "cloudflare",
        "paywall",
        "login wall",
        "anti-bot",
        "antibot",
        "access control",
        "evade",
    ]
    if any(term in lower for term in prohibited_terms):
        return ChatCommandResponse(
            action="noop",
            message=(
                "I cannot help bypass security, CAPTCHA, paywalls, login walls, or anti-bot systems. "
                "Use a public page, official API, or authorized source data."
            ),
        )

    if any(term in lower for term in ["autopilot", "automatic", "auto scrape", "decide for me", "ultimate bot"]):
        return ChatCommandResponse(
            action="agent_run",
            fields=_fields_from_command(command, payload.available_fields),
            message="I will analyze the page, decide if it is clear enough, and ask you only if needed.",
        )

    if "export" in lower:
        export_format = "json"
        if "excel" in lower or "xlsx" in lower:
            export_format = "excel"
        elif "csv" in lower:
            export_format = "csv"
        return ChatCommandResponse(
            action="export",
            export_format=export_format,
            message=f"I can export the latest result as {export_format.upper()}.",
        )

    if "template" in lower:
        return ChatCommandResponse(
            action="save_template",
            fields=_fields_from_command(command, payload.available_fields),
            message="I can save these selected fields as a reusable template for this website type.",
        )

    if "scrape" in lower or "extract" in lower or "get" in lower:
        fields = _fields_from_command(command, payload.available_fields)
        if "discounted" in lower and "discount" not in fields:
            fields.append("discount")
        return ChatCommandResponse(
            action="scrape",
            fields=fields,
            message=f"I mapped that to scraping: {', '.join(fields) if fields else 'the currently selected fields'}.",
        )

    if "analyze" in lower or "inspect" in lower:
        return ChatCommandResponse(action="analyze", message="I will analyze the URL and suggest scrapeable fields.")

    return ChatCommandResponse(
        action="clarify",
        message="I can analyze a URL, scrape selected public fields, save a template, or export the latest result.",
    )
