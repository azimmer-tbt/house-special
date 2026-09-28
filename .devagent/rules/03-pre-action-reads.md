# Pre-Action Reads and Skills Index

Before any work, look at the file listing first. Then read what the task needs.
Skills are **not** loaded automatically — this table is how you find them. Read
the skill file before doing the task it covers.

## Skills (`.devagent/skills/`)

| Skill | Use when… |
|-------|-----------|
| `autopkg-recipe-development.md` | Writing, fixing or debugging **any** AutoPkg recipe. Always read this first for recipe work, plus `reference/methodology.md`. |
| `first-recipe-interview.md` | A newcomer has one package and wants to be walked through their first recipe, as an interview. |
| `analyze-package.md` | Someone hands you a `.pkg` and asks what it is / which pattern / vendor or in-house. |
| `plan-of-attack.md` | "Analyze these materials", "plan a batch", a folder of vendor files to work through. |
| `compare-packages.md` | Validating a rebuilt package against the one it replaces. |
| `postinstall-as-user.md` | A package must change per-user settings or files (runs as root, acts as the user). |
| `new-customer.md` | Setting up a new org or customer workspace under `customer/<name>/`. |
| `sanitize-check.md` | Before any commit or hand-off; whenever you might have written org or personal data. |
| `recipe-linting.md` | Changing the linter or `config/checks.yaml`; debugging a lint result. |
| `spec-creation.md` | Writing or hardening a spec under `specs/`. |
| `analyze-screenshot.md` | *(Optional; needs a local vision model.)* Reading installer/error screenshots. |

## Always-read documents by task

| Task | Read |
|------|------|
| Any recipe work | `docs/build-your-first-recipe.md` (the walkthrough), `docs/patterns.md`, `reference/methodology.md`, `guardrails/GUARDRAILS.md` |
| Per-package workflow | `specs/method/00-methodology.md`, then rule 11 (sign-off) |
| Changing a tool in `bin/` | its spec folder (index: `specs/README.md`), `CONTRIBUTING.md`, `.devagent/standards/bash-code-standards.md` or `python-code-standards.md` |
| Writing tests | `.devagent/standards/shellspec.md` |
| Customer files | `docs/customer-contract.md`, `docs/FORMATS.md` |
