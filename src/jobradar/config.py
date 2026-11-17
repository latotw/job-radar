from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_yaml(name: str) -> dict[str, Any]:
    path = ROOT / "config" / name
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return value


def profile() -> dict[str, Any]:
    return load_yaml("profile.yaml")
