from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

import feedparser
import httpx

from jobradar.config import load_yaml
from jobradar.models import Job

LOG = logging.getLogger(__name__)


class Collector:
    def __init__(self, timeout: float | None = None, retries: int | None = None):
        config = load_yaml("sources.yaml")
        self.timeout = timeout or float(config.get("timeout_seconds", 20))
        self.retries = config.get("retries", 2) if retries is None else retries
        self.rate_limit = float(config.get("rate_limit_seconds", 1.0))
        self.last_request = 0.0
        self.client = httpx.Client(timeout=self.timeout, headers={"User-Agent": config.get("user_agent", "GlobalRemoteJobRadar/0.1")}, follow_redirects=True)

    def _get(self, url: str) -> httpx.Response:
        delay = self.rate_limit - (time.monotonic() - self.last_request)
        if delay > 0:
            time.sleep(delay)
        for attempt in range(self.retries + 1):
            try:
                response = self.client.get(url)
                self.last_request = time.monotonic()
                response.raise_for_status()
                return response
            except httpx.HTTPError as exc:
                LOG.warning("Source request failed (%s), attempt %d/%d", urlparse(url).netloc, attempt + 1, self.retries + 1)
                if attempt == self.retries:
                    raise RuntimeError(f"Unable to fetch source {urlparse(url).netloc}") from exc
                time.sleep(min(2**attempt, 5))
        raise RuntimeError("Unreachable request retry state")

    def close(self) -> None:
        self.client.close()

    @staticmethod
    def _date(value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value / 1000 if value > 10_000_000_000 else value, timezone.utc)
            except (OverflowError, OSError, ValueError):
                return None
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                parsed = parsedate_to_datetime(value)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                return None

    @staticmethod
    def _id(source: str, raw_id: Any, url: str) -> str:
        value = str(raw_id or url or "job")
        return f"{source}:{value}" if not value.startswith(f"{source}:") else value

    @staticmethod
    def _text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, tuple, set)):
            return ", ".join(str(item) for item in value if item is not None)
        if isinstance(value, dict):
            return ", ".join(f"{key}: {item}" for key, item in value.items() if item is not None)
        return str(value)

    def himalayas(self, keywords: list[str] | None = None) -> list[Job]:
        base = load_yaml("sources.yaml")["sources"]["himalayas"]["url"]
        terms = keywords or ["program manager", "senior program manager", "business operations", "process manager", "FinOps", "APAC operations"]
        jobs: list[Job] = []
        for term in terms:
            # The public API accepts these three query parameters; job type, seniority,
            # and timezone are retained from postings and evaluated locally.
            params = {"country": "TW", "worldwide": "true", "query": term}
            try:
                data = self._get(f"{base}?" + httpx.QueryParams(params).__str__()).json()
            except (RuntimeError, ValueError) as exc:
                LOG.warning("Himalayas search failed for a query: %s", exc)
                continue
            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict):
                rows = data.get("jobs") or data.get("results") or data.get("data") or []
                if isinstance(rows, dict):
                    rows = rows.get("jobs") or rows.get("results") or []
            else:
                rows = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                url = row.get("applicationLink") or row.get("application_link") or row.get("url") or ""
                original = row.get("url") or row.get("jobUrl") or url
                if not url or not original:
                    continue
                jobs.append(Job(id=self._id("himalayas", row.get("id"), original), company=self._text(row.get("companyName") or row.get("company") or "Unknown"), title=self._text(row.get("title") or "Untitled"), description=self._text(row.get("description") or ""), source="Himalayas", original_url=original, application_url=url, location=self._text(row.get("location") or row.get("locationRestrictions") or ""), employment_type=self._text(row.get("employmentType") or row.get("type") or "Unknown"), salary_text=self._text(row.get("salary") or ""), published_at=self._date(row.get("pubDate") or row.get("publishedAt"))))
        return jobs

    def rss(self, url: str, source: str) -> list[Job]:
        try:
            parsed = feedparser.parse(self._get(url).content)
        except RuntimeError as exc:
            LOG.warning("RSS source unavailable: %s", exc)
            return []
        jobs = []
        for row in parsed.entries:
            link = row.get("link", "")
            if not link:
                continue
            summary = row.get("summary", "")
            published = self._date(row.get("published") or row.get("updated"))
            company = row.get("author") or "Unknown"
            jobs.append(Job(id=self._id(source.lower().replace(" ", ""), row.get("id"), link), company=company, title=row.get("title", "Untitled"), description=summary, source=source, original_url=link, application_url=link, published_at=published, work_arrangement="Remote"))
        return jobs

    def weworkremotely(self) -> list[Job]:
        feeds = load_yaml("sources.yaml")["sources"]["weworkremotely"]["feeds"]
        jobs: list[Job] = []
        for url in feeds:
            jobs.extend(self.rss(url, "We Work Remotely"))
        return jobs

    def remoteok(self, use_rss: bool = False) -> list[Job]:
        cfg = load_yaml("sources.yaml")["sources"]["remoteok"]
        if use_rss:
            return self.rss(cfg["rss_url"], "Remote OK")
        try:
            data = self._get(cfg["url"]).json()
        except (RuntimeError, ValueError) as exc:
            LOG.warning("Remote OK source unavailable: %s", exc)
            return []
        jobs = []
        for row in data:
            if not isinstance(row, dict) or not row.get("url") or not row.get("position"):
                continue
            tags = row.get("tags", [])
            if not isinstance(tags, list):
                tags = [tags]
            salary = " ".join(filter(None, [self._text(row.get("salary_min")), self._text(row.get("salary_max"))]))
            jobs.append(Job(id=self._id("remoteok", row.get("id"), row["url"]), company=self._text(row.get("company", "Unknown")), title=self._text(row["position"]), description=self._text(row.get("description", "")), source="Remote OK", original_url=row["url"], application_url=row.get("apply_url") or row["url"], location=self._text(row.get("location", "")), employment_type=", ".join(self._text(tag) for tag in tags), salary_text=salary, published_at=self._date(row.get("date"))))
        return jobs

    def company_board(self, provider: str, token: str, company: str) -> list[Job]:
        urls = {
            "greenhouse": f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true",
            "lever": f"https://api.lever.co/v0/postings/{token}?mode=json",
            "ashby": f"https://api.ashbyhq.com/posting-api/job-board/{token}",
        }
        if provider not in urls:
            raise ValueError(f"Unsupported company board: {provider}")
        try:
            data = self._get(urls[provider]).json()
        except (RuntimeError, ValueError) as exc:
            LOG.warning("Company board unavailable (%s): %s", provider, exc)
            return []
        rows = data.get("jobs", []) if isinstance(data, dict) else data
        jobs = []
        for row in rows:
            if provider == "greenhouse":
                url = row.get("absolute_url", "")
                title, description = row.get("title", "Untitled"), row.get("content", "")
                location = (row.get("location") or {}).get("name", "")
                raw_id = row.get("id")
                published = self._date(row.get("updated_at"))
                employment = "Unknown"
            elif provider == "lever":
                url = row.get("hostedUrl", "")
                title, description = row.get("text", "Untitled"), row.get("descriptionPlain", "")
                location = (row.get("categories") or {}).get("location", "")
                raw_id = row.get("id")
                published = self._date(row.get("createdAt"))
                employment = (row.get("categories") or {}).get("commitment", "Unknown")
            else:
                url = row.get("jobUrl", "")
                title, description = row.get("title", "Untitled"), row.get("descriptionPlain", "")
                location = ", ".join((row.get("location") or {}).get("name", "") for _ in [0])
                raw_id = row.get("id")
                published = self._date(row.get("publishedAt"))
                employment = row.get("employmentType", "Unknown")
            if not url:
                continue
            jobs.append(Job(id=self._id(provider, raw_id, url), company=company, title=title, description=description, source=provider.title(), original_url=url, application_url=url, location=location, employment_type=employment, published_at=published))
        return jobs

    def enabled_company_jobs(self) -> list[Job]:
        boards = load_yaml("target_companies.yaml").get("companies", [])
        jobs = []
        for board in boards:
            if board.get("enabled"):
                jobs.extend(self.company_board(board["provider"], board["token"], board["name"]))
        return jobs


def stable_hash(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()
