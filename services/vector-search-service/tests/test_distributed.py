from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from hnsw_core import HNSWIndex
from vector_search_service.api import create_app
from vector_search_service.cluster import ShardHealthRegistry, ShardMapEntry
from vector_search_service.routing import RouterConfig, create_router
from vector_search_service.state import ServiceState


class FakeShardClient:
    def __init__(self) -> None:
        self.query_payloads: list[tuple[str, dict[str, object]]] = []
        self.ingest_payloads: list[tuple[str, dict[str, object]]] = []
        self.health: dict[str, bool] = {}
        self.query_responses: dict[str, dict[str, object]] = {}
        self.ingest_responses: dict[str, dict[str, object]] = {}
        self.query_fail_urls: set[str] = set()
        self.ingest_fail_urls: set[str] = set()

    def query_shard(
        self,
        base_url: str,
        payload: dict[str, object],
        *,
        timeout_sec: float | None = None,
    ) -> dict[str, object]:
        del timeout_sec
        self.query_payloads.append((base_url, payload))
        if base_url in self.query_fail_urls:
            raise TimeoutError("query timeout")
        return self.query_responses[base_url]

    def ingest_shard(self, base_url: str, payload: dict[str, object]) -> dict[str, object]:
        self.ingest_payloads.append((base_url, payload))
        if base_url in self.ingest_fail_urls:
            raise TimeoutError("ingest timeout")
        fallback_queued = 0
        vectors = payload.get("vectors")
        if isinstance(vectors, list):
            fallback_queued = len(vectors)
        return self.ingest_responses.get(
            base_url,
            {"job_id": f"job-{base_url}", "queued": fallback_queued},
        )

    def is_healthy(self, base_url: str, *, timeout_sec: float | None = None) -> bool:
        del timeout_sec
        return self.health.get(base_url, True)


def _gateway_client(tmp_path: Path, fake_client: FakeShardClient) -> TestClient:
    index = HNSWIndex(dim=2)
    shard_map = [
        ShardMapEntry(shard_id="shard-a", base_url="http://shard-a"),
        ShardMapEntry(shard_id="shard-b", base_url="http://shard-b"),
        ShardMapEntry(shard_id="shard-c", base_url="http://shard-c"),
    ]
    health = ShardHealthRegistry()
    for entry in shard_map:
        health.set_state(entry.shard_id, "healthy")

    state = ServiceState(
        index=index,
        index_version=1,
        shard_router=create_router(RouterConfig(strategy="broadcast_all")),
        router_config=RouterConfig(strategy="broadcast_all"),
        runtime_role="gateway",
        shard_id="gateway-1",
        shard_map=shard_map,
        health_registry=health,
        shard_client=fake_client,
        gateway_timeout_sec=0.2,
    )
    app = create_app(state, queue_db_path=str(tmp_path / "ingest.db"), start_worker=False)
    return TestClient(app)


def test_gateway_query_merges_top_k_across_shards(tmp_path: Path) -> None:
    fake = FakeShardClient()
    fake.query_responses = {
        "http://shard-a": {
            "neighbors": [{"id": "a1", "score": 0.40}],
            "index_version": 10,
            "partial_results": False,
            "shard_id": "shard-a",
        },
        "http://shard-b": {
            "neighbors": [{"id": "b1", "score": 0.10}],
            "index_version": 11,
            "partial_results": False,
            "shard_id": "shard-b",
        },
        "http://shard-c": {
            "neighbors": [{"id": "c1", "score": 0.20}],
            "index_version": 9,
            "partial_results": False,
            "shard_id": "shard-c",
        },
    }
    client = _gateway_client(tmp_path, fake)

    response = client.post("/query", json={"vector": [0.0, 0.0], "k": 2})
    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["neighbors"]] == ["b1", "c1"]
    assert payload["index_version"] == 11
    assert payload["partial_results"] is False


def test_gateway_query_sets_partial_results_on_shard_failure(tmp_path: Path) -> None:
    fake = FakeShardClient()
    fake.query_responses = {
        "http://shard-a": {"neighbors": [{"id": "a1", "score": 0.3}], "index_version": 1},
        "http://shard-b": {"neighbors": [{"id": "b1", "score": 0.2}], "index_version": 1},
        "http://shard-c": {"neighbors": [{"id": "c1", "score": 0.1}], "index_version": 1},
    }
    fake.query_fail_urls.add("http://shard-c")
    client = _gateway_client(tmp_path, fake)

    response = client.post("/query", json={"vector": [0.0, 0.0], "k": 5})
    assert response.status_code == 200
    payload = response.json()
    assert payload["partial_results"] is True
    assert [item["id"] for item in payload["neighbors"]] == ["b1", "a1"]


def test_gateway_query_returns_empty_when_all_shards_fail(tmp_path: Path) -> None:
    fake = FakeShardClient()
    fake.query_responses = {
        "http://shard-a": {"neighbors": [{"id": "a1", "score": 0.3}], "index_version": 1},
        "http://shard-b": {"neighbors": [{"id": "b1", "score": 0.2}], "index_version": 1},
        "http://shard-c": {"neighbors": [{"id": "c1", "score": 0.1}], "index_version": 1},
    }
    fake.query_fail_urls = {"http://shard-a", "http://shard-b", "http://shard-c"}
    client = _gateway_client(tmp_path, fake)

    response = client.post("/query", json={"vector": [0.0, 0.0], "k": 5})
    assert response.status_code == 200
    payload = response.json()
    assert payload["neighbors"] == []
    assert payload["partial_results"] is True


def test_gateway_routes_only_to_healthy_shards(tmp_path: Path) -> None:
    fake = FakeShardClient()
    fake.query_responses = {
        "http://shard-a": {"neighbors": [{"id": "a1", "score": 0.3}], "index_version": 1},
        "http://shard-b": {"neighbors": [{"id": "b1", "score": 0.2}], "index_version": 1},
    }
    fake.health = {"http://shard-a": True, "http://shard-b": True, "http://shard-c": False}
    client = _gateway_client(tmp_path, fake)

    response = client.post("/query", json={"vector": [0.0, 0.0], "k": 5})
    assert response.status_code == 200
    target_urls = [url for url, _ in fake.query_payloads]
    assert "http://shard-c" not in target_urls


def test_gateway_ingest_forwards_to_selected_shards(tmp_path: Path) -> None:
    fake = FakeShardClient()
    client = _gateway_client(tmp_path, fake)

    response = client.post(
        "/vectors",
        json={
            "vectors": [
                {"id": "tenant-a:doc-1", "vector": [0.1, 0.1]},
                {"id": "tenant-b:doc-2", "vector": [0.2, 0.2]},
                {"id": "tenant-c:doc-3", "vector": [0.3, 0.3]},
            ]
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["queued"] == 3
    assert payload["job_id"].startswith("gw-")
