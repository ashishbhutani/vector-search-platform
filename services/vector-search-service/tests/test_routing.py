from vector_search_service.models import QueryRequest, VectorRecord
from vector_search_service.routing import (
    BroadcastAllRouter,
    RouterConfig,
    create_router,
)


def test_create_router_returns_broadcast_router() -> None:
    router = create_router(RouterConfig(strategy="broadcast_all"))
    assert isinstance(router, BroadcastAllRouter)


def test_broadcast_router_query_targets_all_shards() -> None:
    router = BroadcastAllRouter()
    shard_ids = ["s1", "s2", "s3"]
    query = QueryRequest(vector=[0.1, 0.2], k=2)

    query_targets = router.route_for_query(query=query, shard_ids=shard_ids)
    assert query_targets == shard_ids


def test_broadcast_router_ingest_is_single_shard_and_deterministic() -> None:
    router = BroadcastAllRouter()
    record = VectorRecord(id="doc-1", vector=[0.1, 0.2])

    first = router.route_for_ingest(record=record, shard_count=8)
    second = router.route_for_ingest(record=record, shard_count=8)

    assert first == second
    assert first.startswith("shard-")


def test_create_router_rejects_unknown_strategy() -> None:
    try:
        create_router(RouterConfig(strategy="unknown"))
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Unsupported routing strategy" in str(exc)


def test_create_router_marks_future_strategies_not_implemented() -> None:
    router = create_router(RouterConfig(strategy="hash_vector_id"))
    try:
        router.route_for_ingest(
            record=VectorRecord(id="doc-1", vector=[0.1, 0.2]),
            shard_count=4,
        )
        assert False, "expected NotImplementedError"
    except NotImplementedError as exc:
        assert "is not implemented yet" in str(exc)


def test_broadcast_router_ingest_requires_positive_shard_count() -> None:
    router = BroadcastAllRouter()
    record = VectorRecord(id="doc-1", vector=[0.1, 0.2])

    try:
        router.route_for_ingest(record=record, shard_count=0)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "shard_count must be > 0" in str(exc)
