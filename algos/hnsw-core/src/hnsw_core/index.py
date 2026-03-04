"""Public HNSW index class contract.

Phase 1 keeps the implementation intentionally simple and readable while preserving
stable APIs. The graph-optimized traversal is introduced incrementally on top of
this baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Sequence

import numpy as np

from .distance import distance, to_vector
from .serialize import load_index, save_index
from .types import VectorId, VectorLike

SNAPSHOT_FORMAT_VERSION = 1


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
    _index_version: int = field(default=0, init=False, repr=False)

    def _next_id(self) -> int:
        next_id = self._auto_id
        self._auto_id += 1
        return next_id

    def _touch(self) -> None:
        self._index_version += 1

    def add(self, vector: VectorLike, id: VectorId | None = None) -> VectorId:
        vec = to_vector(vector, dim=self.dim)
        vector_id: VectorId = self._next_id() if id is None else id
        if vector_id in self._id_to_pos:
            raise ValueError(f"Duplicate vector id: {vector_id}")

        self._id_to_pos[vector_id] = len(self._vectors)
        self._vectors.append(vec)
        self._ids.append(vector_id)
        self._touch()
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
        payload = {
            "format_version": SNAPSHOT_FORMAT_VERSION,
            "algo": "hnsw",
            "dim": self.dim,
            "metric": self.metric,
            "m": self.m,
            "ef_construction": self.ef_construction,
            "node_count": len(self._vectors),
            "index_version": self._index_version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "auto_id": self._auto_id,
            "ids": self._ids,
            "vectors": [vector.tolist() for vector in self._vectors],
        }
        save_index(path, payload)

    @classmethod
    def load(cls, path: str | Path) -> "HNSWIndex":
        payload = load_index(path)
        format_version = payload.get("format_version")
        if format_version != SNAPSHOT_FORMAT_VERSION:
            raise ValueError(
                f"Unsupported snapshot format_version: {format_version}"
            )

        index = cls(
            dim=int(payload["dim"]),
            metric=payload["metric"],
            m=int(payload["m"]),
            ef_construction=int(payload["ef_construction"]),
        )

        raw_ids = payload.get("ids", [])
        raw_vectors = payload.get("vectors", [])
        if len(raw_ids) != len(raw_vectors):
            raise ValueError("Snapshot ids and vectors length mismatch")

        for i, values in enumerate(raw_vectors):
            vector = to_vector(values, dim=index.dim)
            vector_id = raw_ids[i]
            index._id_to_pos[vector_id] = len(index._vectors)
            index._ids.append(vector_id)
            index._vectors.append(vector)

        index._auto_id = int(payload.get("auto_id", len(index._ids)))
        index._index_version = int(payload.get("index_version", len(index._ids)))
        return index

    def __len__(self) -> int:
        return len(self._vectors)
