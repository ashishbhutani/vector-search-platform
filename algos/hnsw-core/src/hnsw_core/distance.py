"""Distance and vector validation helpers for hnsw-core."""

from __future__ import annotations

from typing import Literal, Sequence

import numpy as np

MetricName = Literal["l2", "cosine", "dot"]


def to_vector(values: Sequence[float], dim: int | None = None) -> np.ndarray:
    """Convert a sequence to a float32 vector and validate shape."""
    vector = np.asarray(values, dtype=np.float32)
    if vector.ndim != 1:
        raise ValueError("Vector input must be 1-dimensional")
    if dim is not None and vector.shape[0] != dim:
        raise ValueError(f"Vector dimension mismatch: expected {dim}, got {vector.shape[0]}")
    return vector


def validate_pair(a: np.ndarray, b: np.ndarray) -> None:
    """Validate that two vectors can be compared."""
    if a.ndim != 1 or b.ndim != 1:
        raise ValueError("Distance is defined for 1-dimensional vectors only")
    if a.shape[0] != b.shape[0]:
        raise ValueError("Vector dimension mismatch")


def distance(a: np.ndarray, b: np.ndarray, metric: MetricName) -> float:
    """Compute distance-like score where lower is better."""
    validate_pair(a, b)

    if metric == "l2":
        return float(np.linalg.norm(a - b))

    if metric == "cosine":
        a_norm = float(np.linalg.norm(a))
        b_norm = float(np.linalg.norm(b))
        if a_norm == 0.0 or b_norm == 0.0:
            raise ValueError("Cosine distance is undefined for zero vectors")
        cosine_similarity = float(np.dot(a, b) / (a_norm * b_norm))
        return 1.0 - cosine_similarity

    if metric == "dot":
        return float(-np.dot(a, b))

    raise ValueError(f"Unsupported metric: {metric}")
