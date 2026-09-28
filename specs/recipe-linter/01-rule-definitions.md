# Rule Definitions

**Status:** Hardened
**Date:** 2026-07-31
**Requires:** `00-constitution.md`

---

## Purpose

Define how lint rules are structured in the `checks.yaml` runtime config file.
Any linter implementation must interpret rules in this format.

### Normative vs. Informative Content

- **Normative (MUST/MUST NOT):** The rule YAML schema (§2), field reference
  (§2.1), value comparison types (§3), severity levels (§4), and key path
  resolution (§5). These define what a conforming implementation must support.
- **Informative (reference implementation):** Example rule YAML blocks and the
  specific rule IDs mentioned (e.g., "IDN-001"). A conforming implementation
  may support any rule IDs and may use different example values.

### Classification Key

- **[TESTABLE]** — Observable and automatable. Enforcement mechanism stated.
- **[STRUCTURAL]** — Enforced by schema, layout, or data model constraint.
- **[ADVISORY]** — Review judgment. Reserved for genuine non-checkables.

---

## 1. Rule Structure

Every rule in `checks.yaml` is an entry in the `rules:` array with this format:

```yaml
- id: "RULE-001"
  severity: "error"          # error | warning | info
  description: "Explanation of what the rule checks"
  recipe_type: "download"    # download | pkg | both
  check_target:
    key: "Identifier"        # YAML key to inspect (dot-notation for nested)
    source: "self"           # self | related-file | directory
    # When source is "related-file":
    related_type: "download_recipe"  # download_recipe | pkg_recipe | overrides | autopkg_config
    related_key: "ParentRecipe"      # Which key in the related file to compare
  allowed_values:
    type: "regex"            # regex | exact | list | exists | not_exists | absent
    pattern: "^regex$"       # For type: regex or exact
    list: ["a", "b"]         # For type: list
    min_version: "2.3"       # For version comparisons
  pass_message: "Message when check passes"
  fail_message: "Message when check fails (use %value% for actual value)"
  prompted_by: "Standards §X.Y — context about why this rule exists"
  required: false            # optional; default true. false = a customer may skip it
```

### 1.1 Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique alphanumeric ID (e.g., IDN-001, SRC-002) |
| `severity` | Yes | One of: `error` (exit 1), `warning` (non-zero exit), `info` (no exit impact) |
| `description` | Yes | Human-readable summary of what this rule validates |
| `recipe_type` | Yes | `download`, `pkg`, or `both` — filters which recipe files get this check |
| `check_target.key` | Conditional | Dot-notation path to the YAML key (e.g., `Identifier`, `Input.NAME`, `Process` for processor lists). Required for every type except `exists_any`, where each condition supplies its own target. |
| `check_target.source` | Yes | `self` = inspect this recipe file; `related-file` = inspect a companion file; `directory` = inspect directory structure |
| `check_target.related_type` | Conditional | Required when `source: related-file`. One of: `download_recipe`, `pkg_recipe`, `overrides`, `autopkg_config`. Upstream's `config/checks.yaml` uses only the recipe types; `overrides` and `autopkg_config` are for a fork's own sidecar rules (`03-cross-file-checks.md` §3) |
| `check_target.related_key` | Conditional | Required when `source: related-file`. The key in the related file to compare against `check_target.key` |
| `allowed_values.type` | Yes | One of: `regex`, `exact`, `list`, `exists`, `not_exists`, `absent`, `exists_any` |
| `allowed_values.conditions` | Conditional | Required for `exists_any`. A list of condition maps (§2.7). |
| `allowed_values.pattern` | Conditional | Regex pattern (for `regex` type) or exact string (for `exact` type). Required for those types. |
| `allowed_values.list` | Conditional | Array of allowed strings. Required for `list` type. |
| `allowed_values.min_version` | Conditional | Minimum version string (for version comparison checks). Optional. |
| `pass_message` | Yes | Message emitted when check passes |
| `fail_message` | Yes | Message emitted when check fails. Use `%value%` as placeholder for the actual value found, `%key%` for the key path, `%file%` for the filename. |
| `prompted_by` | No | Reference to the standards (`reference/recipe-standards.md`, cited as "Standards §x") or the real-world incident that motivated this rule |
| `required` | No | `true` (the default when absent) or `false`. A customer's `checks.local.yaml` may `skip:` only rules with `required: false`; skipping a required rule exits 2 (`specs/toolkit/02-customers.md` FR-04). In upstream's `config/checks.yaml` the optional rules are SRC-002, SRC-003, NAM-002, NAM-003, DIR-001, MIN-001 and CMT-001 to CMT-004. |

