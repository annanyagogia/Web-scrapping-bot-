from __future__ import annotations

from urllib.parse import urljoin, urlparse, urlunparse


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        parsed = urlparse(f"https://{url.strip()}")
    normalized = parsed._replace(fragment="")
    return urlunparse(normalized)


def domain_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def absolute_url(base_url: str, value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("data:") or value.startswith("mailto:") or value.startswith("tel:"):
        return value
    return urljoin(base_url, value)


def same_domain(url_a: str, url_b: str) -> bool:
    return domain_from_url(url_a) == domain_from_url(url_b)
