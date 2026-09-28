# Config File Parsing

**Status:** Hardened
**Date:** 2026-07-31
**Requires:** `00-constitution.md`, `01-rule-definitions.md`

---

## Purpose

Define what config files the linter must be able to parse, what fields to
extract from each, and how to detect syntax errors in each format.

### Normative vs. Informative Content

- **Normative (MUST/MUST NOT):** The file formats the linter must parse
  (`.recipe.yaml`, `.overrides`, `.autopkg_config`, `checks.yaml`), the fields
  it must extract, the syntax validation rules per file type, and the acceptance
  criteria. These define what a conforming implementation does.
- **Informative (reference implementation):** The specific field names in the
  examples (e.g., `teamid`, `auto_rebuild`, `tf_name`) and the example YAML
  blocks. Upstream requires neither `.overrides` nor `.autopkg_config` and ships no
  rule that reads them; the parsers exist so a fork can lint its own sidecar files
  (`03-cross-file-checks.md` §3). A conforming implementation may use different field names as long as
  it satisfies the normative parsing and extraction contracts.

### Classification Key

- **[TESTABLE]** — Observable and automatable. Enforcement mechanism stated.
- **[STRUCTURAL]** — Enforced by schema, layout, or data model constraint.
- **[ADVISORY]** — Review judgment. Reserved for genuine non-checkables.

---

## 1. AutoPKG Recipe YAML (`.recipe.yaml`)

### 1.1 File Format

[STRUCTURAL] Standard YAML with the following AutoPKG-specific structure:

```yaml
Comment: Human-readable description
Description: Longer description
Identifier: com.acmefruit.autopkg.download.AppName
MinimumVersion: "2.3"
Input:
  NAME: AppName
  DOWNLOAD_URL: "https://vendor.com/download/latest"
Process:
  - Processor: URLDownloader
    Arguments:
      url: "%DOWNLOAD_URL%"
      filename: "%NAME%.dmg"
  - Processor: CodeSignatureVerifier
    Arguments:
      input_path: "%pathname%/App.app"
      requirement: "anchor apple generic and identifier ..."
```

### 1.2 Fields to Extract

[STRUCTURAL] The linter must parse the following fields from any valid recipe:

| Key Path | Type | Description |
|----------|------|-------------|
| `Identifier` | String | Recipe identifier (required) |
| `ParentRecipe` | String | Parent recipe identifier (pkg recipes only, optional) |
| `MinimumVersion` | String | Minimum AutoPkg version required |
| `Input.NAME` | String | App name input variable |
| `Input.APP_FILENAME` | String | App bundle filename (when differs from NAME) |
| `Process` | Array of processors | Ordered list of processor steps |
| `Process[N].Processor` | String | Processor name (e.g., URLDownloader) |
| `Process[N].Arguments` | Dict | Processor-specific arguments |

**AC-1.2.1:** [TESTABLE] All fields listed in §1.2 are extracted from a valid
recipe. **Enforced via:** automated test — parse example-download-recipe.yaml;
assert each field is present and correctly typed.

**AC-1.2.2:** [TESTABLE] A recipe missing `Identifier` or `Process` is rejected
with a clear fail message. **Enforced via:** automated test — parse recipe
missing those keys; assert fail.

### 1.3 Syntax Validation

[STRUCTURAL] The linter must detect and report:

| Issue | Detection | Severity |
|-------|-----------|----------|
| Invalid YAML syntax | YAML parse error | error |
| Missing `Identifier` | Key not present | error |
| Missing `Process` section | Section not present | error |
| Empty Process section | Process: with no entries | error |
| Unparseable processor arguments | Processor block with no Arguments | warning |

**AC-1.3.1:** [TESTABLE] Invalid YAML syntax is reported with line number and
description. **Enforced via:** automated test — run linter on malformed YAML;
assert error reported with line number.

**AC-1.3.2:** [TESTABLE] Each issue in the table above is detected and produces
the correct severity. **Enforced via:** automated test — one test per issue
type.

---

## 2. `.overrides` Files

`.overrides` is an optional, org-defined file (Standards §3.4). AutoPkg never reads
it; `bin/run-recipes.sh` passes its lines to `autopkg run` as `--key`. Upstream lint
rules don't read it. The parser below serves forks that add rules for it.

### 2.1 File Format

[STRUCTURAL] A flat text file with `key=value` pairs, one per line. Lines
starting with `#` and blank lines are ignored/comments.

```text
# Written by the pipeline at run time; never committed
LICENSE_KEY=REPLACE_AT_RUN_TIME

# Which MDM server this run uploads to
JSS_URL=https://jamf.acmefruit.example
```

(The test fixture `artifacts/example-overrides.txt` uses older keys such as `teamid`;
the parser treats every key the same.)

### 2.2 Fields to Extract

[STRUCTURAL] The linter must parse every `key=value` pair. No key is required or
special-cased; which keys a fork expects is up to that fork's own rules.

**AC-2.2.1:** [TESTABLE] All key=value pairs are extracted from a valid
overrides file. **Enforced via:** automated test — parse example-overrides.txt;
assert all pairs extracted.

### 2.3 Syntax Validation

[STRUCTURAL] The linter must detect and report:

| Issue | Detection | Severity |
|-------|-----------|----------|
| Empty file | File exists but has no non-comment content | warning |
| Malformed line (no `=` separator) | Line contains no `=` | error |
| Empty key (e.g., `=value`) | Text before `=` is empty | error |
| Empty value (e.g., `key=`) | Text after `=` is empty | warning |
| Duplicate key | Same key appears more than once | error |
| Smart quotes present | Line contains Unicode curly quotes | error |

**AC-2.3.1:** [TESTABLE] Empty overrides file produces a warning. **Enforced
via:** automated test — parse malformed-overrides.txt; assert expected issues
detected.

