# make-dist.sh — build a function-only distribution of the kit

**Status:** Draft
**Date:** 2026-09-27
**Requires:** `specs/toolkit/00-constitution.md`, `specs/toolkit/01-toolkit-common.md`, `specs/manifest/01-manifest.md`
**Implementation:** `bin/make-dist.sh`

---

## Purpose

`make-dist.sh` builds a copy of House Special that a team can use without the
kit's development scaffolding: no tests, no specs, no worked customer example,
no git history. It copies an allowlist of paths into a new directory, writes a
`PROVENANCE.md` and a `manifest.sha256`, runs a smoke test on the copy, and can
also pack the copy into a `.tar.gz`.

It copies. It never rewrites, reconfigures or templates what it copies.

This spec closes KI-12 ("unspecified shipped components") for the distribution
build: it states exactly what a dist contains and what it leaves out. The
user-facing summary of the same content is `docs/minimal-kit.md`. Where the two
disagree, this spec wins and the doc is corrected.

### In scope

- The command line: `--out`, `--with-wiki`, `--with-devagent`, `--tar`, `-h`/`--help`.
- What is copied, what is excluded, and what is removed after copying.
- Symlink dereferencing.
- `PROVENANCE.md`, `manifest.sha256`, the smoke test and the tarball.
- Exit codes, output and side effects.

### Out of scope

- Signing, notarising or uploading the dist.
- Editing `config/org.yaml` for a customer. The dist ships the source's
  `config/` as it is; a team edits its own copy afterwards.
- Verifying a delivered dist. That is `shasum -a 256 -c manifest.sha256`, run by
  the receiver (see `docs/minimal-kit.md`).
- Building from anything other than the tree the script lives in. There is no
  source-directory option (P-1: the toolkit root comes from the script's own
  location).

### Normative vs. Informative

- **Normative:** the shipped and excluded sets, the refusal to overwrite an
  existing output path, symlink dereferencing, the provenance fields, manifest
  coverage, the smoke-test checks and their failure behaviour, exit codes.
- **Informative:** the dist name `house-special`, the default output
  `dist/house-special/` under the toolkit root, the wording of `PROVENANCE.md`,
  the section banners printed while building, and the digest algorithm
  (SHA-256).

### Classification Key

- **[TESTABLE]** — can be checked by an automated test; the test is named.
- **[STRUCTURAL]** — checked by reading the code or the layout.
- **[ADVISORY]** — reviewer judgment.

---

## FR-01 — Command line

[TESTABLE]

The script takes options only. It takes no positional arguments.

| Option | Effect |
|---|---|
| `--out <dir>` | Build into `<dir>` instead of the default `<toolkit root>/dist/house-special`. A relative path is taken relative to the caller's working directory. |
| `--with-wiki` | Also ship `reference/autopkg-wiki/` (FR-05). |
| `--with-devagent` | Also ship the agent scaffolding (FR-05). |
| `--tar` | After a passing smoke test, also write a `.tar.gz` (FR-10). |
| `-h`, `--help` | Print a one-line usage message and exit 0. Nothing is built. |

Options may appear in any order and may be combined. Options are read left to
right, so `--help` exits before any option after it is checked.

**Acceptance Criteria:**

- AC-01.1: [TESTABLE] `--help` prints a usage line naming all four options and
  exits 0 without creating any directory.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-01.2: [TESTABLE] `--out` with no value, or with a value that starts with
  `-`, exits 2 with `ERROR: --out requires a directory path` on stderr.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-01.3: [TESTABLE] An unknown option, or any positional argument, exits 2
  with `ERROR: Unknown option: <arg>` on stderr.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-01.4: [STRUCTURAL] There is no option or environment variable that changes
  the source tree. The source is always the toolkit root derived by
  `lib/toolkit-common.sh` (toolkit-common FR-01).
  **Enforced via:** inspection.

## FR-02 — Output location

[TESTABLE]

The build MUST write into a directory that did not exist before the run. It
MUST NOT merge into, or overwrite, an existing path.

Step by step:

