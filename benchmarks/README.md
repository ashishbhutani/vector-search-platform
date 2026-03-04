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