**AC-2.3.2:** [TESTABLE] Each issue in §2.3 is detected with correct severity.
**Enforced via:** automated test — one test per issue type.

**AC-2.3.3:** [TESTABLE] Blank lines and `#` comment lines are correctly
ignored. **Enforced via:** automated test — parse file with comments and blank
lines; assert key extraction is correct.

**AC-2.3.4:** [TESTABLE] Duplicate keys resolve to the last occurrence (override
semantics). **Enforced via:** automated test — parse file with duplicate key;
assert last occurrence wins; assert duplicate-key issue is reported.

---

## 3. `.autopkg_config` Files

Upstream defines no deployment-pipeline metadata file (Standards §3.5). The
`.autopkg_config` parser is kept for forks that keep such a sidecar and lint it with
`related_type: "autopkg_config"` rules. The keys below are one example layout.

### 3.1 File Format

[STRUCTURAL] A flat text file with `key: value` pairs (YAML-like), one per line.
Lines starting with `#` and blank lines are ignored/comments.

```text
# Workflow metadata
auto_rebuild: true
promote_to: prod
regions: [global]
tf_name: microsoft_teams
```

### 3.2 Fields to Extract

[STRUCTURAL] The linter must parse every `key: value` pair. Example keys (informative):

| Key | Type | Description |
|-----|------|-------------|
| `auto_rebuild` | Boolean string | Whether workflow rebuilds automatically |
| `promote_to` | String | Highest environment for promotion |
| `regions` | String (array-like) | Region list |
| `tf_name` | String | Terraform resource name |
| `legacy_package_prefix` | String | Previous naming convention (optional) |

**AC-3.2.1:** [TESTABLE] All key: value pairs are extracted from a valid
config file. **Enforced via:** automated test — parse example-autopkg-config.txt;
assert all pairs extracted.

### 3.3 Syntax Validation

[STRUCTURAL] The linter must detect and report:

| Issue | Detection | Severity |
|-------|-----------|----------|
| Empty file | File exists but has no non-comment content | warning |
| Malformed line (no `:` separator) | Line contains no `:` | error |
| Empty key (e.g., `: value`) | Text before `:` is empty | error |
| Smart quotes present | Line contains Unicode curly quotes | error |

**AC-3.3.1:** [TESTABLE] Each issue in §3.3 is detected with correct severity.
**Enforced via:** automated test — one test per issue type.

**AC-3.3.2:** [TESTABLE] Blank lines and `#` comment lines are correctly
ignored. **Enforced via:** automated test — parse file with comments and blank
lines; assert key extraction is correct.

---

## 4. `checks.yaml` (Runtime Config)

### 4.1 File Format

[STRUCTURAL] YAML with a `rules:` top-level key containing an array of rule
objects as defined in `01-rule-definitions.md`.

### 4.2 Syntax Validation

[STRUCTURAL] The linter must detect and report:

| Issue | Detection | Severity |
|-------|-----------|----------|
| Invalid YAML syntax | YAML parse error | error |
| Missing `rules:` key | No rules array | error |
| Empty rules array | `rules: []` | error |
| Rule missing required field | Field absent per §2.1 schema | error |
| Invalid severity value | Not one of error/warning/info | error |
| Invalid allowed_values.type | Not one of the defined types | error |
| Duplicate rule ID | Same `id` appears in more than one rule | error |

**AC-4.2.1:** [TESTABLE] Invalid `checks.yaml` is rejected with exit code 2 and
a clear error message. **Enforced via:** automated test — run linter with a
malformed checks.yaml; assert exit 2.

**AC-4.2.2:** [TESTABLE] Each issue in §4.2 is detected. **Enforced via:**
automated test — one test per issue type (except invalid severity and
allowed_values.type, which are tested separately below).

### 4.3 Acceptance Criteria

**AC-4.3.1:** [TESTABLE] `checks.yaml` is parsed and validated before any recipe
checks run. **Enforced via:** automated test — run linter with valid checks.yaml
but no recipe files; assert config parsing succeeds.

**AC-4.3.2:** [STRUCTURAL] Config errors are reported independently of recipe
errors. **Enforced via:** automated test — run linter with invalid config and
valid recipes; assert config error is reported; assert recipe checks are not
attempted or are cleanly skipped.

**AC-4.3.3:** [TESTABLE] Invalid config produces exit code 2. **Enforced via:**
automated test.

---

## 5. Architecture-Incompatible Patterns

**AIP-01: YAML-only parsing.** Assuming the linter only handles `.recipe.yaml`
files (ignoring `.overrides` and `.autopkg_config`) violates Constitution §5
(Cross-File Integrity): a fork's cross-file rules must be able to read its companion
files, even though upstream's rules don't.

**AIP-02: Silent comment inclusion.** Including comment lines or blank lines as
extracted entries violates the format spec. Lines starting with `#` and blank
lines are always ignored.

**AIP-03: Curly quote tolerance.** Accepting smart/curly quotes as valid syntax
would allow human-editing artifacts through CI. Curly quotes are rejected with
error.

**AIP-04: Missing required field handled as warning.** A recipe missing
`Identifier` is an error, not a warning. Exit code must be 1 per Constitution
§2.2.

**AIP-05: Running checks before config validation.** If `checks.yaml` itself is
invalid, running any recipe-level checks would produce undefined results.
Config must be validated first per §4.3.

---

## 6. Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-07-31 | Initial release |
| 1.1 | 2026-07-31 | Hardened with methodology: Normative/Informative split, classification tags, AIPs, enforcement mechanisms |
| 1.2 | 2026-09-27 | .overrides optional; .autopkg_config removed from upstream. Parsers kept for forks; no required keys |
