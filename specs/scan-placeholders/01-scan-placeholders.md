# scan-placeholders — Report unresolved placeholder values and incomplete certificate chains

**Status:** Draft
**Date:** 2026-09-27
**Requires:** `specs/toolkit/00-constitution.md` (P-1 to P-7, P-10), `specs/toolkit/01-toolkit-common.md` (FR-03, FR-04), `specs/recipekit/01-recipe-model.md`
**Implementation:** `bin/scan-placeholders.sh`

---

## Purpose

Recipes are often written before every real value is known. The author leaves a
marked placeholder (`REPLACE_WITH_TEAM_ID`, `TEAMID_PENDING`, …) and fills it in
later. `scan-placeholders.sh` lists every placeholder still left in a recipe repo,
grouped by app, so the operator can see what remains. It is meant to be run again
and again as values are filled in.

It also runs one structural check: a download recipe that verifies a code
signature by authority names should list the whole certificate chain, not just
the vendor's leaf certificate. A leaf-only list fails on the first real run with
"Mismatch in authority names".

It needs no AutoPkg, makes no network call and changes no file.

This spec defines the **contract**: what counts as a placeholder, which files are
read, the output and the exit codes. It does not fix the language. The tool is
planned to become a query against the shared recipe model (FR-10); the contract
stays the same across that move.

### Normative vs. Informative

- **Normative:** the scanned scope, the placeholder tokens, the chain rule, the
  shape of each finding, exit codes, the absence of side effects.
- **Informative:** the header and footer wording, separator lines, and the
  current grep-based mechanism.

### Classification Key

- **[TESTABLE]** — automatable, mechanism named alongside.
- **[STRUCTURAL]** — enforced by layout or inspection.
- **[ADVISORY]** — review judgment.

No ShellSpec file covers this tool yet.

---

## FR-01 — Command line

[TESTABLE]

```
scan-placeholders.sh [--repo <recipe-repo>] [filter]
```

| Argument | Meaning |
|---|---|
| `--repo <dir>` | The recipe repo to scan. Resolved by toolkit-common (FR-03). |
| `filter` | A substring. Only apps whose folder name contains it are scanned. Case-sensitive. |
| `-h`, `--help` | Print a one-line usage and exit 0. |

Only the **first** positional argument is used as the filter; any further ones
are ignored. An unknown option such as `--json` is not rejected: it becomes the
filter and matches nothing.

**Acceptance Criteria:**

- AC-01.1: [TESTABLE] `--help` prints a line starting `Usage:` and exits 0.
  **Enforced via:** planned test `tests/scan_placeholders_spec.sh` (planned)
- AC-01.2: [TESTABLE] `--repo` with no value exits 2 with `--repo requires a
  directory path`. **Enforced via:** planned test `tests/scan_placeholders_spec.sh` (planned)
- AC-01.3: [TESTABLE] `scan-placeholders.sh --repo R Orchard` reports only apps
  whose folder name contains `Orchard`. **Enforced via:** planned test
  `tests/scan_placeholders_spec.sh` (planned)
- AC-01.4: [TESTABLE] An unrecognised option exits 2 rather than becoming the
  filter. (Not yet met; see OQ-04.) **Enforced via:** planned test
  `tests/scan_placeholders_spec.sh` (planned)

## FR-02 — Repo resolution

[TESTABLE]

The repo is resolved with toolkit-common's `resolve_repo_root` (toolkit-common
FR-03, FR-04): `--repo`, then `$AUTOPKG_TOOLKIT_REPO`, then the current directory
if it is a recipe repo. Failure exits 2.

**Acceptance Criteria:**

- AC-02.1: [TESTABLE] No repo source available → exit 2, nothing scanned.
  **Enforced via:** planned test `tests/scan_placeholders_spec.sh` (planned)
- AC-02.2: [STRUCTURAL] No repo-root logic of its own (constitution AIP-02).
  **Enforced via:** inspection.

## FR-03 — What is scanned

[TESTABLE]

- An **app folder** is a directory exactly two levels under `recipes/`:
  `recipes/<Vendor>/<App>/`. App folders are visited in sorted path order.
