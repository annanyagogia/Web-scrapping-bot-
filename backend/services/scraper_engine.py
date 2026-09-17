from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from bs4 import BeautifulSoup, Tag
from sqlalchemy.orm import Session

from services.ai_planner import plan_scrape
from services.compliance_guard import PROTECTED_SITE_MESSAGE
from services.html_analyzer import analyze_html
from services.memory_service import get_template_for_domain, save_or_update_template
from services.page_loader import load_page
from utils.cleaner import clean_record, clean_text, remove_duplicate_records
from utils.url_tools import absolute_url, domain_from_url


PRICE_RE = re.compile(r"([$₹€£]\s?\d[\d,.]*(?:\.\d{2})?)")
PERCENT_RE = re.compile(r"(\d{1,2}\s?% ?(?:off|discount)?)", re.IGNORECASE)
RATING_RE = re.compile(r"(\d(?:\.\d)?)\s?(?:/ ?5|stars?|rating)", re.IGNORECASE)
REVIEWS_RE = re.compile(r"([\d,]+)\s?(?:reviews?|ratings?)", re.IGNORECASE)


FIELD_SELECTOR_HINTS = {
    "product_name": [
        '[class*="product-title"]',
        '[class*="product-name"]',
        '[class*="title"]',
        "h2",
        "h3",
        "a[title]",
    ],
    "price": ['[class*="price"]', '[data-testid*="price"]', '[aria-label*="price" i]'],
    "discount": ['[class*="discount"]', '[class*="sale"]', '[class*="offer"]'],
    "image_url": ["img"],
    "product_url": ["a[href]"],
    "brand": ['[class*="brand"]', '[itemprop="brand"]'],
    "rating": ['[class*="rating"]', '[aria-label*="rating" i]'],
    "availability": ['[class*="stock"]', '[class*="availability"]'],
    "title": ["h1", "h2", "h3", "a[href]"],
    "author": ['[rel="author"]', '[class*="author"]', '[itemprop="author"]'],
    "published_date": ["time", '[class*="date"]', '[itemprop="datePublished"]'],
    "summary": ["p", '[class*="summary"]', '[class*="excerpt"]'],
    "article_url": ["a[href]"],
    "image_url": ["img"],
    "job_title": ["h2", "h3", '[class*="title"]'],
    "company": ['[class*="company"]', '[itemprop="hiringOrganization"]'],
    "location": ['[class*="location"]', '[itemprop="jobLocation"]'],
    "salary": ['[class*="salary"]', '[class*="compensation"]'],
    "job_url": ["a[href]"],
    "posted_date": ["time", '[class*="posted"]', '[class*="date"]'],
    "video_title": ['meta[property="og:title"]', "h1"],
    "thumbnail_url": ['meta[property="og:image"]', "img"],
    "embedded_video_url": ["iframe[src]", "video source[src]", "video[src]"],
}


@dataclass
class ScrapeResult:
    records: list[dict[str, Any]]
    website_type: str
    fields: list[str]
    selectors: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    reused_template: bool = False
    strategy: str = "static_html"


def _max_records() -> int:
    return int(os.getenv("MAX_SCRAPE_RECORDS", "500"))


def _flatten_schema(schema: Any) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    if isinstance(schema, dict):
        if "@graph" in schema:
            nodes.extend(_flatten_schema(schema["@graph"]))
        nodes.append(schema)
        for value in schema.values():
            if isinstance(value, (dict, list)):
                nodes.extend(_flatten_schema(value))
    elif isinstance(schema, list):
        for item in schema:
            nodes.extend(_flatten_schema(item))
    return nodes


