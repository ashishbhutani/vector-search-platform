"""Distributed gateway benchmark runner."""

from __future__ import annotations

import argparse
import json
from statistics import median
import time
import urllib.request

import numpy as np


def _request_json(
    method: str,
    url: str,
    payload: dict[str, object] | None = None,
    *,
    timeout_sec: float = 2.0,
) -> dict[str, object]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url=url, method=method, data=data)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:  # nosec B310
        parsed = json.loads(resp.read().decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("benchmark request expected JSON object response")
    return parsed


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(np.percentile(np.asarray(values, dtype=np.float64), 95))


def _run_gateway_query_benchmark(
    *,
    gateway_url: str,
    num_queries: int,
    dim: int,
    k: int,
    ef_search: int | None,
    timeout_sec: float,
    seed: int,
) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    vectors = rng.random((num_queries, dim), dtype=np.float64)

    latencies: list[float] = []
    partial_count = 0
    errors = 0
    start = time.perf_counter()
    for vector in vectors:
        payload: dict[str, object] = {"vector": vector.tolist(), "k": k}
        if ef_search is not None:
            payload["ef_search"] = ef_search
        t0 = time.perf_counter()
        try:
            response = _request_json(
                "POST",
                f"{gateway_url.rstrip('/')}/query",
                payload,
                timeout_sec=timeout_sec,
            )
        except Exception:
            errors += 1
            continue
        latencies.append(time.perf_counter() - t0)
        if bool(response.get("partial_results", False)):
            partial_count += 1
    duration = time.perf_counter() - start
    successful = len(latencies)
    throughput = (successful / duration) if duration > 0 else 0.0
    partial_rate = (partial_count / successful) if successful > 0 else 0.0

    return {
        "num_queries": float(num_queries),
        "successful_queries": float(successful),
        "query_errors": float(errors),
        "query_p50_ms": median(latencies) * 1000.0 if latencies else 0.0,
        "query_p95_ms": _p95(latencies) * 1000.0,
        "throughput_qps": throughput,
        "partial_results_rate": partial_rate,
    }


def _fanout_report(
    *,
    gateway_url: str,
    strategy: str,
    semantic_top_n: int,
    timeout_sec: float,
) -> dict[str, float]:
    status = _request_json("GET", f"{gateway_url.rstrip('/')}/status", timeout_sec=timeout_sec)
    shard_count = int(status.get("gateway_shard_count", 0))
    healthy_count = int(status.get("gateway_healthy_shard_count", shard_count))

    if strategy == "semantic_lsh":
        estimated_target = min(healthy_count, semantic_top_n)
    else:
        estimated_target = healthy_count

    return {
        "configured_shard_count": float(shard_count),
        "healthy_shard_count": float(healthy_count),
        "estimated_target_fanout": float(estimated_target),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m benchmarks.distributed_run")
    parser.add_argument("--gateway-url", required=True)
    parser.add_argument("--num-queries", type=int, default=500)
    parser.add_argument("--dim", type=int, default=64)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--ef-search", type=int, default=None)
    parser.add_argument("--timeout-sec", type=float, default=2.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--strategy",
        choices=["broadcast_all", "hash_tenant_or_doc", "hash_vector_id", "semantic_lsh"],
        default="broadcast_all",
    )
    parser.add_argument("--semantic-top-n", type=int, default=2)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    fanout = _fanout_report(
        gateway_url=args.gateway_url,
        strategy=args.strategy,
        semantic_top_n=args.semantic_top_n,
        timeout_sec=args.timeout_sec,
    )
    query = _run_gateway_query_benchmark(
        gateway_url=args.gateway_url,
        num_queries=args.num_queries,
        dim=args.dim,
        k=args.k,
        ef_search=args.ef_search,
        timeout_sec=args.timeout_sec,
        seed=args.seed,
    )
    report = {
        "gateway_url": args.gateway_url,
        "strategy": args.strategy,
        "fanout": fanout,
        "query": query,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
