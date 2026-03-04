# Phase 2 Parallelization Plan

## Worktree Ownership
- `wt-dist-router`: `P2-01`, `P2-02`, `P2-03`
- `wt-dist-shard`: `P2-05`
- `wt-dist-gateway`: `P2-04`, `P2-06`
- `wt-dist-qa`: `P2-07`, `P2-08`, `P2-09`

## Parallel Execution Waves

## Wave 0 (foundation)
- `P2-00` must merge first.

## Wave 1 (parallel build)
After `P2-00`, run in parallel:
- `P2-01` router interface/config
- `P2-05` shard node mode
- `P2-06` shard map/health registry

## Wave 2 (strategy and gateway)
- `P2-02` and `P2-03` after `P2-01`
- `P2-04` after `P2-00`, `P2-01`, `P2-05`, `P2-06`

## Wave 3 (validation)
- `P2-07` after `P2-02`, `P2-03`, `P2-04`, `P2-05`, `P2-06`
- `P2-08` after `P2-04`, `P2-07`
- `P2-09` after `P2-04`, `P2-07`

## Merge Order
1. Merge `P2-00`
2. Merge `P2-01`, `P2-05`, `P2-06`
3. Merge `P2-02`, `P2-03`, `P2-04`
4. Merge `P2-07`
5. Merge `P2-08`, `P2-09`

## Conflict Mitigation
- Keep router logic in dedicated strategy modules.
- Keep gateway code separate from shard node runtime code.
- Do not modify shared contracts without explicit contract-change ticket.