A customer's `checks.local.yaml` adds rules with this same schema under `rules:`. An
added rule's `id` must not repeat a kit rule's id (exit 2). See `docs/FORMATS.md` §11.

---

## 2. Value Comparison Types

### 2.1 `regex`

[STRUCTURAL] The value at `check_target.key` must match the regex pattern in
`allowed_values.pattern`.

```yaml
allowed_values:
  type: "regex"
  pattern: "^com\\.acmefruit\\.autopkg\\.download\\..+$"
```

**AC-2.1.1:** [TESTABLE] A value matching the pattern passes. **Enforced via:**
automated test — run rule against known-matching input; assert pass.
**AC-2.1.2:** [TESTABLE] A value NOT matching the pattern fails. **Enforced
via:** automated test — run rule against known-non-matching input; assert fail.

### 2.2 `exact`

[STRUCTURAL] The value at `check_target.key` must exactly equal
`allowed_values.pattern`.

```yaml
allowed_values:
  type: "exact"
  pattern: "com.acmefruit.autopkg.download.MicrosoftTeams"
```

**AC-2.2.1:** [TESTABLE] An exact match passes. **Enforced via:** automated
test.
**AC-2.2.2:** [TESTABLE] Any deviation fails (case-sensitive). **Enforced via:**
automated test.

### 2.3 `list`

[STRUCTURAL] The value at `check_target.key` must be one of the values in
`allowed_values.list`.

```yaml
allowed_values:
  type: "list"
  list: ["SparkleUpdateInfoProvider", "GitHubReleasesInfoProvider", "URLTextSearcher"]
```

**AC-2.3.1:** [TESTABLE] A value present in the list passes. **Enforced via:**
automated test.
**AC-2.3.2:** [TESTABLE] A value NOT in the list fails. **Enforced via:**
automated test.

### 2.4 `exists`

[STRUCTURAL] The key at `check_target.key` must exist in the recipe (value can
be anything non-null).

```yaml
allowed_values:
  type: "exists"
```

**AC-2.4.1:** [TESTABLE] A recipe with the key present passes. **Enforced via:**
automated test.
**AC-2.4.2:** [TESTABLE] A recipe missing the key fails. **Enforced via:**
automated test.

### 2.5 `not_exists`

[STRUCTURAL] The key at `check_target.key` must NOT exist in the recipe.

**AC-2.5.1:** [TESTABLE] A recipe missing the key passes. **Enforced via:**
automated test.
**AC-2.5.2:** [TESTABLE] A recipe with the key present fails. **Enforced via:**
automated test.

### 2.6 `absent`

[STRUCTURAL] The key at `check_target.key` must exist, but its value must be
empty/null/absent.

**AC-2.6.1:** [TESTABLE] A recipe with an empty/null value at the key passes.
**Enforced via:** automated test.
**AC-2.6.2:** [TESTABLE] A recipe with a non-empty value at the key fails.
**Enforced via:** automated test.

---

### 2.7 `exists_any`

[STRUCTURAL] The rule passes if **at least one** listed condition matches. Use it
when several recipe shapes are all legitimate proofs of the same fact (for example,
"version is accounted for" by a download-recipe processor, by a vendor-drop
`LOCAL_FILE_PATH`, or by extraction in the paired pkg recipe).

```yaml
allowed_values:
  type: "exists_any"
  conditions:
    - source: "self"                  # self | related-file
      key: "Process"                  # key path per §4 (self conditions)
      pattern: "(Versioner|AppDmgVersioner)"
    - source: "related-file"
      related_type: "pkg_recipe"      # download_recipe | pkg_recipe | overrides | autopkg_config
      related_key: "Process"          # key read from the companion; the literal "exists" = presence only
      pattern: "FlatPkgUnpacker.*Versioner"
```

Semantics:
1. Conditions are evaluated in order. The first match short-circuits to PASS, and the
   matched value (plus companion path, if any) is reported.
