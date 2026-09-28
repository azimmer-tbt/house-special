# Guardrail Audits — The Nine Checks

**Status:** Draft
**Date:** 2026-09-27
**Requires:** `specs/guardrail-audits/00-constitution.md`, `specs/recipekit/01-recipe-model.md`, `specs/toolkit/00-constitution.md`, `reference/methodology.md`, `docs/known-issues.md`
**Implementation:** `lib/python/recipekit/audits.py` (all audit logic), with front ends `guardrails/audit/check_no_pathdeleter.py`, `guardrails/audit/check_vendor_cache_path.py`, `guardrails/audit/check_no_pathname_reliance.py`, `guardrails/audit/check_cert_chain_complete.py`, `guardrails/audit/check_unsigned_declared.py`, `guardrails/audit/check_variables_declared.py`, `guardrails/audit/check_copier_overwrite.py`, `guardrails/audit/check_readme_exists.py` (`recipe_pairing`, FR-10, has no script)

---

## Purpose

One requirement per audit: what it asserts, which methodology lesson it comes
from, what it takes as input, and the condition it uses to decide PASS, FAIL or
SKIP. Each FR also lists the known false positives (a valid recipe fails) and
false negatives (a broken recipe passes).

Every audit reads recipes through the recipe model
(`specs/recipekit/01-recipe-model.md`): a `Pair` is a download recipe and its pkg
recipe in one folder, matched by file stem. The audits judge the pair's
*effective chain*: the pkg recipe (or the download recipe, if there is no pkg
recipe) and the parents it names through `ParentRecipe`, root first. Comments
never count as steps or values. FR-09 reads no recipe.

This spec describes the code as it is. Where the code falls short of what the
lesson asks for, the AC says "(Not yet met; see KI-…)" or the gap is an Open
Question.

The order below is the FR order. `bin/autopkg-preflight.py` runs them in the
order in `02-autopkg-preflight.md` FR-05.

### Normative vs. Informative

- **Normative:** each audit's assertion, its input, when it applies, and its exit
  codes.
- **Informative:** message wording.

### Classification Key

- **[TESTABLE]** — automatable, mechanism named alongside.
- **[STRUCTURAL]** — enforced by layout or inspection.
- **[ADVISORY]** — review judgment.

### Tests today

- `tests/python/test_audits.py` (unittest, run by `tests/python_unittest_spec.sh`)
  gives every audit (FR-02 to FR-10) a failing and a passing fixture, and a
  skipping one where the audit can skip. It also checks the command-line exit
  codes, that `run_all` runs every audit, and preflight's `main([...])`. Fixtures
  are written to temporary folders.
- `tests/guardrail_audits_spec.sh` (ShellSpec) runs the scripts for FR-05, FR-06
  and FR-07 on small inline recipes, and runs `bin/autopkg-preflight.py`.
- `tests/kit_hygiene_spec.sh` covers the shebangs and the black/isort/flake8 style
  of `guardrails/audit/*.py` and `lib/python/`.

ACs below name the test that enforces them: a unittest `Class.test_name`, or a
ShellSpec example's text.

---

## FR-01 — Common command-line contract

[TESTABLE]

Each audit has a script, `guardrails/audit/check_<thing>.py <target>`, which calls
`recipekit.audits.cli("<thing>")`. The arguments are parsed with `argparse`, so
`-h`/`--help` works and an extra argument is a usage error.

- **Target:** a recipe file or its app folder (constitution OQ-1). A folder
  target checks every pair in it; a file target checks the pair that file belongs
  to. The README audit uses the folder (a file target means its folder).
- **Output:** one or more lines on stdout starting `PASS:`, `FAIL:` or `SKIP:`.
  An audit's overall result is FAIL if any line is FAIL, else SKIP if any line is
  SKIP, else PASS.
- **Errors:** on stderr, starting `ERROR:`.

`recipe_pairing` (FR-10) has no script; it runs only through `run_all` and
preflight.

