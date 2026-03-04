# Task Tracking Guide (Multi-Agent)

Use Jira as the system of record, and keep these CSV tracker files in git for agent automation and handoff.

## When is a ticket "done"?
A ticket is done only if all of the following are true:
- `Status=done`
- `PRURL` is present
- `MergeCommit` is present
- `Tests=pass`
- `DocsUpdated=yes` (or `n/a`)

## Tracker Fields
- `Status`: `todo | ready | in_progress | blocked | in_review | done`
- `BlockedBy`: comma-separated ticket keys this ticket depends on
- `Assignee`: agent name or owner
- `Worktree`: assigned git worktree
- `Branch`: working branch
- `PRURL`: pull request link
- `MergeCommit`: merged commit SHA
- `Tests`: `pending | pass | fail`
- `DocsUpdated`: `yes | no | n/a`
- `LastUpdatedUTC`: ISO-8601 timestamp
- `Notes`: short status note

## Dependency Rule
A ticket is `ready` only when all tickets in `BlockedBy` are `done`.

## Update Cadence
- Update tracker on every state change.
- Minimum once daily for in-progress tickets.
- Update `LastUpdatedUTC` every change.
