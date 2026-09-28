# PROGRESS.md — Progress Tracking

`PROGRESS.md` tracks multi-step work on **the kit itself**. Update it as tasks
are completed; each entry may annotate the spec it relates to. Per-customer recipe
progress lives in `customer/<name>/autopkg-recipes.csv` instead.

## Template

```markdown
# Progress Tracking — [Project/Phase Title]

**Last Updated:** YYYY-MM-DD
**Objective:** [Short description of what this round covers]

---

## Summary

| Component | Items | Status |
|-----------|-------|--------|
| [e.g., Linter] | [count] | ⬜ Not Started / 🟡 In Progress / ✅ Complete |
| [e.g., Batch Creator] | [count] | ⬜ Not Started / 🟡 In Progress / ✅ Complete |

---

## [Component Name]

**Spec ref:** specs/recipe-linter/00-constitution.md

### [Sub-section / Feature]

- [ ] Task description — Spec: specs/recipe-linter/01-rule-definitions.md §"section"
- [ ] Another task

---

## Verification

- [ ] All tests pass (shellspec)
- [ ] shellcheck clean
- [ ] bin/check-doc-links.sh and bin/check-sanitized.sh clean
```

## Guidelines
- Update checkboxes as items are completed
- Use spec annotations (Spec: ... §"section") to anchor progress to specs
- Mark verification items only after successful validation
