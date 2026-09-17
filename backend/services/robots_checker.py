from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import requests


@dataclass
class RobotsCheckResult:
    allowed: bool
    warning: str | None = None
    robots_url: str | None = None


def robots_url_for(page_url: str) -> str:
    parsed = urlparse(page_url)
    root = parsed._replace(path="/robots.txt", params="", query="", fragment="")
    return urlunparse(root)


def check_robots_txt(url: str) -> RobotsCheckResult:
    user_agent = os.getenv("USER_AGENT", "JasonWebScraperBot/1.0")
    robots_url = robots_url_for(url)
    parser = RobotFileParser()
    parser.set_url(robots_url)

    try:
        response = requests.get(
            robots_url,
            timeout=10,
            headers={"User-Agent": user_agent},
        )
    except requests.RequestException:
        return RobotsCheckResult(
            allowed=True,
            warning="robots.txt could not be reached. Continue only if you have permission and the data is public.",
            robots_url=robots_url,
        )

    if response.status_code == 404:
        return RobotsCheckResult(allowed=True, robots_url=robots_url)

    if response.status_code >= 400:
        return RobotsCheckResult(
            allowed=True,
            warning=f"robots.txt returned HTTP {response.status_code}. Continue only with public, permitted data.",
            robots_url=robots_url,
        )

    parser.parse(response.text.splitlines())
    if not parser.can_fetch(user_agent, url):
        return RobotsCheckResult(
            allowed=False,
            warning="robots.txt does not allow this bot to fetch the requested URL. Scraping has been stopped.",
            robots_url=robots_url,
        )

    crawl_delay = parser.crawl_delay(user_agent) or parser.crawl_delay("*")
    warning = None
    if crawl_delay:
        warning = f"robots.txt specifies a crawl delay of {crawl_delay} seconds. The bot will throttle requests."
    return RobotsCheckResult(allowed=True, warning=warning, robots_url=robots_url)
