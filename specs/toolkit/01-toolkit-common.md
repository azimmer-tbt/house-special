# toolkit-common — Shared Frontend Library

**Status:** Draft
**Date:** 2026-08-31
**Requires:** `00-constitution.md`

---

## Purpose

Defines the contract of the shared library every frontend sources. This is the
single most depended-upon component in the toolkit and currently has no test
coverage; the guarded-fallback defect (P-6) reached a user because nothing
exercised the precedence chain directly.

### Normative vs. Informative

- **Normative:** resolution precedence, failure modes, exported names' meanings.
- **Informative:** the file path `lib/toolkit-common.sh`, the specific variable
  spellings, and the marker directory name.

### Classification Key

- **[TESTABLE]** — automatable, mechanism named alongside.
- **[STRUCTURAL]** — enforced by layout or inspection.
- **[ADVISORY]** — review judgment.

---

## FR-01 — Toolkit root derivation

[TESTABLE]

The library MUST derive the toolkit root from its own file location, resolved
physically so that a symlinked entry point resolves to the real tree. The value
MUST be read-only once set.

**Acceptance Criteria:**

- AC-01.1: [TESTABLE] Sourcing the library from any working directory yields the
  same toolkit root.
  **Enforced via:** automated test — source from `/`, from `/tmp`, and from
  inside a recipe repo; assert identical values.
- AC-01.2: [TESTABLE] Invoking a frontend through a symlink placed on `PATH`
  yields the real toolkit root, not the symlink's directory.
  **Enforced via:** automated test — symlink a frontend into a temp dir on
  `PATH`, invoke by bare name, assert config is found.
- AC-01.3: [STRUCTURAL] The toolkit root is marked read-only after assignment.
  **Enforced via:** inspection — `readonly` declaration present.
- AC-01.4: [TESTABLE] Derived asset paths (config, guardrails, templates,
  reference) are absolute.
  **Enforced via:** automated test — assert each begins with `/`.

## FR-02 — Recipe repo identification

[TESTABLE]

A directory is a recipe repo if and only if it contains the marker directory.
Identification MUST NOT consider the presence of a VCS directory, a manifest, or
any file naming convention.

**Acceptance Criteria:**

- AC-02.1: [TESTABLE] A directory containing the marker is identified as a repo.
  **Enforced via:** automated test — fixture directory, assert success.
- AC-02.2: [TESTABLE] A directory without it is not, even if it contains
  recipe-shaped files at the top level.
  **Enforced via:** automated test — fixture with loose `*.recipe.yaml`, assert
  failure.
- AC-02.3: [TESTABLE] A path that does not exist is not a repo, and produces no
  error output from the identification routine itself.
  **Enforced via:** automated test — assert non-zero return, empty stderr.
- AC-02.4: [TESTABLE] An empty argument is not a repo.
  **Enforced via:** automated test — call with `""`, assert non-zero return.

## FR-03 — Repo resolution precedence

[TESTABLE]

Resolution MUST consider sources in this order, stopping at the first present:

1. The explicit argument
2. The environment variable
3. The current working directory — **only if** it is identified as a repo

Per P-6, each source MUST be independently sufficient.

**Acceptance Criteria:**

- AC-03.1: [TESTABLE] With only the explicit argument supplied, it is used.
  **Enforced via:** automated test — no env var set, CWD not a repo.
- AC-03.2: [TESTABLE] With only the environment variable set, it is used.
  **Enforced via:** automated test — no argument passed, CWD not a repo. *This
  is the case the guarded-fallback defect broke; it must be tested in isolation.*
- AC-03.3: [TESTABLE] With neither supplied and CWD a repo, CWD is used.
  **Enforced via:** automated test — `cd` into a fixture repo, assert resolution.
- AC-03.4: [TESTABLE] The explicit argument wins over the environment variable
  when both are present and both valid.
  **Enforced via:** automated test — set both to different valid repos, assert
  the argument's value.
- AC-03.5: [TESTABLE] The environment variable wins over CWD when both apply.
  **Enforced via:** automated test — `cd` into repo A with the variable set to
  repo B; assert B.
- AC-03.6: [TESTABLE] The resolved value is absolute and physical, regardless of
  how it was supplied.
  **Enforced via:** automated test — supply a relative path and a path
  containing `..`; assert a normalized absolute result.

## FR-04 — Resolution failure behavior

[TESTABLE]

Per P-4 and P-5, failure MUST be loud and MUST NOT degrade to a lower-precedence
source.

**Acceptance Criteria:**

- AC-04.1: [TESTABLE] No source available → exit 2, and the message names all
  three remedies.
  **Enforced via:** automated test — assert exit code and assert stderr contains
  each remedy.
- AC-04.2: [TESTABLE] An explicit argument naming a non-existent path → exit 2,
  even when a valid environment variable is set.
  **Enforced via:** automated test.
- AC-04.3: [TESTABLE] An explicit argument naming an existing directory that is
  not a repo → exit 2, and the message states the marker directory was expected.
  **Enforced via:** automated test.
- AC-04.4: [TESTABLE] An environment variable naming an invalid path → exit 2,
  even when CWD is a valid repo.
  **Enforced via:** automated test. *This is P-5 by the second route.*
