import numpy as np
import pytest

from hnsw_core.distance import distance, to_vector


def test_l2_orders_closer_vectors_lower() -> None:
    base = np.array([0.0, 0.0], dtype=np.float32)
    near = np.array([1.0, 0.0], dtype=np.float32)
    far = np.array([3.0, 0.0], dtype=np.float32)
    assert distance(base, near, "l2") < distance(base, far, "l2")


def test_cosine_orders_closer_vectors_lower() -> None:
    base = np.array([1.0, 0.0], dtype=np.float32)
    aligned = np.array([2.0, 0.0], dtype=np.float32)
    orthogonal = np.array([0.0, 1.0], dtype=np.float32)
    assert distance(base, aligned, "cosine") < distance(base, orthogonal, "cosine")


def test_dot_uses_negative_dot_score() -> None:
    base = np.array([1.0, 0.0], dtype=np.float32)
    better = np.array([2.0, 0.0], dtype=np.float32)
    worse = np.array([0.5, 0.0], dtype=np.float32)
    assert distance(base, better, "dot") < distance(base, worse, "dot")


def test_to_vector_dim_validation() -> None:
    with pytest.raises(ValueError):
        to_vector([1.0, 2.0], dim=3)


def test_dimension_mismatch_raises() -> None:
    a = np.array([1.0, 2.0], dtype=np.float32)
    b = np.array([1.0], dtype=np.float32)
    with pytest.raises(ValueError):
        distance(a, b, "l2")


def test_cosine_zero_vector_raises() -> None:
    a = np.array([0.0, 0.0], dtype=np.float32)
    b = np.array([1.0, 0.0], dtype=np.float32)
    with pytest.raises(ValueError):
        distance(a, b, "cosine")
