"""Application state for vector-search-service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from hnsw_core import HNSWIndex


@dataclass
class ServiceState:
    index: HNSWIndex
    index_version: int = 0
    last_checkpoint_at: str | None = None

    def status_payload(self) -> dict[str, object]:
        return {
            "index_size": len(self.index),
            "index_version": self.index_version,
            "queue_depth": 0,
            "worker": "not_configured",
            "last_checkpoint_at": self.last_checkpoint_at,
        }

    def save_snapshot(self, path: str) -> dict[str, object]:
        self.index.save(path)
        self.last_checkpoint_at = datetime.now(timezone.utc).isoformat()
        return {
            "ok": True,
            "path": path,
            "index_version": self.index_version,
        }
