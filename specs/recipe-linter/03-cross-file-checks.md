# Cross-File Validation

**Status:** Hardened
**Date:** 2026-07-31
**Requires:** `00-constitution.md`, `01-rule-definitions.md`, `02-config-parsing.md`

---

## Purpose

Define how the linter performs cross-file validation — checking relationships
between companion files in the same recipe directory (e.g., download recipe ↔
pkg recipe, recipe ↔ `.overrides`, recipe ↔ `.autopkg_config`).

Upstream's `config/checks.yaml` only uses the recipe companions (`download_recipe`,
`pkg_recipe`). `.overrides` is optional and org-defined, and upstream has no
`.autopkg_config` (Standards §3.4–3.5). The engine keeps `overrides` and
`autopkg_config` support so a fork can lint its own sidecar files with rules in its
own `checks.yaml`.

### Normative vs. Informative Content

- **Normative (MUST/MUST NOT):** Companion file discovery rules (§3),
  comparison types (§4), pair completeness checks (§5), cross-file rule
  structure (§6), all acceptance criteria. These define what a conforming
  implementation does.
- **Informative (reference implementation):** Example companion filenames
  (e.g., `Microsoft-Teams.download.recipe.yaml` as a download recipe), the
  specific example YAML blocks, and placeholder rule IDs (e.g., "IDN-004"). A
  conforming implementation may use different filenames and rule IDs as long as
  the discovery and comparison contracts are satisfied.

### Classification Key

- **[TESTABLE]** — Observable and automatable. Enforcement mechanism stated.
- **[STRUCTURAL]** — Enforced by schema, layout, or data model constraint.
- **[ADVISORY]** — Review judgment. Reserved for genuine non-checkables.

---

## 1. When Cross-File Checks Apply

[STRUCTURAL] A rule with `check_target.source: related-file` triggers
cross-file validation. Instead of inspecting only the primary recipe file, the
linter must:

1. Identify the companion file (based on `related_type` and filename matching
   per §3)
2. Parse the companion file according to its format (`02-config-parsing.md`)
3. Extract the specified value from the companion file
4. Compare the values and report pass/fail per §4 (`check_target.key` vs.
   `related_key`)

---

## 2. Related-File Rules

[STRUCTURAL] Rules with `source: related-file` exist for the following purposes:

| `related_type` | Direction | What Is Checked |
|----------------|-----------|-----------------|
| `download_recipe` | Primary → companion | pkg recipe's `ParentRecipe` matches download recipe's `Identifier` |
| `pkg_recipe` | Primary → companion | download recipe has a corresponding pkg recipe (existence check) |
| `overrides` | Primary → companion | Fork rules only: the fork's `.overrides` contains the keys it requires |
| `autopkg_config` | Primary → companion | Fork rules only: the fork's pipeline-metadata sidecar has the entries it requires |

---

## 3. Companion File Discovery

[STRUCTURAL] The linter must discover companion files based on the directory
containing the primary recipe file and the related type:

| `related_type` | File to Find | Discovery Rule |
|----------------|-------------|----------------|
| `download_recipe` | `AppName.download.recipe.yaml` | Same directory, same app name (extracted from primary filename per §3.1) |
| `pkg_recipe` | `AppName.pkg.recipe.yaml` | Same directory, same app name (extracted from primary filename per §3.1) |
| `overrides` | `.overrides` | Same directory as the recipe file |
| `autopkg_config` | `.autopkg_config` | Same directory as the recipe file |

### 3.1 App Name Extraction

[STRUCTURAL] The app name is extracted from the primary recipe filename by
removing the type-and-format suffix:

| Primary Filename | Extracted App Name |
|-----------------|-------------------|
| `Microsoft-Teams.download.recipe.yaml` | `Microsoft-Teams` |
| `Microsoft-Word.pkg.recipe.yaml` | `Microsoft-Word` |
| `Smartsheet.download.recipe.yaml` | `Smartsheet` |

**AC-3.1.1:** [TESTABLE] App name is correctly extracted from all three
patterns above. **Enforced via:** automated test — run extraction on each
pattern; assert correct app name.