- AC-04.5: [TESTABLE] Every failure message identifies which source supplied the
  offending value.
  **Enforced via:** automated test — assert the source is named in stderr.

## FR-05 — Prerequisite checks

[TESTABLE]

The library MUST provide a command-presence check that fails with actionable
remediation rather than allowing a bare "command not found" from deeper in a
call stack.

**Acceptance Criteria:**

- AC-05.1: [TESTABLE] A present command passes silently.
  **Enforced via:** automated test — check `sh`, assert exit 0 and no output.
- AC-05.2: [TESTABLE] An absent command exits 2 and emits both the command name
  and the supplied remediation text.
  **Enforced via:** automated test — check a nonsense name, assert both strings.
- AC-05.3: [TESTABLE] The platform check fails on a non-Darwin system with a
  message naming the platform requirement.
  **Enforced via:** automated test — stub `uname`, assert exit 2.

## FR-06 — Dialect conformance

[STRUCTURAL]

Per P-7, the library is sourced by universal frontends and MUST therefore be
bash 3.2 compatible.

**Acceptance Criteria:**

- AC-06.1: [STRUCTURAL] No associative arrays, `mapfile`/`readarray`, or
  case-modification expansion.
  **Enforced via:** lint rule — grep for those constructs in non-comment lines
  only; any hit fails. *Matching comment text as well would flag the very
  comment that documents this constraint.*
- AC-06.2: [TESTABLE] The library parses under a bash 3.2 compatible parse check.
  **Enforced via:** automated test — `bash -n`.
- AC-06.3: [STRUCTURAL] The library is sourced, never executed: it defines
  functions and variables and takes no action at load beyond assignment.
  **Enforced via:** inspection — no top-level command invocations with effects.

## FR-07 — Optional resource lookup

[TESTABLE]

Lookups into vendored reference material MUST distinguish "resource absent" from
"error", because distribution builds may omit reference directories.

**Acceptance Criteria:**

- AC-07.1: [TESTABLE] A lookup for present material prints its path, returns 0.
  **Enforced via:** automated test.
- AC-07.2: [TESTABLE] A lookup for absent material returns non-zero, prints
  nothing, and emits no error.
  **Enforced via:** automated test — assert empty stdout and stderr.

---

## FR-08 — Org naming configuration

[TESTABLE]

Everything that makes the kit one organisation's kit — the recipe identifier
namespace, the package-name prefix, the org's display name, its internal domain and
its vendor-cache folder, the oldest macOS it still supports — comes from one flat file, `config/org.yaml`, loaded by
`read_org_config [file]`. Kit files (scripts, `config/checks.yaml`) MUST NOT contain
literal org values; they read `ORG_*` globals or use `{{TOKEN}}` placeholders
rendered by `org_render`.

