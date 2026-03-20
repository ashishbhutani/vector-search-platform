# Benchmarks

Run from repo root:

```bash
PYTHONPATH=algos/hnsw-core/src python3 -m benchmarks.run
```

Example with custom sizes:

```bash
PYTHONPATH=algos/hnsw-core/src python3 -m benchmarks.run --num-vectors 10000 --num-queries 500 --ingest-vectors 2000 --dim 128 --metric l2 --k 10
```

Output is JSON with:
- `build`: total time and throughput for index construction
- `query`: p50/p95 query latency
- `ingest`: batch ingest time and throughput

## Distributed Gateway Benchmark

Run against a running gateway service:

```bash
PYTHONPATH=algos/hnsw-core/src python3 -m benchmarks.distributed_run --gateway-url http://127.0.0.1:8000 --num-queries 1000 --dim 64 --k 10 --strategy broadcast_all
```

Output includes:
- `query.query_p50_ms`, `query.query_p95_ms`
- `query.throughput_qps`
- `query.partial_results_rate`
- `fanout.configured_shard_count`, `fanout.healthy_shard_count`, `fanout.estimated_target_fanout`