2. A `self` condition resolves `key` in the recipe under test. A `related-file`
   condition resolves `related_key` in the companion found by `related_type` (§ Cross-File
   Checks, companion discovery). `related_key: "exists"` treats companion presence as
   the value `present`.
3. A `pattern` starting with `!` is **negated**: the condition holds when the value
   does *not* match the rest of the pattern (e.g. `"!Processor:[[:space:]]*PkgCreator"`
   — "this recipe doesn't build a package"). This is how an implication ("if the
   recipe uses PkgCreator, then pkgname carries the prefix") is written as a
   disjunction.
4. `pattern` is an extended regex matched against the resolved value, with the same
   unescaping as `exists` (§2.4). `".+"` means "non-empty" and `"^$"` means
   "absent or empty".
5. A missing companion makes that condition unsatisfied. It is not an error and never
   produces `__COMPANION_MISSING__`.
6. An empty `conditions:` list (or `conditions: []`) always FAILS.
7. Values are double-quoted scalars, one condition per `- source:` item. `pattern` MUST
   NOT contain `;` (reserved by the reference implementation's condition serializer).

**AC-2.7.1:** [TESTABLE] The first condition matching gives PASS. **Enforced via:** automated test (EXA-001).
**AC-2.7.2:** [TESTABLE] A later condition matching, with earlier ones missing, gives PASS. **Enforced via:** automated test (EXA-004).
**AC-2.7.3:** [TESTABLE] All conditions missing gives FAIL. **Enforced via:** automated test (EXA-004 all-miss).
**AC-2.7.4:** [TESTABLE] A missing companion with no other match gives FAIL, not a crash. **Enforced via:** automated test (EXA-002).
**AC-2.7.5:** [TESTABLE] An empty conditions list gives FAIL. **Enforced via:** automated test (EXA-003).
**AC-2.7.6:** [TESTABLE] A `related-file` condition matches through `related_key`. **Enforced via:** automated test (**new**; covers KI-3a).

### 2.8 `classification`

[STRUCTURAL] The rule passes if the pattern the recipe **claims** in the value of
`check_target.key` (normally `Comment`) is what the classifier concludes from the
recipe pair's processors (`specs/analysis/classify-recipe/`, built on the recipe
model, `specs/recipekit/`). No `pattern` is used.

```yaml
check_target:
  key: "Comment"
  source: "self"
allowed_values:
  type: "classification"
```

Semantics:
1. The claim is the label after a leading `Pattern ` in the value (`Pattern 4d — …`
   claims `4d`).
2. The rule passes when the claim equals the classification, or one of its
   alternatives when the classifier is uncertain (a faux DMG classifies as `7`, with
   `4c` as the alternative).
3. A claim of the number alone (`Pattern 4`) accepts any letter of that pattern.
   Generic templates use it.
4. It passes, without judging, when there is nothing to judge: no `Pattern` claim
   (CMT-003's business), no complete download/pkg pair in the folder (SEN-001's), or a
   classification of `?` or `!` (the classifier can't decide, or PKG-001 applies).
5. On failure, `%value%` is the claim and `%related_value%` is the classification
   (with alternatives joined by `or`).

This is the one comparison type that asks the recipe model instead of matching
text; it exists because a label is a claim to check against what the recipe does
(methodology lesson 26), which text matching can't do.

**AC-2.8.1:** [TESTABLE] A matching claim passes; a wrong claim fails, naming both. **Enforced via:** `tests/python/test_lint.py` (`ClassificationRuleTest`).
**AC-2.8.2:** [TESTABLE] An uncertain classification accepts its alternative. **Enforced via:** `ClassificationRuleTest.test_an_uncertain_alternative_passes`.
**AC-2.8.3:** [TESTABLE] A family claim accepts any letter. **Enforced via:** `ClassificationRuleTest.test_a_family_claim_accepts_any_letter`.
**AC-2.8.4:** [TESTABLE] No claim, or half a pair, passes without judging. **Enforced via:** `ClassificationRuleTest.test_no_claim_and_half_a_pair_are_not_judged`.

**Open question OQ-2.7:** exists_any expresses a disjunction. The "if the recipe is
vendor-drop, then `Input.version` is required" check needs an implication
primitive (`requires_when`), which is not designed. Don't emulate it by putting a
negated precondition inside `exists_any`.

## 3. Severity Levels

[STRUCTURAL] Every rule declares a severity. All severities affect exit code as
defined in Constitution §2.2.

| Severity | Exit Code Impact | Display Color |
|----------|-----------------|---------------|
| `error` | Sets exit code to 1 | Red |
| `warning` | Sets exit code to 1 | Yellow |
| `info` | No exit code impact | Blue |

**AC-3.1:** [TESTABLE] A rule with severity `error` that fails produces exit
code 1. **Enforced via:** automated test — run linter on input that triggers an
error rule; assert exit 1.

**AC-3.2:** [TESTABLE] A rule with severity `warning` that fails produces exit
code 1. **Enforced via:** automated test — run linter on input that triggers a
warning rule; assert exit 1.

**AC-3.3:** [TESTABLE] A rule with severity `info` that fails does NOT affect
exit code; exit code 0 if no error/warning rules fail. **Enforced via:**
automated test — run linter with only info-level failures; assert exit 0.

**AC-3.4:** [STRUCTURAL] An invalid severity value in `checks.yaml` is a config
error per Constitution §4.2, producing exit code 2. **Enforced via:** automated
test — run linter with `severity: critical` in a rule; assert exit 2.

---

## 4. Key Path Resolution

[STRUCTURAL] Dot-notation in `check_target.key` is resolved left-to-right
through YAML nesting:

| Key Path | Resolves To |
|----------|-------------|
| `Identifier` | Top-level `Identifier:` value |
| `Input.NAME` | `Input:` → `NAME:` value |
| `Process` | Full list of processors in the Process section |
| `Process.0` | First processor entry |
| `Process.0.Arguments.url` | The `url:` argument of the first processor |

**AC-4.1:** [TESTABLE] A dot-notation path resolves to the correct nested YAML
value. **Enforced via:** automated test — parse known recipe; assert each path
in the table above resolves correctly.

**AC-4.2:** [TESTABLE] A path to a non-existent nested key produces an
actionable failure message, not a crash. **Enforced via:** automated test —
define rule with path `Process.5.Processor` on a recipe with 3 processors;
assert clear fail.

---

## 5. Architecture-Incompatible Patterns

**AIP-01: Hardcoded rule logic.** Any check that inspects specific identifiers,
keys, or allowed values outside of `checks.yaml` violates Constitution §1
(Config-Driven). The linter engine must be generic; rule details live in config.

**AIP-02: Silent skip.** A rule that cannot determine pass/fail but reports pass
anyway violates Constitution §2 (Transparent Reporting). If the comparison
cannot be made, the result is a fail with an explanatory message.

**AIP-03: Non-deterministic output.** A rule whose result depends on system
state, network, timing, or randomness violates Constitution §3 (Deterministic
Validation). Identical input produces identical output across runs.

**AIP-04: Crash on invalid input.** The linter crashing on malformed YAML,
missing keys, or invalid severity values violates Constitution §4 (Graceful
Degradation). Every invalid input produces a structured failure.

**AIP-05: False pass on missing companion.** A cross-file check that cannot
find its companion file and reports pass (rather than fail) violates
Constitution §5 (Cross-File Integrity). Missing companion = fail with message.

**AIP-06: Exit code 0 when errors exist.** Returning exit 0 when any
high/critical severity rule has failed violates Constitution §5.3. CI pipelines
depend on exit code correctness.

---

## 6. Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-07-31 | Initial release |
| 1.1 | 2026-07-31 | Hardened with methodology: Normative/Informative split, classification tags, AIPs, enforcement mechanisms |
| 1.2 | 2026-09-26 | Add `exists_any` (§2.7); org tokens (`{{IDENTIFIER_PREFIX}}` etc.) documented in `config/checks.yaml` |
| 1.3 | 2026-09-27 | .overrides optional; .autopkg_config removed from upstream. Upstream rules no longer read either file (CSV-006, CFG-001, CFG-002 removed); the engine keeps `related_type: overrides` / `autopkg_config` for forks |
| 1.4 | 2026-09-27 | Add `classification` (§2.8), the first comparison type backed by the recipe model; rule CMT-004 uses it |
| 1.5 | 2026-09-27 | Add the optional `required` field (default true): a customer may skip only rules marked `required: false` (`specs/toolkit/02-customers.md` FR-04) |
