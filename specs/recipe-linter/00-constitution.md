# AutoPKG Recipe Linter — Constitution

**Status:** Hardened
**Date:** 2026-07-31

---

## Purpose

This document establishes the non-negotiable principles of the AutoPKG Recipe
Linter. Every other spec for this tool must conform to these. When a downstream
design decision conflicts with the constitution, the constitution wins and the
decision is revised.

The constitution answers "what kind of tool is this?" — not "what features does
it have?" Features change; principles don't.

**On enforcement.** Most principles below are realized through specific
acceptance criteria in downstream feature specs. Where a principle is the kind
of rule an implementer can violate while believing they complied, an
**Enforcement** line names the concrete mechanism — a lint rule, a test, a
reviewer check. These lines point at the mechanism; the detailed acceptance
criteria live in the relevant feature spec. An Enforcement line is a promise
that the principle is checkable, not merely aspirational.

---

## 1. Config-Driven, Not Hardwired

**1.1** Nothing the linter checks is hardcoded into the tool implementation.
All rules — what YAML keys to inspect, what values are allowed, what constitutes
pass/fail — are defined exclusively in config files under `specs/recipe-linter/`.

**1.2** The linter tool itself is a generic engine that: reads a rules file
describing what to validate, parses recipes and applies each applicable rule,
and reports pass/fail results per rule.

**1.3** Adding a new rule requires adding an entry to `checks.yaml` — not
modifying the linter code. Changing rule severity requires editing the YAML —
not the implementation.

---

## 2. Transparent Reporting

**2.1** Every check produces a result that names the rule that produced it.
Results are structured: rule ID, pass/fail, message. No silent omissions.

**2.2** Exit codes distinguish success, failure, and usage error:
- 0 = all checks passed (no errors)
- 1 = one or more errors detected
- 2 = usage error (bad arguments, missing files, invalid config)

---

## 3. Deterministic Validation

**3.1** The same input always produces the same output. No randomness, no
state-dependent behavior.

**3.2** Rules are pure functions of their inputs: the recipe file, any
companion files in the same directory, and the rule definition in
`checks.yaml`. No network calls, no external services.

---

## 4. Graceful Degradation on Input

**4.1** The linter must tolerate any valid or invalid file it's given. Invalid
YAML, missing keys, malformed overrides, and empty config files are reported as
check failures — never as crashes or unhandled exceptions.

**4.2** Config errors (`checks.yaml` itself is malformed) are reported
separately from recipe errors and cause exit code 2.

**4.3** Missing companion files in cross-file checks produce a clear fail
message — not a crash.

---

## 5. Cross-File Integrity

**5.1** Cross-file checks verify relationships between companion files in the
same recipe directory. The linter must discover companion files based on the
directory containing the primary recipe file and the related type.

**5.2** When a cross-file check cannot complete because a companion file is
missing or invalid, it reports a clear failure — never a false pass, never a
crash.

**5.3** Makefiles and CI pipelines depend on exit codes for correctness. The
linter MUST NOT return exit code 0 when any error-severity rule fails. The
linter MUST return exit code 1 when any warning-severity rule fails.

**Enforcement:** automated test that runs the linter on known-failing input
and asserts exit code is 1, not 0.

---

## 6. Runtime

> **Amended 2026-09-27.** This section used to require stock macOS utilities and pure
> bash 3.2. The linter was ported to Python under toolkit constitution P-7 and P-10;
> the bash engine was retired once the two gave the same results.

**6.1** The linter is `recipekit.lint` (`lib/python/recipekit/lint.py`), run through
`bin/recipe-linter.sh`, which keeps the command name, flags, output and exit codes.
It runs on AutoPkg's bundled Python and uses only the standard library and PyYAML.
A CI runner without AutoPkg sets `AUTOPKG_TOOLKIT_PYTHON` to any Python 3.10+ that
has PyYAML.

**6.2** Rule values are read from the recipe text the way the bash engine read them,
so every rule keeps its meaning: `Process` is the text from the `Process:` line to the
end of the file, minus whole-line comments; a top-level key is its first `key:`
line; `Section.key` is the first matching line inside that section. Patterns are POSIX
extended regular expressions matched line by line (as `grep -E` did), with POSIX
character classes such as `[[:space:]]` translated for Python.

**6.3** The port was accepted on parity: 960 of 962 comparisons identical over the
Acme repo, every template, the linter fixtures, error cases, an alternate org, and
938 mutated recipes (each line deleted; each value replaced). The two differences
were bash bugs, fixed by the port: `--list-rules` cut a description at an escaped
quote, and `--dir` with no value crashed.

**6.4** Kept on purpose, because rules and habits depend on them: warnings fail the
run (exit 1); `--pair-check` findings (SEN-001) are printed but don't change the exit
code; a failure message's `%value%` is the first line of a multi-line value.

**6.5** New rules that need real structure (processor order, arguments of a given
step, what a variable resolves to) ask the recipe model (`specs/recipekit/`) rather
than extending the text matching. They are still config-driven (§1): the rule lives
in `config/checks.yaml` and names a comparison type the engine implements on the
model. The first is `classification` (rule-definitions §2.8), used by CMT-004.

**Enforcement:** `tests/python/test_lint.py` (engine behaviour), `tests/examples_lint_spec.sh`
and `tests/org_config_spec.sh` (the command), `tests/kit_hygiene_spec.sh` (style).

---

## 7. Backward Compatibility

**7.1** `checks.yaml` evolves additively. Removing a rule is a major version
change; adding a rule is a minor version change. Changing a rule's semantics is
always a major version change.

**7.2** The linter must parse any `checks.yaml` file that conforms to the
schema defined in `01-rule-definitions.md`, regardless of the checks.yaml
version label.

---

## 8. Amendment

**8.1** This constitution may be amended, but amendments are explicit, dated,
and require re-review of any downstream specs that depended on the amended
clause.

**8.2** During design, if a constitution clause appears to block a reasonable
feature, the correct response is to surface the conflict for discussion — not to
quietly work around the clause.

**8.3** Amendment history:
- 2026-07-31: Initial release — 6 principles derived from the original
  LINTER-STD-001 specification, restructured as inviolable principles with
  enforcement lines where checkable.
- 2026-08-01: §6 "Stock macOS Toolchain Constraint" added, renumbering
  former §6→§7, §7→§8.
- 2026-09-27: §6 note: Python allowed per toolkit P-7; the linter port is planned.
- 2026-09-27: §6 rewritten as "Runtime": the linter is Python (`recipekit.lint`),
  accepted on parity with the bash engine, which was retired.
