from __future__ import annotations

import csv
import html
from datetime import datetime
from pathlib import Path

from jobradar.models import Job


def markdown_report(jobs: list[Job], limit: int = 10) -> str:
    out = [f"# Global Remote Job Radar — {datetime.now().astimezone():%Y-%m-%d}", "", "Eligibility is evidence-based. Confirm engagement details with the employer before applying.", ""]
    for job in sorted(jobs, key=lambda j: j.fit_score, reverse=True)[:limit]:
        reasons = "; ".join(job.match_explanation.get("why_it_matches", [])) or "See score breakdown."
        concern = "; ".join(job.match_explanation.get("potential_concerns", [])) or (job.eligibility_reasoning if job.eligibility_status != "CONFIRMED" else "No major concern detected")
        out.extend([f"## {job.company} — {job.title}", f"- Salary: {job.salary_text or 'Not disclosed'}", f"- Employment: {job.employment_type}", f"- Taiwan eligibility: {job.eligibility_status}", f"- Fit score: {job.fit_score}/100", f"- Why it matches: {reasons}", f"- Main concern: {concern}", f"- Posted: {job.published_at or 'Unknown'}", f"- Source: {job.source}", f"- Apply: {job.application_url}", ""])
    return "\n".join(out)


def write_reports(jobs: list[Job], directory: Path) -> tuple[Path, Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    md_path, html_path, csv_path = directory / "daily-report.md", directory / "daily-report.html", directory / "jobs.csv"
    md = markdown_report(jobs)
    md_path.write_text(md, encoding="utf-8")
    html_path.write_text("<!doctype html><meta charset='utf-8'><title>Job Radar</title><pre>" + html.escape(md) + "</pre>", encoding="utf-8")
    rows = [j.model_dump(mode="json") for j in jobs]
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    else:
        csv_path.write_text("id,company,title\n", encoding="utf-8")
    return md_path, html_path, csv_path


def weekly_summary(jobs: list[Job]) -> str:
    counts: dict[str, int] = {}
    for job in jobs:
        counts[job.pipeline_status] = counts.get(job.pipeline_status, 0) + 1
    return f"# Weekly Review\n\nActive opportunities: {len(jobs)}\n\n" + "\n".join(f"- {status}: {count}" for status, count in sorted(counts.items())) + "\n"
