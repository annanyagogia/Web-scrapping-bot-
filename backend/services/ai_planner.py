from __future__ import annotations

import json
import os
import re
from typing import Any


FIELD_PRESETS = {
    "fashion_ecommerce": [
        "product_name",
        "price",
        "discount",
        "image_url",
        "product_url",
        "size",
        "color",
        "category",
        "availability",
    ],
    "makeup_ecommerce": [
        "product_name",
        "brand",
        "price",
        "discount",
        "shade",
        "rating",
        "image_url",
        "product_url",
        "availability",
    ],
    "ecommerce": [
        "product_name",
        "price",
        "discount",
        "image_url",
        "product_url",
        "rating",
        "reviews_count",
        "availability",
    ],
    "blog": ["title", "author", "published_date", "summary", "article_url", "image_url", "tags"],
    "news": ["title", "author", "published_date", "summary", "article_url", "image_url", "tags"],
    "job_board": ["job_title", "company", "location", "salary", "experience", "job_url", "posted_date"],
    "video_page": [
        "video_title",
        "thumbnail_url",
        "duration",
        "description",
        "embedded_video_url",
        "platform_source",
    ],
    "real_estate": ["property_title", "price", "location", "bedrooms", "bathrooms", "area", "image_url", "listing_url"],
    "table_documentation": ["table_headers", "table_rows", "source_url"],
    "unknown": ["title", "link", "image_url", "summary"],
}


def _context_text(context: dict[str, Any]) -> str:
    chunks = [
        str(context.get("url", "")),
        str(context.get("page_title", "")),
        " ".join(context.get("headings", [])[:20]),
        " ".join(str(item.get("text", "")) for item in context.get("links_sample", [])[:20]),
        " ".join(str(item.get("alt", "")) for item in context.get("images_sample", [])[:20]),
        str(context.get("html_structure_summary", "")),
        " ".join(context.get("json_ld_schema_types", [])),
    ]
    return " ".join(chunks).lower()


def _infer_strategy(context: dict[str, Any], category: str) -> str:
    schema_types = " ".join(context.get("json_ld_schema_types", [])).lower()
    if category == "table_documentation" or context.get("tables_detected"):
        return "table_extraction"
    if any(marker in schema_types for marker in ["product", "article", "jobposting", "videoobject"]):
        return "schema_json"
    summary = str(context.get("html_structure_summary", "")).lower()
    if "scripts=" in summary:
        script_match = re.search(r"scripts=(\d+)", summary)
        card_match = re.search(r"product_like_cards=(\d+)", summary)
        if script_match and int(script_match.group(1)) > 12 and (not card_match or int(card_match.group(1)) == 0):
            return "dynamic_browser"
    return "static_html"


