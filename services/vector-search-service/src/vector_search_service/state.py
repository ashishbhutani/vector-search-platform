"""Application state for vector-search-service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from hnsw_core import HNSWIndex

from .routing import RouterConfig, ShardRouter


@dataclass
class ServiceState:
    index: HNSWIndex
    index_version: int = 0
    last_checkpoint_at: str | None = None
    shard_router: ShardRouter | None = None
    router_config: RouterConfig = RouterConfig()

    def bump_index_version(self, applied_count: int) -> None:
        if applied_count > 0:
            self.index_version += applied_count

    def status_payload(self, queue_depth: int, worker_status: str) -> dict[str, object]:
        return {
            "index_size": len(self.index),
            "index_version": self.index_version,
            "queue_depth": queue_depth,
            "worker": worker_status,
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
