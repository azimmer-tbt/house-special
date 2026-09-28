# Toolkit Frontends — Constitution

**Status:** Draft
**Date:** 2026-08-31 (amended 2026-09-27)
**Requires:** none (Level 1)

---

## Purpose

This constitution governs every user-facing entry point in `bin/` and the shared
library they source. It answers "what kind of tool is a toolkit frontend?" — not
what any individual frontend does.

It exists because the toolkit is **standalone**: it is cloned beside an AutoPkg
recipe repo and operates on it from outside. That separation is the source of
every principle below. A frontend that assumes it lives inside the repo it
operates on will appear to work on the author's machine and fail everywhere else.

### Normative vs. Informative Content

- **Normative:** path resolution semantics, precedence order, failure behavior,
  the shell dialect boundary, the Python runtime boundary.
- **Informative:** the specific variable names (`TOOLKIT_ROOT`, `REPO_ROOT`),
  the library filename, and the directory names `bin/` and `lib/`. A conforming
  implementation MAY rename these; it MAY NOT change the semantics.

---

## Principles

### P-1 — Toolkit assets resolve from the script's own location

A frontend MUST locate its own configuration, templates, and reference data
relative to the script file, resolved physically. It MUST NOT locate them
relative to the current working directory, and MUST NOT accept an override for
the toolkit root.

*Rationale:* a bare relative path such as `config/checks.yaml` resolves
correctly only when the caller happens to be standing in the toolkit. That is
the failure this principle exists to eliminate.

**Enforced via:** automated test — invoke each frontend from a directory
unrelated to both the toolkit and any recipe repo; it must still find its config.

### P-2 — Work targets resolve from an explicit repo argument

A frontend that operates on a recipe repo MUST accept that repo as an explicit
argument, and MUST resolve it through the shared resolution routine rather than
implementing its own.

**Enforced via:** reviewer check — any frontend containing its own repo-root
derivation is non-conforming.

### P-3 — The current working directory is never load-bearing

CWD MAY serve as the last fallback in repo resolution, and only when it is
positively identified as a recipe repo. No other behavior may depend on it.

**Enforced via:** automated test — the same command run from three different
directories, with an explicit repo argument, produces identical output.

### P-4 — Ambiguity is a hard error, never a guess

When a frontend cannot determine which repo to operate on, it MUST exit non-zero
with a message naming every available remedy. It MUST NOT fall back to a default
path, the toolkit's own directory, or a partially-matching candidate.

*Rationale:* these tools write files and rebuild packages. Operating on the wrong
tree silently is worse than refusing.

**Enforced via:** automated test — invoke with no repo argument, no environment
variable, and a CWD that is not a repo; assert non-zero exit and that the message
names all supported remedies.

### P-5 — A repo argument that cannot be honored is an error, not a fallback

If an explicitly supplied repo path does not exist or is not a recipe repo, the
frontend MUST fail. It MUST NOT silently fall back to a lower-precedence source.

*Rationale:* falling back means operating on a different tree than the caller
named — the precise failure P-4 exists to prevent, arrived at by another route.

**Enforced via:** automated test — supply a non-existent path and a valid
environment variable; assert failure rather than use of the variable.

### P-6 — Every resolution source must be independently sufficient

Each source in the precedence chain MUST work on its own. Requiring one source
to be present in order for another to be consulted renders the second unusable.

*Rationale:* this is not hypothetical. A frontend once consulted the environment
variable only inside a branch guarded by the explicit argument's presence,
making the variable unreachable in the only situation it existed for.

**Enforced via:** automated test — one case per source, with all other sources
absent.

### P-7 — Two languages, each with a fixed runtime

A frontend is written in **bash** or **Python**, and each has one runtime:

- **Bash** frontends use the system shell's dialect, bash 3.2 (no associative
  arrays, `mapfile` or case-modification expansion), and utilities present on a
  clean macOS install.
- **Python** frontends run on **AutoPkg's bundled interpreter** (toolkit-common
  FR-09) and use only the standard library and PyYAML, both of which ship with
  it. Nothing is installed with `pip`: the kit must work where package downloads
  go through a proxy or mirror, or aren't possible at all.

The kit is only meaningful where AutoPkg is installed, so AutoPkg's Python is
treated as part of the platform. A reviewer or CI job without AutoPkg points
`AUTOPKG_TOOLKIT_PYTHON` at any Python ≥ 3.10 that has PyYAML.