1. Pick the output: `--out <dir>`, else `<toolkit root>/dist/house-special`.
2. If anything exists at that path (file, directory or symlink to an existing
   target), exit 2 with `ERROR: Output path already exists: <path> (remove it or
   pass --out elsewhere)`.
3. Create it, with parents (`mkdir -p`). If that fails, exit 2.

**Acceptance Criteria:**

- AC-02.1: [TESTABLE] With no `--out`, the dist lands in
  `<toolkit root>/dist/house-special/`, whatever the working directory.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned; must run on a disposable copy of the kit so the real tree is not written to)
- AC-02.2: [TESTABLE] With `--out <tmp>/kit`, the dist lands in `<tmp>/kit/`
  and nothing is written under the toolkit root.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-02.3: [TESTABLE] An existing output path exits 2, and its contents are
  unchanged afterwards.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)

## FR-03 — What ships

[TESTABLE]

The copy is an allowlist. Exactly these paths are copied from the toolkit root,
each only if it exists in the source:

| Source path | Notes |
|---|---|
| `bin/` | Every front end, then `make-dist.sh` is removed (FR-04). |
| `lib/` | The whole directory, including `lib/toolkit-common.sh`. |
| `config/` | All of it, including `config/org.yaml` as it stands in the source. |
| `guardrails/` | All of it. |
| `templates/` | All of it, including the worked examples. |
| `reference/methodology.md` | Single file. |
| `reference/recipe-standards.md` | Single file. |
| `docs/` | All of it. |
| `README.md`, `LICENSE`, `LICENSE.md`, `NOTICE`, `CONTRIBUTING.md`, `requirements.txt` | Each only if it is a regular file in the source. |

Two files are then written by the build itself: `PROVENANCE.md` (FR-07) and
`manifest.sha256` (FR-08).

A missing allowlisted directory, or `reference/methodology.md` /
`reference/recipe-standards.md`, prints `WARN:  skipping <path> (not present in
source)` on stderr and the build continues. A missing top-level file from the
list above is skipped silently.

Everything inside an allowlisted directory ships, including files that git
does not track or that `.gitignore` ignores (see OQ-02). The only exceptions are
the removals in FR-04.

**Acceptance Criteria:**

- AC-03.1: [TESTABLE] After a default build, the top level of the dist contains
  exactly: `bin`, `lib`, `config`, `guardrails`, `templates`, `reference`,
  `docs`, the top-level files from the table that exist in the source,
  `PROVENANCE.md` and `manifest.sha256`.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-03.2: [TESTABLE] `reference/` in the dist contains exactly
  `methodology.md` and `recipe-standards.md` when neither option is given.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-03.3: [TESTABLE] `config/org.yaml` in the dist is byte-identical to the
  source (no rewriting).
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-03.4: [TESTABLE] Removing an allowlisted directory from a disposable source
  copy produces a `WARN:  skipping` line and does not by itself stop the build
  (the smoke test may still fail on it).
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)

## FR-04 — What is excluded

[TESTABLE]

Anything not in FR-03 or FR-05 is excluded because it is never copied. That
covers, among others: `.git/`, `tests/`, `specs/`, `customer/`, `BUGFIX.md`,
`PROGRESS.md`, `.leak-patterns`, `dist/`, a top-level `.venv/`, and, unless the
options in FR-05 are given, `reference/autopkg-wiki/`, `.devagent/`, `.roo/`,
`.clinerules` and `AGENT_GREETING.md`.

After copying, the build also removes, inside the dist:

1. `bin/make-dist.sh`. A dist that can build a dist of itself invites confusion
   about which tree is the source.
2. A `venv` directory directly under the dist's `bin/`, and a `.venv/` at the
   dist root. Virtual environments are machine-specific.
3. Every file named `.DS_Store`, at any depth.
4. Every directory named `__pycache__`, at any depth.

Nothing else is filtered. A stray `*.pyc` outside `__pycache__`, an editor
backup file or any other untracked file inside an allowlisted directory ships.

**Acceptance Criteria:**

