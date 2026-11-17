#!/usr/bin/env python3
from pathlib import Path
import logging
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jobradar.cli import run_search

ROOT.joinpath("logs").mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s", handlers=[logging.StreamHandler(), logging.FileHandler(ROOT / "logs" / "jobradar.log", encoding="utf-8")])
run_search()
