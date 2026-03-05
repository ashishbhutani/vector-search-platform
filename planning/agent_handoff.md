# Agent Handoff Package

## Purpose
This is the standard brief for orchestrators or humans running parallel delivery.

## Fixed Inputs
- PRD: `docs/PRD.md`
- Contracts: `docs/architecture/contracts.md`
- Tracking guide: `planning/tracking_guide.md`

## Phase 1 Files
- Ticket list: `planning/jira_phase1.csv`
- Dependencies: `planning/jira_phase1_dependencies.csv`
- Tracker: `planning/jira_phase1_tracker.csv`
- Parallelization plan: `planning/parallelization.md`

## Phase 2 Files
- Ticket list: `planning/jira_phase2.csv`
- Dependencies: `planning/jira_phase2_dependencies.csv`
- Tracker: `planning/jira_phase2_tracker.csv`
- Parallelization plan: `planning/parallelization_phase2.md`

## Phase 3 Files
- Ticket list: `planning/jira_phase3.csv`
- Dependencies: `planning/jira_phase3_dependencies.csv`
- Tracker: `planning/jira_phase3_tracker.csv`
- Parallelization plan: `planning/parallelization_phase3.md`

## Rules for All Agents
- Do not change frozen contracts without a dedicated contract-change ticket.
- Stay within assigned ticket scope and ownership boundaries.
- Add tests for all behavior changes.
- Keep implementation readable over micro-optimizations.
- Update tracker CSV status on every state change.

## Standard Agent Prompt Template
"Implement `<TICKET_KEY>` from the phase ticket CSV.
Follow contracts in `docs/architecture/contracts.md`.
Respect dependency edges from `<phase>_dependencies.csv`.
Update `<phase>_tracker.csv` for status transitions.
Do not modify unrelated modules.
Deliver code + tests + short change summary + known risks."

## Gate Checks Before Merge
- Acceptance criteria satisfied.
- Tests pass locally and in CI.
- No contract drift.
- Tracker fields updated (`Status`, `PRURL`, `MergeCommit`, `Tests`).
