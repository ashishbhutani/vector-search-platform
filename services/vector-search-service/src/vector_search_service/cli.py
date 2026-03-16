"""CLI for vector-search-service."""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path
from typing import Any

import uvicorn

from hnsw_core import HNSWIndex

from .api import create_app
from .routing import RouterConfig, create_router
from .state import ServiceState


def _read_jsonl_file(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise ValueError(f"Invalid JSONL record in {path}")
        records.append(parsed)
    return records


def _load_vectors_from_path(path: Path) -> list[dict[str, Any]]:
    if path.is_file():
        files = [path]
    else:
        files = sorted(path.glob("*.jsonl"))
    if not files:
        raise ValueError(f"No JSONL files found at {path}")

    records: list[dict[str, Any]] = []
    for file_path in files:
        records.extend(_read_jsonl_file(file_path))
    return records


def _request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url=url, method=method, data=data)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:  # nosec B310 - controlled by CLI input
        body = resp.read().decode("utf-8")
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise ValueError("Server response is not a JSON object")
    return parsed


def command_build(args: argparse.Namespace) -> int:
    vectors_path = Path(args.vectors_dir)
    records = _load_vectors_from_path(vectors_path)

    index = HNSWIndex(
        dim=args.dim,
        metric=args.metric,
        m=args.m,
        ef_construction=args.ef_construction,
    )

    for record in records:
        if "vector" not in record:
            raise ValueError("Each record must include 'vector'")
        index.add(record["vector"], id=record.get("id"))

    index.save(args.out)
    print(f"built index: {args.out} nodes={len(index)} metric={args.metric}")
    return 0


def command_serve(args: argparse.Namespace) -> int:
    index = HNSWIndex.load(args.index)
    index_version = int(getattr(index, "_index_version", len(index)))
    router_config = RouterConfig(
        strategy=args.router_strategy,
        semantic_top_n=args.router_semantic_top_n,
        semantic_bootstrap_path=args.router_semantic_bootstrap_path,
    )
    state = ServiceState(
        index=index,
        index_version=index_version,
        shard_router=create_router(router_config),
        router_config=router_config,
    )
    app = create_app(state, queue_db_path=args.queue_db, start_worker=True)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def command_add(args: argparse.Namespace) -> int:
    records = _load_vectors_from_path(Path(args.input))
    payload = {"vectors": records}
    response = _request_json("POST", f"{args.server.rstrip('/')}/vectors", payload)
    print(json.dumps(response))
    return 0


def command_status(args: argparse.Namespace) -> int:
    response = _request_json("GET", f"{args.server.rstrip('/')}/status")
    print(json.dumps(response))
    return 0


def command_snapshot(args: argparse.Namespace) -> int:
    response = _request_json(
        "POST",
        f"{args.server.rstrip('/')}/snapshot",
        {"path": args.out},
    )
    print(json.dumps(response))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vss")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build")
    build.add_argument("--vectors-dir", required=True)
    build.add_argument("--out", required=True)
    build.add_argument("--metric", choices=["l2", "cosine", "dot"], default="l2")
    build.add_argument("--dim", required=True, type=int)
    build.add_argument("--m", type=int, default=16)
    build.add_argument("--ef-construction", type=int, default=200)
    build.set_defaults(func=command_build)

    serve = sub.add_parser("serve")
    serve.add_argument("--index", required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", default=8000, type=int)
    serve.add_argument("--queue-db", default="/tmp/vss-ingest.db")
    serve.add_argument(
        "--router-strategy",
        default="broadcast_all",
        choices=[
            "broadcast_all",
            "hash_tenant_or_doc",
            "hash_vector_id",
            "semantic_lsh",
        ],
    )
    serve.add_argument("--router-semantic-top-n", default=2, type=int)
    serve.add_argument("--router-semantic-bootstrap-path", default=None)
    serve.set_defaults(func=command_serve)

    add = sub.add_parser("add")
    add.add_argument("--server", required=True)
    add.add_argument("--input", required=True)
    add.set_defaults(func=command_add)

    status = sub.add_parser("status")
    status.add_argument("--server", required=True)
    status.set_defaults(func=command_status)

    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("--server", required=True)
    snapshot.add_argument("--out", required=True)
    snapshot.set_defaults(func=command_snapshot)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    exit_code = args.func(args)
    raise SystemExit(exit_code)