**AC-3.1.2:** [TESTABLE] A filename with an unrecognized recipe type suffix
(e.g., `App.munki.recipe.yaml`) is handled gracefully: the app name extraction
still produces a result, but the linter skips rules targeting related types it
cannot match. **Enforced via:** automated test — parse recipe with unrecognized
type; assert no crash; assert cross-file rules are skipped.

**AC-3.1.3:** [STRUCTURAL] The extraction removes ONLY the known suffix pattern
(`.(download|pkg|munki|jss|abs|local).recipe.yaml`). If a filename does not
match any known pattern, the cross-file check is skipped with an info message.

### 3.2 Error Handling

[STRUCTURAL] When discovering companion files:

| Condition | Behavior |
|-----------|----------|
| Companion file not found | Fail with message: "Required companion file not found: <path>" |
| Companion file invalid (bad syntax) | Fail with message from config parsing |
| Primary recipe type is standalone (no companion needed) | Skip rule silently |

---

## 4. Comparison Types

### 4.1 Exact Match

[STRUCTURAL] The value in the primary recipe must exactly equal the value in the
companion file's specified key.

```yaml
check_target:
  key: "ParentRecipe"
  source: "related-file"
  related_type: "download_recipe"
  related_key: "Identifier"
```

**Behavior:** Read `Identifier` from the download recipe, compare to
`ParentRecipe` in the pkg recipe. Must be exact string match.

**AC-4.1.1:** [TESTABLE] Matching values pass. **Enforced via:** automated test
— create paired recipes with matching Identifier/ParentRecipe; assert pass.
**AC-4.1.2:** [TESTABLE] Mismatched values fail. **Enforced via:** automated test
— create paired recipes with mismatched values; assert fail.

### 4.2 Presence Check

[STRUCTURAL] The companion file must exist and contain the specified key.

```yaml
# A fork's rule: its pipeline-metadata sidecar must name the IaC resource.
check_target:
  key: "Input.NAME"
  source: "related-file"
  related_type: "autopkg_config"
  related_key: "tf_name"
```

**Behavior:** Verify the `.autopkg_config` file exists and contains the `tf_name`
key. (Informative: upstream ships no such rule.)

**AC-4.2.1:** [TESTABLE] Companion file present with required key passes.
**Enforced via:** automated test — create companion with required key; assert
pass.
**AC-4.2.2:** [TESTABLE] Companion file missing required key fails. **Enforced
via:** automated test — create companion without required key; assert fail.
**AC-4.2.3:** [TESTABLE] Companion file absent fails. **Enforced via:**
automated test — run cross-file check without creating companion; assert fail.

### 4.3 Version-based Comparisons

[STRUCTURAL] An optional `min_version` in `allowed_values` enables minimum
version validation:

```yaml
allowed_values:
  type: "regex"
  pattern: "^\\d+\\.\\d+$"
  min_version: "2.3"
```

**Behavior:** After the regex pattern match succeeds, check that the actual
value is ≥ `min_version` in semantic-version comparison.

**AC-4.3.1:** [TESTABLE] A version ≥ min_version passes. **Enforced via:**
automated test — recipe with `MinimumVersion: "2.7"`; assert pass.
**AC-4.3.2:** [TESTABLE] A version < min_version fails. **Enforced via:**
automated test — recipe with `MinimumVersion: "2.0"`; assert fail.
**AC-4.3.3:** [STRUCTURAL] `min_version` is ignored if `allowed_values.type` is
not `regex` or `exact`. **Enforced via:** automated test — define rule with
`type: exists` and min_version present; assert min_version is not evaluated.

---

## 5. Pair Completeness Checks

[STRUCTURAL] When run with `--dir <directory> --pair-check`, the linter must:

1. Scan the entire directory tree for all `.recipe.yaml` files
2. Group files by their extracted app name (see §3.1)
3. For each app name, verify that both a `.download.recipe.yaml` and
   `.pkg.recipe.yaml` exist
4. Flag any app that has only one type

This is a directory-level check, not a per-file check. It is governed by rule
SEN-001 in `checks.yaml`.

### 5.1 Pair Check Behavior

[STRUCTURAL]

