from pathlib import Path

from fastapi.testclient import TestClient

from hnsw_core import HNSWIndex
from vector_search_service.api import create_app
from vector_search_service.state import ServiceState


def _client(tmp_path: Path) -> TestClient:
    index = HNSWIndex(dim=2)
    index.add([0.0, 0.0], id="a")
    state = ServiceState(index=index, index_version=1)
    db_path = tmp_path / "ingest.db"
    return TestClient(create_app(state, queue_db_path=str(db_path), start_worker=False))


def test_status_endpoint(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.get("/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["index_size"] == 1
    assert payload["index_version"] == 1
    assert payload["routing_strategy"] == "broadcast_all"
    assert payload["runtime_role"] == "shard_node"
    assert payload["shard_id"] == "shard-0"


def test_query_endpoint(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post("/query", json={"vector": [0.0, 0.0], "k": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["neighbors"][0]["id"] == "a"


def test_snapshot_endpoint(tmp_path: Path) -> None:
    client = _client(tmp_path)
    out = tmp_path / "service-snapshot.json"
    response = client.post("/snapshot", json={"path": str(out)})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert out.exists()


def test_ingest_job_lifecycle_and_visibility(tmp_path: Path) -> None:
    client = _client(tmp_path)

    enqueue = client.post(
        "/vectors",
        json={"vectors": [{"id": "b", "vector": [0.1, 0.0]}]},
    )
    assert enqueue.status_code == 200
    job_id = enqueue.json()["job_id"]

    queued = client.get(f"/jobs/{job_id}")
    assert queued.status_code == 200
    assert queued.json()["status"] == "queued"

    client.app.state.ingest_worker.run_once()

    done = client.get(f"/jobs/{job_id}")
    assert done.status_code == 200
    assert done.json()["status"] == "done"
    assert done.json()["applied"] == 1

    query = client.post("/query", json={"vector": [0.1, 0.0], "k": 1})
    assert query.status_code == 200
    assert query.json()["neighbors"][0]["id"] == "b"
