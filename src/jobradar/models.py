from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Job(BaseModel):
    id: str = ""
    company: str = "Unknown"
    title: str
    description: str = ""
    source: str
    original_url: str
    application_url: str = ""
    location: str = ""
    work_arrangement: str = "Unknown"
    employment_type: str = "Unknown"
    salary_text: str = ""
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str = ""
    compensation_period: str = ""
    published_at: datetime | None = None
    last_updated: datetime = Field(default_factory=utc_now)
    restrictions: list[str] = Field(default_factory=list)
    eligibility_status: str = "UNCERTAIN"
    eligibility_evidence: list[str] = Field(default_factory=list)
    eligibility_reasoning: str = ""
    recruiter_questions: list[str] = Field(default_factory=list)
    last_verified: datetime | None = None
    fit_score: int = 0
    match_explanation: dict[str, Any] = Field(default_factory=dict)
    pipeline_status: str = "New"
    personal_notes: str = ""
    risk_warnings: list[str] = Field(default_factory=list)

    @property
    def canonical_url(self) -> str:
        from urllib.parse import urlsplit, urlunsplit
        parts = urlsplit(self.original_url or self.application_url)
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower().removeprefix("www."), parts.path.rstrip("/"), "", ""))

