from vector_search_service.models import QueryRequest, VectorRecord
from vector_search_service.routing import (
    BroadcastAllRouter,
    HashTenantOrDocRouter,
    HashVectorIdRouter,
    RouterConfig,
    create_router,
)


def test_create_router_returns_broadcast_router() -> None:
    router = create_router(RouterConfig(strategy="broadcast_all"))
    assert isinstance(router, BroadcastAllRouter)


def test_create_router_returns_hash_routers() -> None:
    tenant_router = create_router(RouterConfig(strategy="hash_tenant_or_doc"))
    vector_router = create_router(RouterConfig(strategy="hash_vector_id"))
    assert isinstance(tenant_router, HashTenantOrDocRouter)
    assert isinstance(vector_router, HashVectorIdRouter)


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


def test_semantic_lsh_strategy_is_not_implemented() -> None:
    router = create_router(RouterConfig(strategy="semantic_lsh"))
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


def test_hash_vector_id_router_is_deterministic() -> None:
    router = create_router(RouterConfig(strategy="hash_vector_id"))
    record = VectorRecord(id="vec-123", vector=[0.1, 0.2])

    first = router.route_for_ingest(record=record, shard_count=16)
    second = router.route_for_ingest(record=record, shard_count=16)

    assert first == second
    assert first.startswith("shard-")


def test_hash_tenant_or_doc_keeps_same_tenant_on_same_shard() -> None:
    router = create_router(RouterConfig(strategy="hash_tenant_or_doc"))
    record_a = VectorRecord(id="tenant-a:doc-1", vector=[0.1, 0.2])
    record_b = VectorRecord(id="tenant-a:doc-2", vector=[0.2, 0.3])

    shard_a = router.route_for_ingest(record=record_a, shard_count=16)
    shard_b = router.route_for_ingest(record=record_b, shard_count=16)

    assert shard_a == shard_b


def test_hash_routers_query_fanout_targets_all_shards() -> None:
    query = QueryRequest(vector=[0.1, 0.2], k=3)
    shard_ids = ["s1", "s2", "s3"]
    tenant_router = create_router(RouterConfig(strategy="hash_tenant_or_doc"))
    vector_router = create_router(RouterConfig(strategy="hash_vector_id"))

    assert tenant_router.route_for_query(query=query, shard_ids=shard_ids) == shard_ids
    assert vector_router.route_for_query(query=query, shard_ids=shard_ids) == shard_ids
