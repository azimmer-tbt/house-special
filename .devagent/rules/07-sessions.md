# Sessions

For recipe work on a customer, keep a session log so the next session (human or
agent) can pick up where this one stopped.

- **Where:** `customer/<name>/sessions/session-NNN-<short-topic>.md` — `NNN` is the
  next number in that folder. These logs are gitignored: they routinely contain
  hostnames, user names and ticket numbers.
- **When:** create it at the start of a working session; update it as you go;
  finish it before you stop.
- **Kit development** (work on `bin/`, `specs/`, docs) uses `PROGRESS.md` and
  `BUGFIX.md` instead (rules 05, 06).

## Template

```markdown
# Session NNN — <short title>

**Date:** YYYY-MM-DD · **Customer:** <name> · **Operator:** <who>

## Objective
<what this session is for>

## Log
- HH:MM <what was done, command run, result>

## Decisions
- <decision> — <why>

## Next steps
- [ ] <next action>
```

Anything durable — a lesson, a recipe design decision — belongs in the recipe's
`README.md`, the customer's `plans/`, or `reference/methodology.md`, not only in a
session log.
