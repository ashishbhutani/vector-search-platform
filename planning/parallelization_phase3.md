# Phase 3 Parallelization Plan

## Worktree Ownership
- `wt-p3-replica-core`: `P3-01`
- `wt-p3-gateway`: `P3-02`, `P3-03`
- `wt-p3-consistency`: `P3-04`
- `wt-p3-perf`: `P3-05`
- `wt-p3-ops`: `P3-06`, `P3-07`
- `wt-p3-release`: `P3-08`
- `wt-p3-qa`: `P3-09`

## Parallel Execution Waves

## Wave 0 (foundation)
- `P3-00` must merge first.

## Wave 1 (core HA behavior)
After `P3-00`, run in parallel:
- `P3-01` primary/replica roles
- `P3-03` replica health/failover policy
- `P3-06` metrics/dashboards

## Wave 2 (routing and consistency)
- `P3-02` after `P3-00`, `P3-01`, `P3-03`
- `P3-04` after `P3-00`, `P3-01`
- `P3-07` after `P3-06`

## Wave 3 (perf and release)
- `P3-05` after `P3-02`
- `P3-08` after `P3-05`, `P3-07`

## Wave 4 (final acceptance)
- `P3-09` after `P3-02`, `P3-03`, `P3-04`, `P3-05`, `P3-08`

## Merge Order
1. Merge `P3-00`
2. Merge `P3-01`, `P3-03`, `P3-06`
3. Merge `P3-02`, `P3-04`, `P3-07`
4. Merge `P3-05`
5. Merge `P3-08`
6. Merge `P3-09`

## Conflict Mitigation
- Keep replica role and health logic modular and isolated from query merge paths.
- Separate performance harness changes from runtime service changes.
- Enforce contract freeze from `P3-00` before high-churn distributed work.