| Scenario | Verdict | Message |
|----------|---------|---------|
| Both download and pkg exist | PASS | "AppName: download + pkg pair complete" |
| Only download exists | FAIL | "AppName: missing pkg recipe" |
| Only pkg exists | INFO | "AppName: pkg recipe without download (standalone?)" |

**AC-5.1.1:** [TESTABLE] A directory with complete pairs passes all
pair-completeness checks. **Enforced via:** automated test — run `--pair-check`
on directory with paired recipes; assert pass.
**AC-5.1.2:** [TESTABLE] A directory with an orphaned download recipe fails
with expected message. **Enforced via:** automated test — run `--pair-check` on
directory with only download recipes; assert fail.
**AC-5.1.3:** [TESTABLE] A directory with a standalone pkg recipe passes with
info-level note. **Enforced via:** automated test — run `--pair-check` on
directory with only pkg recipes; assert info.

### 5.2 Duplicate Detection

[STRUCTURAL] When run with `--dir <directory>`, the linter must also detect:

| Scenario | Verdict | Message |
|----------|---------|---------|
| Multiple download recipes for the same app name | ERROR | "AppName: multiple download recipes found" |
| Multiple pkg recipes for the same app name | ERROR | "AppName: multiple pkg recipes found" |
| Multiple duplicate recipes in different directories | ERROR | "Duplicate recipe: <path1> and <path2>" |

---

## 6. Cross-File Rules in checks.yaml

[STRUCTURAL] Rules that perform cross-file validation follow this structure:

```yaml
- id: "IDN-004"
  severity: "error"
  description: "ParentRecipe must match download recipe Identifier"
  recipe_type: "pkg"
  check_target:
    key: "ParentRecipe"          # From this file (pkg recipe)
    source: "related-file"
    related_type: "download_recipe"
    related_key: "Identifier"    # From the companion download recipe
  allowed_values:
    type: "regex"                # Applied to the comparison result
    pattern: "must match"
  pass_message: "ParentRecipe matches download Identifier"
  fail_message: "ParentRecipe (%value%) does not match download Identifier (%related_value%)"
  prompted_by: "Standards §6.7 item 1 — Recipe Robot namespace collision bug"
```

### 6.1 Message Placeholder Variables

[STRUCTURAL] Placeholder variables available in `pass_message` and
`fail_message`:

| Variable | Replaced With |
|----------|---------------|
| `%value%` | The value from the primary recipe's `check_target.key` |
| `%related_value%` | The value from the companion file's `related_key` |
| `%file%` | The primary recipe filename |
| `%related_file%` | The companion filename |
| `%key%` | The dot-notation key path being inspected |

**AC-6.1.1:** [TESTABLE] Each placeholder variable is replaced with the correct
value in rule output messages. **Enforced via:** automated test — define rule
with all placeholders used; trigger check; assert each placeholder is resolved.

---

## 7. Architecture-Incompatible Patterns

**AIP-01: Hardcoded app name extraction.** App name extraction logic that does
not use the suffix-removal pattern (or that is not configurable) violates
Constitution §1 (Config-Driven). The extraction pattern should be deriveable
from config, not hardcoded.

**AIP-02: Missing companion → pass.** Failing to find a required companion file
and reporting PASS instead of FAIL violates Constitution §5 (Cross-File
Integrity). Every required companion must be present; if not, the rule fails.

**AIP-03: Cross-directory search.** Searching outside the primary recipe's
directory for companion files violates the single-directory convention assumed
by AutoPKG recipe batchers. Companion files always live in the same directory
as the primary recipe.

**AIP-04: Silent duplicate.** Detecting a duplicate recipe file and not
reporting it violates Constitution §2 (Transparent Reporting). Every duplicate
is an error.

**AIP-05: Pair check runs per-file.** Running the `--pair-check` logic per-file
(without a directory-level grouping pass) would miss cross-app relationships.
Pair check is always a directory-level operation.

---

## 8. Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-07-31 | Initial release |
| 1.1 | 2026-07-31 | Hardened with methodology: Normative/Informative split, classification tags, AIPs, enforcement mechanisms |
| 1.2 | 2026-09-27 | .overrides optional; .autopkg_config removed from upstream. `overrides` / `autopkg_config` companions documented as fork-only |
