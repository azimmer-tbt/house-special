# Guardrail Audits — Constitution

**Status:** Draft
**Date:** 2026-09-27
**Requires:** `specs/toolkit/00-constitution.md`, `specs/recipe-linter/00-constitution.md`, `specs/recipekit/01-recipe-model.md`, `reference/methodology.md`
**Implementation:** `lib/python/recipekit/audits.py`, `guardrails/audit/` (front ends), `bin/autopkg-preflight.py`

---

## Purpose

This constitution says what a guardrail audit is, and how audits relate to the
recipe linter and to the shared recipe model. The requirements for each
audit are in [`01-audits.md`](01-audits.md). The front end that runs them is in
[`02-autopkg-preflight.md`](02-autopkg-preflight.md).

Audits exist because of the core lesson in `reference/methodology.md`: review and
linting only catch what they know to look for, and many AutoPkg failures only show
up at runtime. Each audit turns one of those runtime lessons into a check that runs
before `autopkg run`.

### Normative vs. Informative

- **Normative:** what an audit is (G-1 to G-4), the exit-code contract, the split
  between audits and linter rules, and reading recipes through the recipe model.
- **Informative:** the `check_<thing>.py` file names, the `guardrails/audit/`
  location, and the exact wording of PASS/FAIL/SKIP messages.

### Classification Key

- **[TESTABLE]** — automatable, mechanism named alongside.
- **[STRUCTURAL]** — enforced by layout or inspection.
- **[ADVISORY]** — review judgment.

---

## Principles

### G-1 — One audit, one runtime behaviour

An audit checks one AutoPkg runtime behaviour that the static linter cannot
express. Examples: "`Copier` never sets `%pathname%`" (methodology lesson 3), or
"a `LOCAL_*_PATH` must resolve to a file that exists on this machine" (lesson 1).
Each audit cites the numbered methodology lesson it exists for.

If a check can be written as a rule in `config/checks.yaml` (a key exists, a value
matches a pattern, a companion file agrees), it belongs in the linter, not here.
Audits are for checks that need code: following a parent recipe, resolving a path
on disk, or reasoning across the download and pkg recipes together.

**Enforced via:** reviewer check — a new audit names its lesson and says why a
linter rule can't express it.

### G-2 — One target in, one verdict out

An audit takes one positional argument: a recipe file or its app folder (both
are accepted, OQ-1). It checks the recipe pair the target belongs to, or every
pair in the folder. It prints lines starting `PASS:`, `FAIL:` or `SKIP:` on
stdout, with enough context to fix the problem. Errors go to stderr.

There are three results:

- **PASS:** the check ran and the recipe is fine, or the check does not apply
  (the line says so, for example "or none is used").
- **FAIL:** the check ran and found the problem.
- **SKIP:** the audit could not check (OQ-2). Examples: half a recipe pair, a
  vendor cache that isn't on this machine, a variable only an unknown processor
  could set.

Exit codes follow the linter's (recipe-linter constitution §2.2):

| Exit | Meaning |
|---|---|
| 0 | pass or skip |
| 1 | the check failed |
| 2 | usage or input error: no argument, the target does not exist, the target recipe (or, for a folder, any recipe in it) is not valid, or no recipe pair was found |

A FAIL message names the methodology lesson it comes from (OQ-3).

**Enforced via:** `tests/python/test_audits.py`, `RunAllAndCliTest.test_cli_exit_codes_and_targets`
(exit 1 for a folder and a file target; exit 2 for a missing target and an
invalid recipe); `tests/guardrail_audits_spec.sh` (PASS and FAIL lines).

### G-3 — Audits are read-only and local

An audit reads the recipe (and, where it needs one, its sibling recipe or the
filesystem path the recipe names). It never writes, never runs a processor, never
runs `autopkg`, and never makes a network call.

**Enforced via:** reviewer check.

### G-4 — Every audit can be shown to fail

Methodology lesson 26: a checker you have never seen fail is untested. Each audit
keeps a deliberately broken fixture that makes it exit 1, and a clean fixture that
makes it exit 0.

**Enforced via:** `tests/python/test_audits.py` and
`tests/guardrail_audits_spec.sh` together give every audit a failing and a
passing fixture, and a skipping one where the audit can skip (`01-audits.md`
AC-01.4). The fixtures are written to temporary folders, so the verdicts don't
depend on the machine.

---

## Relationship to the linter

The linter (`bin/recipe-linter.sh`, [`specs/recipe-linter/`](../recipe-linter/00-constitution.md))
is config-driven and runs in CI with only stock macOS tools. Audits are Python and
need AutoPkg's interpreter. `bin/autopkg-preflight.py` runs every audit and then
the linter, so an author gets both from one command.

