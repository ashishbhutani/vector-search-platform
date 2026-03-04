"""Serialization helpers for hnsw-core snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def save_index(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload), encoding="utf-8")


def load_index(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Snapshot payload must be a JSON object")
    return data