| Exit | When |
|---|---|
| 0 | every result is PASS or SKIP |
| 1 | any result is FAIL |
| 2 | no argument or an unknown option (argparse); the target does not exist; the target recipe is not valid (for a folder target, any recipe in it); no recipe pair found for the target |

**Acceptance Criteria:**

- AC-01.1: [TESTABLE] With no argument, the audit prints argparse's usage on
  stderr and exits 2. `--help` prints the usage and the spec name and exits 0.
  **Enforced via:** planned test (planned `tests/python/test_audits.py` case).
- AC-01.2: [TESTABLE] A target that does not exist, or a folder holding a recipe
  that does not parse, prints `ERROR: …` on stderr and exits 2. An invalid
  sibling does not block a named recipe file.
  **Enforced via:** `tests/python/test_audits.py`,
  `RunAllAndCliTest.test_cli_exit_codes_and_targets` and
  `CliExtraTest.test_an_invalid_sibling_does_not_block_a_named_recipe`.
- AC-01.3: [TESTABLE] A failing audit exits 1 whether the target is the folder or
  a recipe file in it. A passing one prints `PASS:` and exits 0; a failing one
  prints `FAIL:`. A run with only SKIP and PASS lines exits 0.
  **Enforced via:** `tests/python/test_audits.py`,
  `RunAllAndCliTest.test_cli_exit_codes_and_targets` (exit 1 for both targets)
  and `CliExtraTest.test_skip_only_exits_0`; `tests/guardrail_audits_spec.sh`,
  every `check_*` example (PASS/FAIL lines and exit codes).
- AC-01.4: [TESTABLE] Each audit has a fixture that makes it FAIL and one that
  makes it PASS, and one that makes it SKIP where it can skip (constitution G-4,
  methodology lesson 26). Met for all nine audits:
  FR-02 `PathDeleterTest.test_fr_02`;
  FR-03 `VendorCacheTest.test_fr_03_file_url_pass_fail_and_skip`;
  FR-04 `PathnameTest.test_fr_04`, `PathnameTest.test_ac_04_2_missing_download_is_skip`;
  FR-05 `CertChainTest.test_fr_05`;
  FR-06 `UnsignedTest.test_fr_06`;
  FR-07 `VariablesTest.test_fr_07_fail_pass_and_skip`;
  FR-08 `CopierOverwriteTest.test_fr_08_folder_copies_need_overwrite`;
  FR-09 `ReadmeTest.test_fr_09`;
  FR-10 `PairingTest.test_a_parent_that_is_not_the_sibling_fails`.
  FR-05 to FR-07 also have the `tests/guardrail_audits_spec.sh` examples named
  under each FR.
  **Enforced via:** `tests/python/test_audits.py` and
  `tests/guardrail_audits_spec.sh`, as listed.
- AC-01.5: [TESTABLE] Each script starts with the AutoPkg Python shebang
  `#!/usr/local/autopkg/python`, and the audits import only the standard library,
  PyYAML and `recipekit`.
  **Enforced via:** `tests/kit_hygiene_spec.sh` (shebang); reviewer check (imports).
- AC-01.6: [TESTABLE] The scripts and `lib/python/` pass black, isort and flake8.
  **Enforced via:** `tests/kit_hygiene_spec.sh`.
- AC-01.7: [STRUCTURAL] No audit writes a file, runs a subprocess or opens a
  network connection (constitution G-3).
  **Enforced via:** inspection.
- AC-01.8: [TESTABLE] `run_all(pair)` runs every audit, in the order of the
  `PAIR_AUDITS` table (`recipe_pairing` first) and then `readme_exists`.
  **Enforced via:** `tests/python/test_audits.py`,
  `RunAllAndCliTest.test_run_all_covers_every_audit`.

**Known gaps (all audits):**

- The effective chain follows `ParentRecipe`. A pkg recipe whose parent is not
  loaded, or is not its sibling download recipe, is judged without the sibling's
  steps. `recipe_pairing` (FR-10) fails such a pair, so the gap is not silent.

