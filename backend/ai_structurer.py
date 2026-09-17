from __future__ import annotations

import json
import os
import re
from typing import Any


def _first_columns(rows: list[dict[str, Any]]) -> list[str]:
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    return columns


def _row_value(value: Any) -> Any:
    if value in (None, ""):
        return "Not available"
    return value


def _product_rows(product_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, card in enumerate(product_cards, start=1):
        product_name = card.get("product_name") or card.get("raw_text", "")[:120]
        rows.append(
            {
                "No.": index,
                "Product Name": _row_value(product_name),
                "Seller Type": _row_value(card.get("seller_type")),
                "Seller Rating": _row_value(card.get("rating")),
                "Brand": _row_value(card.get("brand")),
                "Minimum Quantity per Consignee": _row_value(card.get("minimum_quantity")),
                "Listed Values Shown": " and ".join(card.get("prices", [])) if card.get("prices") else "Not available",
            }
        )
    return rows


def _link_rows(links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"No.": index, "Text": link.get("text") or "Not available", "URL": link.get("href") or "Not available"}
        for index, link in enumerate(links, start=1)
    ]


def _image_rows(images: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"No.": index, "Alt Text": image.get("alt") or "Not available", "Image URL": image.get("src") or "Not available"}
        for index, image in enumerate(images, start=1)
    ]


def _filter_rows(filters: list[str]) -> list[dict[str, Any]]:
    return [{"No.": index, "Filter or Option": value} for index, value in enumerate(filters, start=1)]


def _visible_text_rows(visible_text: str) -> list[dict[str, Any]]:
    lines = [line.strip() for line in (visible_text or "").splitlines() if line.strip()]
    if not lines and visible_text:
        lines = [visible_text[:3000]]
    return [{"No.": index, "Content": line} for index, line in enumerate(lines[:250], start=1)]


def _title_listing_structure(title_listings: list[dict[str, Any]]) -> dict[str, Any]:
    columns = [
        "Rank",
        "Title",
        "Year or Release",
        "Runtime",
        "Certificate",
        "Title Type",
        "IMDb Rating",
        "Vote Count",
        "Link",
        "Image URL",
    ]
    return {
        "summary": "Extracted ranked title list data from the live rendered webpage.",
        "columns": columns,
        "rows": title_listings,
        "confidence": 0.88 if title_listings else 0.4,
        "issues": [] if title_listings else ["No ranked title rows were found."],
        "extraction_notes": ["Detected a ranked movie/TV title list and parsed titles, metadata, ratings, votes, links, and images."],
    }


