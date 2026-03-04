import numpy as np
import pytest

from hnsw_core.eval import brute_force_top_k, generate_synthetic_vectors, recall_at_k


def test_generate_synthetic_vectors_is_deterministic() -> None:
    first = generate_synthetic_vectors(num_vectors=4, dim=3, seed=7)
    second = generate_synthetic_vectors(num_vectors=4, dim=3, seed=7)
    assert np.array_equal(first, second)


def test_generate_synthetic_vectors_validates_args() -> None:
    with pytest.raises(ValueError):
        generate_synthetic_vectors(num_vectors=0, dim=3)
    with pytest.raises(ValueError):
        generate_synthetic_vectors(num_vectors=2, dim=0)


def test_brute_force_top_k_orders_by_distance() -> None:
    ids = ["a", "b", "c"]
    vectors = [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]]
    result = brute_force_top_k(
        query=[0.1, 0.0],
        ids=ids,
        vectors=vectors,
        k=2,
        metric="l2",
    )
    assert [r[0] for r in result] == ["a", "b"]


def test_brute_force_top_k_validates_inputs() -> None:
    with pytest.raises(ValueError):
        brute_force_top_k(query=[0.0], ids=[1], vectors=[[0.0]], k=0, metric="l2")
    with pytest.raises(ValueError):
        brute_force_top_k(query=[0.0], ids=[1, 2], vectors=[[0.0]], k=1, metric="l2")


def test_recall_at_k() -> None:
    approx = [1, 3, 2]
    truth = [1, 2, 4]
    assert recall_at_k(approx, truth, k=3) == pytest.approx(2.0 / 3.0)


def test_recall_at_k_validates_k() -> None:
    with pytest.raises(ValueError):
        recall_at_k([1], [1], k=0)