---

## FR-02 — No early `PathDeleter` (`check_no_pathdeleter.py`)

[TESTABLE]

**Asserts:** no `PathDeleter` runs before something has been staged.
**Why:** methodology lesson 2. `PathDeleter` errors when its target doesn't
exist, which is always the case on a fresh cache.
**Input:** a pair.

**Condition:** walk the effective chain's steps in order. FAIL each
`PathDeleter` that comes before the first staging step. The staging processors
are `URLDownloader`, `Copier`, `Unarchiver`, `DmgMounter`, `PkgRootCreator`,
`FlatPkgUnpacker`, `PkgPayloadUnpacker`, `FileCreator`, `PkgCopier` and
`PkgCreator`. A `PathDeleter` after one of them (a clean-up) passes. No early
`PathDeleter`: PASS.

**Acceptance Criteria:**

- AC-02.1: [TESTABLE] A `PathDeleter` before the first staging step fails, also
  when an info provider runs first; one after `URLDownloader` passes.
  **Enforced via:** `tests/python/test_audits.py`, `PathDeleterTest.test_fr_02`.
- AC-02.2: [TESTABLE] A comment that mentions `PathDeleter` does not fail.
  **Enforced via:** `tests/python/test_audits.py`, `PathDeleterTest.test_fr_02`.

**Known false results:**

- *False negative:* a `PathDeleter` after staging can still target a path that
  the run did not create. The audit only checks the order.
- *False positive:* only the built-in staging processors count, so a
  `PathDeleter` that cleans up after a shared or custom processor fails.

---

## FR-03 — Vendor-cache path resolves (`check_vendor_cache_path.py`)

[TESTABLE]

**Asserts:** every local vendor-cache path the pair names points at something
that exists.
**Why:** methodology lesson 1 (count the `..` levels) and lesson 24 (the cache
lives outside the repo and can vanish).
**Input:** a pair.

**Condition:**

1. Collect, from every recipe in the effective chain: each `Input` key named
   `LOCAL_*PATH` (for example `LOCAL_FILE_PATH`, `LOCAL_DIR_PATH`); each `Input`
   value that starts with `file://`; each `URLDownloader` `url` argument that
   starts with `file://`.
2. None: PASS ("nothing to check").
3. Resolve each value through the pair's merged `Input` (so
   `%VENDOR_CACHE_ROOT%` and `%NAME%` are replaced). `%RECIPE_DIR%` is the folder
   of the recipe that declares the value. Drop a leading `file://`. A relative
   path is taken from that recipe's folder, and `..` is collapsed.
4. If a `%variable%` is still left, or the value comes from a processor: SKIP
   ("can't resolve statically").
5. Find the cache root: the resolved `VENDOR_CACHE_ROOT` if the path is under
   it, otherwise the path up to and including its `vendor_cache` folder.
6. Root found but not on this machine: SKIP. Path exists: PASS. Otherwise FAIL.

Each value prints its own line.

**Acceptance Criteria:**

- AC-03.1: [TESTABLE] `LOCAL_FILE_PATH: "%RECIPE_DIR%/../../../vendor_cache/Acme/App/App.pkg"`
  fails when the cache exists without that file, and passes when the file exists.
  **Enforced via:** `tests/python/test_audits.py`,
  `VendorCacheTest.test_fr_03_relative_local_path`.
- AC-03.2: [TESTABLE] A pair with no local vendor-cache paths passes.
  **Enforced via:** `tests/python/test_audits.py`,
  `VendorCacheTest.test_nothing_to_check_passes`.
- AC-03.3: [TESTABLE] `DOWNLOAD_URL: "file://%VENDOR_CACHE_ROOT%/Acme/App/App.dmg"`
  is resolved and checked: SKIP when the cache root is missing, FAIL when the
  root exists but the file doesn't, PASS when the file exists (KI-8a, fixed).
  **Enforced via:** `tests/python/test_audits.py`,
  `VendorCacheTest.test_fr_03_file_url_pass_fail_and_skip`.