- AC-04.1: [TESTABLE] None of `tests`, `specs`, `customer`, `.git`,
  `BUGFIX.md`, `PROGRESS.md`, `.leak-patterns` or `dist` exists in a default
  dist, even when all of them exist in the source.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-04.2: [TESTABLE] The dist's `bin/` has no `make-dist.sh`.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-04.3: [TESTABLE] No `.DS_Store` file and no `__pycache__` directory exists
  anywhere in the dist, even when the source has them inside `bin/` and `docs/`.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-04.4: [TESTABLE] A `venv` directory under the source's `bin/` is absent
  from the dist.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-04.5: [TESTABLE] Without `--with-wiki` and `--with-devagent`, none of
  `reference/autopkg-wiki`, `.devagent`, `.roo`, `.clinerules` or
  `AGENT_GREETING.md` exists in the dist.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)

## FR-05 — Optional content

[TESTABLE]

- `--with-wiki` adds `reference/autopkg-wiki/` (the offline AutoPkg wiki mirror).
- `--with-devagent` adds `.devagent/`, `.clinerules`, `AGENT_GREETING.md`, and
  `.roo/rules`. In the source, `.roo/rules` is a symlink to `../.devagent/rules`.
  In the dist it is a real directory copied from `.devagent/rules`, not a link.

Each added path follows FR-03's rule: a missing source path warns and is
skipped. The one exception is `.roo/rules`, which is copied unconditionally
(see OQ-04).

**Acceptance Criteria:**

- AC-05.1: [TESTABLE] `--with-wiki` produces `reference/autopkg-wiki/` in the
  dist with the same file list as the source.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-05.2: [TESTABLE] `--with-devagent` produces `.devagent/`, `.clinerules`,
  `AGENT_GREETING.md` and `.roo/rules/`, and `.roo/rules` is a directory, not a
  symlink.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-05.3: [TESTABLE] `PROVENANCE.md` records each option as `true` or `false`
  (FR-07).
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)

## FR-06 — Symlinks are dereferenced

[TESTABLE]

Every copy uses `cp -RL`. A symlink in the source becomes a real file or
directory in the dist, holding the content the link pointed at. A dist MUST NOT
contain a symlink. The reason: a link that works in the source checkout can
point at a path that does not exist on the machine that receives the dist.

**Acceptance Criteria:**

- AC-06.1: [TESTABLE] `find <dist> -type l` prints nothing, including after a
  `--with-devagent` build.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-06.2: [TESTABLE] A symlinked file inside `docs/` of a disposable source copy
  arrives as a regular file with the target's content.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-06.3: [TESTABLE] A dangling symlink inside an allowlisted directory makes
  the build fail. (Not yet met: `cp` reports an error, but `copy_tree` ignores
  its exit status and the build goes on; see OQ-01.)
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)

## FR-07 — PROVENANCE.md

[TESTABLE]

A dist has no git history, so the build writes `PROVENANCE.md` at the dist root.
It holds a table with these rows:

| Field | Value |
|---|---|
| Built | UTC time of the build, `YYYY-MM-DD HH:MM UTC` |
| Source commit | Short hash of the source's `HEAD`, or `unknown` if git can't tell. Followed by ` (working tree had uncommitted changes)` when `git diff --quiet HEAD` fails. |
| Source branch | `git rev-parse --abbrev-ref HEAD`, or `unknown` |
| Wiki included | `true` or `false` |
| Agent scaffolding included | `true` or `false` |

Below the table it explains, in prose: what was left out and why; that links
into `specs/` or `customer/acme/` point at the source repository; that a
missing `reference/autopkg-wiki/` is expected unless the build used
`--with-wiki`; and that changes belong in the source repository, since the dist
has no tests.

`PROVENANCE.md` is written before the manifest, so the manifest covers it.

**Acceptance Criteria:**