def heuristic_plan(context: dict[str, Any]) -> dict[str, Any]:
    text = _context_text(context)
    schema_types = " ".join(context.get("json_ld_schema_types", [])).lower()
    detected_sections = context.get("detected_sections", [])

    category = "unknown"
    confidence = 0.48

    if context.get("has_video") or "videoobject" in schema_types:
        category = "video_page"
        confidence = 0.88
    elif "jobposting" in schema_types or re.search(r"\b(job|career|salary|hiring|apply now)\b", text):
        category = "job_board"
        confidence = 0.83
    elif context.get("tables_detected") and not ("product_cards" in detected_sections):
        category = "table_documentation"
        confidence = 0.82
    elif "product" in schema_types or "product_cards" in detected_sections or re.search(r"[$₹€£]\s?\d|add to cart|buy now", text):
        makeup_terms = ["makeup", "cosmetic", "lipstick", "foundation", "mascara", "shade", "skincare", "beauty"]
        fashion_terms = ["fashion", "dress", "shirt", "shoe", "sneaker", "apparel", "size", "color", "denim", "wear"]
        if any(term in text for term in makeup_terms):
            category = "makeup_ecommerce"
            confidence = 0.88
        elif any(term in text for term in fashion_terms):
            category = "fashion_ecommerce"
            confidence = 0.86
        else:
            category = "ecommerce"
            confidence = 0.78
    elif any(marker in schema_types for marker in ["newsarticle", "article", "blogposting"]) or re.search(
        r"\b(author|published|read more|news|blog|article)\b", text
    ):
        category = "news" if "news" in text or "newsarticle" in schema_types else "blog"
        confidence = 0.78
    elif re.search(r"\b(real estate|property|bedroom|bathroom|sqft|apartment|rent)\b", text):
        category = "real_estate"
        confidence = 0.76

    clarifying_question = None
    if context.get("has_video"):
        clarifying_question = (
            "This page contains an embedded video. Do you want me to extract only video metadata such as title, "
            "thumbnail, duration, and source URL?"
        )
    elif confidence < 0.70:
        sections = ", ".join(detected_sections) or "links, images, headings, and page metadata"
        clarifying_question = f"I found multiple sections on this page: {sections}. Which section should I extract?"

    return {
        "website_category": category,
        "recommended_fields": FIELD_PRESETS.get(category, FIELD_PRESETS["unknown"]),
        "possible_scraping_strategy": _infer_strategy(context, category),
        "confidence_score": round(confidence, 2),
        "clarifying_question": clarifying_question,
    }


async def _openai_plan(context: dict[str, Any]) -> dict[str, Any] | None:
    if not os.getenv("OPENAI_API_KEY"):
        return None

    try:
        from openai import AsyncOpenAI
    except ImportError:
        return None

    client = AsyncOpenAI()
    prompt = {
        "url": context.get("url"),
        "page_title": context.get("page_title"),
        "headings": context.get("headings", [])[:20],
        "links_sample": context.get("links_sample", [])[:20],
        "images_sample": context.get("images_sample", [])[:10],
        "tables_detected": context.get("tables_detected"),
        "json_ld_schema": context.get("json_ld_schema", [])[:3],
        "html_structure_summary": context.get("html_structure_summary"),
    }

    system = (
        "You classify public webpages for compliant scraping. Return compact JSON only with keys: "
        "website_category, recommended_fields, possible_scraping_strategy, confidence_score, clarifying_question. "
        "Allowed categories: ecommerce, fashion_ecommerce, makeup_ecommerce, blog, news, video_page, "
        "job_board, real_estate, table_documentation, unknown. Never suggest bypassing login, CAPTCHA, paywalls, "
        "or anti-bot protection. For video pages, metadata only."
    )

    try:
        response = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(prompt, default=str)[:12000]},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = response.choices[0].message.content or "{}"
        planned = json.loads(content)
    except Exception:
        return None

    category = planned.get("website_category") or planned.get("website_type") or "unknown"
    if category not in FIELD_PRESETS:
        category = "unknown"
    fields = planned.get("recommended_fields") or FIELD_PRESETS[category]
    strategy = planned.get("possible_scraping_strategy") or _infer_strategy(context, category)
    confidence = float(planned.get("confidence_score") or 0.5)
    clarifying_question = planned.get("clarifying_question")
    if context.get("has_video"):
        clarifying_question = (
            "This page contains an embedded video. Do you want me to extract only video metadata such as title, "
            "thumbnail, duration, and source URL?"
        )
    elif confidence < 0.70 and not clarifying_question:
        sections = ", ".join(context.get("detected_sections", [])) or "several sections"
        clarifying_question = f"I found multiple sections on this page: {sections}. Which section should I extract?"

    return {
        "website_category": category,
        "recommended_fields": fields,
        "possible_scraping_strategy": strategy,
        "confidence_score": round(max(0.0, min(confidence, 1.0)), 2),
        "clarifying_question": clarifying_question,
    }


async def plan_scrape(context: dict[str, Any]) -> dict[str, Any]:
    openai_result = await _openai_plan(context)
    if openai_result:
        return openai_result
    return heuristic_plan(context)
