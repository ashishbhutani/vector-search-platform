# Contracts: hnsw-core and vector-search-service

## 1. `hnsw-core` Public API

## Class
`HNSWIndex(dim: int, metric: Literal["l2", "cosine", "dot"] = "l2", m: int = 16, ef_construction: int = 200, ef_search: int = 50, random_seed: int = 42)`

## Methods
- `add(vector: ArrayLike, id: str | int | None = None) -> str | int`
- `add_batch(vectors: ArrayLike, ids: Sequence[str | int] | None = None) -> list[str | int]`
- `search(query: ArrayLike, k: int, ef_search: int | None = None) -> list[tuple[str | int, float]]`
- `search_batch(queries: ArrayLike, k: int, ef_search: int | None = None) -> list[list[tuple[str | int, float]]]`
- `save(path: str) -> None`
- `load(path: str) -> HNSWIndex` (classmethod or module-level loader)
- `__len__() -> int`

## Behavioral Guarantees
- Score semantics are distance-like (lower is better) for all metrics.
- For `dot`, use `-dot(a, b)` internally to preserve ordering semantics.
- Dimension mismatch raises `ValueError`.
- `k > n` returns up to `n` neighbors.

## 2. HTTP API Contracts (`vector-search-service`)

## `POST /query`
### Request
```json
{
  "vector": [0.1, 0.2, 0.3],
  "k": 10,
  "ef_search": 64
}
```

### Response
```json
{
  "neighbors": [{ "id": "vec-1", "score": 0.123 }],
  "index_version": 42,
  "partial_results": false
}
```

## `POST /vectors`
### Request
```json
{
  "vectors": [
    { "id": "vec-100", "vector": [0.4, 0.5, 0.6] }
  ]
}
```

### Response
```json
{
  "job_id": "job-abc-123",
  "queued": 1
}
```

## `GET /jobs/{job_id}`
### Response
```json
{
  "job_id": "job-abc-123",
  "status": "queued",
  "applied": 0,
  "error": null,
  "created_at": "2026-03-04T00:00:00Z",
  "updated_at": "2026-03-04T00:00:01Z"
}
```

## `GET /status`
### Response
```json
{
  "index_size": 100000,
  "index_version": 42,
  "queue_depth": 3,
  "worker": "healthy",
  "last_checkpoint_at": "2026-03-04T00:10:00Z"
}
```

## `POST /snapshot`
### Request
```json
{
  "path": "snapshots/hnsw-2026-03-04.bin"
}
```

### Response
```json
{
  "ok": true,
  "path": "snapshots/hnsw-2026-03-04.bin",
  "index_version": 42
}
```

## 3. CLI Contracts
- `vss build --vectors-dir <dir> --out <index_path> --metric <l2|cosine|dot> --dim <int> [--m <int>] [--ef-construction <int>]`
- `vss serve --index <index_path> --host <host> --port <port> [--checkpoint-interval-sec <int>]`
- `vss add --server <url> --input <jsonl_file>`
- `vss status --server <url>`
- `vss snapshot --server <url> --out <index_path>`

## 4. Queue and Consistency Contract
- Ingestion is asynchronous and queued (SQLite-backed).
- Visibility is eventual: vectors are queryable only when job status is `done`.
- Single writer mutates index in worker; concurrent queries are allowed.

## 5. Snapshot Metadata Contract
Snapshot header fields:
- `format_version` (int)
- `algo` (`"hnsw"`)
- `dim` (int)
- `metric` (`"l2" | "cosine" | "dot"`)
- `m` (int)
- `ef_construction` (int)
- `node_count` (int)
- `index_version` (int)
- `created_at` (RFC3339 UTC)

## Compatibility Rule
- Reader must reject unsupported `format_version` with actionable error.
