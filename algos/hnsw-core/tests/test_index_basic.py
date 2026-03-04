import pytest

from hnsw_core import HNSWIndex


def test_add_and_len() -> None:
    index = HNSWIndex(dim=2)
    assert len(index) == 0
    first_id = index.add([0.0, 0.0])
    assert first_id == 0
    assert len(index) == 1


def test_add_batch_with_ids() -> None:
    index = HNSWIndex(dim=2)
    ids = index.add_batch([[0.0, 0.0], [1.0, 1.0]], ids=["a", "b"])
    assert ids == ["a", "b"]
    assert len(index) == 2


def test_duplicate_ids_raise() -> None:
    index = HNSWIndex(dim=2)
    index.add([0.0, 0.0], id="dup")
    with pytest.raises(ValueError):
        index.add([1.0, 1.0], id="dup")


def test_search_returns_sorted_results() -> None:
    index = HNSWIndex(dim=2, metric="l2")
    index.add([0.0, 0.0], id="origin")
    index.add([2.0, 0.0], id="far")
    index.add([1.0, 0.0], id="mid")

    result = index.search([0.0, 0.0], k=2)
    assert [item[0] for item in result] == ["origin", "mid"]


def test_search_empty_index_raises() -> None:
    index = HNSWIndex(dim=2)
    with pytest.raises(ValueError):
        index.search([0.0, 0.0], k=1)


def test_search_k_bounds() -> None:
    index = HNSWIndex(dim=2)
    index.add([0.0, 0.0], id=1)
    index.add([1.0, 1.0], id=2)
    assert len(index.search([0.0, 0.0], k=10)) == 2


def test_search_batch() -> None:
    index = HNSWIndex(dim=2)
    index.add_batch([[0.0, 0.0], [1.0, 1.0]], ids=[1, 2])
    results = index.search_batch([[0.0, 0.0], [1.0, 1.0]], k=1)
    assert len(results) == 2
    assert results[0][0][0] == 1
    assert results[1][0][0] == 2
