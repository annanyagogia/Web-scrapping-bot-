from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class ScheduledScrapePlan:
    url: str
    fields: list[str]
    cron_expression: str
    template_id: int | None = None


@dataclass
class PriceMonitorRule:
    url: str
    product_key: str
    target_price: float
    currency: str = "USD"


class AlertChannel(Protocol):
    def send(self, subject: str, message: str) -> None:
        ...


class FutureAddonRegistry:
    """Interfaces reserved for production add-ons without coupling them to the prototype routes."""

    scheduled_scraping_enabled = False
    price_monitoring_enabled = False
    deal_tracking_enabled = False
    email_alerts_enabled = False
    telegram_whatsapp_alerts_enabled = False
    chrome_extension_enabled = False
    admin_dashboard_enabled = False
    multi_user_accounts_enabled = False
    brand_templates_enabled = False
    api_based_scraping_enabled = False

    def schedule_scrape(self, plan: ScheduledScrapePlan) -> None:
        raise NotImplementedError("Scheduled scraping is a future add-on.")

    def register_price_monitor(self, rule: PriceMonitorRule) -> None:
        raise NotImplementedError("Price monitoring is a future add-on.")

    def record_deal_snapshot(self, url: str, scraped_at: datetime) -> None:
        raise NotImplementedError("Deal tracking is a future add-on.")
