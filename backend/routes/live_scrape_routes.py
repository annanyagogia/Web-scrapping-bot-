from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse, urlunparse

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ai_structurer import structure_scraped_data
from exporters import export_data
from live_page_scraper import (
    detect_page_type,
    detect_pagination,
    extract_filters,
    extract_images,
    extract_links,
    extract_product_cards,
    extract_tables,
    extract_title_listings,
    extract_with_template_selectors,
    fetch_live_page,
    infer_live_template_selectors,
)
from scrape_history import get_scrape_history, save_scrape_history
from scrape_templates import get_scrape_template, save_scrape_template
from utils.validators import URLValidationError, validate_public_url


BACKEND_DIR = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = BACKEND_DIR / "static" / "downloads"

router = APIRouter(prefix="/api", tags=["live-scraping"])


class LiveScrapeRequest(BaseModel):
    url: str
    mode: str = "auto"
    instruction: str | None = None
    output_format: Literal["json", "csv", "excel", "xlsx", "markdown", "text", "plain_text", "plain text"] = "json"
    scrape_full_page: bool = False
    pagination_scope: Literal["current_page", "all_pages"] | None = None


def _normalize_live_url(url: str) -> str:
    raw = url.strip()
    parsed = urlparse(raw)
    if not parsed.scheme:
        parsed = urlparse(f"https://{raw}")
    return urlunparse(parsed)


def _mode_to_page_type(mode: str, instruction: str | None, detected_type: str) -> str:
    normalized = (mode or "auto").lower().replace("_", " ").strip()
    if normalized in {"auto", "auto detect"}:
        return detected_type
    if "product" in normalized or "listing" in normalized:
        return "product_listing"
    if "table" in normalized:
        return "table_page"
    if "link" in normalized:
        return "directory_or_link_page"
    if "image" in normalized:
        return "image_page"
    if "filter" in normalized:
        return "filter_page"
    if "text" in normalized or "content" in normalized:
        return "article_or_content_page"
    instruction_lower = (instruction or "").lower()
    if "title chart" in instruction_lower or "ranked" in instruction_lower or "movie" in instruction_lower:
        return "ranked_title_list"
    if "product" in instruction_lower or "listing" in instruction_lower:
        return "product_listing"
    if "table" in instruction_lower:
        return "table_page"
    if "link" in instruction_lower:
        return "directory_or_link_page"
    if "image" in instruction_lower:
        return "image_page"
    if "filter" in instruction_lower:
        return "filter_page"
    if "text" in instruction_lower or "content" in instruction_lower:
        return "article_or_content_page"
    return detected_type


def _urls_meaningfully_different(source_url: str | None, final_url: str | None) -> bool:
    if not source_url or not final_url:
        return False
    source = urlparse(source_url)
    final = urlparse(final_url)
    source_path = source.path.rstrip("/") or "/"
    final_path = final.path.rstrip("/") or "/"
    return (
        source.netloc.lower() != final.netloc.lower()
        or source_path != final_path
        or source.query != final.query
        or source.fragment != final.fragment
    )


def _clarification_options(
    *,
    page_type: str,
    mode: str,
    tables: list[dict[str, Any]],
    product_cards: list[dict[str, Any]],
    filters: list[str],
    links: list[dict[str, Any]],
    images: list[dict[str, Any]],
) -> list[str]:
    if mode.lower() not in {"auto", "auto detect"}:
        return []
    if page_type in {"product_listing", "table_page", "article_or_content_page", "directory_or_link_page", "ranked_title_list"}:
        return []

    options = []
    if product_cards:
        options.append("Product listings")
    if tables:
        options.append("Tables")
    if filters:
        options.append("Filters")
    if len(links) >= 5:
        options.append("Page links")
    if len(images) >= 3:
        options.append("Images")
    return options if len(options) > 1 else []