def _rule_based_structure(raw_data: dict[str, Any], user_instruction: str | None = None) -> dict[str, Any]:
    page_type = raw_data.get("page_type")
    mode = (raw_data.get("mode") or "auto").lower()
    tables = raw_data.get("tables", [])
    product_cards = raw_data.get("product_cards", [])
    title_listings = raw_data.get("title_listings", [])
    filters = raw_data.get("filters", [])
    links = raw_data.get("links", [])
    images = raw_data.get("images", [])
    visible_text = raw_data.get("visible_text", "")

    if mode in {"title_list", "title listing", "ranked_title_list", "titles", "movies"} and title_listings:
        return _title_listing_structure(title_listings)

    if mode in {"table", "tables"} and tables:
        first_table = tables[0]
        return {
            "summary": "Extracted table data from the live rendered webpage.",
            "columns": first_table["columns"],
            "rows": first_table["rows"],
            "confidence": 0.9,
            "issues": [],
            "extraction_notes": ["Mode forced table extraction."],
        }

    if mode in {"product", "products", "product_listing", "product listings"} and product_cards:
        rows = _product_rows(product_cards)
        return {
            "summary": "Extracted product listing data from the live rendered webpage.",
            "columns": [
                "No.",
                "Product Name",
                "Seller Type",
                "Seller Rating",
                "Brand",
                "Minimum Quantity per Consignee",
                "Listed Values Shown",
            ],
            "rows": rows,
            "confidence": 0.78 if rows else 0.45,
            "issues": [],
            "extraction_notes": ["Mode forced product listing extraction."],
        }

    if mode in {"links", "link"}:
        rows = _link_rows(links)
        return {
            "summary": "Extracted visible webpage links.",
            "columns": ["No.", "Text", "URL"],
            "rows": rows,
            "confidence": 0.88 if rows else 0.4,
            "issues": [] if rows else ["No links were found in the rendered page."],
            "extraction_notes": ["Mode forced link extraction."],
        }

    if mode in {"images", "image"}:
        rows = _image_rows(images)
        return {
            "summary": "Extracted visible webpage images.",
            "columns": ["No.", "Alt Text", "Image URL"],
            "rows": rows,
            "confidence": 0.88 if rows else 0.4,
            "issues": [] if rows else ["No images were found in the rendered page."],
            "extraction_notes": ["Mode forced image extraction."],
        }

    if mode in {"filters", "filter"}:
        rows = _filter_rows(filters)
        return {
            "summary": "Extracted filter labels and visible options.",
            "columns": ["No.", "Filter or Option"],
            "rows": rows,
            "confidence": 0.72 if rows else 0.35,
            "issues": [] if rows else ["No filter labels were found in visible text."],
            "extraction_notes": ["Mode forced filter extraction."],
        }

    if mode in {"text", "text_content", "plain text"}:
        rows = _visible_text_rows(visible_text)
        return {
            "summary": "Extracted visible text content from the live rendered webpage.",
            "columns": ["No.", "Content"],
            "rows": rows,
            "confidence": 0.8 if rows else 0.3,
            "issues": [] if rows else ["No visible text was found."],
            "extraction_notes": ["Mode forced text extraction."],
        }

    if page_type == "table_page" and tables:
        first_table = tables[0]
        return {
            "summary": "Extracted table data from the live rendered webpage.",
            "columns": first_table["columns"],
            "rows": first_table["rows"],
            "confidence": 0.9,
            "issues": [],
            "extraction_notes": ["Detected an HTML table and used Pandas table parsing."],
        }

    if page_type in {"ranked_title_list", "title_listing"} and title_listings:
        return _title_listing_structure(title_listings)

    if page_type == "product_listing" and product_cards:
        rows = _product_rows(product_cards)
        return {
            "summary": "Extracted product listing data from the live rendered webpage.",
            "columns": [
                "No.",
                "Product Name",
                "Seller Type",
                "Seller Rating",
                "Brand",
                "Minimum Quantity per Consignee",
                "Listed Values Shown",
            ],
            "rows": rows,
            "confidence": 0.78 if rows else 0.45,
            "issues": [],
            "extraction_notes": [
                "Detected product/listing card signals such as prices, seller labels, brand, rating, or minimum quantity."
            ],
        }

    if page_type == "directory_or_link_page" and links:
        rows = _link_rows(links[:500])
        return {
            "summary": "Extracted directory-style links from the webpage.",
            "columns": ["No.", "Text", "URL"],
            "rows": rows,
            "confidence": 0.76,
            "issues": [],
            "extraction_notes": ["Detected a link-heavy page and returned meaningful links."],
        }

    if page_type == "article_or_content_page" and visible_text:
        rows = _visible_text_rows(visible_text)
        return {
            "summary": "Extracted visible content from the webpage.",
            "columns": ["No.", "Content"],
            "rows": rows,
            "confidence": 0.7,
            "issues": [],
            "extraction_notes": ["Detected a content-heavy page and returned visible text sections."],
        }

    return {
        "summary": "The page content was extracted, but the structure could not be confidently detected.",
        "columns": ["Content"],
        "rows": [{"Content": (visible_text or "")[:3000] or "Not available"}],
        "confidence": 0.45,
        "issues": ["Page structure unclear. User clarification or AI structuring recommended."],
        "extraction_notes": ["Returned visible text fallback without inventing missing values."],
    }


def _extract_json_object(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text or "", flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _maybe_ai_structure(raw_data: dict[str, Any], user_instruction: str | None = None) -> dict[str, Any] | None:
    if os.getenv("LIVE_SCRAPER_USE_AI", "false").lower() not in {"1", "true", "yes"}:
        return None
    if not os.getenv("OPENAI_API_KEY"):
        return None

    try:
        from openai import OpenAI
    except Exception:
        return None

    safe_payload = {
        "page_title": raw_data.get("page_title"),
        "page_type": raw_data.get("page_type"),
        "visible_text": (raw_data.get("visible_text") or "")[:12000],
        "product_cards": raw_data.get("product_cards", [])[:40],
        "tables": raw_data.get("tables", [])[:3],
        "filters": raw_data.get("filters", [])[:100],
        "links": raw_data.get("links", [])[:100],
        "images": raw_data.get("images", [])[:80],
        "user_instruction": user_instruction,
    }
    prompt = (
        "Convert this extracted live webpage data into clean JSON only. Use only provided values. "
        "Do not hallucinate. If a value is missing, use \"Not available\". Preserve currency symbols "
        "and visible product names. Return keys: summary, columns, rows, confidence, issues, extraction_notes.\n\n"
        + json.dumps(safe_payload, ensure_ascii=False, default=str)
    )

    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict web-scrape structuring engine. Return valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        content = response.choices[0].message.content or ""
        structured = _extract_json_object(content)
        if not structured:
            return None
        if not {"summary", "columns", "rows", "confidence", "issues"}.issubset(structured):
            return None
        structured.setdefault("extraction_notes", ["Structured with AI from extracted live-page data."])
        return structured
    except Exception:
        return None


def structure_scraped_data(raw_data: dict[str, Any], user_instruction: str | None = None) -> dict[str, Any]:
    """
    Converts extracted raw content into clean structured data.
    Rule-based extraction is used first. Optional AI structuring is attempted only when
    LIVE_SCRAPER_USE_AI=true and the rule-based confidence is low.
    """
    structured = _rule_based_structure(raw_data, user_instruction)
    if structured.get("confidence", 0) >= 0.7:
        return structured

    ai_structured = _maybe_ai_structure(raw_data, user_instruction)
    if ai_structured:
        ai_structured.setdefault("extraction_notes", []).append("AI fallback used because rule-based confidence was low.")
        return ai_structured

    return structured