**Known false results:**

- *Environment-dependent, by design:* the verdict depends on the vendor cache of
  the machine running it. For example, a machine with `/tmp/autopkg/vendor_cache`
  but without Acme's fictional drops makes those Acme examples FAIL; a machine
  with no cache makes them SKIP.
- *False positive:* a missing path with no `vendor_cache` folder in it and no
  `VENDOR_CACHE_ROOT` fails; there is no root to tell "cache absent" from "wrong
  path".
- *False negative:* a local path written straight into a step argument (for
  example a `Copier` `source_path`) is not checked unless it is a
  `URLDownloader` `file://` URL.

---

## FR-04 — `%pathname%` is set before use (`check_no_pathname_reliance.py`)

[TESTABLE]

**Asserts:** no step uses `%pathname%` before a step that sets it.
**Why:** methodology lesson 3. `URLDownloader` sets `%pathname%`; `Copier` does
not (see also lesson 14).
**Input:** a pair.

**Condition:**

- No download recipe in the pair: SKIP ("could not check").
- Otherwise FAIL for each of the model's variable findings about `pathname` with
  error severity: `used_before_set` or `undeclared_variable`. The model walks
  the effective chain in order and knows which processors set `pathname` from its
  catalogue.
- A `pathname` finding of `unverifiable` (a shared or unknown processor ran
  first and might set it): SKIP.
- No such finding: PASS.

**Acceptance Criteria:**

- AC-04.1: [TESTABLE] A pkg recipe with `source_pkg: "%pathname%"` fails when its
  download recipe stages with `Copier` only, and passes when it uses
  `URLDownloader`.
  **Enforced via:** `tests/python/test_audits.py`, `PathnameTest.test_fr_04`.
- AC-04.2: [TESTABLE] A missing download recipe is reported as SKIP, not as a
  pass (constitution AIP-04).
  **Enforced via:** `tests/python/test_audits.py`,
  `PathnameTest.test_ac_04_2_missing_download_is_skip`.

- AC-04.3: [TESTABLE] `%pathname%` after only a shared or unknown processor is
  reported as SKIP.
  **Enforced via:** `tests/python/test_audits.py`,
  `VariablesTest.test_pathname_from_an_unknown_processor_is_skip`.

---

## FR-05 — Full certificate chain (`check_cert_chain_complete.py`)

[TESTABLE]

**Asserts:** a recipe that verifies signatures lists the whole chain in
`expected_authority_names`, not just the vendor's leaf certificate.
**Why:** methodology lesson 6.
**Input:** a pair.

**Condition:** each `CodeSignatureVerifier` step in the effective chain is judged
on its own `Arguments`:

- A step with `expected_authority_names` passes only if that list, after
  variable resolution, includes both `Developer ID Certification Authority` and
  `Apple Root CA`.
- A step without `expected_authority_names` (for example one that verifies with
  a designated `requirement`) passes. It has no chain to list; the linter's
  CSV-005 checks that the requirement pins the Team ID.
- No such step: PASS (not applicable).

The audit fails if any step fails.

**Acceptance Criteria:**

- AC-05.1: [TESTABLE] A `CodeSignatureVerifier` step whose
  `expected_authority_names` lists only the leaf fails; one listing the leaf,
  `Developer ID Certification Authority` and `Apple Root CA` passes, even when a
  comment names the missing entries.
  **Enforced via:** `tests/python/test_audits.py`, `CertChainTest.test_fr_05`;
  `tests/guardrail_audits_spec.sh`, "fails authority names without the Apple
  chain, even if a comment names it" and "passes authority names with the full
  chain".
- AC-05.2: [TESTABLE] A chain through `Apple Worldwide Developer Relations
  Certification Authority` (Mac App Store–style installer certificate) passes.
  (Not yet met; see KI-8b.)
  **Enforced via:** planned test (planned `tests/python/test_audits.py` case).
