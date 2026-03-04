# Phase 1 Parallelization Plan

## Worktree Ownership
- `wt-core`: `P1-01`, `P1-02`, `P1-03`
- `wt-service-api`: `P1-04`
- `wt-service-ingest`: `P1-05`
- `wt-cli`: `P1-07`
- `wt-qa`: `P1-06`, `P1-08`, `P1-09`

## Parallel Execution Waves

## Wave 0 (foundation)
- `P1-00` must merge first. It freezes contracts and package skeleton.

## Wave 1 (parallel build)
These can run concurrently after `P1-00`:
- `P1-01` core engine
- `P1-02` metrics and validation
- `P1-03` serialization
- `P1-04` API scaffold query status
- `P1-05` queue worker jobs API
- `P1-06` QA harness

## Wave 2 (dependent integration)
- `P1-07` CLI begins after `P1-01`, `P1-03`, `P1-04`, `P1-05`.
- `P1-08` E2E begins after `P1-04`, `P1-05`, `P1-06`, `P1-07`.
- `P1-09` Bench begins after stable implementations of `P1-01`, `P1-04`, `P1-05`.

## Merge Order
1. Merge `P1-00`
2. Merge core/service foundations: `P1-01`, `P1-02`, `P1-03`, `P1-04`, `P1-05`
3. Merge `P1-07`
4. Merge `P1-06`
5. Merge `P1-08`
6. Merge `P1-09`

## Conflict Mitigation
- Keep ownership boundaries strict by directory.
- Treat contracts as immutable after `P1-00` unless explicit RFC is approved.
- Rebase each worktree daily onto main during active development.
