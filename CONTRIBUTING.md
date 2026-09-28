# Contributing

Thanks for improving the toolkit. This file covers how to change the **kit**
(scripts, specs, docs, templates). For packaging apps with it, start at
[`docs/getting-started.md`](docs/getting-started.md).

## Ground rules

1. **Kit files stay org-neutral.** Anything org-specific — identifier prefix,
   package-name prefix, org name — comes from [`config/org.yaml`](config/org.yaml).
   Scripts read it with `read_org_config`; `config/checks.yaml` uses `{{TOKENS}}`
   ([`specs/toolkit/01-toolkit-common.md`](specs/toolkit/01-toolkit-common.md) FR-08).
   Customer data lives only under `customer/<name>/`.
   `tests/kit_hygiene_spec.sh` fails if an org literal appears in script logic.
2. **Shell scripts target stock macOS bash 3.2** (`/bin/bash`): no associative
   arrays, `mapfile`, `${var,,}`, and no `${var//x/y}` with a backslash or `&` in
   the replacement (bash 3.2 and 5.2+ disagree). Stock tools only — `/usr/bin/grep`,
   BSD `sed`/`awk`/`find`.
3. **Python runs on AutoPkg's interpreter**, standard library plus PyYAML only:
   nothing to `pip install`. Use it for anything that reads structured data
   (recipes, plists, bills of materials); keep thin wrappers around system commands
   in bash ([`specs/toolkit/00-constitution.md`](specs/toolkit/00-constitution.md)
   P-7). How to write it:
   [`.devagent/standards/python-code-standards.md`](.devagent/standards/python-code-standards.md).
4. **Spec first.** A new tool or behaviour starts as a spec in its own folder,
   `specs/<family>/` (index: [`specs/README.md`](specs/README.md)):
   `00-constitution.md` for principles, numbered files for requirements with
   `[TESTABLE]` acceptance criteria. See `.devagent/skills/spec-creation.md`.
5. **No confidential data, ever.** Real hostnames, user names, ticket numbers,
   license keys and vendor binaries don't belong in this repository — including in
   test fixtures and sample output.

## Before you commit

```bash
shellspec                                   # the suite runs under /bin/bash 3.2 (.shellspec)
shellcheck -S warning bin/*.sh lib/*.sh     # no new warnings
# Python: black, isort and flake8 (tests/kit_hygiene_spec.sh runs them too)
bin/check-doc-links.sh                      # every doc reference resolves
bin/check-sanitized.sh                      # no leaks (see below)
```

When the Python unit tests fail, `tests/python_unittest_spec.sh` saves the full
verbose run, plus the disk images mounted at that moment, to
`$TMPDIR/house-special-python-tests-<timestamp>.log` and prints its path. Keep it:
the package and DMG tests share the machine, so an intermittent failure is easiest
to explain from that log.

If you changed `config/checks.yaml`, the linter, or a template, also run:

```bash
bin/recipe-linter.sh --repo customer/acme/output --pair-check
```

`tests/examples_lint_spec.sh` already asserts every shipped example lints clean.

## The leak check

`bin/check-sanitized.sh` scans the tree for home-directory paths, ticket numbers,
serial numbers, sync-folder paths, oversized files and stray installers. It also
reads a **denylist** from `.leak-patterns` at the repo root — one extended regex
per line — which is gitignored on purpose: a committed denylist would leak every
name it lists. Keep your own, listing your org's names, employee-ID formats,
internal hostnames and in-house app names.

Install it as a pre-commit hook so staged changes are checked every time:

```bash
bin/check-sanitized.sh --install-hook
```

Forks contributing back upstream: see [`docs/forking.md`](docs/forking.md).

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`,
e.g. `fix(linter): pair check on bash 3.2`. Types: `feat`, `fix`, `docs`,
`refactor`, `test`, `chore`. Scopes are usually a tool or area: `linter`, `batch`,
`analysis`, `pkg-reverse`, `config`, `templates`, `docs`, `acme`, `devagent`.

## Bugs and progress

- Found a toolkit bug? Log the investigation in [`BUGFIX.md`](BUGFIX.md) and, once
  it's understood, add it to [`docs/known-issues.md`](docs/known-issues.md) (or mark
  it fixed there).
- Multi-step work on the kit is tracked in [`PROGRESS.md`](PROGRESS.md).

## Releasing a distribution

```bash
bin/make-dist.sh --tar                  # function only: no tests, specs or customer/
bin/make-dist.sh --tar --with-devagent  # plus the agent rules and skills
```

The build copies, stamps provenance, writes a manifest and smoke-tests the result.
See [`docs/minimal-kit.md`](docs/minimal-kit.md) for what ships.
