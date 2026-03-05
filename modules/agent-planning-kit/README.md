# Agent Planning Kit (Reusable Module)

Reusable planning and execution kit for multi-agent software delivery.

## Goals
- Keep planning artifacts consistent across projects.
- Enable deterministic ticket claiming in parallel agent loops.
- Provide export-ready templates, prompts, and scripts.

## Contents
- `templates/`: generic CSV/Markdown templates for tasks, dependencies, trackers, and handoff.
- `prompts/`: reusable planning/execution prompts for agents.
- `scripts/`: claim/validate automation and phase bootstrap helper.

## Deterministic Parallel Claiming
Use:
- `scripts/validate_dependencies.py` to list ready tickets, validate readiness, and claim next ticket.
- `scripts/claim_next_ticket.sh` as a thin wrapper for claim-next.

Race handling:
1. file lock (`fcntl.flock`) around claim operation,
2. deterministic selection (`lexicographically smallest ready key`),
3. atomic tracker write (`tmp file + os.replace`).

## Quick Start
```bash
# 1) Bootstrap phase files
python3 modules/agent-planning-kit/scripts/bootstrap_phase.py --phase P2 --out planning

# 2) Check ready tickets
python3 modules/agent-planning-kit/scripts/validate_dependencies.py \
  --tracker planning/jira_phase2_tracker.csv \
  --dependencies planning/jira_phase2_dependencies.csv \
  --list-ready

# 3) Claim next ticket (deterministic)
modules/agent-planning-kit/scripts/claim_next_ticket.sh agent-1 \
  planning/jira_phase2_tracker.csv \
  planning/jira_phase2_dependencies.csv \
  planning/.claim.lock
```

## Export Guidance
This directory is intentionally self-contained. To export into a separate repo later:
1. Copy `modules/agent-planning-kit` as-is.
2. Keep script entrypoints unchanged.
3. Optional: add a package/release wrapper around this folder.
