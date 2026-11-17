#!/usr/bin/env python3
from datetime import datetime
from pathlib import Path
import logging
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jobradar.cli import run_search

ROOT.joinpath("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(ROOT / "logs" / "jobradar.log", encoding="utf-8"),
    ],
)


def push_db_to_github() -> None:
    db_path = ROOT / "data" / "jobs.db"
    if not db_path.exists():
        logging.warning("data/jobs.db not found, skipping GitHub push.")
        return

    try:
        subprocess.run(
            ["git", "add", "-f", "data/jobs.db"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        # 檢查 staged 區是否真的有變更，避免無變動時 git commit 報錯
        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet", "--", "data/jobs.db"],
            cwd=ROOT,
        )
        if diff.returncode == 0:
            logging.info("No changes in data/jobs.db; skipping commit and push.")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(
            ["git", "commit", "-m", f"chore(data): daily jobs.db update ({timestamp})"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        logging.info("Successfully pushed updated data/jobs.db to GitHub.")
    except subprocess.CalledProcessError as exc:
        logging.error("Failed to push data/jobs.db to GitHub: %s", exc.stderr or exc)


if __name__ == "__main__":
    run_search()
    push_db_to_github()