The two overlap in places, and where they overlap they can disagree:

- The linter's CSV-005 accepts a `CodeSignatureVerifier` step whose `requirement`
  pins `subject.OU`. `check_cert_chain_complete.py` fails that same step, because
  it has no `expected_authority_names` (see `01-audits.md` FR-05).
- The linter's CSV-001 accepts `NO_CODE_SIGNATURE_REQUIRED: true` on its own.
  `check_unsigned_declared.py` also demands a comment giving the reason, on the
  flag's line or the line above (FR-06).

So a recipe can pass the linter and fail preflight. That is intended: the audits
check more than the linter does. The Acme example apps pass both, except that
`vendor_cache_path` can fail on a machine whose vendor cache lacks Acme's
fictional drops (`01-audits.md` FR-03).

## Relationship to the recipe model

Every audit reads recipes through the recipe model
(`specs/recipekit/01-recipe-model.md`, package `lib/python/recipekit/`). The model
parses each recipe once, follows `ParentRecipe`, and answers questions such as
"which processors run, in order", "what does this variable resolve to" and
"which variables are used before anything sets them". So comments never count
as steps or values, blank lines don't matter, and both YAML and plist recipes
are read.

- The audits are functions in `lib/python/recipekit/audits.py`, one per check,
  each taking a `Pair` (the README audit takes a folder). They return a result
  with PASS, FAIL or SKIP lines.
- The `guardrails/audit/check_<thing>.py` scripts are thin front ends that call
  `recipekit.audits.cli(<name>)`. `bin/autopkg-preflight.py` calls the same
  functions in-process.
- The `recipe_pairing` audit runs first and fails a pair whose recipes the model
  can't pair properly (a wrong or missing `ParentRecipe`, half a pair, a plist
  recipe). So a pair the other audits can only partly judge is never passed
  silently. It has no standalone script.
- No audit matches recipe text with regular expressions. The one exception is
  `unsigned_declared`'s comment check: the model drops comments, and that check
  is about a comment.
- The port was checked against every recipe under `customer/acme/output/recipes/`
  and every template example. It found three template gaps, now fixed: two
  examples lacked the reason comment for `NO_CODE_SIGNATURE_REQUIRED`, and one
  lacked a README.

Audits are Python for the reason toolkit constitution P-7 gives: they read
structured data, so they run on AutoPkg's bundled interpreter, with the standard
library, PyYAML and the toolkit's own `recipekit` package.

---

## Architecture-Incompatible Patterns

**AIP-01: An audit that duplicates a linter rule.** Two implementations of one
check drift. If the linter can express it, delete the audit or the rule.
**Enforced via:** G-1 review.

**AIP-02: Regex over raw recipe text.** An audit that reads recipe content with
`re` or `in` instead of the recipe model. (`unsigned_declared`'s comment check is
the one exception; see above.) **Enforced via:** toolkit AIP-08 review.

**AIP-03: An audit with side effects.** Writing, cleaning or "fixing" anything.
**Enforced via:** G-3 review.

**AIP-04: A silent pass on missing context.** Treating "I couldn't find the
sibling recipe" as a pass. Report SKIP instead (G-2). **Enforced via:** reviewer
check; `tests/python/test_audits.py`, `PathnameTest.test_ac_04_2_missing_download_is_skip`.

---

## Open Questions

**OQ-1:** **(Resolved 2026-09-27)** Both are accepted: a recipe file or its app
folder; the audit checks the pair(s) through the model. Original question: Should audits that inspect a pair (FR-04 and FR-07 in `01-audits.md`)
take the app directory instead of the pkg recipe, as the recipe model's
`RecipePair.load(<dir>)` does? That would remove the sibling-by-filename lookup.
Leaning: yes, when they move onto the model; keep accepting a recipe path for
P-10.

**OQ-2:** **(Resolved 2026-09-27)** Yes: `SKIP:` means "could not check", exits
0, and preflight counts it separately. Original question: Should "not applicable" and "could not check" be different results?
Today both are exit 0 with a PASS line. A third outcome (for example exit 0 with
`SKIP:`) would make the missing-sibling case visible in preflight's summary.

**OQ-3:** **(Resolved 2026-09-27)** Yes: every FAIL message names its lesson.
Original question: Should each audit's lesson number appear in its FAIL message, so a
reader can go straight to `reference/methodology.md`?

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-09-27 | Initial spec, written from the existing implementation. |
| 0.2 | 2026-09-27 | Ported onto the recipe model; SKIP result added; OQ-1 to OQ-3 resolved. |
| 0.3 | 2026-09-27 | Added the `recipe_pairing` audit; an invalid sibling no longer blocks a named recipe. |
