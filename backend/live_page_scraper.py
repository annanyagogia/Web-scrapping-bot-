from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import pandas as pd
from bs4 import BeautifulSoup, Tag


BACKEND_DIR = Path(__file__).resolve().parent
STATIC_DIR = BACKEND_DIR / "static"
SCREENSHOT_DIR = STATIC_DIR / "screenshots"

PRICE_RE = re.compile(r"(?:₹|Rs\.?|INR|\$|€|£)\s?\d[\d,]*(?:\.\d{1,2})?", re.IGNORECASE)
RATING_RANGE_RE = re.compile(r"(\d(?:\.\d)?)\s*[–-]\s*(\d(?:\.\d)?)")
RATING_RE = re.compile(r"(?:rating|rated)[:\s]*(\d(?:\.\d)?)|(\d(?:\.\d)?)\s*(?:/ ?5|stars?)", re.IGNORECASE)
QUANTITY_PATTERNS = [
    re.compile(r"(?:minimum quantity(?: per consignee)?|min qty|moq|minimum order quantity)[^\d]{0,80}(\d+)", re.IGNORECASE),
    re.compile(r"(\d+)\s*(?:kg|g|litre|liter|ltr|ml|pack|packs|pcs|pieces)\b", re.IGNORECASE),
]
SELLER_KEYWORDS = [
    "resellers",
    "reseller",
    "manufacturers",
    "manufacturer",
    "oem",
    "authorized seller",
    "seller",
]


