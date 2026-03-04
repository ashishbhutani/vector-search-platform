import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

from hnsw_core import HNSWIndex
from vector_search_service.api import create_app
from vector_search_service.cli import command_build
from vector_search_service.state import ServiceState


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")


def test_build_load_serve_ingest_visibility_e2e(tmp_path: Path) -> None:
    vectors_file = tmp_path / "bootstrap.jsonl"
    _write_jsonl(vectors_file, [{"id": "a", "vector": [0.0, 0.0]}])

    snapshot = tmp_path / "index.json"
    build_args = argparse.Namespace(
        vectors_dir=str(vectors_file),
        out=str(snapshot),
        metric="l2",
        dim=2,
        m=16,
        ef_construction=200,
    )
    assert command_build(build_args) == 0

    index = HNSWIndex.load(snapshot)
    state = ServiceState(index=index, index_version=int(getattr(index, "_index_version", len(index))))
    app = create_app(state, queue_db_path=str(tmp_path / "ingest.db"), start_worker=False)
    client = TestClient(app)

    bootstrap_query = client.post("/query", json={"vector": [0.0, 0.0], "k": 1})
    assert bootstrap_query.status_code == 200
    assert bootstrap_query.json()["neighbors"][0]["id"] == "a"

    enqueue = client.post(
        "/vectors",
        json={"vectors": [{"id": "b", "vector": [0.1, 0.0]}]},
    )
    assert enqueue.status_code == 200
    job_id = enqueue.json()["job_id"]

    before = client.get(f"/jobs/{job_id}")
    assert before.status_code == 200
    assert before.json()["status"] == "queued"

    client.app.state.ingest_worker.run_once()

    after = client.get(f"/jobs/{job_id}")
    assert after.status_code == 200
    assert after.json()["status"] == "done"

    visible_query = client.post("/query", json={"vector": [0.1, 0.0], "k": 1})
    assert visible_query.status_code == 200
    assert visible_query.json()["neighbors"][0]["id"] == "b"