- AC-05.3: [TESTABLE] A `CodeSignatureVerifier` step that uses `requirement`
  instead of `expected_authority_names` is not judged by this audit (the lesson
  is about authority names).
  **Enforced via:** `tests/python/test_audits.py`, `CertChainTest.test_fr_05`;
  `tests/guardrail_audits_spec.sh`, "passes a verifier that uses a designated
  requirement".

**Known false results:**

- *False positive (KI-8b):* valid Mac App Store–style chains fail.
- *False negative:* a verifier step with neither `expected_authority_names` nor
  `requirement` passes. This audit leaves that case to the linter.

---

## FR-06 — Unsigned status is declared (`check_unsigned_declared.py`)

[TESTABLE]

**Asserts:** a pair with no signature check says so explicitly, with a reason.
**Why:** methodology lesson 7 (and lesson 16 for when "unsigned" is actually
correct).
**Input:** a pair.

**Condition:**

- Any `CodeSignatureVerifier` step in the effective chain: PASS (not applicable).
- Otherwise find the recipe that declares `NO_CODE_SIGNATURE_REQUIRED` as true
  in its `Input` (the leaf-most one in the chain). True means `true`, `True`,
  `yes`, `Yes` or `1`, as a YAML value or a string.
- None: FAIL.
- A YAML recipe must also explain the flag: its line carries an inline `#`
  comment, or the line directly above it is a non-empty comment. This is the one
  raw-text read in the audits; the model drops comments. No comment: FAIL.
- A plist recipe can't carry comments, so the flag alone passes.

Any wording counts as the reason. A flag that appears only in a comment does not
count as declared.

**Acceptance Criteria:**

- AC-06.1: [TESTABLE] A recipe with no verifier and no
  `NO_CODE_SIGNATURE_REQUIRED` fails.
  **Enforced via:** `tests/python/test_audits.py`, `UnsignedTest.test_fr_06`;
  `tests/guardrail_audits_spec.sh`, "fails when the flag exists only in a
  comment" (the recipe has no real flag).
- AC-06.2: [TESTABLE] A recipe with `Input.NO_CODE_SIGNATURE_REQUIRED: true` and a
  comment giving the reason passes, whatever the comment's wording.
  **Enforced via:** `tests/python/test_audits.py`, `UnsignedTest.test_fr_06`;
  `tests/guardrail_audits_spec.sh`, "passes the flag with a reason in the
  comment above it".
- AC-06.3: [TESTABLE] `Input.NO_CODE_SIGNATURE_REQUIRED: true` with no comment on
  or directly above its line fails.
  **Enforced via:** `tests/python/test_audits.py`, `UnsignedTest.test_fr_06`;
  `tests/guardrail_audits_spec.sh`, "fails the flag with no reason".
- AC-06.4: [TESTABLE] A flag that exists only inside a comment fails.
  **Enforced via:** `tests/guardrail_audits_spec.sh`, "fails when the flag exists
  only in a comment".

**Known false results:**

- *False negative:* any non-empty comment counts as the reason, for example a
  divider line (`# ---`) above the flag, or a `#` inside a quoted value on the
  flag's line. The audit can't judge whether the comment explains anything.
- *False negative:* `NO_CODE_SIGNATURE_REQUIRED: true` alongside a signed `.app`
  in the payload passes (lesson 16). The audit can't know what's in the payload.

---

## FR-07 — Every variable is declared (`check_variables_declared.py`)

[TESTABLE]

**Asserts:** every `%variable%` the pair uses has a source: an `Input`
declaration in the chain, AutoPkg itself, or an earlier step that sets it.
**Why:** methodology lesson 12. `.overrides` values are not read by a bare
`autopkg run`, so they don't count.
**Input:** a pair.

**Condition:**

- Only half a pair (no download or no pkg recipe): SKIP ("could not check").
- Otherwise use the model's variable findings
  (`specs/recipekit/01-recipe-model.md` FR-06, FR-09). The model reads every
  string under `Input` and each step's `Arguments` in the effective chain, in
  order. A step's arguments may use only variables that are declared in `Input`,
  set by AutoPkg, or set by an earlier step. Which processors set which
  variables comes from the model's processor-output catalogue (FR-07 there),
  including `URLTextSearcher`'s named groups and `Versioner`'s `output_var_name`.
