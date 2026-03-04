"""Serialization contracts for hnsw-core."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def save_index(path: str | Path, payload: dict[str, Any]) -> None:
    raise NotImplementedError("Implemented in P1-03")


def load_index(path: str | Path) -> dict[str, Any]:
    raise NotImplementedError("Implemented in P1-03")
