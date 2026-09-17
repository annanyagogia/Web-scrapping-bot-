from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from utils.cleaner import clean_text
from utils.url_tools import absolute_url


PRICE_RE = re.compile(r"[$₹€£]\s?\d|(?:price|sale|discount)", re.IGNORECASE)
VIDEO_RE = re.compile(r"(youtube|vimeo|wistia|video|embed)", re.IGNORECASE)


def _safe_json_loads(value: str) -> Any | None:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _schema_types(schema: Any) -> list[str]:
    found: list[str] = []
    if isinstance(schema, dict):
        schema_type = schema.get("@type")
        if isinstance(schema_type, list):
            found.extend(str(item) for item in schema_type)
        elif schema_type:
            found.append(str(schema_type))
        for value in schema.values():
            found.extend(_schema_types(value))
    elif isinstance(schema, list):
        for item in schema:
            found.extend(_schema_types(item))
    return found


def analyze_html(url: str, html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html or "", "lxml")

    title = clean_text(soup.title.string if soup.title else None)
    headings = [
        clean_text(tag.get_text(" ", strip=True))
        for tag in soup.select("h1, h2, h3")
        if clean_text(tag.get_text(" ", strip=True))
    ][:30]

    links_sample = []
    for link in soup.select("a[href]")[:80]:
        href = absolute_url(url, link.get("href"))
        text = clean_text(link.get_text(" ", strip=True)) or clean_text(link.get("aria-label"))
        if href:
            links_sample.append({"text": text, "url": href})

    images_sample = []
    for image in soup.select("img")[:60]:
        src = image.get("src") or image.get("data-src") or image.get("data-lazy-src")
        full_src = absolute_url(url, src)
        if full_src:
            images_sample.append(
                {
                    "alt": clean_text(image.get("alt")),
                    "url": full_src,
                }
            )

    tables = soup.select("table")
    json_ld_schema = []
    for script in soup.select('script[type="application/ld+json"]'):
        payload = _safe_json_loads(script.string or script.get_text() or "")
        if payload:
            json_ld_schema.append(payload)

    open_graph = {
        tag.get("property", "").replace("og:", ""): clean_text(tag.get("content"))
        for tag in soup.select('meta[property^="og:"]')
        if tag.get("content")
    }
    metadata = {
        tag.get("name", ""): clean_text(tag.get("content"))
        for tag in soup.select("meta[name]")
        if tag.get("name") and tag.get("content")
    }

    product_candidates = soup.select(
        '[class*="product" i], [class*="card" i], [class*="listing" i], [class*="grid-item" i], [data-product-id]'
    )
    priced_candidates = [node for node in product_candidates[:200] if PRICE_RE.search(node.get_text(" ", strip=True))]

    video_nodes = soup.select("video, iframe[src], embed[src]")
    has_video = bool(video_nodes) or any(
        VIDEO_RE.search(str(item.get("url", ""))) or VIDEO_RE.search(str(item.get("text", ""))) for item in links_sample
    )

    detected_sections = []
    if headings:
        detected_sections.append("headings")
    if links_sample:
        detected_sections.append("links")
    if images_sample:
        detected_sections.append("images")
    if tables:
        detected_sections.append("tables")
    if priced_candidates:
        detected_sections.append("product_cards")
    if json_ld_schema:
        detected_sections.append("schema_json_ld")
    if open_graph:
        detected_sections.append("open_graph")
    if has_video:
        detected_sections.append("embedded_video")
    if soup.select("article"):
        detected_sections.append("articles")
    if soup.select('[class*="job" i], [data-job-id]'):
        detected_sections.append("job_listings")

    schema_types = sorted(set(_schema_types(json_ld_schema)))
    structure_summary = (
        f"title={title!r}; h1_h3={len(headings)}; links={len(links_sample)}; images={len(images_sample)}; "
        f"tables={len(tables)}; product_like_cards={len(priced_candidates)}; "
        f"schema_types={schema_types[:12]}; video={has_video}; "
        f"forms={len(soup.select('form'))}; scripts={len(soup.select('script'))}"
    )

    return {
        "url": url,
        "page_title": title,
        "headings": headings,
        "links_sample": links_sample[:40],
        "images_sample": images_sample[:30],
        "tables_detected": bool(tables),
        "table_count": len(tables),
        "json_ld_schema": json_ld_schema[:10],
        "json_ld_schema_types": schema_types,
        "open_graph": open_graph,
        "metadata": metadata,
        "detected_sections": detected_sections,
        "html_structure_summary": structure_summary,
        "has_video": has_video,
    }