- AC-07.1: [TESTABLE] `PROVENANCE.md` exists and its commit row matches
  `git rev-parse --short HEAD` of the source.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-07.2: [TESTABLE] A tracked file modified in a disposable source clone adds
  the uncommitted-changes note; a clean clone does not.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-07.3: [TESTABLE] An untracked file inside an allowlisted directory, which
  ships, also adds the uncommitted-changes note. (Not yet met: `git diff --quiet
  HEAD` ignores untracked files; see OQ-02.)
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-07.4: [TESTABLE] A source that is not a git work tree records `unknown` for
  commit and branch and does not claim uncommitted changes. (Not yet met: when
  git fails, the dirty check also fails, so the note is added; see OQ-03.)
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)

## FR-08 — manifest.sha256

[TESTABLE]

The build writes `manifest.sha256` at the dist root. It lists a SHA-256 digest
for every regular file in the dist except `manifest.sha256` itself and any
`.DS_Store`. Paths are relative to the dist root with no leading `./`, sorted,
in the format `shasum -a 256` prints. The receiver checks the dist with
`shasum -a 256 -c manifest.sha256` from inside it.

The file list is passed NUL-delimited end to end, so names with spaces or
quotes are digested (KI-20). After writing, the build counts the manifest's
lines and the dist's files. If they differ, it exits 2 with `ERROR: manifest
lists <n> files but <m> were shipped`.

The digest step is a second implementation beside `bin/generate-manifest.sh`,
which `specs/manifest/01-manifest.md` FR-01 forbids. That spec's OQ-4 records
the open choice; this spec does not settle it.

**Acceptance Criteria:**

- AC-08.1: [TESTABLE] `shasum -a 256 -c manifest.sha256`, run inside a fresh
  dist, reports every line `OK`.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-08.2: [TESTABLE] The manifest has one line per regular file in the dist
  other than itself, and includes `PROVENANCE.md`.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-08.3: [TESTABLE] A file in the source's `docs/` whose name contains a
  space and a single quote appears in the manifest and verifies.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-08.4: [STRUCTURAL] Manifest digests are computed in one place shared with
  the manifest front ends. (Not yet met; see `specs/manifest/01-manifest.md`
  OQ-4.)
  **Enforced via:** inspection.

## FR-09 — Smoke test

[TESTABLE]

The copy is an allowlist, so a runtime file added to the source outside the
allowlist would be left out silently. The smoke test catches that at build time.
It runs the dist's own tools, which find their own `lib/` and `config/` from
their own location (P-1). The checks run in this order; the first failure
prints `ERROR: [FAIL] …` on stderr and exits 1:

1. Every `*.sh` and `*.py` directly in the dist's `bin/` has the owner exec bit.
   The build never `chmod`s: a missing bit here is missing in the source too
   (KI-18, KI-20).
2. `bin/recipe-linter.sh --list-rules` exits 0.
3. `bin/analyze-package.sh --help` exits 0.
4. `bin/inspect-app.sh --help` exits 0.
5. `bin/inspect-archive.sh --help` exits 0.
6. `bin/capture-perms.sh --help` exits 0.
7. `bin/recipe-linter.sh --dir templates/pattern-4-vendor-drop/example-Xerox-Drivers --pair-check`
   exits 0: a shipped example passes the shipped linter with the shipped config.
8. `docs/` holds at least one `*.md` file.

Each passing check prints `  [PASS] <what>` on stdout. The tools' own output is
discarded.

Not checked: `inspect-dmg.sh`, any Python front end (such as
`bin/autopkg-preflight.py`), the `guardrails/audit/` scripts, and every other
front end's `--help` (see OQ-05).

**Acceptance Criteria:**

- AC-09.1: [TESTABLE] A clean build prints eight `[PASS]` lines and exits 0.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-09.2: [TESTABLE] A front end without the exec bit in a disposable source
  copy fails the build with exit 1 and names the file.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-09.3: [TESTABLE] Removing `config/checks.yaml` from a disposable source copy
  fails the build at the `--list-rules` check with exit 1.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-09.4: [TESTABLE] A smoke-test failure writes no tarball, even with `--tar`.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)

## FR-10 — Tarball (`--tar`)

[TESTABLE]

With `--tar`, after the smoke test passes, the build runs `tar czf` in the
output directory's parent. The archive holds one top-level directory, named as
the output directory is named. The archive file is always called
`house-special.tar.gz` and is written into the output's parent directory, next
to the output. Its absolute path is printed.

Examples:

- Default: `dist/house-special/` and `dist/house-special.tar.gz`.
- `--out /tmp/kit --tar`: `/tmp/kit/` and `/tmp/house-special.tar.gz`, whose top
  directory is `kit/`.

**Acceptance Criteria:**

- AC-10.1: [TESTABLE] `--tar` writes `<parent>/house-special.tar.gz`, and
  `tar tzf` on it lists `<output name>/manifest.sha256`.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-10.2: [TESTABLE] Without `--tar`, no `.tar.gz` is written.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-10.3: [TESTABLE] If an archive already exists at that path, the build
  refuses rather than overwriting it, as FR-02 does for the directory. (Not yet
  met: `tar czf` overwrites it; see OQ-06.)
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-10.4: [TESTABLE] A `tar` failure makes the build exit non-zero. (Not yet
  met: the `tar` exit status is not checked; see OQ-06.)
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)

## FR-11 — Output and exit codes

[TESTABLE]

Progress goes to stdout as section banners (`=== <name> ===`) followed by
indented lines: `  source:` and `  output:` paths, one `  + <path>` per copied
path, the provenance commit, the manifest file count, the `[PASS]` lines, the
tarball path, and finally the output directory under `=== Done ===`. Warnings
(`WARN:  …`) and errors (`ERROR: …`) go to stderr.

| Exit | Meaning |
|---|---|
| 0 | Dist built and smoke test passed (and tarball written, if asked), or `--help` |
| 1 | Smoke test failed |
| 2 | Usage error, output path exists, output directory can't be created, or manifest count mismatch |

On a failure after step 3 of FR-02, the partial output directory is left in
place. A second run then stops at FR-02 until it is removed (see OQ-07).

**Acceptance Criteria:**

- AC-11.1: [TESTABLE] Each exit code in the table is produced by the case it
  names.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-11.2: [TESTABLE] A successful build's last stdout line is the output
  directory.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)

## FR-12 — Side effects

[STRUCTURAL]

The build writes only inside the output directory and, with `--tar`, the one
archive beside it. It reads the source tree and runs read-only `git` queries in
it. It never modifies the source tree, never changes file modes, and needs no
network or elevated privileges.

**Acceptance Criteria:**

- AC-12.1: [TESTABLE] `git status --porcelain` of a disposable source clone is
  unchanged by a build with `--out` outside the clone.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned)
- AC-12.2: [STRUCTURAL] No `chmod`, `sed -i` or other in-place edit is applied to
  source or dist files.
  **Enforced via:** inspection.

## FR-13 — Dialect and runtime

[STRUCTURAL]

The script stays in bash (P-7): it is a thin wrapper around `cp`, `find`,
`shasum` and `tar`, and it reads no structured data. It runs under `/bin/bash`
3.2 with `set -uo pipefail` (no `-e`) and uses only tools on a clean macOS
install: `cp`, `mkdir`, `rm`, `find`, `sort -z`, `xargs -0`, `shasum`, `sed`,
`wc`, `tr`, `date`, `tar`. `git` is optional; without it the provenance rows
read `unknown`. It sources `lib/toolkit-common.sh` for `TOOLKIT_ROOT` and its
message helpers. It does not resolve a recipe repo: it has no repo to operate
on, so P-2 to P-6 do not apply.

**Acceptance Criteria:**

- AC-13.1: [TESTABLE] The planned tests run the script under `/bin/bash` 3.2.
  **Enforced via:** planned test `tests/make_dist_spec.sh` (planned; ShellSpec runs under `/bin/bash` per `.shellspec`)
- AC-13.2: [STRUCTURAL] No associative arrays, `mapfile` or case-modification
  expansion (AIP-05 of the constitution).
  **Enforced via:** inspection.

---

## Architecture-Incompatible Patterns

**AIP-01: Transforming shipped files.** Rewriting `config/org.yaml`, stripping
comments or substituting names during the build. The dist would no longer match
its source commit, and `PROVENANCE.md` would lie. **Enforced via:** AC-03.3,
AC-12.2.

**AIP-02: A denylist copy.** Copying the whole tree and deleting what shouldn't
ship. A new development file would ship by default. The allowlist fails the
other way, and the smoke test (FR-09) catches that. **Enforced via:** inspection.

**AIP-03: Fixing exec bits in the dist.** `chmod +x` on the copy hides a
source defect (this happened: KI-18, KI-20). **Enforced via:** AC-09.2, AC-12.2.

**AIP-04: Shipping symlinks.** See FR-06. **Enforced via:** AC-06.1.

**AIP-05: Building over an existing output.** Merging into an old dist leaves
stale files the manifest then blesses. **Enforced via:** AC-02.3.

---

## Open Questions

**OQ-01:** `copy_tree` (`bin/make-dist.sh` line 81) ignores the exit status of
`cp -RL`. A dangling symlink or unreadable file prints a `cp` error and the build
still exits 0 if the smoke test doesn't touch the missing file. Should any copy
failure end the build with exit 2? Leaning: yes.

**OQ-02:** Untracked and git-ignored files inside allowlisted directories ship,
and the dirty check (`bin/make-dist.sh` line 134) does not see them. Options: (a)
copy from `git ls-files` instead of the directory tree; (b) keep copying the
tree but add `git status --porcelain` to the dirty check; (c) refuse to build
from a dirty tree without a `--allow-dirty` flag. Leaning: (b) now, (a) later.

**OQ-03:** In a source that is not a git work tree, `git diff --quiet HEAD`
fails and `PROVENANCE.md` says the tree "had uncommitted changes", which is
wrong. Should the note be skipped when the commit is `unknown`?

**OQ-04:** With `--with-devagent`, `.roo/rules` is copied with a bare `cp -RL`
(`bin/make-dist.sh` line 119), not through `copy_tree`. If `.devagent/rules` is
missing, `cp` errors, the build goes on, and `+ .roo/rules (dereferenced)` is
still printed. Route it through the same existence check?

**OQ-05:** The smoke test covers five front ends. Should it run `--help` on
every `bin/*.sh`, and one Python front end, so a missing module under `lib/`
fails the build?

**OQ-06:** The tarball name is fixed (`house-special.tar.gz`) whatever `--out`
is called, an existing archive is overwritten silently, and a `tar` failure is
not detected (`bin/make-dist.sh` lines 263-264). Should the archive be named after the
output directory, refuse to overwrite, and fail on a `tar` error?

**OQ-07:** A failed build leaves a partial output directory, which blocks the
next run (FR-02). Should the build delete an output directory it created itself
when it fails? That removes evidence useful for diagnosis. Leaning: leave it,
but print the path to remove.

**OQ-08:** `bin/check-sanitized.sh` and `bin/check-doc-links.sh` ship in `bin/`.
They are kit-maintenance tools, and `check-doc-links.sh` will report every
link into `specs/` as broken in a dist. Ship them, or exclude them like
`make-dist.sh`?

**OQ-09:** `--out` pointing inside an allowlisted source directory (for example
`--out docs/kit`) would copy a directory into itself. Should the build refuse
any output path inside the toolkit root other than under `dist/`?

**OQ-10:** `config/customers.yaml` is local and gitignored
(`specs/toolkit/02-customers.md` FR-01), but `copy_tree` copies ignored files, so a
build from a checkout that has one ships it: the dist then names the builder's
customers, and the smoke test fails when a registered folder (such as
`customer/acme/`) isn't shipped. A fresh clone has no registry and builds clean.
Leaning: remove `config/customers.yaml` from the dist in FR-04, keep
`config/customers.example.yaml`, and add a test.

**OQ-11:** `reference/autopkg-wiki/` is no longer tracked: each user clones the
AutoPkg wiki there (README, Getting ready). `--with-wiki` therefore copies that
clone, including its `.git/`, and redistributes AutoPkg's wiki content, whose
licence isn't stated. Leaning: drop `--with-wiki` and have the dist's docs point at
the clone command, as the kit's do.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-09-27 | Initial spec, written from the existing implementation. |
