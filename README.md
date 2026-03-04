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

## Principles
- Keep implementation clean and readable.
- Prioritize correctness, tests, and reproducibility.
- Make contracts explicit before parallel execution.

## References
- HNSW paper: https://arxiv.org/pdf/1603.09320
- Practical explainer: https://www.pinecone.io/learn/series/faiss/hnsw/