**Which language:** Python for anything that reads structured data (recipe YAML,
plists, bills of materials, CSV, config YAML). Bash for thin wrappers around
system commands, and for tools whose safety rests on being simple enough to read
in one sitting.

*Rationale:* this replaces an earlier "the universal artifact is bash-only" rule.
It existed because Python was believed to need a virtual environment; AutoPkg's
bundled interpreter removes that need. Parsing structured data with `grep` and
`sed` produced whole classes of bugs (KI-3, KI-4, KI-8, KI-23).

**Enforced via:** automated test (`tests/kit_hygiene_spec.sh`: AutoPkg shebang on
every `.py`, no bare `python3` in shell); ShellSpec runs under `/bin/bash`
(`.shellspec`); reviewer check against
`.devagent/standards/python-code-standards.md`.

### P-8 — Tools that cannot be aimed must not accept aim

A frontend whose safety rests on operating only within a fixed, hardcoded
location MUST NOT accept an argument that redirects it. Adding a repo argument
for consistency's sake would remove the property that makes it safe.

**Enforced via:** reviewer check.

### P-9 — Python code lives in the kit's own package, tested with unittest

- Shared Python code lives under `lib/python/` (for example
  `lib/python/recipekit/`). Front ends find it from their own location
  (P-1), never from an installed site-packages.
- Tests use the standard library's `unittest`, live in `tests/python/test_*.py`,
  and run from ShellSpec so `shellspec` stays the single test entry point.

**Enforced via:** automated test (the ShellSpec wrapper runs the unittest suite);
reviewer check.

### P-10 — A port keeps the command

When a frontend moves from bash to Python, its command name, flags, exit codes
and output format stay the same. The new implementation replaces the old one
only after both produce the same results on every recipe and fixture the tests
cover. Documentation and habits don't change because the language did.

**Enforced via:** automated test (parity run of old and new over the same inputs,
kept until the old implementation is removed).

---

## Architecture-Incompatible Patterns

**AIP-01: CWD-relative asset paths.** A bare relative path to a config file,
template, or reference document. Works only from one directory; fails silently
elsewhere by reading a different file or none. **Enforced via:** P-1 test.

**AIP-02: Private repo-root derivation.** A frontend computing its own repo root
— walking up for a marker directory, or assuming a fixed offset from the script.
Each copy drifts and each fails differently. **Enforced via:** P-2 review.

**AIP-03: Guarded fallback.** Consulting a lower-precedence source only inside a
branch conditioned on a higher-precedence one being present. **Enforced via:**
P-6 test.

**AIP-04: Silent default on ambiguity.** Choosing a plausible repo when none was
specified. **Enforced via:** P-4 test.

**AIP-05: Modern bash.** `declare -A`, `mapfile`, `${var,,}` in any bash
frontend. Passes under a Homebrew bash and fails under `/bin/bash`.
**Enforced via:** ShellSpec under `/bin/bash`; P-7 review.

**AIP-06: A Python dependency beyond PyYAML.** Anything that needs `pip install`,
a virtual environment or `requirements.txt` entries beyond PyYAML.
**Enforced via:** P-7 review.

**AIP-07: A bare `python3`.** Calling whichever Python is first on `PATH`
(Apple's has no PyYAML). **Enforced via:** `tests/kit_hygiene_spec.sh`.

**AIP-08: Parsing structured data with text tools.** `grep`/`sed`/`awk` over
YAML, plists or bills of materials in new code. **Enforced via:** P-7 review.

---

## Open Questions

**OQ-1 (resolved 2026-09-27):** P-7's bash dialect is now enforced mechanically:
ShellSpec runs every spec under `/bin/bash` 3.2, so AIP-05 fails a test.

**OQ-2:** Should the repo-marker directory name (`recipes/`) be configurable?
Currently hardcoded in the identification routine. Making it configurable would
weaken P-4, since a mis-set value would make an arbitrary directory resolvable.
Leaning: keep it fixed.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-08-31 | Initial release. Principles derived from the existing implementation and from the guarded-fallback defect that motivated P-6. |
| 1.1 | 2026-09-27 | P-7 rewritten: bash 3.2 or AutoPkg's Python (stdlib + PyYAML), replacing "bash-only". Added P-9 (Python layout and unittest), P-10 (a port keeps the command), AIP-06 to AIP-08. OQ-1 resolved. |
