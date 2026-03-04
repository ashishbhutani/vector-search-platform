"""Public HNSW index class contract.

Phase 1 keeps the implementation intentionally simple and readable while preserving
stable APIs. The graph-optimized traversal is introduced incrementally on top of
this baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Sequence

import numpy as np

from .distance import distance, to_vector
from .types import VectorId, VectorLike


@dataclass
class HNSWIndex:
    dim: int
    metric: Literal["l2", "cosine", "dot"] = "l2"
    m: int = 16
    ef_construction: int = 200
    ef_search: int = 50
    random_seed: int = 42

    _vectors: list[np.ndarray] = field(default_factory=list, init=False, repr=False)
    _ids: list[VectorId] = field(default_factory=list, init=False, repr=False)
    _id_to_pos: dict[VectorId, int] = field(default_factory=dict, init=False, repr=False)
    _auto_id: int = field(default=0, init=False, repr=False)

    def _next_id(self) -> int:
        next_id = self._auto_id
        self._auto_id += 1
        return next_id

    def add(self, vector: VectorLike, id: VectorId | None = None) -> VectorId:
        vec = to_vector(vector, dim=self.dim)
        vector_id: VectorId = self._next_id() if id is None else id
        if vector_id in self._id_to_pos:
            raise ValueError(f"Duplicate vector id: {vector_id}")

        self._id_to_pos[vector_id] = len(self._vectors)
        self._vectors.append(vec)
        self._ids.append(vector_id)
        return vector_id

    def add_batch(
        self,
        vectors: Sequence[VectorLike],
        ids: Sequence[VectorId] | None = None,
    ) -> list[VectorId]:
        if ids is not None and len(vectors) != len(ids):
            raise ValueError("vectors and ids length mismatch")

        out: list[VectorId] = []
        for idx, vector in enumerate(vectors):
            vector_id = None if ids is None else ids[idx]
            out.append(self.add(vector, id=vector_id))
        return out

    def search(
        self,
        query: VectorLike,
        k: int,
        ef_search: int | None = None,
    ) -> list[tuple[VectorId, float]]:
        if not self._vectors:
            raise ValueError("Cannot search an empty index")
        if k <= 0:
            raise ValueError("k must be > 0")

        q = to_vector(query, dim=self.dim)
        limit = min(k, len(self._vectors))

        # Baseline exhaustive scan; ANN graph traversal is layered on this API.
        scored = [
            (self._ids[i], distance(q, self._vectors[i], self.metric))
            for i in range(len(self._vectors))
        ]
        scored.sort(key=lambda item: item[1])
        return scored[:limit]

    def search_batch(
        self,
        queries: Sequence[VectorLike],
        k: int,
        ef_search: int | None = None,
    ) -> list[list[tuple[VectorId, float]]]:
        return [self.search(query=q, k=k, ef_search=ef_search) for q in queries]

    def save(self, path: str | Path) -> None:
        raise NotImplementedError("Implemented in P1-03")

    @classmethod
    def load(cls, path: str | Path) -> "HNSWIndex":
        raise NotImplementedError("Implemented in P1-03")

    def __len__(self) -> int:
        return len(self._vectors)