def clean_text(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _clean_lines(text: str | None) -> list[str]:
    return [clean_text(line) for line in (text or "").splitlines() if clean_text(line)]


def _unique_dicts(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        value = clean_text(str(item.get(key, "")))[:300]
        if not value or value in seen:
            continue
        seen.add(value)
        unique.append(item)
    return unique


async def auto_scroll(page, max_scrolls: int = 6):
    """
    Scrolls the page to load lazy-loaded or infinite-scroll content.
    """
    previous_height = 0
    for _ in range(max_scrolls):
        current_height = await page.evaluate("document.body.scrollHeight")
        if current_height == previous_height:
            break
        previous_height = current_height
        await page.mouse.wheel(0, 3000)
        await page.wait_for_timeout(1500)


async def fetch_live_page(url: str, scrape_full_page: bool = False) -> dict[str, Any]:
    """
    Opens the webpage using Playwright.
    Waits for the webpage to render fully.
    Extracts page title, rendered HTML, visible text, links, images, buttons, forms, and screenshot.
    Supports optional full-page scrolling.
    """
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed. Run `pip install -r requirements.txt` and `playwright install chromium`."
        ) from exc

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        page = await browser.new_page(
            viewport={"width": 1440, "height": 1200},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        response_status: int | None = None
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            response_status = response.status if response else None
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except PlaywrightTimeoutError:
                warnings.append("Network activity did not become fully idle; continuing with rendered content.")
            await page.wait_for_timeout(3000)
            if scrape_full_page:
                await auto_scroll(page)

            title = await page.title()
            html = await page.content()
            try:
                visible_text = await page.locator("body").inner_text(timeout=7000)
            except Exception:
                visible_text = ""

            links = await page.eval_on_selector_all(
                "a",
                """
                elements => elements.map(a => ({
                    text: (a.innerText || a.getAttribute("aria-label") || "").trim(),
                    href: a.href
                })).filter(a => a.text || a.href)
                """,
            )
            images = await page.eval_on_selector_all(
                "img",
                """
                elements => elements.map(img => ({
                    alt: img.alt || "",
                    src: img.currentSrc || img.src || img.getAttribute("data-src") || ""
                })).filter(img => img.src)
                """,
            )
            buttons = await page.eval_on_selector_all(
                "button, [role='button']",
                """
                elements => elements.map(btn => ({
                    text: (btn.innerText || btn.getAttribute("aria-label") || "").trim()
                })).filter(btn => btn.text)
                """,
            )
            forms = await page.eval_on_selector_all(
                "form",
                """
                elements => elements.map(form => ({
                    action: form.action || "",
                    method: form.method || "get",
                    text: (form.innerText || "").trim(),
                    inputs: Array.from(form.querySelectorAll("input, select, textarea")).map(input => ({
                        name: input.getAttribute("name") || "",
                        type: input.getAttribute("type") || input.tagName.toLowerCase(),
                        placeholder: input.getAttribute("placeholder") || ""
                    }))
                }))
                """,
            )

            screenshot_name = f"screenshot_{uuid.uuid4().hex}.png"
            screenshot_path = SCREENSHOT_DIR / screenshot_name
            await page.screenshot(path=str(screenshot_path), full_page=True)

            return {
                "url": url,
                "final_url": page.url,
                "domain": urlparse(page.url).netloc or urlparse(url).netloc,
                "status_code": response_status,
                "title": title,
                "html": html,
                "visible_text": visible_text,
                "links": links,
                "images": images,
                "buttons": buttons,
                "forms": forms,
                "screenshot_path": f"static/screenshots/{screenshot_name}",
                "screenshot_url": f"/static/screenshots/{screenshot_name}",
                "warnings": warnings,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        finally:
            await browser.close()


def detect_page_type(html: str, visible_text: str) -> str:
    """
    Detects whether the webpage is product_listing, table_page, article_or_content_page,
    directory_or_link_page, login_required, blocked_or_captcha, or unknown.
    """
    text = (visible_text or "").lower()
    html_lower = (html or "").lower()
    blocked_text_markers = [
        "captcha",
        "verify you are human",
        "checking your browser",
        "are you a robot",
        "unusual traffic",
        "access denied",
        "cloudflare ray id",
    ]
    html_challenge_markers = ["cf-challenge", "g-recaptcha", "h-captcha", "px-captcha"]
    if any(marker in text for marker in blocked_text_markers):
        return "blocked_or_captcha"
    if len((visible_text or "").split()) < 80 and any(marker in html_lower for marker in html_challenge_markers):
        return "blocked_or_captcha"
    if ("login" in text or "sign in" in text) and ("password" in text or 'type="password"' in html_lower):
        return "login_required"

    if re.search(r"\bimdb charts?\b", text) or re.search(r"\b\d+\s+titles\b", text):
        if re.search(r"#\d+\s+.+?\s+\d(?:\.\d)?", visible_text or "", re.DOTALL):
            return "ranked_title_list"

    product_keywords = [
        "price",
        "₹",
        "rs.",
        "inr",
        "brand",
        "seller",
        "rating",
        "minimum quantity",
        "add to cart",
        "buy now",
        "product",
        "catalog",
        "listing",
    ]
    product_score = sum(1 for keyword in product_keywords if keyword in text)
    if product_score >= 3:
        return "product_listing"
    if "<table" in html_lower:
        return "table_page"
    if len(re.findall(r"https?://", html or "")) > 20:
        return "directory_or_link_page"
    if len((visible_text or "").split()) > 500:
        return "article_or_content_page"
    return "unknown"


def extract_title_listings(html: str, visible_text: str = "", base_url: str = "") -> list[dict[str, Any]]:
    """
    Extracts ranked movie/TV title lists such as IMDb chart pages.
    """
    soup = BeautifulSoup(html or "", "lxml")
    selectors = [
        "li.ipc-metadata-list-summary-item",
        "[data-testid='chart-layout-main-column'] li",
        "[class*='metadata-list-summary-item' i]",
    ]
    items: list[Tag] = []
    seen: set[int] = set()
    for selector in selectors:
        try:
            nodes = soup.select(selector)
        except Exception:
            continue
        for node in nodes:
            if id(node) not in seen:
                seen.add(id(node))
                items.append(node)

    rows: list[dict[str, Any]] = []
    for item in items:
        raw_text = item.get_text("\n", strip=True)
        if not raw_text or len(raw_text) < 10:
            continue

        rank_node = item.select_one(".ipc-signpost__text, [class*='RankSignpost' i], [class*='signpost' i]")
        rank_text = clean_text(rank_node.get_text(" ", strip=True) if rank_node else "")
        rank_match = re.search(r"#?\s*(\d+)", rank_text) or re.search(r"#\s*(\d+)", raw_text)
        if not rank_match:
            continue
        rank = int(rank_match.group(1))

        title = ""
        for title_selector in [
            "h3.ipc-title__text",
            "[class*='cli-title' i] h3",
            "a.ipc-title-link-wrapper",
            "a[href*='/title/']",
        ]:
            title_node = item.select_one(title_selector)
            title = clean_text(title_node.get_text(" ", strip=True) if title_node else "")
            if title:
                break
        title = re.sub(r"^#?\d+\.?\s*", "", title).strip()
        if not title or title.lower() in {"rate", "mark as watched"}:
            continue

        link_node = item.select_one("a.ipc-title-link-wrapper[href], a[href*='/title/'][href]")
        link = urljoin(base_url, link_node.get("href")) if link_node else "Not available"

        metadata_nodes = item.select("[class*='cli-title-metadata' i] li, [class*='title-metadata' i] li")
        metadata = [clean_text(node.get_text(" ", strip=True)) for node in metadata_nodes if clean_text(node.get_text(" ", strip=True))]
        year_or_release = metadata[0] if metadata else "Not available"
        runtime = next((value for value in metadata[1:] if re.search(r"\d+\s*h|\d+\s*m", value, re.IGNORECASE)), "Not available")
        type_re = re.compile(r"\b(series|special|mini series|episode|tv movie|short|video game|documentary)\b", re.IGNORECASE)
        title_type = next((value for value in metadata[1:] if type_re.search(value)), "Movie")
        certificate_candidates = [
            value
            for value in metadata[1:]
            if value != runtime and value != title_type and not type_re.search(value)
        ]
        certificate = certificate_candidates[0] if certificate_candidates else "Not available"

        rating_node = item.select_one(".ipc-rating-star--rating, [class*='rating-star--rating' i]")
        votes_node = item.select_one(".ipc-rating-star--voteCount, [class*='rating-star--voteCount' i]")
        rating = clean_text(rating_node.get_text(" ", strip=True) if rating_node else "") or "Not available"
        votes = clean_text(votes_node.get_text(" ", strip=True) if votes_node else "")
        votes = clean_text(votes.strip("()")) or "Not available"

        image_node = item.select_one("img")
        image_url = image_node.get("src") or image_node.get("data-src") if image_node else None

        rows.append(
            {
                "Rank": rank,
                "Title": title,
                "Year or Release": year_or_release,
                "Runtime": runtime,
                "Certificate": certificate,
                "Title Type": title_type,
                "IMDb Rating": rating,
                "Vote Count": votes,
                "Link": link,
                "Image URL": image_url or "Not available",
            }
        )

    rows.sort(key=lambda row: row["Rank"])
    unique: list[dict[str, Any]] = []
    seen_ranks: set[int] = set()
    for row in rows:
        if row["Rank"] in seen_ranks:
            continue
        seen_ranks.add(row["Rank"])
        unique.append(row)
    return unique[:500]


def extract_tables(html: str) -> list[dict[str, Any]]:
    """
    Extracts normal HTML tables from rendered HTML using Pandas.
    """
    tables: list[dict[str, Any]] = []
    try:
        dfs = pd.read_html(StringIO(html or ""))
        for index, df in enumerate(dfs):
            df = df.dropna(how="all").fillna("")
            tables.append(
                {
                    "table_index": index,
                    "columns": [str(col) for col in df.columns],
                    "rows": df.to_dict(orient="records"),
                }
            )
    except Exception:
        pass
    return tables


def extract_prices(text: str) -> list[str]:
    return list(dict.fromkeys(match.group(0).strip() for match in PRICE_RE.finditer(text or "")))


def extract_rating(text: str) -> str | None:
    range_match = RATING_RANGE_RE.search(text or "")
    if range_match:
        return f"{range_match.group(1)} - {range_match.group(2)}"
    match = RATING_RE.search(text or "")
    if match:
        return match.group(1) or match.group(2)
    return None


def extract_quantity(text: str) -> str | None:
    for pattern in QUANTITY_PATTERNS:
        match = pattern.search(text or "")
        if match:
            return match.group(1)
    return None


def _label_value_from_lines(lines: list[str], labels: list[str]) -> str | None:
    label_re = "|".join(re.escape(label) for label in labels)
    for line in lines:
        match = re.search(rf"\b(?:{label_re})\b\s*[:\-]?\s*(.+)$", line, flags=re.IGNORECASE)
        if match:
            value = clean_text(match.group(1))
            value = re.split(
                r"\b(?:seller|rating|price|minimum quantity|moq|category|availability|filter)\b",
                value,
                flags=re.IGNORECASE,
            )[0]
            value = clean_text(value.strip(":-|"))
            if value and value.lower() not in {"brand", "seller", "rating"}:
                return value[:80]
    return None


def extract_brand(text: str) -> str | None:
    lines = _clean_lines(text)
    value = _label_value_from_lines(lines, ["brand", "brand name"])
    if value:
        return value
    match = re.search(r"\bbrand\b\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\s\-&()./]{0,80})", text or "", flags=re.IGNORECASE)
    if match:
        return clean_text(match.group(1))[:80]
    return None


def extract_seller_type(text: str) -> str | None:
    lower_text = (text or "").lower()
    for keyword in SELLER_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", lower_text):
            return keyword.title()
    return None


def _best_selector_for_node(node: Tag) -> str | None:
    if not node or not isinstance(node, Tag):
        return None
    node_id = node.get("id")
    if node_id:
        return f"#{node_id}"
    classes = [cls for cls in node.get("class", []) if isinstance(cls, str)]
    useful = [cls for cls in classes if re.search(r"product|listing|card|catalog|item|result|tile", cls, re.IGNORECASE)]
    selected = useful[:2] or classes[:2]
    if selected:
        sanitized = [re.sub(r"[^A-Za-z0-9_-]", "", cls) for cls in selected]
        return node.name + "".join(f".{cls}" for cls in sanitized if cls)
    return node.name


def _extract_product_name(card: Tag, raw_text: str) -> str | None:
    selectors = [
        "[class*='product-title' i]",
        "[class*='product-name' i]",
        "[class*='item-title' i]",
        "[class*='title' i]",
        "[class*='name' i]",
        "h1",
        "h2",
        "h3",
        "a[title]",
        "img[alt]",
    ]
    for selector in selectors:
        try:
            node = card.select_one(selector)
        except Exception:
            continue
        if not node:
            continue
        value = node.get("title") or node.get("alt") or node.get_text(" ", strip=True)
        value = clean_text(value)
        if value and len(value) >= 3 and not PRICE_RE.search(value):
            return value[:180]

    ignored = re.compile(
        r"\b(price|seller|rating|brand|filter|sort|minimum quantity|moq|add to cart|buy now|compare|view)\b",
        re.IGNORECASE,
    )
    for line in _clean_lines(raw_text):
        if len(line) < 3 or PRICE_RE.search(line) or ignored.search(line):
            continue
        return line[:180]
    return None


def _candidate_cards(soup: BeautifulSoup) -> list[Tag]:
    selectors = [
        "[data-product-id]",
        "[itemtype*='Product']",
        "[class*='product' i]",
        "[class*='listing' i]",
        "[class*='catalog' i]",
        "[class*='result' i]",
        "[class*='card' i]",
        "[class*='tile' i]",
        "[class*='item' i]",
        "article",
        "li",
    ]
    candidates: list[Tag] = []
    seen: set[int] = set()
    for selector in selectors:
        try:
            nodes = soup.select(selector)
        except Exception:
            continue
        for node in nodes:
            if id(node) not in seen:
                seen.add(id(node))
                candidates.append(node)
    return candidates


def _product_signal_score(text: str, node: Tag) -> int:
    lower = (text or "").lower()
    score = 0
    if extract_prices(text):
        score += 3
    if extract_rating(text):
        score += 1
    if extract_quantity(text):
        score += 1
    if extract_brand(text):
        score += 1
    if extract_seller_type(text):
        score += 1
    for keyword in ["seller", "price", "product", "add to cart", "buy now", "minimum quantity", "brand"]:
        if keyword in lower:
            score += 1
    if node.select_one("a[href]"):
        score += 1
    if node.select_one("img"):
        score += 1
    return score


def extract_product_cards(html: str, visible_text: str) -> list[dict[str, Any]]:
    """
    Detects repeated product/listing/card elements from the page.
    Extracts product name, prices, rating, brand, seller type, quantity, and raw text.
    """
    soup = BeautifulSoup(html or "", "lxml")
    products: list[dict[str, Any]] = []

    for card in _candidate_cards(soup):
        raw_text = card.get_text("\n", strip=True)
        text = clean_text(raw_text)
        if len(text) < 25 or len(text) > 6000:
            continue
        score = _product_signal_score(text, card)
        prices = extract_prices(text)
        rating = extract_rating(text)
        quantity = extract_quantity(text)
        brand = extract_brand(raw_text) or extract_brand(text)
        seller_type = extract_seller_type(text)
        strong_signal = bool(prices or rating or quantity)
        contextual_signal = bool(brand and seller_type and re.search(r"\b(product|catalog|listing|quantity|pack)\b", text, re.IGNORECASE))
        if score < 4 or not (strong_signal or contextual_signal):
            continue

        products.append(
            {
                "product_name": _extract_product_name(card, raw_text),
                "raw_text": text,
                "prices": prices,
                "rating": rating,
                "brand": brand,
                "seller_type": seller_type,
                "minimum_quantity": quantity,
                "links": [
                    {"text": clean_text(a.get_text(" ", strip=True)), "href": a.get("href")}
                    for a in card.select("a[href]")[:5]
                ],
                "images": [
                    {"alt": img.get("alt", ""), "src": img.get("src") or img.get("data-src") or ""}
                    for img in card.select("img")[:3]
                    if img.get("src") or img.get("data-src")
                ],
                "selector": _best_selector_for_node(card),
                "signal_score": score,
            }
        )

    unique = _unique_dicts(products, "raw_text")
    unique.sort(key=lambda item: item.get("signal_score", 0), reverse=True)
    return unique[:200]


def extract_links(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html or "", "lxml")
    links = []
    base = ""
    canonical = soup.select_one("link[rel='canonical'][href]")
    if canonical:
        base = canonical.get("href", "")
    for a in soup.find_all("a"):
        text = clean_text(a.get_text(" ") or a.get("aria-label") or a.get("title"))
        href = a.get("href")
        if href:
            links.append({"text": text, "href": urljoin(base, href) if base else href})
    return _unique_dicts(links, "href")


def extract_images(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html or "", "lxml")
    images = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        alt = img.get("alt", "")
        if src:
            images.append({"alt": clean_text(alt), "src": src})
    return _unique_dicts(images, "src")


def extract_filters(visible_text: str) -> list[str]:
    possible_filter_words = [
        "filter",
        "sort by",
        "brand",
        "price",
        "rating",
        "seller",
        "category",
        "availability",
        "discount",
    ]
    filters = []
    for line in _clean_lines(visible_text):
        lower = line.lower()
        if any(word in lower for word in possible_filter_words) and len(line) <= 180:
            filters.append(line)
    return list(dict.fromkeys(filters))


def detect_pagination(visible_text: str, buttons: list[dict[str, Any]] | None = None, links: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    labels = []
    for item in [*(buttons or []), *(links or [])]:
        value = clean_text(str(item.get("text", "")))
        if value:
            labels.append(value)
    text = "\n".join([visible_text or "", *labels]).lower()
    markers = ["next", "load more", "show more", ">", "pagination"]
    found = [marker for marker in markers if re.search(rf"(^|\s){re.escape(marker)}($|\s)", text)]
    return {"detected": bool(found), "markers": list(dict.fromkeys(found))}


def extract_with_template_selectors(html: str, selectors: dict[str, str] | None) -> list[dict[str, Any]]:
    if not selectors:
        return []
    product_card_selector = selectors.get("product_card") or selectors.get("card") or selectors.get("listing")
    if not product_card_selector:
        return []

    soup = BeautifulSoup(html or "", "lxml")
    try:
        cards = soup.select(product_card_selector)
    except Exception:
        return []

    products: list[dict[str, Any]] = []
    for card in cards[:200]:
        raw_text = card.get_text("\n", strip=True)
        text = clean_text(raw_text)
        if not text:
            continue
        prices = extract_prices(text)
        rating = extract_rating(text)
        quantity = extract_quantity(text)
        brand = extract_brand(raw_text) or extract_brand(text)
        seller_type = extract_seller_type(text)
        score = _product_signal_score(text, card)
        strong_signal = bool(prices or rating or quantity)
        contextual_signal = bool(brand and seller_type and re.search(r"\b(product|catalog|listing|quantity|pack)\b", text, re.IGNORECASE))
        if score < 4 or not (strong_signal or contextual_signal):
            continue
        product_name = None
        for field in ["product_name", "name", "title"]:
            selector = selectors.get(field)
            if selector:
                try:
                    node = card.select_one(selector)
                except Exception:
                    node = None
                if node:
                    product_name = clean_text(node.get("title") or node.get_text(" ", strip=True))
                    break
        products.append(
            {
                "product_name": product_name or _extract_product_name(card, raw_text),
                "raw_text": text,
                "prices": prices,
                "rating": rating,
                "brand": brand,
                "seller_type": seller_type,
                "minimum_quantity": quantity,
                "selector": product_card_selector,
                "signal_score": score,
            }
        )
    return _unique_dicts(products, "raw_text")


def infer_live_template_selectors(product_cards: list[dict[str, Any]]) -> dict[str, str]:
    for card in product_cards:
        selector = card.get("selector")
        if selector:
            return {"product_card": selector}
    return {}


def structure_scraped_data(raw_data: dict[str, Any], user_instruction: str | None = None) -> dict[str, Any]:
    """
    Converts extracted raw content into clean structured data.
    Uses rule-based extraction first. Uses AI only if rule-based extraction is unclear.
    """
    from ai_structurer import structure_scraped_data as _structure_scraped_data

    return _structure_scraped_data(raw_data, user_instruction)


def export_data(data: list[dict[str, Any]], output_format: str) -> dict[str, Any]:
    """
    Exports scraped data to JSON, CSV, Excel, Markdown table, or plain text.
    Returns downloadable file path if applicable.
    """
    from exporters import export_data as _export_data

    columns = []
    for row in data:
        for key in row:
            if key not in columns:
                columns.append(key)
    return _export_data(data, columns, output_format)
