from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Iterable

from jobradar.models import Job

DEFAULT_DB = Path(__file__).resolve().parents[3] / "data" / "jobs.db"
PIPELINE = ["New", "Shortlisted", "Eligibility Check", "Preparing Application", "Applied", "Recruiter Screen", "Interview", "Offer", "Rejected", "Withdrawn"]


def normalize_title(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


class JobStore:
    def __init__(self, path: str | Path = DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, company TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL,
                source TEXT NOT NULL, original_url TEXT NOT NULL, application_url TEXT NOT NULL, location TEXT,
                work_arrangement TEXT, employment_type TEXT, salary_text TEXT, salary_min REAL, salary_max REAL,
                currency TEXT, compensation_period TEXT, published_at TEXT, last_updated TEXT NOT NULL,
                restrictions TEXT NOT NULL, eligibility_status TEXT NOT NULL, eligibility_evidence TEXT NOT NULL,
                eligibility_reasoning TEXT NOT NULL, recruiter_questions TEXT NOT NULL, last_verified TEXT,
                fit_score INTEGER NOT NULL, match_explanation TEXT NOT NULL, pipeline_status TEXT NOT NULL,
                personal_notes TEXT NOT NULL, risk_warnings TEXT NOT NULL, canonical_url TEXT NOT NULL,
                closed INTEGER NOT NULL DEFAULT 0, expires_at TEXT
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS jobs_company_title ON jobs(company, title)")
            db.execute("CREATE INDEX IF NOT EXISTS jobs_canonical_url ON jobs(canonical_url)")

    def upsert(self, job: Job) -> str:
        with self._connect() as db:
            existing = db.execute("SELECT id FROM jobs WHERE canonical_url=? OR (source=? AND id=?) LIMIT 1", (job.canonical_url, job.source, job.id)).fetchone()
            if existing is None:
                candidates = db.execute("SELECT id, title FROM jobs WHERE lower(company)=lower(?)", (job.company,)).fetchall()
                existing = next((row for row in candidates if normalize_title(row["title"]) == normalize_title(job.title)), None)
            result = "new" if existing is None else "updated"
            if existing:
                job.id = existing["id"]
            record = job.model_dump(mode="json")
            columns = ["id", "company", "title", "description", "source", "original_url", "application_url", "location", "work_arrangement", "employment_type", "salary_text", "salary_min", "salary_max", "currency", "compensation_period", "published_at", "last_updated", "restrictions", "eligibility_status", "eligibility_evidence", "eligibility_reasoning", "recruiter_questions", "last_verified", "fit_score", "match_explanation", "pipeline_status", "personal_notes", "risk_warnings"]
            values = [record.get(c) for c in columns]
            for col in ("restrictions", "eligibility_evidence", "recruiter_questions", "match_explanation", "risk_warnings"):
                values[columns.index(col)] = json.dumps(record.get(col), ensure_ascii=False)
            placeholders = ",".join("?" for _ in columns)
            updates = ",".join(f"{c}=excluded.{c}" for c in columns if c not in {"id", "pipeline_status", "personal_notes"})
            db.execute(f"INSERT INTO jobs ({','.join(columns)}, canonical_url) VALUES ({placeholders}, ?) ON CONFLICT(id) DO UPDATE SET {updates}, canonical_url=excluded.canonical_url", (*values, job.canonical_url))
            return result

    def list_jobs(self) -> list[Job]:
        with self._connect() as db:
            return [self._to_job(row) for row in db.execute("SELECT * FROM jobs WHERE closed=0 ORDER BY fit_score DESC")]

    def _to_job(self, row: sqlite3.Row) -> Job:
        keys = set(row.keys())
        data = {k: row[k] for k in Job.model_fields if k in keys}
        for key in ("restrictions", "eligibility_evidence", "recruiter_questions", "match_explanation", "risk_warnings"):
            data[key] = json.loads(data[key] or ("{}" if key == "match_explanation" else "[]"))
        return Job.model_validate(data)

    def update_pipeline(self, job_id: str, status: str, notes: str | None = None) -> None:
        if status not in PIPELINE:
            raise ValueError(f"Invalid pipeline status: {status}")
        with self._connect() as db:
            if notes is None:
                db.execute("UPDATE jobs SET pipeline_status=? WHERE id=?", (status, job_id))
            else:
                db.execute("UPDATE jobs SET pipeline_status=?, personal_notes=? WHERE id=?", (status, notes, job_id))

    def mark_closed(self, job_id: str) -> None:
        with self._connect() as db:
            db.execute("UPDATE jobs SET closed=1 WHERE id=?", (job_id,))

    def export_rows(self) -> list[dict[str, object]]:
        with self._connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM jobs ORDER BY fit_score DESC")]
