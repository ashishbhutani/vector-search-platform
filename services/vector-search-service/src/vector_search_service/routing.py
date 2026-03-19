"""Shard routing interfaces and strategy registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
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


RouterFactory = Callable[[RouterConfig], ShardRouter]


def _create_broadcast_all(_: RouterConfig) -> ShardRouter:
    return BroadcastAllRouter()


def _create_hash_tenant_or_doc(_: RouterConfig) -> ShardRouter:
    return HashTenantOrDocRouter()


def _create_hash_vector_id(_: RouterConfig) -> ShardRouter:
    return HashVectorIdRouter()


def _create_semantic_lsh(_: RouterConfig) -> ShardRouter:
    return _NotImplementedRouter("semantic_lsh")


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