- Findings map to results:

| Model finding | Result |
|---|---|
| `undeclared_variable` (error) | FAIL |
| `used_before_set` (error) | FAIL |
| `unverifiable` (only a shared or unknown processor could set it) | SKIP |
| `harness_supplied` (only `.overrides` has it) | PASS, with a note that the pipeline must supply it |

- No finding: PASS.

**Acceptance Criteria:**

- AC-07.1: [TESTABLE] A `PkgCreator` using `%version%` with no `Input.version` and
  no version-setting processor fails, naming `version`. `URLDownloader` alone
  does not set it.
  **Enforced via:** `tests/python/test_audits.py`,
  `VariablesTest.test_fr_07_fail_pass_and_skip`; `tests/guardrail_audits_spec.sh`,
  "fails %version% when only URLDownloader runs (it does not set version)".
- AC-07.2: [TESTABLE] A key declared after a blank line or a comment inside
  `Input:` counts as declared.
  **Enforced via:** `tests/guardrail_audits_spec.sh`, "knows URLTextSearcher sets
  its named groups, and reads Input past a blank line (KI-8c)" (the blank line;
  a comment inside `Input:` is planned).
- AC-07.3: [TESTABLE] A variable set by an earlier processor (for example `url`
  from a `URLTextSearcher` named group) counts as declared.
  **Enforced via:** `tests/guardrail_audits_spec.sh`, "knows URLTextSearcher sets
  its named groups, and reads Input past a blank line (KI-8c)".
- AC-07.4: [TESTABLE] A `%token%` that appears only in a comment is not a
  reference.
  **Enforced via:** `tests/guardrail_audits_spec.sh`, "ignores %tokens% that
  appear only in comments".
- AC-07.5: [TESTABLE] A variable used before the step that sets it fails; a
  variable only a shared or unknown processor could set skips; half a pair
  skips.
  **Enforced via:** `tests/python/test_audits.py`,
  `VariablesTest.test_used_before_set_fails` and
  `VariablesTest.test_fr_07_fail_pass_and_skip`; half a pair is planned (planned
  test case).

**Known false results:**

- *False positive:* a built-in processor missing from the model's catalogue
  makes later uses `unverifiable` (SKIP), not FAIL, so the gap is visible but
  the recipe is not checked past that step.
- *False positive:* a `URLTextSearcher` pattern built from a variable that a
  processor sets (not an `Input` value) is not resolved, so its named groups are
  missed.

---

## FR-08 — Folder `Copier` overwrites (`check_copier_overwrite.py`)

[TESTABLE]

**Asserts:** a `Copier` step that copies a folder sets `overwrite: true`.
**Why:** methodology lesson 11 (and lesson 13, which introduced whole-folder
copies). Without it, a second run fails with `[Errno 17] File exists`.
**Input:** a pair.

**Condition:** check every `Copier` step in the effective chain (both recipes).
Its source is a folder if its `source_path`:

- mentions `LOCAL_DIR_PATH`, or ends with `/`; or
- after variable resolution, ends in a bundle suffix: `.app`, `.saver`,
  `.prefPane`, `.plugin`, `.bundle` or `.framework`; or
- resolves to an absolute path that is an existing folder on this machine.

A folder `Copier` whose `overwrite` is not true (`true`, `True`, `yes`, `Yes`
or `1`) fails. No folder `Copier`: PASS.

**Acceptance Criteria:**

- AC-08.1: [TESTABLE] A `Copier` with `source_path: "%LOCAL_DIR_PATH%"` and no
  `overwrite: true` fails; with it, passes.
  **Enforced via:** `tests/python/test_audits.py`,
  `CopierOverwriteTest.test_fr_08_folder_copies_need_overwrite`.
