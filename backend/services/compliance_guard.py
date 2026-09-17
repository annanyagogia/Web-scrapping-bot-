from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from bs4 import BeautifulSoup


PROTECTED_SITE_MESSAGE = (
    "This website appears to block automated scraping. I cannot bypass protection. "
    "Try another public page, an official API, or manual source data you are authorized to use."
)


@dataclass
class ComplianceDecision:
    allowed: bool
    warning: str | None = None
    reasons: list[str] = field(default_factory=list)
    blocked_by: str | None = None


SENSITIVE_PATH_MARKERS = {
    "login": "login_only_or_authentication",
    "signin": "login_only_or_authentication",
    "sign-in": "login_only_or_authentication",
    "auth": "login_only_or_authentication",
    "account": "private_account_area",
    "admin": "admin_area",
    "checkout": "payment_or_checkout_flow",
    "payment": "payment_or_checkout_flow",
    "billing": "payment_or_checkout_flow",
    "cart": "cart_or_checkout_flow",
    "captcha": "captcha_challenge",
}

BLOCKING_STATUS_REASONS = {
    401: "authentication_required",
    403: "access_forbidden",
    407: "proxy_authentication_required",
    423: "resource_locked",
    429: "rate_limited_or_bot_protection",
}

CHALLENGE_MARKERS = {
    "captcha": "captcha_challenge",
    "g-recaptcha": "recaptcha_challenge",
    "h-captcha": "hcaptcha_challenge",
    "cf-challenge": "cloudflare_challenge",
    "cloudflare ray id": "cloudflare_challenge",
    "checking your browser": "browser_integrity_challenge",
    "verify you are human": "human_verification_challenge",
    "are you a robot": "human_verification_challenge",
    "unusual traffic": "automated_traffic_challenge",
    "access denied": "access_denied",
    "bot protection": "bot_protection",
    "perimeterx": "perimeterx_challenge",
    "px-captcha": "perimeterx_challenge",
    "datadome": "datadome_challenge",
    "akamai bot manager": "akamai_bot_manager",
    "incapsula": "imperva_challenge",
    "_abck": "akamai_bot_manager",
    "please enable cookies": "browser_integrity_challenge",
}


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def evaluate_url_compliance(url: str) -> ComplianceDecision:
    parsed = urlparse(url)
    path = f"{parsed.path}/{parsed.query}".lower()
    reasons = _unique([reason for marker, reason in SENSITIVE_PATH_MARKERS.items() if marker in path])

    if reasons:
        return ComplianceDecision(
            allowed=False,
            warning=(
                "This URL appears to point at login, account, checkout, payment, CAPTCHA, or other protected areas. "
                "The bot only works with publicly visible pages and will not bypass access controls."
            ),
            reasons=reasons,
            blocked_by="url_policy",
        )

    return ComplianceDecision(allowed=True)


def evaluate_response_compliance(html: str, status_code: int | None = None) -> ComplianceDecision:
    reasons: list[str] = []
    if status_code in BLOCKING_STATUS_REASONS:
        reasons.append(BLOCKING_STATUS_REASONS[status_code])

    lower = (html or "").lower()
    for marker, reason in CHALLENGE_MARKERS.items():
        if marker in lower:
            reasons.append(reason)

    if html:
        soup = BeautifulSoup(html, "lxml")
        password_inputs = soup.select('input[type="password"]')
        login_forms = soup.select('form[action*="login" i], form[action*="signin" i], form[action*="auth" i]')
        payment_inputs = soup.select(
            'input[name*="card" i], input[id*="card" i], input[name*="cvv" i], input[id*="cvv" i]'
        )
        paywall_markers = soup.select('[class*="paywall" i], [id*="paywall" i], [data-testid*="paywall" i]')
        if password_inputs or login_forms:
            reasons.append("login_only_or_authentication")
        if payment_inputs:
            reasons.append("payment_or_checkout_flow")
        if paywall_markers or re.search(r"\b(subscribe to continue|sign in to continue|subscriber only)\b", lower):
            reasons.append("paywall_or_restricted_content")

    reasons = _unique(reasons)
    if reasons:
        return ComplianceDecision(
            allowed=False,
            warning=PROTECTED_SITE_MESSAGE,
            reasons=reasons,
            blocked_by="response_policy",
        )

    return ComplianceDecision(allowed=True)


def compliance_warning_for_terms(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower()
    if any(marker in host for marker in ["linkedin", "facebook", "instagram", "x.com", "twitter", "tiktok"]):
        return (
            "This website commonly restricts automated scraping in its terms. Use an official API or scrape only "
            "data you are authorized to access."
        )
    return None
