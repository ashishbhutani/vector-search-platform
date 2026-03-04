from hnsw_core import HNSWIndex


def test_contract_instantiation() -> None:
    index = HNSWIndex(dim=3)
    assert index.dim == 3
