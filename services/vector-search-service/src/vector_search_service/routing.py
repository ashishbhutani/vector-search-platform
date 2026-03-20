"""Shard routing interfaces and strategy registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable, Sequence

from .models import QueryRequest, VectorRecord


class ShardRouter(ABC):
    """Stable distributed routing contract."""

    @abstractmethod
    def route_for_ingest(self, record: VectorRecord, shard_count: int) -> str:
        """Select a single target shard id for ingest."""

    @abstractmethod
    def route_for_query(
        self,
        query: QueryRequest,
        shard_ids: Sequence[str],
        top_n: int | None = None,
    ) -> list[str]:
        """Select shard ids to target for query fanout."""


@dataclass(frozen=True)
class RouterConfig:
    """Runtime routing configuration."""

    strategy: str = "broadcast_all"
    semantic_top_n: int = 2
    semantic_bootstrap_path: str | None = None


def _stable_bucket(value: str, shard_count: int) -> int:
    if shard_count <= 0:
        raise ValueError("shard_count must be > 0")
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False) % shard_count


class BroadcastAllRouter(ShardRouter):
    """Broadcast query strategy with deterministic single-shard ingest."""

    def route_for_ingest(
        self,
        record: VectorRecord,
        shard_count: int,
    ) -> str:
        bucket = _stable_bucket(str(record.id), shard_count)
        return f"shard-{bucket}"

    def route_for_query(
        self,
        query: QueryRequest,
        shard_ids: Sequence[str],
        top_n: int | None = None,
    ) -> list[str]:
        del query
        del top_n
        return list(shard_ids)


class _HashRouterBase(ShardRouter):
    """Base class for deterministic hash routing strategies."""

    def _routing_key(self, record: VectorRecord) -> str:
        raise NotImplementedError

    def route_for_ingest(self, record: VectorRecord, shard_count: int) -> str:
        key = self._routing_key(record)
        bucket = _stable_bucket(key, shard_count)
        return f"shard-{bucket}"

    def route_for_query(
        self,
        query: QueryRequest,
        shard_ids: Sequence[str],
        top_n: int | None = None,
    ) -> list[str]:
        del query
        del top_n
        return list(shard_ids)


class HashVectorIdRouter(_HashRouterBase):
    """Hash vector id to pick a deterministic ingest shard."""

    def _routing_key(self, record: VectorRecord) -> str:
        return str(record.id)


class HashTenantOrDocRouter(_HashRouterBase):
    """Hash tenant id when present in record id, otherwise hash full doc id."""

    @staticmethod
    def _tenant_key_from_id(record_id: str | int) -> str:
        raw = str(record_id)
        for sep in (":", "/"):
            if sep in raw:
                tenant, _ = raw.split(sep, 1)
                if tenant:
                    return tenant
        return raw

    def _routing_key(self, record: VectorRecord) -> str:
        return self._tenant_key_from_id(record.id)


class _NotImplementedRouter(ShardRouter):
    """Placeholder strategy for follow-up tickets."""

    def __init__(self, strategy_name: str) -> None:
        self._strategy_name = strategy_name

    def route_for_ingest(self, record: VectorRecord, shard_count: int) -> str:
        del record
        del shard_count
        raise NotImplementedError(f"Strategy '{self._strategy_name}' is not implemented yet")

    def route_for_query(
        self,
        query: QueryRequest,
        shard_ids: Sequence[str],
        top_n: int | None = None,
    ) -> list[str]:
        del query
        del shard_ids
        del top_n
        raise NotImplementedError(f"Strategy '{self._strategy_name}' is not implemented yet")


class SemanticLSHRouter(ShardRouter):
    """Semantic top-N routing using a bootstrap centroid artifact."""

    def __init__(self, *, top_n: int, bootstrap_path: str) -> None:
        if top_n <= 0:
            raise ValueError("semantic_top_n must be > 0")
        self._top_n = top_n
        self._centroids = self._load_centroids(bootstrap_path)

    @staticmethod
    def _load_centroids(path: str) -> list[tuple[str, list[float]]]:
        raw = Path(path).read_text(encoding="utf-8")
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("semantic bootstrap artifact must be a JSON object")
        rows = parsed.get("centroids")
        if not isinstance(rows, list) or not rows:
            raise ValueError("semantic bootstrap artifact must include non-empty 'centroids'")

        centroids: list[tuple[str, list[float]]] = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("semantic bootstrap centroid rows must be JSON objects")
            shard_id = row.get("shard_id")
            vector = row.get("centroid")
            if not isinstance(shard_id, str) or not shard_id:
                raise ValueError("semantic bootstrap centroid requires non-empty 'shard_id'")
            if not isinstance(vector, list) or not vector:
                raise ValueError("semantic bootstrap centroid requires non-empty 'centroid'")
            centroids.append((shard_id, [float(v) for v in vector]))
        return centroids

    @staticmethod
    def _l2_sq(a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            raise ValueError("semantic routing vector dimension mismatch")
        return sum((x - y) * (x - y) for x, y in zip(a, b))

    def _ranked_shards(self, vector: list[float], allowed: set[str] | None = None) -> list[str]:
        scored: list[tuple[float, str]] = []
        for shard_id, centroid in self._centroids:
            if allowed is not None and shard_id not in allowed:
                continue
            score = self._l2_sq(vector, centroid)
            scored.append((score, shard_id))
        scored.sort(key=lambda item: (item[0], item[1]))
        return [shard_id for _, shard_id in scored]

    def route_for_ingest(self, record: VectorRecord, shard_count: int) -> str:
        del shard_count
        ranked = self._ranked_shards(record.vector)
        if not ranked:
            raise ValueError("semantic routing found no candidate shards")
        return ranked[0]

    def route_for_query(
        self,
        query: QueryRequest,
        shard_ids: Sequence[str],
        top_n: int | None = None,
    ) -> list[str]:
        allowed = set(shard_ids)
        ranked = self._ranked_shards(query.vector, allowed=allowed)
        limit = self._top_n if top_n is None else top_n
        if limit <= 0:
            return []
        return ranked[: min(limit, len(ranked))]


RouterFactory = Callable[[RouterConfig], ShardRouter]


def _create_broadcast_all(_: RouterConfig) -> ShardRouter:
    return BroadcastAllRouter()


def _create_hash_tenant_or_doc(_: RouterConfig) -> ShardRouter:
    return HashTenantOrDocRouter()


def _create_hash_vector_id(_: RouterConfig) -> ShardRouter:
    return HashVectorIdRouter()


def _create_semantic_lsh(config: RouterConfig) -> ShardRouter:
    if not config.semantic_bootstrap_path:
        raise ValueError("semantic_lsh strategy requires --router-semantic-bootstrap-path")
    return SemanticLSHRouter(
        top_n=config.semantic_top_n,
        bootstrap_path=config.semantic_bootstrap_path,
    )


ROUTER_REGISTRY: dict[str, RouterFactory] = {
    "broadcast_all": _create_broadcast_all,
    "hash_tenant_or_doc": _create_hash_tenant_or_doc,
    "hash_vector_id": _create_hash_vector_id,
    "semantic_lsh": _create_semantic_lsh,
}


def create_router(config: RouterConfig) -> ShardRouter:
    """Build a router from runtime strategy config."""

    try:
        factory = ROUTER_REGISTRY[config.strategy]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported routing strategy: {config.strategy}. "
            f"Expected one of: {sorted(ROUTER_REGISTRY.keys())}"
        ) from exc
    return factory(config)
