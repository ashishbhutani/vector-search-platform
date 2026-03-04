"""Public HNSW index class contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence

from .types import VectorId, VectorLike


@dataclass
class HNSWIndex:
    dim: int
    metric: Literal["l2", "cosine", "dot"] = "l2"
    m: int = 16
    ef_construction: int = 200
    ef_search: int = 50
    random_seed: int = 42

    def add(self, vector: VectorLike, id: VectorId | None = None) -> VectorId:
        raise NotImplementedError("Implemented in P1-01")

    def add_batch(
        self,
        vectors: Sequence[VectorLike],
        ids: Sequence[VectorId] | None = None,
    ) -> list[VectorId]:
        raise NotImplementedError("Implemented in P1-01")

    def search(
        self,
        query: VectorLike,
        k: int,
        ef_search: int | None = None,
    ) -> list[tuple[VectorId, float]]:
        raise NotImplementedError("Implemented in P1-01")

    def search_batch(
        self,
        queries: Sequence[VectorLike],
        k: int,
        ef_search: int | None = None,
    ) -> list[list[tuple[VectorId, float]]]:
        raise NotImplementedError("Implemented in P1-01")

    def save(self, path: str | Path) -> None:
        raise NotImplementedError("Implemented in P1-03")

    @classmethod
    def load(cls, path: str | Path) -> "HNSWIndex":
        raise NotImplementedError("Implemented in P1-03")

    def __len__(self) -> int:
        raise NotImplementedError("Implemented in P1-01")
