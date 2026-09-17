from __future__ import annotations

import re
from urllib.parse import urlparse

from services.compliance_guard import evaluate_response_compliance, evaluate_url_compliance


BLOCKED_SCHEMES = {"file", "ftp", "data", "javascript", "mailto"}
PRIVATE_HOST_RE = re.compile(
    r"(^localhost$)|(^127\.)|(^10\.)|(^172\.(1[6-9]|2\d|3[0-1])\.)|(^192\.168\.)|(^0\.0\.0\.0$)",
    re.IGNORECASE,
)


class URLValidationError(ValueError):
    pass


def validate_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme.lower() in BLOCKED_SCHEMES:
        raise URLValidationError("Unsupported URL scheme. Please use a public http or https URL.")
    if parsed.scheme.lower() not in {"http", "https"}:
        raise URLValidationError("URL must start with http:// or https://.")
    if not parsed.netloc:
        raise URLValidationError("URL host is missing.")
    host = parsed.hostname or ""
    if PRIVATE_HOST_RE.search(host):
        raise URLValidationError("Private, localhost, and internal network URLs are not supported.")
    return url


def compliance_warning_for_url(url: str) -> str | None:
    return evaluate_url_compliance(url).warning


def looks_like_captcha_or_block(html: str, status_code: int | None = None) -> bool:
    return not evaluate_response_compliance(html, status_code).allowed
