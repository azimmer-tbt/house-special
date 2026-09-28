# Minimal kit — what a distribution build contains

`bin/make-dist.sh` builds a **function-only** copy of the toolkit: everything a team
needs to author, lint and build recipes, and none of the development scaffolding.
It copies; it never rewrites. This page describes the result so you can check it.

```bash
bin/make-dist.sh --tar                   # dist/house-special/ + .tar.gz
bin/make-dist.sh --out /path/to/kit      # somewhere else
bin/make-dist.sh --with-devagent         # + agent rules, skills, .clinerules, .roo/rules
bin/make-dist.sh --with-wiki             # + offline AutoPkg wiki mirror
```

## What ships

| Path | What it is |
|------|------------|
| `bin/` | Every front end except `make-dist.sh` itself |
| `lib/toolkit-common.sh` | Shared library every front end sources |
| `config/` | `checks.yaml` (lint rules), `org.yaml` (**your naming — edit this**), `paths.yaml`, `screenshot-analyzer.yaml` |
| `guardrails/` | Task framing, checklist, and the `audit/` checks `bin/autopkg-preflight.py` runs |
| `templates/` | One template per pattern, most with a worked example; see [`templates/README.md`](../templates/README.md) |
| `docs/` | User documentation (this folder) |
| `reference/methodology.md` | Lessons from real recipe runs — read before writing a new recipe shape |
| `reference/recipe-standards.md` | The standard the linter and templates implement |
| `README.md`, `LICENSE`, `NOTICE`, `CONTRIBUTING.md`, `requirements.txt` | |
| `PROVENANCE.md` | Written by the build: source commit, branch, dirty flag, options |
| `manifest.sha256` | Checksums of every shipped file; verify with `shasum -a 256 -c manifest.sha256` |

With `--with-devagent`: `.devagent/`, `.clinerules`, `.roo/rules` (symlink
dereferenced into a real directory) and `AGENT_GREETING.md`.
With `--with-wiki`: `reference/autopkg-wiki/`.

## What doesn't ship

| Left out | Why |
|----------|-----|
| `tests/`, `specs/` | Development of the kit, not use of it. Docs that link into `specs/` point at the source repository. |
| `customer/` | The Acme worked example and every customer workspace. A team starts its own (see [`customer-contract.md`](customer-contract.md)). |
| `BUGFIX.md`, `PROGRESS.md` | Kit development logs |
| `bin/make-dist.sh` | A dist that can re-dist itself invites confusion about which copy is canonical |
| Virtualenvs, `.leak-patterns`, `dist/`, `.git/` | Machine-local or history |

## How the build checks itself

The smoke test fails the build if:

- any `bin/` front end has lost its exec bit (it is **not** `chmod`ed back — a
  missing bit here means it is missing in the source too);
- `recipe-linter.sh --list-rules`, or `--help` on the analysis tools, fails in the copy
  (a runtime file missing from the allowlist);
- the shipped linter doesn't pass a shipped template example
  (`templates/pattern-4-vendor-drop/example-Xerox-Drivers`);
- `docs/` is empty;
- the manifest doesn't cover every shipped file.

## Checking a delivered kit

```bash
cd house-special
shasum -a 256 -c manifest.sha256 | grep -v ': OK$'   # prints nothing when intact
cat PROVENANCE.md                                     # which commit you have
bin/recipe-linter.sh --list-rules | head -5           # org naming is filled in from config/org.yaml
```
