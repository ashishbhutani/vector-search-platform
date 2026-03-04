# Agent Handoff Package (Phase 1)

## Purpose
This document is the standard brief for any orchestrator or human running parallel Phase 1 delivery.

## Fixed Inputs
- PRD: `docs/PRD.md`
- API and lifecycle contracts: `docs/architecture/contracts.md`
- Jira list: `planning/jira_phase1.csv`
- Dependency graph: `planning/jira_phase1_dependencies.csv`
- Parallel plan: `planning/parallelization.md`

## Rules for All Agents
- Do not change frozen contracts from `P1-00` without a tracked contract-change ticket.
- Stay within assigned ticket scope and ownership boundaries.
- Add tests for all behavior changes.
- Keep implementation readable over micro-optimizations.

## Standard Agent Prompt Template
Use this template for each assigned ticket:

"Implement `<TICKET_KEY>` from `planning/jira_phase1.csv`.
Follow contracts in `docs/architecture/contracts.md`.
Respect dependencies in `planning/jira_phase1_dependencies.csv`.
Do not modify unrelated modules.
Deliver code + tests + short change summary + known risks."

## Gate Checks Before Merge
- Ticket acceptance criteria satisfied.
- Tests pass locally and in CI.
- No contract drift from `P1-00`.
- Changelog/notes updated where needed.

## Example Assignment Split (4 agents)
- Agent A: `P1-01`, `P1-02`, `P1-03`
- Agent B: `P1-04`, `P1-07`
- Agent C: `P1-05`
- Agent D: `P1-06`, `P1-08`, `P1-09`
