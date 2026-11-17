from __future__ import annotations

import argparse
import logging
from pathlib import Path

from jobradar.collectors.adapters import Collector
from jobradar.config import ROOT, profile
from jobradar.eligibility.classifier import classify
from jobradar.matching.scorer import detect_risks, score
from jobradar.models import Job
from jobradar.reporting.reports import weekly_summary, write_reports
from jobradar.storage.database import JobStore

LOG = logging.getLogger("jobradar")


def run_search(offline: bool = False, db_path: str | None = None) -> list[Job]:
    store = JobStore(db_path) if db_path else JobStore()
    found: list[Job] = []
    if not offline:
        collector = Collector()
        try:
            for name, call in [("Himalayas", collector.himalayas), ("We Work Remotely", collector.weworkremotely), ("Remote OK", collector.remoteok), ("Company boards", collector.enabled_company_jobs)]:
                try:
                    batch = call()
                    LOG.info("Fetched %d jobs from %s", len(batch), name)
                    found.extend(batch)
                except Exception as exc:
                    LOG.warning("Collector %s failed: %s: %s", name, type(exc).__name__, exc)
        finally:
            collector.close()
    candidate = profile()
    for job in found:
        classify(job)
        score(job, candidate)
        job.risk_warnings = detect_risks(job)
        store.upsert(job)
    jobs = store.list_jobs()
    write_reports(jobs, ROOT / "reports")
    (ROOT / "reports" / "weekly-summary.md").write_text(weekly_summary(jobs), encoding="utf-8")
    return jobs


def main() -> None:
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s", handlers=[logging.StreamHandler(), logging.FileHandler(ROOT / "logs" / "jobradar.log", encoding="utf-8")])
    parser = argparse.ArgumentParser(description="Taiwan-aware international remote job discovery")
    sub = parser.add_subparsers(dest="command")
    search = sub.add_parser("search", help="Collect, classify, score, and report opportunities")
    search.add_argument("--offline", action="store_true", help="Regenerate reports without network calls")
    sub.add_parser("weekly", help="Write weekly summary")
    args = parser.parse_args()
    if args.command in (None, "search"):
        jobs = run_search(offline=getattr(args, "offline", False))
        print(f"Stored {len(jobs)} active jobs. Reports are in {ROOT / 'reports'}")
    elif args.command == "weekly":
        target = ROOT / "reports" / "weekly-summary.md"
        target.parent.mkdir(exist_ok=True)
        target.write_text(weekly_summary(JobStore().list_jobs()), encoding="utf-8")
        print(target)


if __name__ == "__main__":
    main()
