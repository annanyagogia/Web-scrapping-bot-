from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


ExportFormat = Literal["json", "csv", "excel", "xlsx"]


class AnalyzeUrlRequest(BaseModel):
    url: HttpUrl


class AnalyzeUrlResponse(BaseModel):
    website_type: str
    suggested_fields: list[str]
    detected_sections: list[str]
    confidence_score: float
    clarifying_question: str | None = None
    possible_scraping_strategy: str = "static_html"
    compliance_allowed: bool = True
    compliance_warning: str | None = None
    compliance_reasons: list[str] = Field(default_factory=list)
    template_available: bool = False
    page_title: str | None = None


class ScrapeRequest(BaseModel):
    url: HttpUrl
    fields: list[str] = Field(default_factory=list)
    format: ExportFormat = "json"
    manual_selectors: dict[str, str] | None = None
    update_template: bool = True


class ScrapeResponse(BaseModel):
    status: str
    total_records: int
    data: list[dict[str, Any]]
    task_id: int | None = None
    export_url: str | None = None
    warnings: list[str] = Field(default_factory=list)
    compliance_reasons: list[str] = Field(default_factory=list)
    reused_template: bool = False


class AgentRunRequest(BaseModel):
    url: HttpUrl
    user_instruction: str | None = None
    approved_fields: list[str] = Field(default_factory=list)
    confidence_threshold: float = 0.70
    format: ExportFormat = "json"


class AgentRunResponse(BaseModel):
    mode: Literal["scraped", "needs_clarification", "blocked", "empty"]
    message: str
    analysis: AnalyzeUrlResponse
    selected_fields: list[str] = Field(default_factory=list)
    clarification_options: list[str] = Field(default_factory=list)
    scrape_result: ScrapeResponse | None = None
    decision_reason: str


class SaveTemplateRequest(BaseModel):
    template_name: str
    website_type: str
    fields: list[str]
    website_url: HttpUrl | None = None
    website_domain: str | None = None
    last_successful_selectors: dict[str, str] = Field(default_factory=dict)


class TemplateResponse(BaseModel):
    id: int
    template_name: str
    website_domain: str
    website_type: str
    preferred_fields: list[str]
    last_successful_selectors: dict[str, str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    id: int
    url: str
    website_type: str | None
    status: str
    selected_fields: list[str]
    total_records: int
    compliance_warning: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SaveTemplateResponse(BaseModel):
    status: str
    template: TemplateResponse


class ChatCommandRequest(BaseModel):
    command: str
    current_url: HttpUrl | None = None
    available_fields: list[str] = Field(default_factory=list)


class ChatCommandResponse(BaseModel):
    action: Literal["analyze", "scrape", "agent_run", "export", "save_template", "clarify", "noop"]
    fields: list[str] = Field(default_factory=list)
    export_format: ExportFormat | None = None
    message: str
