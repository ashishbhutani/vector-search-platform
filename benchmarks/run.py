"""Benchmark runner for build, query, and ingest flows."""

from __future__ import annotations

import argparse
import json
import time
from statistics import median

import numpy as np

from hnsw_core import HNSWIndex
from hnsw_core.eval import generate_synthetic_vectors


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(np.percentile(np.asarray(values, dtype=np.float64), 95))


def benchmark_build(num_vectors: int, dim: int, metric: str) -> dict[str, float]:
    vectors = generate_synthetic_vectors(num_vectors=num_vectors, dim=dim, seed=42)
    index = HNSWIndex(dim=dim, metric=metric)

    start = time.perf_counter()
    for i, vector in enumerate(vectors):
        index.add(vector.tolist(), id=i)
    duration = time.perf_counter() - start

    return {
        "num_vectors": float(num_vectors),
        "build_seconds": duration,
        "build_vectors_per_sec": (num_vectors / duration) if duration > 0 else 0.0,
    }


def benchmark_query(
    num_vectors: int,
    num_queries: int,
    dim: int,
    metric: str,
    k: int,
) -> dict[str, float]:
    vectors = generate_synthetic_vectors(num_vectors=num_vectors, dim=dim, seed=42)
    queries = generate_synthetic_vectors(num_vectors=num_queries, dim=dim, seed=7)

    index = HNSWIndex(dim=dim, metric=metric)
    index.add_batch([v.tolist() for v in vectors], ids=list(range(num_vectors)))

    latencies: list[float] = []
    for query in queries:
        start = time.perf_counter()
        index.search(query.tolist(), k=k)
        latencies.append(time.perf_counter() - start)

    return {
        "num_queries": float(num_queries),
        "query_p50_ms": median(latencies) * 1000.0,
        "query_p95_ms": _p95(latencies) * 1000.0,
    }


def benchmark_ingest(
    initial_vectors: int,
    ingest_vectors: int,
    dim: int,
    metric: str,
) -> dict[str, float]:
    base = generate_synthetic_vectors(num_vectors=initial_vectors, dim=dim, seed=42)
    ingest = generate_synthetic_vectors(num_vectors=ingest_vectors, dim=dim, seed=99)

    index = HNSWIndex(dim=dim, metric=metric)
    index.add_batch([v.tolist() for v in base], ids=list(range(initial_vectors)))

    start = time.perf_counter()
    index.add_batch(
        [v.tolist() for v in ingest],
        ids=list(range(initial_vectors, initial_vectors + ingest_vectors)),
    )
    duration = time.perf_counter() - start

    return {
        "ingest_vectors": float(ingest_vectors),
        "ingest_seconds": duration,
        "ingest_vectors_per_sec": (ingest_vectors / duration) if duration > 0 else 0.0,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m benchmarks.run")
    parser.add_argument("--num-vectors", type=int, default=5000)
    parser.add_argument("--num-queries", type=int, default=200)
    parser.add_argument("--ingest-vectors", type=int, default=1000)
    parser.add_argument("--dim", type=int, default=64)
    parser.add_argument("--metric", choices=["l2", "cosine", "dot"], default="l2")
    parser.add_argument("--k", type=int, default=10)
    return parser


def main() -> None:
    args = build_parser().parse_args()

    report = {
        "build": benchmark_build(args.num_vectors, args.dim, args.metric),
        "query": benchmark_query(
            args.num_vectors,
            args.num_queries,
            args.dim,
            args.metric,
            args.k,
        ),
        "ingest": benchmark_ingest(
            args.num_vectors,
            args.ingest_vectors,
            args.dim,
            args.metric,
        ),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
