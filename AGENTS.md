# Repository Guidelines

## Project Structure & Module Organization
This repository is currently in the planning/bootstrap phase.
- `README.md`: product and implementation requirements for a Python HNSW implementation.
- `AGENTS.md`: contributor guide for repository standards.

When adding code, keep the layout explicit and stable:
- `hnsw/`: core implementation (graph, indexing, search, distance functions).
- `tests/`: unit and integration tests.
- `benchmarks/`: performance scripts (insert/search latency, throughput).
- `data/` (optional): small benchmark fixtures and golden recall datasets.

## Build, Test, and Development Commands
Use a Python virtual environment and run tools from the repo root.
- `python -m venv .venv && source .venv/bin/activate`: create and activate env.
- `pip install -r requirements.txt`: install runtime deps.
- `pip install -r requirements-dev.txt`: install lint/test tooling.
- `pytest -q`: run test suite.
- `pytest tests/test_recall.py -q`: run a focused test file.
- `python -m benchmarks.run`: run benchmark entrypoint.

If Make targets are added, mirror the same flows (`make test`, `make bench`, etc.).

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation and type hints on public APIs.
- Prefer small, readable functions over dense micro-optimizations.
- Naming: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants.
- Keep distance/similarity interfaces consistent (e.g., `distance(a, b) -> float`).
- Use `ruff` (lint/format) and keep imports sorted.

## Testing Guidelines
- Framework: `pytest`.
- Test files: `tests/test_<module>.py`.
- Include:
1. correctness tests for insert/search behavior,
2. recall/precision comparisons against brute-force kNN,
3. edge cases (empty index, duplicate vectors, incremental inserts).
- Add deterministic seeds for randomized tests.

## Commit & Pull Request Guidelines
Git history is not available in this workspace, so use Conventional Commits moving forward:
- `feat: add layer-aware greedy search`
- `fix: handle empty index query`
- `test: add recall regression coverage`

PRs should include:
- concise problem/solution summary,
- linked issue or requirement,
- test evidence (`pytest` output and, when relevant, benchmark deltas),
- notes on API or behavior changes.

## Security & Configuration Tips
- Do not commit large datasets, credentials, or generated artifacts.
- Keep benchmark fixtures small and reproducible.
- Prefer environment variables for runtime configuration.