- Within an app folder, every file named `*.yaml` or `.overrides` is read, at any
  depth below the folder. `.overrides` is optional and org-defined (Standards §3.4);
  upstream recipes don't ship one, but a fork's pipeline may.
- Files directly in `recipes/` or directly in `recipes/<Vendor>/` are not
  scanned. Files deeper than the app folder are, because the search inside an
  app folder is recursive.
- Other files (READMEs, scripts, plists) are not scanned.

**Acceptance Criteria:**

- AC-03.1: [TESTABLE] A placeholder in `recipes/Acme/Orchard/Orchard.pkg.recipe.yaml`
  and one in `recipes/Acme/Orchard/.overrides` are both reported.
  **Enforced via:** planned test `tests/scan_placeholders_spec.sh` (planned)
- AC-03.2: [TESTABLE] A placeholder in `recipes/Acme/Orchard/README.md` is not
  reported. **Enforced via:** planned test `tests/scan_placeholders_spec.sh` (planned)
- AC-03.3: [TESTABLE] Apps are reported in sorted order of `<Vendor>/<App>`.
  **Enforced via:** planned test `tests/scan_placeholders_spec.sh` (planned)

## FR-04 — What counts as a placeholder

[TESTABLE]

A line is a finding when it contains any of these tokens (case-sensitive,
anywhere on the line):

| Token | Matches, for example |
|---|---|
| `REPLACE_` | `REPLACE_WITH_VERSION`, `REPLACE_ME` |
| `TEAMID_` followed by one or more capital letters | `TEAMID_PENDING`, `TEAMID_TBD` |
| `PENDING` | `version: PENDING` |
| `NOT_APPLICABLE_SEE_README` | `expected_authority_names: NOT_APPLICABLE_SEE_README` |
| `PLACEHOLDER` | `url: https://PLACEHOLDER/` |

Each matching line is one finding, however many tokens it holds.

Current behaviour that the contract should settle (see Open Questions):

- **`UNSIGNED_NO_TEAMID` is not a token.** It records, in the download recipe's
  `Input`, that the publisher has no team ID (an ad-hoc signed app): a decision,
  not a gap. The footer says so.
- **Comments count.** A YAML comment such as `# fill REPLACE_ values first` is a
  finding, and so is a commented-out line. This is the same class as KI-23 in the
  linter. See OQ-02.
- **`PKG_ID` values are not flagged.** Invented package identifiers are a
  different category from marked placeholders; the footer tells the operator to
  check them by hand.

**Acceptance Criteria:**

- AC-04.1: [TESTABLE] A fixture with one line for each token in the table yields
  one finding per line. **Enforced via:** planned test
  `tests/scan_placeholders_spec.sh` (planned)
- AC-04.2: [TESTABLE] A line holding two tokens yields one finding.
  **Enforced via:** planned test `tests/scan_placeholders_spec.sh` (planned)
- AC-04.3: [TESTABLE] Lowercase `replace_me` is not a finding.
  **Enforced via:** planned test `tests/scan_placeholders_spec.sh` (planned)