Resolution order: the explicit argument (a frontend's `--org <file>`), then
`$AUTOPKG_TOOLKIT_ORG`, then `config/org.yaml`. The file uses flat `key: value`
lines (quoted or bare values; trailing `# comments` on bare values) so that both
readers stay simple: `read_org_config` in bash for the shell tools, and its twin
`recipekit.org.read_org_config` for the Python ones (the linter among them), with the
same precedence, validation messages and tokens.

A customer's own `org.yaml` (`specs/toolkit/02-customers.md` FR-03) is layered over
the resolved file key by key: `recipekit.org.read_org_config(file, overlay=<customer
org.yaml>)` takes each key the overlay sets, keeps the base file's value for each key
it leaves out, then validates the merged values as below. An explicit `--org` or
`$AUTOPKG_TOOLKIT_ORG` replaces the merged result; the front ends don't pass an
overlay then. The bash `read_org_config` does not layer yet: shell tools read one
file.

| Key | Global | Rule |
|-----|--------|------|
| `org_name` | `ORG_NAME` | Free text; defaults to the identifier prefix |
| `identifier_prefix` | `ORG_IDENTIFIER_PREFIX`, `ORG_IDENTIFIER_PREFIX_RE` | Reverse-DNS, ≥ 2 segments of `[A-Za-z0-9-]` |
| `pkgname_prefix` | `ORG_PKGNAME_PREFIX` | Non-empty, `[A-Za-z0-9][A-Za-z0-9._-]*` |
| `internal_domain` | `ORG_INTERNAL_DOMAIN` | Free text |
| `vendor_dir` | `ORG_VENDOR_DIR` | Defaults to `pkgname_prefix` minus a trailing `_` |
| `fleet_min_macos` | `ORG_FLEET_MIN_MACOS` | Optional. A macOS version, `N`, `N.N` or `N.N.N`; the equivalence audit compares apps' `LSMinimumSystemVersion` against it (Standards §6.10.2) |

Tokens rendered by `org_render`: `{{ORG_NAME}}`, `{{IDENTIFIER_PREFIX}}`,
`{{IDENTIFIER_PREFIX_RE}}` (dots escaped once), `{{IDENTIFIER_PREFIX_RE_YAML}}`
(dots escaped twice, for regexes inside YAML double-quoted strings),
`{{PKGNAME_PREFIX}}`, `{{INTERNAL_DOMAIN}}`, `{{VENDOR_DIR}}`.

**Acceptance Criteria:**

- AC-08.1: [TESTABLE] With no argument and no env override, the kit default loads.
  **Enforced via:** `tests/org_config_spec.sh`.
- AC-08.2: [TESTABLE] `$AUTOPKG_TOOLKIT_ORG` overrides the default; an explicit
  argument overrides both. **Enforced via:** `tests/org_config_spec.sh`.
- AC-08.3: [TESTABLE] An invalid `identifier_prefix`, an empty `pkgname_prefix`, or a
  `fleet_min_macos` that isn't a version returns non-zero with a message naming the
  key; an absent `fleet_min_macos` is empty, not an error.
  **Enforced via:** `tests/org_config_spec.sh`.
- AC-08.4: [TESTABLE] Rendering is literal: values containing `\` or `&` are
  substituted unchanged, identically under bash 3.2 and bash 5.x (no
  `${var//pattern/replacement}` with org values as the replacement).
  **Enforced via:** automated test (run under `/bin/bash`).
- AC-08.5: [TESTABLE] With an alternate org file, the linter fails IDN-001, IDN-002
  and PKG-002 on recipes that use the default org's naming.
  **Enforced via:** `tests/org_config_spec.sh`.

---

## FR-09 — Python interpreter

[TESTABLE]

Front ends that need Python run **AutoPkg's bundled interpreter**, which always
ships PyYAML (AutoPkg needs it for YAML recipes). They MUST NOT run a bare
`python3` from `PATH`: Apple's `/usr/bin/python3` has no PyYAML, and "whichever
Python is first" differs per machine (toolkit constitution P-7).
`bin/recipe-linter.sh` runs `recipekit.lint` this way.

- `.py` tools use the shebang `#!/usr/local/autopkg/python`.
- Shell front ends call `tk_python <args>`, which puts `TOOLKIT_ROOT/lib/python` on
  `PYTHONPATH` (so `tk_python -m recipekit.facts` works from any directory) and resolves
  the interpreter with
  `toolkit_python_path`: `$AUTOPKG_TOOLKIT_PYTHON` if set (must be executable),
  else `/usr/local/autopkg/python`, else
  `/Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3`.
- Code must stay compatible with the Python version AutoPkg bundles (3.10 as of
  AutoPkg 2.9).

**Acceptance Criteria:**

- AC-09.1: [TESTABLE] With AutoPkg installed and no override, the interpreter is
  `/usr/local/autopkg/python` and `import yaml` succeeds through `tk_python`.
  **Enforced via:** `tests/toolkit_python_spec.sh`.
- AC-09.2: [TESTABLE] `$AUTOPKG_TOOLKIT_PYTHON` overrides the default; a
  non-executable override fails with status 127 and a message naming the variable.
  **Enforced via:** `tests/toolkit_python_spec.sh`.
- AC-09.3: [TESTABLE] No shell front end calls a bare `python3`, and every `.py`
  tool carries the AutoPkg shebang. **Enforced via:** `tests/kit_hygiene_spec.sh`.

---

## Architecture-Incompatible Patterns

**AIP-01: Resolution inside a conditional on another source.** See P-6 and
AC-03.2. **Enforced via:** AC-03.2 in isolation.

**AIP-02: Silent normalization of an invalid repo.** Creating the marker
directory to make an invalid path valid. Resolution is a query, not a mutation.
**Enforced via:** automated test — assert the filesystem is unchanged after a
failed resolution.

**AIP-03: Caching resolution across invocations.** Writing the resolved repo to
a state file for reuse. Reintroduces hidden state that the precedence chain
exists to make explicit. **Enforced via:** reviewer check.

**AIP-04: Toolkit root override.** Accepting an argument or variable that
relocates the toolkit root. Violates P-1 and makes asset resolution
caller-dependent. **Enforced via:** AC-01.3.

---

## Open Questions

**OQ-1:** Should resolution emit the resolved repo path on stderr at an
informational level? It would make "which tree did that touch?" answerable from
a log without re-deriving it. Cost is noise on every invocation. Leaning: yes,
but only under an explicit verbosity flag.

**OQ-2:** Should there be a `--dry-run` convention in the library rather than
per-frontend? Several frontends mutate the filesystem and each handles this
differently or not at all. Out of scope for this spec; worth a follow-on.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-08-31 | Initial release. FR-03 and FR-04 written against the guarded-fallback defect. |
| 1.1 | 2026-09-27 | FR-08: optional `fleet_min_macos` (ORG_FLEET_MIN_MACOS). FR-09: `tk_python` puts `lib/python` on `PYTHONPATH`. |
| 1.2 | 2026-09-27 | FR-08: a Python twin (`recipekit.org`) reads the same file; FR-09: the linter runs on `tk_python`. |
| 1.3 | 2026-09-27 | FR-08: `recipekit.org.read_org_config(..., overlay=)` layers a customer's `org.yaml` over the kit's key by key (`specs/toolkit/02-customers.md`); the bash reader does not layer yet. |