def _failure_response(
    *,
    message: str,
    request: LiveScrapeRequest,
    raw_page: dict[str, Any] | None = None,
    page_type: str = "unknown",
    status: int | None = None,
    needs_clarification: bool = False,
    clarification_options: list[str] | None = None,
) -> dict[str, Any]:
    response = {
        "success": False,
        "message": message,
        "needs_clarification": needs_clarification,
        "clarification_options": clarification_options or [],
        "url": raw_page.get("url") if raw_page else request.url,
        "domain": raw_page.get("domain") if raw_page else None,
        "page_title": raw_page.get("title") if raw_page else None,
        "page_type": page_type,
        "screenshot_url": raw_page.get("screenshot_url") if raw_page else None,
        "visible_text_preview": (raw_page.get("visible_text") or "")[:1500] if raw_page else "",
        "scrape_explanation": {
            "data_source": "Live rendered webpage" if raw_page else "No live webpage data",
            "extraction_method": "Playwright browser automation + visible text fallback",
            "records_found": 0,
            "confidence": 0,
            "issues": [message],
        },
    }
    save_scrape_history(
        response,
        {
            "url": request.url,
            "instruction": request.instruction,
            "output_format": request.output_format,
        },
    )
    if status:
        response["status_code"] = status
    return response


@router.post("/live-scrape")
async def live_scrape(request: LiveScrapeRequest) -> dict[str, Any]:
    url = _normalize_live_url(request.url)
    try:
        validate_public_url(url)
    except URLValidationError:
        return {
            "success": False,
            "message": "Please enter a valid website URL.",
            "needs_clarification": False,
            "clarification_options": [],
        }

    raw_page: dict[str, Any] | None = None
    try:
        raw_page = await fetch_live_page(url, scrape_full_page=request.scrape_full_page)

        visible_text = raw_page.get("visible_text") or ""
        html = raw_page.get("html") or ""
        if not visible_text.strip():
            return _failure_response(
                message="No visible content was found. The page may be blocked, empty, or fully protected.",
                request=request,
                raw_page=raw_page,
                status=raw_page.get("status_code"),
            )

        page_type = _mode_to_page_type(request.mode, request.instruction, detect_page_type(html, visible_text))
        if page_type == "blocked_or_captcha":
            return _failure_response(
                message="This website is blocking automated access using CAPTCHA or bot protection. The bot cannot bypass CAPTCHA.",
                request=request,
                raw_page=raw_page,
                page_type=page_type,
                status=raw_page.get("status_code"),
            )
        if page_type == "login_required":
            return _failure_response(
                message="This page requires login. Please provide an authenticated session or use a public page.",
                request=request,
                raw_page=raw_page,
                page_type=page_type,
                status=raw_page.get("status_code"),
            )

        tables = extract_tables(html)
        links = raw_page.get("links") or extract_links(html)
        images = raw_page.get("images") or extract_images(html)
        filters = extract_filters(visible_text)
        title_listings = extract_title_listings(html, visible_text, raw_page.get("final_url") or raw_page["url"])
        pagination = detect_pagination(visible_text, raw_page.get("buttons"), links)

        saved_template = get_scrape_template(raw_page["domain"])
        product_cards = []
        template_reused = False
        if saved_template and saved_template.get("selectors"):
            product_cards = extract_with_template_selectors(html, saved_template.get("selectors"))
            template_reused = bool(product_cards)
        if not product_cards:
            product_cards = extract_product_cards(html, visible_text)

        if page_type == "unknown" and product_cards:
            page_type = "product_listing"
        if page_type == "unknown" and title_listings:
            page_type = "ranked_title_list"
        if page_type == "unknown" and tables:
            page_type = "table_page"

        clarification_options = _clarification_options(
            page_type=page_type,
            mode=request.mode,
            tables=tables,
            product_cards=product_cards,
            filters=filters,
            links=links,
            images=images,
        )
        if clarification_options:
            return _failure_response(
                message=(
                    "I found multiple extractable sections on this page. "
                    "Choose the section you want to scrape: "
                    + ", ".join(clarification_options)
                    + "."
                ),
                request=request,
                raw_page=raw_page,
                page_type=page_type,
                needs_clarification=True,
                clarification_options=clarification_options,
            )

        raw_data = {
            "page_title": raw_page["title"],
            "page_type": page_type,
            "mode": request.mode,
            "visible_text": visible_text,
            "tables": tables,
            "title_listings": title_listings,
            "product_cards": product_cards,
            "filters": filters,
            "links": links,
            "images": images,
            "buttons": raw_page.get("buttons", []),
            "forms": raw_page.get("forms", []),
            "user_instruction": request.instruction,
        }
        structured = structure_scraped_data(raw_data, request.instruction)
        rows = structured.get("rows", [])
        columns = structured.get("columns") or []

        try:
            exported = export_data(rows, columns, request.output_format)
        except Exception as exc:
            return _failure_response(
                message="The scrape was completed, but the export file could not be generated.",
                request=request,
                raw_page=raw_page,
                page_type=page_type,
                status=raw_page.get("status_code"),
            ) | {"export_error": str(exc)}

        issues = list(structured.get("issues", []))
        if raw_page.get("warnings"):
            issues.extend(raw_page["warnings"])
        if _urls_meaningfully_different(raw_page.get("url"), raw_page.get("final_url")):
            issues.append(f"The site redirected to {raw_page.get('final_url')}; extracted data from the rendered final page.")
        if pagination.get("detected") and request.pagination_scope != "all_pages":
            issues.append("Pagination or load-more controls were detected; this run scraped the current rendered page.")
        if not rows and raw_page.get("screenshot_url"):
            issues.append("HTML extraction returned no rows, but a screenshot and visible text preview are available.")

        response = {
            "success": True,
            "page_title": raw_page["title"],
            "url": raw_page["url"],
            "final_url": raw_page.get("final_url"),
            "domain": raw_page["domain"],
            "page_type": page_type,
            "summary": structured.get("summary"),
            "columns": columns,
            "data": rows,
            "markdown_table": exported.get("markdown_table"),
            "download_url": exported.get("download_url"),
            "download_file": exported.get("file_name"),
            "screenshot_url": raw_page["screenshot_url"],
            "filters": filters,
            "links_count": len(links),
            "images_count": len(images),
            "raw_counts": {
                "tables": len(tables),
                "title_listings": len(title_listings),
                "product_cards": len(product_cards),
                "filters": len(filters),
                "links": len(links),
                "images": len(images),
                "buttons": len(raw_page.get("buttons", [])),
            },
            "pagination": pagination,
            "template_reused": template_reused,
            "needs_clarification": False,
            "clarification_options": [],
            "created_at": raw_page.get("created_at"),
            "scrape_explanation": {
                "page_type_detected": page_type,
                "data_source": "Live rendered webpage",
                "extraction_method": (
                    "Playwright browser automation + BeautifulSoup + Pandas + visible text parsing "
                    "+ AI/rule-based structuring"
                ),
                "records_found": len(rows),
                "confidence": structured.get("confidence", 0.0),
                "issues": issues,
                "extraction_notes": structured.get("extraction_notes", []),
                "screenshot_assisted_fallback": bool(not rows and raw_page.get("screenshot_url")),
            },
        }

        save_scrape_history(
            response,
            {
                "url": url,
                "instruction": request.instruction,
                "output_format": request.output_format,
            },
        )

        if structured.get("confidence", 0) >= 0.75:
            save_scrape_template(
                {
                    "domain": raw_page["domain"],
                    "page_type": page_type,
                    "instruction": request.instruction,
                    "selectors": infer_live_template_selectors(product_cards),
                    "confidence_score": structured.get("confidence"),
                    "last_successful_scrape": raw_page["created_at"],
                }
            )

        return response
    except Exception as exc:
        message = str(exc)
        if "playwright" in message.lower() or "browser" in message.lower():
            return _failure_response(
                message="The page loaded, but dynamic content failed to render. Try enabling full-page scrape or increasing wait time.",
                request=request,
                raw_page=raw_page,
            ) | {"detail": message}
        raise HTTPException(status_code=500, detail=message) from exc


@router.get("/scrape-history")
def scrape_history() -> list[dict[str, Any]]:
    return get_scrape_history()


@router.get("/download/{file_name}")
def download_file(file_name: str) -> FileResponse:
    safe_name = Path(file_name).name
    path = DOWNLOAD_DIR / safe_name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Download file not found.")
    return FileResponse(path, filename=safe_name)


@router.post("/save-scrape-template")
def create_template(template: dict[str, Any]) -> dict[str, Any]:
    return save_scrape_template(template)


@router.get("/scrape-template/{domain}")
def read_template(domain: str) -> dict[str, Any] | None:
    return get_scrape_template(domain)
