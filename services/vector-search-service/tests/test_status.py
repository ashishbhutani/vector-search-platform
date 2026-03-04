from pathlib import Path

from fastapi.testclient import TestClient

from hnsw_core import HNSWIndex
from vector_search_service.api import create_app
from vector_search_service.state import ServiceState


def _client() -> TestClient:
    index = HNSWIndex(dim=2)
    index.add([0.0, 0.0], id="a")
    state = ServiceState(index=index, index_version=1)
    return TestClient(create_app(state))


def test_status_endpoint() -> None:
    client = _client()
    response = client.get("/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["index_size"] == 1
    assert payload["index_version"] == 1


def test_query_endpoint() -> None:
    client = _client()
    response = client.post("/query", json={"vector": [0.0, 0.0], "k": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["neighbors"][0]["id"] == "a"


def test_snapshot_endpoint(tmp_path: Path) -> None:
    client = _client()
    out = tmp_path / "service-snapshot.json"
    response = client.post("/snapshot", json={"path": str(out)})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert out.exists()