def _first(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _nested(value: dict[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        current = _first(current)
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current


def _schema_type(node: dict[str, Any]) -> str:
    raw = node.get("@type")
    if isinstance(raw, list):
        return " ".join(str(item) for item in raw).lower()
    return str(raw or "").lower()


def _image_from_schema(value: Any) -> str | None:
    value = _first(value)
    if isinstance(value, dict):
        return value.get("url") or value.get("contentUrl")
    return value


def _map_schema_record(node: dict[str, Any], fields: list[str], base_url: str) -> dict[str, Any]:
    schema_type = _schema_type(node)
    record: dict[str, Any] = {}

    for field in fields:
        value: Any = None
        if field in {"product_name", "title", "job_title", "video_title", "property_title"}:
            value = node.get("name") or node.get("headline") or node.get("title")
        elif field == "brand":
            value = _nested(node, "brand", "name") or node.get("brand")
        elif field == "price":
            value = (
                _nested(node, "offers", "price")
                or _nested(node, "offers", "lowPrice")
                or _nested(node, "offers", "highPrice")
                or node.get("price")
            )
        elif field in {"product_url", "article_url", "job_url", "listing_url"}:
            value = absolute_url(base_url, node.get("url") or node.get("@id"))
        elif field in {"image_url", "thumbnail_url"}:
            value = absolute_url(base_url, _image_from_schema(node.get("image") or node.get("thumbnailUrl")))
        elif field == "availability":
            value = _nested(node, "offers", "availability") or node.get("availability")
        elif field == "rating":
            value = _nested(node, "aggregateRating", "ratingValue")
        elif field == "reviews_count":
            value = _nested(node, "aggregateRating", "reviewCount") or _nested(node, "aggregateRating", "ratingCount")
        elif field == "author":
            value = _nested(node, "author", "name") or node.get("author")
        elif field == "published_date":
            value = node.get("datePublished") or node.get("dateCreated") or node.get("dateModified")
        elif field == "summary" or field == "description":
            value = node.get("description")
        elif field == "tags":
            value = node.get("keywords")
        elif field == "company":
            value = _nested(node, "hiringOrganization", "name")
        elif field == "location":
            value = _nested(node, "jobLocation", "address") or node.get("jobLocation")
        elif field == "salary":
            value = node.get("baseSalary")
        elif field == "posted_date":
            value = node.get("datePosted")
        elif field == "duration":
            value = node.get("duration")
        elif field == "embedded_video_url":
            value = absolute_url(base_url, node.get("embedUrl") or node.get("contentUrl"))
        elif field == "platform_source":
            value = _nested(node, "publisher", "name") or node.get("uploadDate")
        elif field in {"discount", "shade", "size", "color", "category", "experience", "bedrooms", "bathrooms", "area"}:
            value = node.get(field)

        if value is not None:
            record[field] = value

    # Avoid converting every nested schema object into a row for unrelated page metadata.
    relevant = {
        "product": {"product_name", "price", "product_url", "image_url"},
        "article": {"title", "article_url", "published_date", "summary"},
        "newsarticle": {"title", "article_url", "published_date", "summary"},
        "blogposting": {"title", "article_url", "published_date", "summary"},
        "jobposting": {"job_title", "company", "location", "job_url"},
        "videoobject": {"video_title", "thumbnail_url", "embedded_video_url"},
    }
    if not any(type_key in schema_type and set(record).intersection(expected) for type_key, expected in relevant.items()):
        if not record.get("title") and not record.get("product_name"):
            return {}
    return clean_record(record)


def extract_schema_records(context: dict[str, Any], fields: list[str], base_url: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for schema in context.get("json_ld_schema", []):
        for node in _flatten_schema(schema):
            if isinstance(node, dict):
                record = _map_schema_record(node, fields, base_url)
                if record:
                    records.append(record)
    return remove_duplicate_records(records)[: _max_records()]


def _extract_node_value(node: Tag, field: str, base_url: str) -> Any:
    if field in {"image_url", "thumbnail_url"}:
        image = node if node.name == "img" else node.select_one("img")
        src = None
        if image:
            src = image.get("src") or image.get("data-src") or image.get("data-lazy-src") or image.get("srcset", "").split(" ")[0]
        return absolute_url(base_url, src)
    if field in {"product_url", "article_url", "job_url", "listing_url", "embedded_video_url"}:
        href_node = node if node.name in {"a", "iframe", "source", "video"} else node.select_one("a[href], iframe[src], source[src], video[src]")
        href = href_node.get("href") or href_node.get("src") if href_node else None
        return absolute_url(base_url, href)
    if node.name == "meta":
        return node.get("content")
    if field == "price":
        text = node.get_text(" ", strip=True)
        match = PRICE_RE.search(text)
        return match.group(1) if match else text
    return clean_text(node.get("title") or node.get("aria-label") or node.get_text(" ", strip=True))


def apply_selectors(html: str, base_url: str, fields: list[str], selectors: dict[str, str]) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html or "", "lxml")
    values_by_field: dict[str, list[Any]] = {}
    max_len = 0

    for field in fields:
        selector = selectors.get(field)
        if not selector:
            continue
        try:
            nodes = soup.select(selector)
        except Exception:
            continue
        values = [_extract_node_value(node, field, base_url) for node in nodes]
        values = [value for value in values if value not in (None, "")]
        values_by_field[field] = values
        max_len = max(max_len, len(values))

    records: list[dict[str, Any]] = []
    for index in range(min(max_len, _max_records())):
        record = {}
        for field, values in values_by_field.items():
            if index < len(values):
                record[field] = values[index]
        if record:
            records.append(clean_record(record))
    return remove_duplicate_records(records)


def scrape_tables(html: str, url: str, fields: list[str]) -> list[dict[str, Any]]:
    try:
        dataframes = pd.read_html(html)
    except ValueError:
        return []

    records: list[dict[str, Any]] = []
    for dataframe in dataframes:
        dataframe = dataframe.dropna(how="all").fillna("")
        headers = [str(column) for column in dataframe.columns]
        rows = dataframe.astype(str).to_dict(orient="records")
        if fields and {"table_headers", "table_rows", "source_url"}.intersection(fields):
            records.append(
                clean_record(
                    {
                        "table_headers": headers,
                        "table_rows": rows[: _max_records()],
                        "source_url": url,
                    }
                )
            )
        else:
            wanted = {field.lower() for field in fields}
            for row in rows:
                cleaned_row = {clean_text(key) or key: clean_text(value) for key, value in row.items()}
                if wanted:
                    filtered = {
                        key: value
                        for key, value in cleaned_row.items()
                        if key and key.lower() in wanted and value not in (None, "")
                    }
                    records.append(filtered or cleaned_row)
                else:
                    records.append(cleaned_row)
        if len(records) >= _max_records():
            break
    return remove_duplicate_records([record for record in records if record])[: _max_records()]


def _candidate_cards(soup: BeautifulSoup) -> list[Tag]:
    selectors = [
        '[data-product-id]',
        '[itemtype*="Product"]',
        '[class*="product"]',
        '[class*="card"]',
        '[class*="listing"]',
        '[class*="tile"]',
        "article",
        "li",
    ]
    cards: list[Tag] = []
    for selector in selectors:
        try:
            cards.extend(soup.select(selector))
        except Exception:
            continue

    filtered: list[Tag] = []
    seen: set[int] = set()
    for card in cards:
        if id(card) in seen:
            continue
        seen.add(id(card))
        text = card.get_text(" ", strip=True)
        has_signal = bool(PRICE_RE.search(text) or card.select_one("img") or card.select_one("a[href]") or card.select_one("time"))
        if has_signal and len(text) < 5000:
            filtered.append(card)
    return filtered[:300]


def _text_from_first(card: Tag, selectors: list[str]) -> str | None:
    for selector in selectors:
        try:
            node = card.select_one(selector)
        except Exception:
            continue
        if node:
            value = clean_text(node.get("content") if node.name == "meta" else node.get_text(" ", strip=True))
            if value:
                return value
    return None


def _field_from_card(card: Tag, field: str, base_url: str) -> Any:
    text = card.get_text(" ", strip=True)
    if field in {"product_name", "title", "job_title", "video_title", "property_title"}:
        value = _text_from_first(card, FIELD_SELECTOR_HINTS.get(field, []))
        if value:
            return value
        image = card.select_one("img[alt]")
        if image and image.get("alt"):
            return clean_text(image.get("alt"))
        link = card.select_one("a[title]")
        return clean_text(link.get("title")) if link else None
    if field == "price":
        value = _text_from_first(card, FIELD_SELECTOR_HINTS.get(field, []))
        match = PRICE_RE.search(value or text)
        return match.group(1) if match else value
    if field == "discount":
        value = _text_from_first(card, FIELD_SELECTOR_HINTS.get(field, []))
        match = PERCENT_RE.search(value or text)
        return match.group(1) if match else value
    if field in {"image_url", "thumbnail_url"}:
        return _extract_node_value(card, field, base_url)
    if field in {"product_url", "article_url", "job_url", "listing_url", "embedded_video_url"}:
        return _extract_node_value(card, field, base_url)
    if field == "rating":
        value = _text_from_first(card, FIELD_SELECTOR_HINTS.get(field, []))
        match = RATING_RE.search(value or text)
        return match.group(1) if match else value
    if field == "reviews_count":
        match = REVIEWS_RE.search(text)
        return match.group(1) if match else None
    if field == "availability":
        if re.search(r"\bin stock\b|available", text, re.IGNORECASE):
            return "In stock"
        if re.search(r"\bout of stock\b|sold out|unavailable", text, re.IGNORECASE):
            return "Out of stock"
        return _text_from_first(card, FIELD_SELECTOR_HINTS.get(field, []))
    if field in {"brand", "company", "location", "salary", "posted_date", "author", "published_date", "summary"}:
        return _text_from_first(card, FIELD_SELECTOR_HINTS.get(field, []))
    if field in {"shade", "size", "color", "category", "experience", "bedrooms", "bathrooms", "area", "duration", "description"}:
        pattern = re.compile(rf"{field.replace('_', ' ')}[:\s]+([^|,;]+)", re.IGNORECASE)
        match = pattern.search(text)
        return clean_text(match.group(1)) if match else None
    return None


def scrape_repeated_elements(html: str, base_url: str, fields: list[str]) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html or "", "lxml")
    cards = _candidate_cards(soup)
    records: list[dict[str, Any]] = []

    for card in cards:
        record = {field: _field_from_card(card, field, base_url) for field in fields}
        record = clean_record(record)
        if record and len(record) >= 1:
            records.append(record)
        if len(records) >= _max_records():
            break

    if records:
        return remove_duplicate_records(records)

    page_record: dict[str, Any] = {}
    title_node = soup.select_one("title, h1")
    og_image = soup.select_one('meta[property="og:image"]')
    og_title = soup.select_one('meta[property="og:title"]')
    og_desc = soup.select_one('meta[property="og:description"], meta[name="description"]')

    for field in fields:
        if field in {"title", "product_name", "video_title"}:
            page_record[field] = clean_text(
                (og_title.get("content") if og_title else None)
                or (title_node.get_text(" ", strip=True) if title_node else None)
            )
        elif field in {"image_url", "thumbnail_url"}:
            page_record[field] = absolute_url(base_url, og_image.get("content") if og_image else None)
        elif field in {"summary", "description"}:
            page_record[field] = clean_text(og_desc.get("content") if og_desc else None)
        elif field in {"article_url", "product_url", "source_url"}:
            page_record[field] = base_url
        elif field == "embedded_video_url":
            video = soup.select_one("iframe[src], video[src], video source[src]")
            page_record[field] = absolute_url(base_url, video.get("src") if video else None)

    page_record = clean_record(page_record)
    return [page_record] if page_record else []


def infer_successful_selectors(html: str, fields: list[str]) -> dict[str, str]:
    soup = BeautifulSoup(html or "", "lxml")
    selectors: dict[str, str] = {}
    for field in fields:
        for selector in FIELD_SELECTOR_HINTS.get(field, []):
            try:
                matches = soup.select(selector)
            except Exception:
                continue
            if len(matches) >= 1:
                selectors[field] = selector
                break
    return selectors


async def scrape_url(
    db: Session,
    *,
    url: str,
    fields: list[str],
    manual_selectors: dict[str, str] | None = None,
    update_template: bool = True,
) -> ScrapeResult:
    warnings: list[str] = []
    page = await load_page(url)
    if page.error:
        raise RuntimeError(page.error)
    if page.blocked:
        details = f" Reasons: {', '.join(page.security_reasons)}." if page.security_reasons else ""
        raise RuntimeError(f"{PROTECTED_SITE_MESSAGE}{details}")
    warnings.extend(page.warnings)

    context = analyze_html(page.final_url, page.html)
    plan = await plan_scrape(context)
    website_type = plan["website_category"]
    strategy = plan["possible_scraping_strategy"]

    records: list[dict[str, Any]] = []
    selectors: dict[str, str] = {}
    reused_template = False

    if manual_selectors:
        records = apply_selectors(page.html, page.final_url, fields, manual_selectors)
        selectors = manual_selectors
        if not records:
            warnings.append("Manual selectors did not produce records. The bot retried automatic extraction.")

    template = get_template_for_domain(db, url) if not records else None
    if template and template.last_successful_selectors:
        records = apply_selectors(page.html, page.final_url, fields, template.last_successful_selectors)
        if records:
            reused_template = True
            selectors = template.last_successful_selectors
        else:
            warnings.append("Saved template selectors did not match this page. The bot re-analyzed the HTML.")

    if not records and strategy == "schema_json":
        records = extract_schema_records(context, fields, page.final_url)

    if not records and strategy == "table_extraction":
        records = scrape_tables(page.html, page.final_url, fields)

    if not records:
        records = scrape_repeated_elements(page.html, page.final_url, fields)

    if not records and not page.used_dynamic:
        dynamic_page = await load_page(url, force_dynamic=True)
        if dynamic_page.html and not dynamic_page.error and not dynamic_page.blocked:
            warnings.append("Static scrape returned empty results, so the bot retried with Playwright.")
            dynamic_context = analyze_html(dynamic_page.final_url, dynamic_page.html)
            if strategy == "schema_json":
                records = extract_schema_records(dynamic_context, fields, dynamic_page.final_url)
            if not records and strategy == "table_extraction":
                records = scrape_tables(dynamic_page.html, dynamic_page.final_url, fields)
            if not records:
                records = scrape_repeated_elements(dynamic_page.html, dynamic_page.final_url, fields)
            if records:
                page = dynamic_page
                context = dynamic_context
        elif dynamic_page.error:
            warnings.append(dynamic_page.error)

    records = remove_duplicate_records([clean_record(record) for record in records if record])[: _max_records()]
    if not records:
        warnings.append("No matching public records were found for the selected fields.")

    if records and not selectors:
        selectors = infer_successful_selectors(page.html, fields)

    if records and update_template and selectors:
        save_or_update_template(
            db,
            template_name=f"{website_type.replace('_', ' ').title()} Template",
            website_domain=domain_from_url(url),
            website_type=website_type,
            preferred_fields=fields,
            last_successful_selectors=selectors,
        )

    return ScrapeResult(
        records=records,
        website_type=website_type,
        fields=fields,
        selectors=selectors,
        warnings=warnings,
        reused_template=reused_template,
        strategy=strategy,
    )
