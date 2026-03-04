from fastapi.testclient import TestClient

from vector_search_service.api import create_app


def test_status_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/status")
    assert response.status_code == 200
