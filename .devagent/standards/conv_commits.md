---
name: conventional-commits
description: How to write commit messages in this repository (Conventional Commits 1.0.0), with this repo's types and scopes. Use when composing any commit message.
---

# Conventional Commits

This repository follows [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).
The full specification is on that site; this is the part you need day to day.

## Format

```
<type>(<scope>): <summary in the imperative, no trailing period>

<optional body: what changed and why, wrapped at ~72 columns>

<optional footers, e.g. BREAKING CHANGE: …  or  Refs: KI-14>
```

- **type** — what kind of change (below).
- **scope** — which part of the repo (below). Optional, but use one when it fits.
- **summary** — ≤ 72 characters, lower-case start, says what the commit does.
- **Breaking changes** — add `!` after the type/scope (`feat(config)!: …`) and a
  `BREAKING CHANGE:` footer explaining the migration. Anything that changes
  `config/org.yaml` keys, `config/checks.yaml` semantics, or a front end's flags or
  exit codes is breaking for forks.

## Types

| Type | Use for |
|------|---------|
| `feat` | A new capability (tool, flag, rule, template, example) |
| `fix` | A bug fix |
| `docs` | Documentation only |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or fixing tests only |
| `chore` | Maintenance: moves, renames, housekeeping |
| `perf`, `style`, `build`, `ci` | As in the specification |

## Scopes in this repository

`linter`, `batch`, `analysis`, `pkg-reverse`, `vendor-drop`, `config`, `lib`,
`bin` (several tools), `templates`, `guardrails`, `specs`, `docs`, `reference`,
`tests`, `acme` (the example customer), `devagent`, `dist`.

## Examples

```
feat(linter): accept pinned versions in VER-001 via exists_any
fix(analysis): expand payload with pkgutil --expand-full
docs(acme): document the Fruit screensaver install flow
refactor(bin)!: read identifier prefix from config/org.yaml

BREAKING CHANGE: forks must set identifier_prefix and pkgname_prefix in
config/org.yaml; the hard-coded prefix is gone.
```
