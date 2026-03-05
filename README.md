# vector-search-platform

Agent-first development for a vector search system.

## Operating Model
- Coding and execution are done by agents.
- Product insight, architecture, and design decisions are made by humans.
- Humans define direction; agents implement against approved plans.

## How We Work
1. Human and agent discuss scope, tradeoffs, and architecture.
2. Agent drafts a phase-wise plan.
3. Agent exports dependency-aware work items (Jira-style tickets).
4. Work is executed phase by phase, with clear acceptance criteria.

## Current Direction
- Build a multi-algorithm vector search service.
- Start with `hnsw-core` as the first ANN algorithm.
- Expose a serving layer that can evolve from single-node to distributed scatter-gather.

## Architecture
- `algos/hnsw-core`: algorithm package with vector distance functions, index API, and snapshot serialization.
- `services/vector-search-service`: service package with HTTP API and CLI surface.
- `planning/`: execution artifacts (phase plans, Jira-style tickets, dependencies, trackers).

## Planning Docs
- Reusable planning/orchestration toolkit (external repo): [agent-project-os](https://github.com/ashishbhutani/agent-project-os)
- PRD: [docs/PRD.md](https://github.com/ashishbhutani/vector-search-platform/blob/main/docs/PRD.md)
- Contracts: [docs/architecture/contracts.md](https://github.com/ashishbhutani/vector-search-platform/blob/main/docs/architecture/contracts.md)
- Agent handoff: [planning/agent_handoff.md](https://github.com/ashishbhutani/vector-search-platform/blob/main/planning/agent_handoff.md)
- Tracking guide: [planning/tracking_guide.md](https://github.com/ashishbhutani/vector-search-platform/blob/main/planning/tracking_guide.md)
- Phase 1 tickets: [planning/jira_phase1.csv](https://github.com/ashishbhutani/vector-search-platform/blob/main/planning/jira_phase1.csv)
- Phase 1 dependencies: [planning/jira_phase1_dependencies.csv](https://github.com/ashishbhutani/vector-search-platform/blob/main/planning/jira_phase1_dependencies.csv)
- Phase 1 tracker: [planning/jira_phase1_tracker.csv](https://github.com/ashishbhutani/vector-search-platform/blob/main/planning/jira_phase1_tracker.csv)
- Phase 2 tickets: [planning/jira_phase2.csv](https://github.com/ashishbhutani/vector-search-platform/blob/main/planning/jira_phase2.csv)
- Phase 2 dependencies: [planning/jira_phase2_dependencies.csv](https://github.com/ashishbhutani/vector-search-platform/blob/main/planning/jira_phase2_dependencies.csv)
- Phase 2 tracker: [planning/jira_phase2_tracker.csv](https://github.com/ashishbhutani/vector-search-platform/blob/main/planning/jira_phase2_tracker.csv)
- Phase 3 tickets: [planning/jira_phase3.csv](https://github.com/ashishbhutani/vector-search-platform/blob/main/planning/jira_phase3.csv)
- Phase 3 dependencies: [planning/jira_phase3_dependencies.csv](https://github.com/ashishbhutani/vector-search-platform/blob/main/planning/jira_phase3_dependencies.csv)
- Phase 3 tracker: [planning/jira_phase3_tracker.csv](https://github.com/ashishbhutani/vector-search-platform/blob/main/planning/jira_phase3_tracker.csv)
- Phase 1 parallelization: [planning/parallelization.md](https://github.com/ashishbhutani/vector-search-platform/blob/main/planning/parallelization.md)
- Phase 2 parallelization: [planning/parallelization_phase2.md](https://github.com/ashishbhutani/vector-search-platform/blob/main/planning/parallelization_phase2.md)
- Phase 3 parallelization: [planning/parallelization_phase3.md](https://github.com/ashishbhutani/vector-search-platform/blob/main/planning/parallelization_phase3.md)

### Index Lifecycle (current and planned)
1. **Offline bootstrap build**
- Vectors are read from files (planned JSONL input) and used to build an index before serving.
- Initial index artifact is saved as a snapshot.

2. **Serve from prebuilt index**
- Service starts by loading the snapshot into memory.
- Queries run against the in-memory index for low-latency search.

3. **Live vector addition while serving**
- New vectors are added without full rebuild.
- Visibility model is async/eventual in service mode: searchable once ingestion job is applied.
- Single-node local API scaffolding is already in place; queued ingestion pipeline is the next ticketed step.

4. **Snapshot behavior**
- **Current:** manual snapshot endpoint and core save/load are implemented.
- **Planned:** periodic checkpointing and explicit snapshot command, including post-ingest state persistence.
- **Future distributed:** shard-level snapshots plus coordinated restore flows.

### Runtime Model (current)
- In-process index (`HNSWIndex`) is loaded by the service.
- HTTP API includes `status`, `query`, and `snapshot` scaffolding.
- Full distributed scatter-gather mode is planned in later phases.

### Distributed Architecture Decisions (planned)
- Sharding is strategy-based and configurable.
  - `hash_tenant_or_doc`
  - `hash_vector_id`
  - `semantic_lsh` (initial semantic strategy)
- Routing interface is explicit:
  - `route_for_ingest(...)` decides vector placement shard.
  - `route_for_query(...)` decides shard fanout for reads.
- Query execution follows scatter-gather.
  - Gateway/combiner fans out to shard nodes.
  - Shards run ANN independently.
  - Combiner merges shard top-k into global top-k.
- Fanout modes:
  - baseline `broadcast_all`
  - semantic `top_n` shard groups
- Replication direction:
  - target model is primary + read replicas per shard.
  - writes go to primary; reads can be replica-aware in later phase.

## Current Capabilities
- Add/search/search_batch support through `hnsw-core` API.
- Metrics: `l2`, `cosine`, `dot` (distance-like scoring).
- Snapshot save/load with metadata and format-version checks.
- Basic service state + API tests for status/query/snapshot flow.
- Phase-based tracker system for multi-agent execution.

## Principles
- Keep implementation clean and readable.
- Prioritize correctness, tests, and reproducibility.
- Make contracts explicit before parallel execution.

## References
- HNSW paper: https://arxiv.org/pdf/1603.09320
- Practical explainer: https://www.pinecone.io/learn/series/faiss/hnsw/