- AC-08.2: [TESTABLE] A `Copier` whose source is a folder by another route
  (`%pathname%/App.app` out of a mounted DMG, or a trailing `/`) is checked too,
  and a `Copier` in the pkg recipe is checked. A single-file copy is not checked.
  **Enforced via:** `tests/python/test_audits.py`,
  `CopierOverwriteTest.test_fr_08_folder_copies_need_overwrite`,
  `CopierOverwriteTest.test_pkg_recipe_copiers_are_checked_too` and
  `CopierOverwriteTest.test_a_file_copy_is_not_checked`.

**Known false results:**

- *False negative:* a folder source with no bundle suffix, no trailing `/` and
  no `LOCAL_DIR_PATH`, that does not exist on this machine (for example a plain
  folder inside a DMG), is taken for a file.

---

## FR-09 — README present (`check_readme_exists.py`)

[TESTABLE]

**Asserts:** each app folder has a `README.md`.
**Why:** `guardrails/GUARDRAILS.md` (Known Constraints) requires a per-app README
recording the pattern, the reason, and the bugs found. Lessons 16, 24 and 25 say
what it must record; lesson 26 warns that READMEs drift.
**Input:** an app folder (a recipe file target means its folder).

**Condition:** PASS if the folder holds an entry named exactly `README.md` that
is a non-empty file. Otherwise FAIL.

**Acceptance Criteria:**

- AC-09.1: [TESTABLE] An app folder without `README.md` fails; with an empty one,
  fails; with a non-empty one, passes.
  **Enforced via:** `tests/python/test_audits.py`, `ReadmeTest.test_fr_09`.

**Known false results:**

- *Scope:* presence only. Whether the README matches the recipe (lesson 26) is not
  checked.
- *Message (intentional):* the FAIL cites `guardrails/GUARDRAILS.md`, where the
  rule lives, not a methodology lesson.

---

## FR-10 — Recipe pairing (`recipe_pairing`)

[TESTABLE]

**Asserts:** the pair's recipes form a proper pair: the pkg recipe's
`ParentRecipe` is its sibling download recipe, both halves exist, and the recipes
are YAML.
**Why:** every other audit judges the effective chain. Without this check, a pkg
recipe with a wrong or missing parent would leave its sibling download recipe
unchecked, silently.
**Input:** a pair. There is no `guardrails/audit/` script; it runs through
`run_all` and preflight only. It runs first.

**Condition:** FAIL for each of the recipe model's findings
(`specs/recipekit/01-recipe-model.md` FR-04, FR-09) about a recipe in this pair
with one of these codes:

| Model finding | Meaning |
|---|---|
| `pair_incomplete` | no download or no pkg recipe with the same stem |
| `parent_mismatch` | the pkg recipe's `ParentRecipe` is loaded but is not the sibling download recipe |
| `parent_missing` | a `ParentRecipe` is not in the loaded folders |
| `plist_recipe` | a plist recipe inside a recipe repo |

No such finding: PASS.

**Acceptance Criteria:**

- AC-10.1: [TESTABLE] A pkg recipe whose `ParentRecipe` is not its sibling
  download recipe fails; a proper pair passes.
  **Enforced via:** `tests/python/test_audits.py`,
  `PairingTest.test_a_parent_that_is_not_the_sibling_fails`.
- AC-10.2: [TESTABLE] Half a pair, and a plist recipe in a recipe repo, fail.
  **Enforced via:** planned test (planned test case).

**Known false results:**

- *By design:* half a pair fails here, while FR-04 and FR-07 report SKIP for it.
  This audit says the pair is wrong; they say they could not check it.

---

## Architecture-Incompatible Patterns

**AIP-01: Reading recipe text to fix a false result.** Fix it in the recipe model,
or add a fixture that pins the case. **Enforced via:** reviewer check.

**AIP-02: An audit that passes when it could not look.** See constitution
AIP-04; report SKIP. **Enforced via:** reviewer check;
`PathnameTest.test_ac_04_2_missing_download_is_skip`.

