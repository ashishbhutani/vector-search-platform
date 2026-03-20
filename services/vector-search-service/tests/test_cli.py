import argparse
import json
from pathlib import Path
from typing import Any

from hnsw_core import HNSWIndex
from vector_search_service.cli import build_parser, command_build, command_serve
from vector_search_service.routing import BroadcastAllRouter, RouterConfig


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")


def test_build_command_creates_snapshot(tmp_path: Path) -> None:
    vectors_file = tmp_path / "vectors.jsonl"
    _write_jsonl(
        vectors_file,
        [
            {"id": "a", "vector": [0.0, 0.0]},
            {"id": "b", "vector": [1.0, 0.0]},
        ],
    )

    out_path = tmp_path / "index.json"
    args = argparse.Namespace(
        vectors_dir=str(vectors_file),
        out=str(out_path),
        metric="l2",
        dim=2,
        m=16,
        ef_construction=200,
    )

    code = command_build(args)
    assert code == 0
    assert out_path.exists()

    index = HNSWIndex.load(out_path)
    assert len(index) == 2
    assert index.search([0.0, 0.0], k=1)[0][0] == "a"


def test_build_parser_has_expected_subcommands() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["build", "--vectors-dir", "./x", "--out", "./y", "--dim", "2"]
    )
    assert args.command == "build"


def test_build_requires_jsonl_files(tmp_path: Path) -> None:
    args = argparse.Namespace(
        vectors_dir=str(tmp_path),
        out=str(tmp_path / "index.json"),
        metric="l2",
        dim=2,
        m=16,
        ef_construction=200,
    )

    try:
        command_build(args)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_serve_command_wires_router_config(tmp_path: Path, monkeypatch: Any) -> None:
    snapshot_path = tmp_path / "index.json"
    index = HNSWIndex(dim=2)
    index.add([0.0, 0.0], id="a")
    index.save(snapshot_path)

    captured: dict[str, Any] = {}

    def fake_create_router(config: RouterConfig) -> BroadcastAllRouter:
        captured["router_config"] = config
        return BroadcastAllRouter()

    def fake_uvicorn_run(app: Any, host: str, port: int) -> None:
        captured["app"] = app
        captured["host"] = host
        captured["port"] = port

    monkeypatch.setattr("vector_search_service.cli.create_router", fake_create_router)
    monkeypatch.setattr("vector_search_service.cli.uvicorn.run", fake_uvicorn_run)

    args = argparse.Namespace(
        index=str(snapshot_path),
        host="127.0.0.1",
        port=8123,
        queue_db=str(tmp_path / "ingest.db"),
        runtime_role="shard_node",
        shard_id="shard-1",
        shard_map_path=None,
        gateway_timeout_ms=750,
        router_strategy="broadcast_all",
        router_semantic_top_n=4,
        router_semantic_bootstrap_path=str(tmp_path / "lsh.json"),
    )
    code = command_serve(args)
    assert code == 0
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8123
    assert captured["router_config"] == RouterConfig(
        strategy="broadcast_all",
        semantic_top_n=4,
        semantic_bootstrap_path=str(tmp_path / "lsh.json"),
    )
    assert isinstance(captured["app"].state.shard_router, BroadcastAllRouter)
