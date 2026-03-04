"""Evaluation utilities for ANN quality validation."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .distance import MetricName, distance, to_vector
from .types import VectorId, VectorLike


def generate_synthetic_vectors(num_vectors: int, dim: int, seed: int = 42) -> np.ndarray:
    """Generate deterministic synthetic vectors for tests/benchmarks."""
    if num_vectors <= 0:
        raise ValueError("num_vectors must be > 0")
    if dim <= 0:
        raise ValueError("dim must be > 0")
    rng = np.random.default_rng(seed)
    return rng.normal(loc=0.0, scale=1.0, size=(num_vectors, dim)).astype(np.float32)


def brute_force_top_k(
    query: VectorLike,
    ids: Sequence[VectorId],
    vectors: Sequence[VectorLike],
    k: int,
    metric: MetricName,
) -> list[tuple[VectorId, float]]:
    """Compute exact top-k neighbors by exhaustive scan."""
    if k <= 0:
        raise ValueError("k must be > 0")
    if len(ids) != len(vectors):
        raise ValueError("ids and vectors length mismatch")
    if not vectors:
        raise ValueError("vectors must not be empty")

    q = to_vector(query)
    scored: list[tuple[VectorId, float]] = []
    for idx, values in enumerate(vectors):
        vec = to_vector(values, dim=q.shape[0])
        scored.append((ids[idx], distance(q, vec, metric)))

    scored.sort(key=lambda item: item[1])
    return scored[: min(k, len(scored))]


def recall_at_k(
    approx_neighbors: Sequence[VectorId],
    true_neighbors: Sequence[VectorId],
    k: int,
) -> float:
    """Compute recall@k based on neighbor id overlap."""
    if k <= 0:
        raise ValueError("k must be > 0")

    approx_top = list(approx_neighbors[:k])
    true_top = list(true_neighbors[:k])
    if not true_top:
        return 0.0

    overlap = len(set(approx_top) & set(true_top))
    return overlap / float(len(true_top))
