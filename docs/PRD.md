# PRD: Vector Search Service (HNSW First)

## 1. Document Control
- Version: v1.0
- Status: Execution Ready
- Owner: Search Platform
- Last Updated: 2026-03-04

## 2. Product Goal
Build a production-oriented vector search service with pluggable ANN algorithms.
Start with HNSW as `hnsw-core`, then evolve to distributed scatter-gather search.

## 3. Scope and Non-Goals
### In Scope
- Monorepo split into algorithm library and serving system.
- Single-node service with async ingest and ANN serving.
- Distributed scaffolding with shard router and gateway fanout.

### Non-Goals (current program)
- Delete/update semantics beyond add-only ingest.
- Metadata filtering.
- Online shard rebalancing.
- Learned router model training/serving.

## 4. Personas
- API consumer service needing ANN query endpoint.
- Platform engineer operating shard nodes and gateway.
- ML/data engineer bootstrapping index from offline vectors.

## 5. Success Metrics
- Correctness: recall@10 >= 0.90 vs brute-force baseline.
- Reliability: partial shard failures return bounded/flagged results.
- Performance: measurable p50/p95 query latency and ingest throughput.
- Operability: snapshot + restore works consistently.

## 6. Architecture Overview
### Repository Layout
- `algos/hnsw-core`: pure ANN library.
- `services/vector-search-service`: CLI + HTTP + ingest queue + runtime orchestration.

### Distribution-Ready Interfaces
- `ShardRouter.route_for_ingest(...)`
- `ShardRouter.route_for_query(...)`

### Query Path
- Single-node mode: local HNSW.
- Distributed mode: gateway fans out to shards, merges global top-k.

## 7. Phase Plan

## Phase 0: Planning and Contract Freeze
### Objective
Make implementation parallelizable and low-risk by freezing interfaces, dependencies, and work ownership.

### Deliverables
- `docs/PRD.md`
- `docs/architecture/contracts.md`
- `planning/jira_phase1.csv`
- `planning/jira_phase1_dependencies.csv`
- `planning/parallelization.md`
- `planning/agent_handoff.md`

### Exit Criteria
- Public contracts are versioned and unambiguous.
- Jira import files include stable task IDs and dependency edges.
- Parallelization map includes merge order and ownership boundaries.

## Phase 1: Single-Node Foundation
### Scope
- `hnsw-core`: add/search/batch, metrics, serialization.
- `vector-search-service`: `build`, `serve`, `add`, `status`, `snapshot` CLI + HTTP APIs.
- SQLite queue + async worker + job lifecycle.
- JSONL vector input format.

### Exit Criteria
- Build index from JSONL and save snapshot.
- Serve ANN from loaded snapshot.
- Runtime adds become searchable after job state `done`.
- Snapshot/restart preserves applied vectors.
- Recall@10 regression gate passes.

## Phase 2: Distributed Scaffolding
### Scope
- Add gateway + shard-node roles.
- Add routing strategies: `hash_tenant_or_doc`, `hash_vector_id`, `semantic_lsh`.
- Default fanout: broadcast-all.
- Optional semantic fanout: top-N shard groups (default N=2).

### Exit Criteria
- Multi-node local deployment works.
- Gateway returns merged top-k across shards.
- Partial failure handling returns `partial_results=true`.

## Phase 3: Distributed Hardening
### Scope
- Primary + read-replica model.
- Replica-aware query routing.
- Performance hardening and runbooks.

### Exit Criteria
- Stable distributed operation under load.
- Replica behavior validated.
- Production runbook complete.

## 8. API Contracts (v1 Stable)
- Query request: `{ "vector": [...], "k": int, "ef_search": int? }`
- Query response: `{ "neighbors": [{"id":"...","score":float}], "index_version": int, "partial_results": bool? }`
- Ingest request: `{ "vectors": [{"id":"...", "vector":[...]}] }`
- Job status: `queued|running|done|failed`

## 9. Risks and Mitigations
- Write/read race conditions: single-writer mutation discipline + explicit job states.
- Shard hotspotting: pluggable routers + shard skew monitoring.
- Early distributed complexity: enforce phase gates.

## 10. Running Checklist (per ticket)
- Spec complete
- Implementation in progress
- Code review passed
- Tests green
- Performance validated (if applicable)
- Docs/runbook updated
- Done
