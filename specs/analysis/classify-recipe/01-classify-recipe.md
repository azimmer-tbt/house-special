# classify-recipe: Pattern Classifier for an Existing Recipe Pair

**Status:** Draft 0.2 · **Requires:** `specs/analysis/00-constitution.md`, `specs/recipekit/01-recipe-model.md`, `specs/toolkit/00-constitution.md` (P-7, P-10) · **Implementation:** `bin/classify-recipe.sh` → `lib/python/recipekit/classify.py`

## Purpose

Given a recipe folder (`<App>.download.recipe.yaml` and `<App>.pkg.recipe.yaml`),
report its pattern as the label in [`docs/patterns.md`](../../../docs/patterns.md)
(`2b`, `4d`, `6c`, `5`, …), with the reasoning, from the recipes alone. Compare it
with the pattern the recipe **claims** in its `Comment:`. Where the recipes can't
settle a distinction, say so and list the options instead of guessing silently. The
tool is read-only.

It asks the recipe model for every fact (recipekit FR-08) and parses nothing itself
(recipekit AIP-01). The pattern is the classifier's job, not the model's.

## FR-1: Interface

`classify-recipe.sh [--interactive|-i] [--dry-run|-n] [--org <org.yaml>] [--output text|json] <recipe-dir>`

The command name and flags are kept from the bash version (constitution P-10);
`--output json` is new. Relative paths resolve against the current directory.

- AC-1.1 [TESTABLE] A missing directory, or a folder without a recipe pair, exits 1
  with a message naming what's missing. Usage errors exit 2.
- AC-1.2 [TESTABLE] The tool writes no files in any mode. `--dry-run` only prints a
  banner (kept for compatibility).
- AC-1.3 [TESTABLE] `--interactive` asks the operator to choose between options only
  when stdin is a terminal; otherwise the options are printed and the exit is 0.
- AC-1.4 [TESTABLE] `--output json` prints only JSON on stdout.

## FR-2: Decision table

Facts come from recipekit: `source`, `artifact`, `signature`, `output`,
`version_source`, `scripts`, `extras`, `payload_paths`, `payload_complete`,
`pkgroot_parents`. "Adds org content" means `scripts` is present or `extras` is
non-empty.

| Source (recipekit) | Condition | Pattern |
|---|---|---|
| `sparkle` | output `PkgCopier` | 1a |
| `sparkle` | otherwise | 1b |
| `github_release` | output `PkgCopier` | 2a |
| `github_release` | adds org content | 2c |
| `github_release` | otherwise | 2b |
| `github_archive` | any | 2d |
| `url_stable` | output `PkgCopier`, and a redirect URL (`fwlink`, `go.microsoft.com`, `/latest`) or the version read from inside the package | 5 |
| `url_stable` | output `PkgCopier` otherwise | 3a |
| `url_stable` | otherwise | 3b |
| `url_scraped` | output `PkgCopier` | 3a (uncertain: 3c is the rebuilt form) |
| `url_scraped` | otherwise | 3c |
| `vendor_cache` | output `PkgCopier` | 4a |
| `vendor_cache` | output `Copier` (a distribution `.pkg` copied as-is) | 4b |
| `vendor_cache` | artifact `dmg`, signature `declared_unsigned` | 7 (uncertain: 4c for a genuinely unsigned vendor DMG) |
| `vendor_cache` | artifact `dmg`, adds org content | 4d |
| `vendor_cache` | artifact `dmg` | 4c |
| `vendor_cache` | artifact `zip`/`tar`, signed | 4e |
| `vendor_cache`, `recipe_dir` or `none` | in-house (signature `declared_unsigned`), rebuilt with `PkgCreator`: see Pattern 6 below | 6a–6d |
| any | artifact `app`, signature `declared_unsigned`, not from the vendor cache | 8 (uncertain) |
| none of the above | | `?` with the facts that didn't match |

**Pattern 6 letter**, in this order:
1. **6d** — the payload is known (`payload_complete`) and empty.
2. **6b** — install scripts are present.
3. **6c** — exactly one `chown` entry outside the shared macOS folders has a `mode`,
   and nothing else is known in the payload apart from that file and the folders
   above it. (The file often arrives in a zip from the vendor cache, so the payload
   itself may not be listable.)
4. **6a** — otherwise.

`AppPkgCreator` as the output is reported as forbidden (`!`), whatever the source.

## FR-3: Claimed pattern

The claim is the `Pattern <label>` at the start of the download recipe's
`Comment:` (the pkg recipe's when the download recipe has none). The report says
whether the classification matches it. A mismatch is information for the linter
and the reviewer; the classifier never uses the claim to decide (recipekit AIP-02).

- AC-3.1 [TESTABLE] A recipe with no `Pattern` in either `Comment:` reports
  "no claim".

## FR-4: Uncertainty

Some distinctions depend on facts outside the recipes (who made a DMG, whether a
link is truly stable). The classifier still reports its best label, marks it
**uncertain**, and lists the other options with the question that settles them.

## FR-5: Output

Text, in this order:
- `Recipe: <Vendor>/<App>`
- **Facts:** source, artifact, signature, output, version source, scripts, extras.
- `Classification: Pattern <label>` (plus `(uncertain: also <options>)` when FR-4 applies)
- `Claimed: Pattern <label>` and `Matches claim: yes|no`, or `Claimed: none`.
- **Reasoning:** one line per decision taken in FR-2.
- **Output naming:** no org prefix for `PkgCopier`/`Copier`; `ORG_PKGNAME_PREFIX` for
  `PkgCreator`.

JSON has the same content as fields.

- AC-5.1 [TESTABLE] Every recipe under `customer/acme/output/recipes/` and every
  template example under `templates/*/example-*` classifies as the pattern its
  `Comment:` claims. **Enforced via:** `tests/python/test_classify.py`.
- AC-5.2 [TESTABLE] Each row of the FR-2 table is covered by a fixture.
  **Enforced via:** `tests/python/test_classify.py`.
- AC-5.3 [TESTABLE] The bash front end passes its arguments through unchanged and
  exits with the Python tool's status. **Enforced via:** `tests/classify_recipe_spec.sh`.

## Version History

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09 | Bash implementation with generic output letters (a copy, b rebuild, c ridealong, d payloadless); 11 of 26 examples matched their claim |
| 0.2 | 2026-09-27 | Rebuilt on recipekit; per-pattern letters from `docs/patterns.md`; claimed-pattern comparison; uncertainty instead of `?`; JSON output |
