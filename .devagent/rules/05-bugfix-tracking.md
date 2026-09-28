# BUGFIX.md — Bug Tracking

`BUGFIX.md` tracks bugs, errors, anomalies and unexpected behavior in **the kit
itself** (scripts, specs, tests, docs), logged with the template below. Once an
issue is understood, summarise it in `docs/known-issues.md` (or mark it fixed
there) — that list is what users read.

Problems with one customer's recipes belong in that customer's
`customer/<name>/sessions/` log or the recipe's `README.md`, not here.

## Issue Template

```markdown
### Issue #XXX — [Short Description]

**Date:** YYYY-MM-DD
**Severity:** Critical | High | Medium | Low
**Status:** Open | In Progress | Resolved | Deferred

**Context:**
- Tool: [linter/batch/docs/etc.]
- Spec ref: [specs/recipe-linter/NN-name.md §"section"]

**Problem:**
[Brief description of what happened]

**Steps to Reproduce:**
1. [Step 1]
2. [Step 2]

**Error Message / Evidence:**
```
[paste error output]
```

**Root Cause Analysis:**
[What went wrong]

**Resolution:**
[How it was fixed]

**Prevention:**
[How to prevent recurrence]
```

## Severity Definitions
- **Critical:** Blocks all progress, requires immediate operator intervention
- **High:** Blocks progress on a component, requires fix before proceeding
- **Medium:** Non-blocking anomaly that should be addressed but work can continue
- **Low:** Cosmetic issue, documentation fix, or minor inefficiency

## Status Definitions
- **Open:** Issue identified, not yet analyzed
- **In Progress:** Root cause analysis in progress or fix in development
- **Resolved:** Fix implemented and verified, issue can be closed
- **Deferred:** Issue acknowledged, resolution deferred to later round

## When to log
- On any tooling failure (linter, batch creator, spec validator)
- On any unexpected behavior discovered during development
- On any spec-AC mismatch discovered during testing