**AIP-03: Hard-coding a single valid form.** One certificate authority (FR-05,
KI-8b) remains. The lessons describe a behaviour; the audit must accept every
recipe that has it. **Enforced via:** reviewer check; the clean fixtures in
`tests/python/test_audits.py`.

---

## Open Questions

**OQ-1:** **(Resolved 2026-09-27)** Yes: only a `PathDeleter` before the first
staging step fails. Original question: FR-02: should the audit fail only a `PathDeleter` that runs before the
first staging step (what lesson 2 says), and allow one at the end?

**OQ-2:** **(Resolved 2026-09-27)** Yes: both report SKIP. Original question:
FR-04 and FR-07 silently skip a missing sibling. Report it (constitution
OQ-2)?

**OQ-3:** **(Resolved 2026-09-27)** This audit passes a `requirement` step and
defers to the linter's CSV-005. Original question: when a verifier uses
`requirement`, should this audit pass it
(defer to the linter's CSV-005), or should it check the requirement's own
anchors (`anchor apple generic`, a certificate OID, `subject.OU`)?

**OQ-4:** **(Resolved 2026-09-27)** Any non-empty comment on the flag's line or
directly above it, found from the file's lines after a YAML parse confirms the
flag. Original question: FR-06: what counts as "an explanatory comment"? Proposed: any comment
on or directly above the `NO_CODE_SIGNATURE_REQUIRED` line, which the recipe model
can report because it keeps line numbers.

**OQ-5:** **(Resolved 2026-09-27)** `BUILTIN_VARS` is gone, and the three
hard-coded setters are replaced by a table of core processors and their outputs
(FR-07). Taking that table from the recipe model is left for the port (see
OQ-8). Original question: FR-07: remove the unused `BUILTIN_VARS`, and take the
list of processor-set variables from the recipe model rather than a hard-coded
three.

**OQ-6:** **(Resolved 2026-09-27)** Yes to both: every `Copier` in the chain,
with folder sources recognised by shape (FR-08). Original question: FR-08: should the audit also run on pkg recipes, and should it
recognise a directory source by its shape (`.app`, trailing `/`, no extension)?

**OQ-7:** **(Resolved 2026-09-27)** Fixed by the port: argparse, spec named in
each docstring, the model instead of regex, typed signatures. Original question:
Deviations from `.devagent/standards/python-code-standards.md`, to fix
when each audit is ported:
- `main(argv)` reads `sys.argv` by hand instead of `argparse`, so there is no
  `--help` and extra arguments are ignored.
- The module docstring does not name its governing spec.
- Four audits (FR-02, FR-03, FR-04, FR-08) still read recipe content with
  regex, not a YAML parser (standards "Pitfalls"; toolkit AIP-08). FR-05 to
  FR-07 now use PyYAML.
- Signatures use bare `list` / `set` instead of `list[str]`, `set[str]`.

**OQ-8:** **(Resolved 2026-09-27)** Outputs come from the model's catalogue; a
variable only an unknown processor could set is SKIP. Original question: FR-07: a processor not in the table is assumed to set nothing. Should
unknown processors make the audit say "could not check" (constitution AIP-04)
instead of failing on their outputs, and should the table come from AutoPkg's
own `output_variables` (or the recipe model) rather than a copy in the audit?

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-09-27 | Initial spec, written from the existing implementation. |
| 0.2 | 2026-09-27 | Updated for the fixes to KI-30 and KI-8c. |
| 0.3 | 2026-09-27 | Ported onto the recipe model; SKIP result; FR-02 order-aware, FR-03 checks `file://` (KI-8a), FR-08 checks every `Copier`; tests in `tests/python/test_audits.py`. OQ-1, OQ-2, OQ-6 to OQ-8 resolved. |
| 0.4 | 2026-09-27 | Added FR-10 `recipe_pairing`; FR-04 skips when `pathname` is unverifiable; FR-06 cites lesson 7; `cli()` no longer blocked by an invalid sibling; ACs point at the new unittest cases. |