- AC-04.4: [TESTABLE] `teamid: "UNSIGNED_NO_TEAMID"` is not a finding, and a repo
  whose only notable line is that one scans clean. **Enforced via:**
  `tests/scan_placeholders_spec.sh` ("does not flag a deliberate teamid:
  UNSIGNED_NO_TEAMID, or a requirement-based verifier (KI-28)")
- AC-04.5: [TESTABLE] A token that appears only in a whole-line YAML comment is not
  a finding. (Not yet met; see OQ-02.) **Enforced via:** planned test
  `tests/scan_placeholders_spec.sh` (planned)

## FR-05 — Certificate-chain check

[TESTABLE]

For each `*.download.recipe.yaml` directly in the app folder (not in subfolders):
if the file contains the text `Processor: CodeSignatureVerifier` **and** an
`expected_authority_names:` key, it must also contain both `Developer ID
Certification Authority` and `Apple Root CA`. If either is missing, the app gets
one `[CHAIN]` finding naming the recipe file. A recipe that verifies with a
designated `requirement:` has no chain to list and is not checked.

Pkg recipes are not checked.

Current behaviour that the contract should settle:

- **The intermediate is hard-coded.** Mac App Store–style chains use a different
  intermediate and fail; this is the same defect as KI-8b in
  `guardrails/audit/check_cert_chain_complete.py`.
- **One finding per app.** If an app folder holds two download recipes with
  chain problems, only the last one (in glob order) is reported.
- **Text match.** The processor and certificate names are matched anywhere in the
  file, comments included.

**Acceptance Criteria:**

- AC-05.1: [TESTABLE] A download recipe with `CodeSignatureVerifier` and
  `expected_authority_names` listing only the leaf certificate yields one
  `[CHAIN]` finding. **Enforced via:** `tests/scan_placeholders_spec.sh` ("flags an
  authority-name list with only the leaf certificate")
- AC-05.2: [TESTABLE] The same recipe listing the leaf, `Developer ID
  Certification Authority` and `Apple Root CA` yields no `[CHAIN]` finding.
  **Enforced via:** planned test `tests/scan_placeholders_spec.sh` (planned)
- AC-05.3: [TESTABLE] A download recipe with no `CodeSignatureVerifier` yields no
  `[CHAIN]` finding. **Enforced via:** planned test `tests/scan_placeholders_spec.sh` (planned)
- AC-05.4: [TESTABLE] A download recipe that verifies with `requirement:` only
  yields no `[CHAIN]` finding. **Enforced via:** `tests/scan_placeholders_spec.sh`
  ("does not flag a deliberate teamid: UNSIGNED_NO_TEAMID, or a requirement-based
  verifier (KI-28)")
- AC-05.5: [TESTABLE] A complete Mac App Store–style chain yields no `[CHAIN]`
  finding. (Not yet met; see KI-8b.) **Enforced via:** planned test
  `tests/scan_placeholders_spec.sh` (planned)

## FR-06 — Output

[TESTABLE]

All output goes to stdout. An app with no findings prints nothing. An app with
findings prints:

```

=== OrchardLabs/Orchard-Analytics ===
  Orchard-Analytics.download.recipe.yaml:9  teamid: "TEAMID_PENDING"
  Orchard-Analytics.download.recipe.yaml:14  version: REPLACE_WITH_VERSION
  [CHAIN] Orchard-Analytics.download.recipe.yaml: CodeSignatureVerifier present but missing 'Developer ID Certification Authority' and/or 'Apple Root CA' — expected_authority_names likely has only the leaf cert, not the full chain
```

Each placeholder line is `  <file name>:<line number>  <line text>`, with the
line's leading whitespace removed. The file is shown by base name only, so two
files with the same name in different subfolders are not told apart. Placeholder
findings come first, in grep's order; the `[CHAIN]` finding, if any, comes last.

The run ends with a footer:

- No findings: `No placeholders found.` between two separator lines.
- Findings: `Total placeholder lines found: <N>`, where N counts placeholder lines
  **and** `[CHAIN]` findings, followed by two fixed notes (on `PKG_ID` values and
  on `UNSIGNED_NO_TEAMID`).

**Acceptance Criteria:**

- AC-06.1: [TESTABLE] Each finding line matches `^  <name>:<digits>  ` or
  `^  \[CHAIN\] `. **Enforced via:** planned test `tests/scan_placeholders_spec.sh` (planned)
- AC-06.2: [TESTABLE] N in the footer equals the number of finding lines printed.
  **Enforced via:** planned test `tests/scan_placeholders_spec.sh` (planned)
- AC-06.3: [TESTABLE] A clean repo prints `No placeholders found.` and no app
  headers. **Enforced via:** planned test `tests/scan_placeholders_spec.sh` (planned)

## FR-07 — Exit codes

[TESTABLE]

| Exit | Meaning |
|---|---|
| 0 | No findings. |
| 1 | At least one finding (placeholder or `[CHAIN]`). |
| 2 | Usage error or repo resolution failed (toolkit-common FR-04). |

Unreadable files are skipped quietly: grep's errors are discarded. See OQ-05.

**Acceptance Criteria:**

- AC-07.1: [TESTABLE] Clean fixture → exit 0; fixture with one placeholder → exit 1;
  fixture with only a `[CHAIN]` problem → exit 1. **Enforced via:** planned test
  `tests/scan_placeholders_spec.sh` (planned)

## FR-08 — No side effects

[TESTABLE]

The tool only reads. It needs no AutoPkg, no network and no privileges, so it is
safe to run in CI or on a machine without AutoPkg.

**Acceptance Criteria:**

- AC-08.1: [TESTABLE] The fixture repo is byte-identical before and after a scan.
  **Enforced via:** planned test `tests/scan_placeholders_spec.sh` (planned)
- AC-08.2: [TESTABLE] The scan succeeds with `autopkg` absent from `PATH`.
  **Enforced via:** planned test `tests/scan_placeholders_spec.sh` (planned)

## FR-09 — Runtime

[TESTABLE]

While it is bash, the tool runs under the system bash 3.2 with stock macOS tools
(constitution P-7). KI-1 (associative arrays in this script) is fixed. Assets are
found from the script's own location (constitution P-1).

**Acceptance Criteria:**

- AC-09.1: [TESTABLE] A full scan of a fixture repo completes under `/bin/bash`.
  **Enforced via:** planned test `tests/scan_placeholders_spec.sh` (planned)
- AC-09.2: [STRUCTURAL] No bash 4 constructs (constitution AIP-05).
  **Enforced via:** ShellSpec under `/bin/bash`; inspection.

## FR-10 — Planned move to the recipe model

[ADVISORY]

The tool reads recipe YAML with `grep`, which is the pattern the constitution
retires for structured data (P-7, AIP-08). It is a listed consumer of the shared
recipe model (`specs/recipekit/01-recipe-model.md`). The plan is to reimplement it
as a query over that model:

- Placeholder findings come from resolved values (Input, overrides, processor
  arguments) rather than raw lines, which settles FR-04's comment problem.
- The chain check reads the `signature` fact (recipe-model FR-06): only
  `authority_names` needs a full chain, which settles OQ-03.

Per constitution P-10, the port keeps the command: same name, flags, exit codes
and output format. The Python version replaces this one only after both give the
same findings on every fixture, apart from the deliberate fixes listed in this
spec's "Not yet met" criteria, which must be written down as they are made.

**Acceptance Criteria:**

- AC-10.1: [TESTABLE] During the port, a parity test runs both implementations
  over the same fixtures and compares output and exit codes. **Enforced via:**
  planned test `tests/scan_placeholders_spec.sh` (planned)

---

## Architecture-Incompatible Patterns

**AIP-01: Editing recipes.** Filling in, removing or "fixing" a placeholder. The
scanner reports; the operator decides. **Enforced via:** AC-08.1.

**AIP-02: Two placeholder lists.** A second, different list of tokens elsewhere
in the kit. `bin/run-recipes.sh` currently has its own narrower list (see its
spec, OQ-02). **Enforced via:** reviewer check.

**AIP-03: Changing the contract during the port.** A Python version with a new
output format or exit codes. **Enforced via:** constitution P-10; AC-10.1.

---

## Open Questions

**OQ-01 (resolved 2026-09-27):** `UNSIGNED_NO_TEAMID` was flagged and counted.
Dropped from the tokens: it records a decision, not a gap.

**OQ-02:** Should tokens inside YAML comments be ignored? Doing it with text tools
invites KI-23-style edge cases; the recipe model port (FR-10) solves it properly.

**OQ-03 (resolved 2026-09-27):** The chain check flagged recipes that verify with
`requirement:`. It now applies only to recipes that use `expected_authority_names`.

**OQ-04:** Should unknown options exit 2, and extra positional arguments be an
error, instead of being taken as, or dropped from, the filter?

**OQ-05:** grep errors (unreadable file) are discarded, so a file that cannot be
read looks clean. Should that be a warning on stderr and exit 2?

**OQ-06:** Should the scope include files directly in `recipes/<Vendor>/`, which
are skipped today? And should findings show the path relative to the app
folder instead of the base name?

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-09-27 | Initial spec, written from the existing implementation. |
| 0.2 | 2026-09-27 | .overrides optional; .autopkg_config removed from upstream. `UNSIGNED_NO_TEAMID` now lives in the download recipe's `Input`; examples updated. |
| 0.3 | 2026-09-27 | KI-28: `UNSIGNED_NO_TEAMID` no longer a token; chain check only for `expected_authority_names` (OQ-01, OQ-03 resolved). |
