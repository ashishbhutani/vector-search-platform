"""Distributed gateway/shard runtime primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import urllib.error
import urllib.request


@dataclass(frozen=True)
class ShardMapEntry:
    shard_id: str
    base_url: str
    role: str = "primary"
    tenant_set: list[str] | None = None


@dataclass
class ShardHealthRegistry:
    states: dict[str, str] = field(default_factory=dict)

    def set_state(self, shard_id: str, state: str) -> None:
        if state not in {"healthy", "degraded", "unavailable"}:
            raise ValueError(f"unsupported health state: {state}")
        self.states[shard_id] = state

    def get_state(self, shard_id: str) -> str:
        return self.states.get(shard_id, "healthy")

    def healthy_shards(self, shard_ids: list[str]) -> list[str]:
        return [shard_id for shard_id in shard_ids if self.get_state(shard_id) == "healthy"]


def load_shard_map(path: str) -> list[ShardMapEntry]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("shard map must be a JSON object")
    rows = raw.get("shards")
    if not isinstance(rows, list) or not rows:
        raise ValueError("shard map must include non-empty 'shards'")

    entries: list[ShardMapEntry] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each shard map row must be a JSON object")
        shard_id = row.get("shard_id")
        base_url = row.get("base_url")
        role = row.get("role", "primary")
        tenant_set = row.get("tenant_set")
        if not isinstance(shard_id, str) or not shard_id:
            raise ValueError("shard map row requires non-empty 'shard_id'")
        if not isinstance(base_url, str) or not base_url:
            raise ValueError("shard map row requires non-empty 'base_url'")
        if role not in {"primary", "replica"}:
            raise ValueError("shard map row 'role' must be 'primary' or 'replica'")
        if tenant_set is not None and not isinstance(tenant_set, list):
            raise ValueError("shard map row 'tenant_set' must be a list when present")
        entries.append(
            ShardMapEntry(
                shard_id=shard_id,
                base_url=base_url.rstrip("/"),
                role=role,
                tenant_set=tenant_set,
            )
        )
    return entries


class HttpShardClient:
    """Small HTTP client used by gateway fanout/health checks."""

    def __init__(self, timeout_sec: float = 1.0) -> None:
        self.timeout_sec = timeout_sec

    def _request_json(
        self,
        method: str,
        url: str,
        payload: dict[str, object] | None = None,
        *,
        timeout_sec: float | None = None,
    ) -> dict[str, object]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url=url, method=method, data=body)
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout_sec or self.timeout_sec) as resp:  # nosec B310
            parsed = json.loads(resp.read().decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("shard response must be a JSON object")
        return parsed

    def query_shard(
        self,
        base_url: str,
        payload: dict[str, object],
        *,
        timeout_sec: float | None = None,
    ) -> dict[str, object]:
        return self._request_json("POST", f"{base_url.rstrip('/')}/query", payload, timeout_sec=timeout_sec)

    def ingest_shard(self, base_url: str, payload: dict[str, object]) -> dict[str, object]:
        return self._request_json("POST", f"{base_url.rstrip('/')}/vectors", payload)

    def is_healthy(self, base_url: str, *, timeout_sec: float | None = None) -> bool:
        try:
            self._request_json("GET", f"{base_url.rstrip('/')}/status", timeout_sec=timeout_sec)
        except (urllib.error.URLError, TimeoutError, ValueError):
            return False
        return True
