from __future__ import annotations

import os
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from services.compliance_guard import evaluate_response_compliance


@dataclass
class PageLoadResult:
    url: str
    final_url: str
    status_code: int | None
    html: str
    used_dynamic: bool = False
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    blocked: bool = False
    security_reasons: list[str] = field(default_factory=list)


def _headers() -> dict[str, str]:
    return {
        "User-Agent": os.getenv("USER_AGENT", "JasonWebScraperBot/1.0"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def fetch_with_requests(url: str) -> PageLoadResult:
    timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
    try:
        response = requests.get(url, timeout=timeout, headers=_headers(), allow_redirects=True)
        html = response.text or ""
        compliance = evaluate_response_compliance(html, response.status_code)
        return PageLoadResult(
            url=url,
            final_url=response.url,
            status_code=response.status_code,
            html=html,
            blocked=not compliance.allowed,
            security_reasons=compliance.reasons,
        )
    except requests.Timeout:
        return PageLoadResult(url=url, final_url=url, status_code=None, html="", error="Website request timed out.")
    except requests.RequestException as exc:
        return PageLoadResult(url=url, final_url=url, status_code=None, html="", error=f"Website unreachable: {exc}")


def appears_javascript_rendered(html: str) -> bool:
    if not html:
        return True
    soup = BeautifulSoup(html, "lxml")
    visible_text = soup.get_text(" ", strip=True)
    scripts = soup.find_all("script")
    app_roots = soup.select("#__next, #root, #app, [data-reactroot], [ng-version]")
    product_like = soup.select('[class*="product" i], [class*="price" i], article, table')
    if len(visible_text) < 250 and len(scripts) >= 3:
        return True
    if app_roots and len(visible_text) < 700 and not product_like:
        return True
    return False


async def fetch_with_playwright(url: str) -> PageLoadResult:
    headless = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() != "false"
    timeout = int(os.getenv("REQUEST_TIMEOUT", "30")) * 1000
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return PageLoadResult(
            url=url,
            final_url=url,
            status_code=None,
            html="",
            error="Playwright is not installed. Run `pip install -r requirements.txt` and `playwright install chromium`.",
        )

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page(user_agent=_headers()["User-Agent"])
            response = await page.goto(url, wait_until="networkidle", timeout=timeout)
            await page.wait_for_timeout(500)
            html = await page.content()
            final_url = page.url
            status_code = response.status if response else None
            compliance = evaluate_response_compliance(html, status_code)
            await browser.close()
            return PageLoadResult(
                url=url,
                final_url=final_url,
                status_code=status_code,
                html=html,
                used_dynamic=True,
                blocked=not compliance.allowed,
                security_reasons=compliance.reasons,
            )
    except Exception as exc:
        return PageLoadResult(
            url=url,
            final_url=url,
            status_code=None,
            html="",
            used_dynamic=True,
            error=f"Dynamic browser load failed: {exc}",
        )


async def load_page(url: str, force_dynamic: bool = False) -> PageLoadResult:
    if force_dynamic:
        return await fetch_with_playwright(url)

    result = fetch_with_requests(url)
    if result.error or result.blocked:
        return result

    if appears_javascript_rendered(result.html):
        dynamic = await fetch_with_playwright(url)
        if dynamic.html and not dynamic.error:
            dynamic.warnings.append("The page appeared JavaScript-rendered, so Playwright was used.")
            return dynamic
        result.warnings.append(dynamic.error or "Dynamic load failed. Continuing with static HTML.")

    return result
