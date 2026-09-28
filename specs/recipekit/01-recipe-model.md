# recipe-model — Shared Python model of a recipe pair

**Status:** Implemented (0.4); consumers not yet moved onto it
**Date:** 2026-09-27
**Requires:** `specs/toolkit/00-constitution.md` (P-7, P-9), `specs/toolkit/01-toolkit-common.md` (FR-09, Python interpreter)
**Consumers:** `bin/classify-recipe.sh`, `guardrails/audit/*.py` and `bin/autopkg-preflight.py` (done). The linter (`recipekit.lint`) is ported but still reads rule values from recipe text; its structural rules will use the model. Planned:
`bin/blueprint-to-recipe.sh`, `bin/scan-placeholders.sh`, `bin/run-recipes.sh`

---

## Purpose

Every tool that reasons about recipes today re-parses YAML its own way. The linter
uses grep/sed line by line. The classifier uses 47 grep chains. Five of the eight
guardrail audits use regex over raw text; the three that were fixed in 2026-09 each
carry their own copy of the facts they need (KI-30). They disagree, and each has its
own bug class: KI-3, KI-6, KI-8, KI-23, and the SRC-002 false positive. The
classifier agrees with the pattern a recipe claims on only 4 of 19 recipes.

This spec defines **one** model of a recipe pair, built with real parsers, that every
tool asks instead. A fix to the model fixes every consumer.

The model describes **what AutoPkg sees**. It reports facts, not verdicts: whether a
fact is acceptable is the linter's business, and which pattern a set of facts adds
up to is the classifier's.

### Normative vs. Informative

- **Normative:** what the model loads, how recipes are paired, how variables
  resolve, the processor-output catalogue's role, the derived facts and their
  meanings, the finding codes, failure behaviour.
- **Informative:** module and class names, file locations, JSON field spellings.

### Classification Key

- **[TESTABLE]** — automatable, mechanism named alongside.
- **[STRUCTURAL]** — enforced by layout or inspection.
- **[ADVISORY]** — review judgment.

---

## FR-01 — Runtime and dependencies

[STRUCTURAL]

As toolkit constitution P-7: AutoPkg's bundled interpreter, the standard library
and PyYAML only, compatible with the Python version AutoPkg ships (3.10 as of
AutoPkg 2.9). Coding conventions: `.devagent/standards/python-code-standards.md`.

## FR-02 — Location

[STRUCTURAL]

- The package lives at `lib/python/recipekit/`.
- Front ends find it from their own location (`TOOLKIT_ROOT/lib/python`), never from
  the current directory or an installed site-packages (toolkit constitution P-1).
- Shell front ends run it as `tk_python -m recipekit.<tool> …`; `tk_python` puts
  `TOOLKIT_ROOT/lib/python` on `PYTHONPATH`. Python front ends in `bin/` insert that
  path themselves.

## FR-03 — What the model loads

[TESTABLE]

`RecipePair.load(<recipe-dir>)` reads:

| File | Read? | Why |
|---|---|---|
| `*.recipe.yaml` | Yes | The kit's recipe format. |
| `*.recipe` (plist), `*.recipe.plist` | **Read only** | Community recipes are reviewed and audited in this format (Standards §6.10.2). The kit never writes plist; an adopted recipe is converted to YAML (§6.10.3). |
| `.overrides` | Yes, when present | Optional, org-defined values a harness passes as `--key` (Standards §3.4). Kept separate from AutoPkg's view (FR-05). |
| Anything else (README, `.autopkg_config`, deployment metadata) | No | Not something AutoPkg reads. Labels and prose are claims to check, never inputs (AIP-02). |

- AC-03.1: [TESTABLE] YAML and plist recipes describing the same processors produce
  the same facts.
- AC-03.2: [TESTABLE] A recipe that isn't valid YAML or plist produces a
  `recipe_invalid` finding naming the file and, where the parser reports it, the line.
  It never raises out of the model.
- AC-03.3: [TESTABLE] Comments never influence any derived fact (the class of KI-23).
- AC-03.4: [TESTABLE] A plist recipe inside a customer recipe repo produces a
  `plist_recipe` finding (so a plist can't land in a repo unconverted).

## FR-04 — Pairing by `ParentRecipe`

[TESTABLE]

AutoPkg links recipes by identifier, not by file name, so the model does too. Each
recipe's `ParentRecipe` is looked up by `Identifier` among the recipes the model has
loaded, and the chain is followed to its root (download recipe, pkg recipe, and any
further child such as a deployment recipe).

**The loaded folders are the whole world.** A House Special repo runs on its own: a
community recipe is never used in place, it is copied in full, rebadged and credited
(Standards §6.10.3), including every parent it needs. So the model never looks for a
parent anywhere else: not in `RECIPE_SEARCH_DIRS`, not in repos added with
`autopkg repo-add`, not in AutoPkg's own recipe overrides. To audit a community
recipe, load the community repo's folder itself; its chain is then complete in the
loaded set.

- AC-04.1: [TESTABLE] A pkg recipe whose `ParentRecipe` equals its sibling download
  recipe's `Identifier` forms a pair.
- AC-04.2: [TESTABLE] A `ParentRecipe` that names an identifier other than the
  sibling's produces `parent_mismatch`; one that matches no loaded recipe produces
  `parent_missing`. A folder with only one half of a pair produces `pair_incomplete`.
  None of these raise.
- AC-04.3: [TESTABLE] Pairing does not depend on file sort order (the defect in
  `autopkg-preflight.py`, KI-30).
- AC-04.4: [TESTABLE] With a parent present in `~/Library/AutoPkg/RecipeRepos/` or a
  `RECIPE_SEARCH_DIRS` folder but not in the loaded folders, the result is still
  `parent_missing`. The model reads no AutoPkg preferences.

## FR-05 — Processors, in order

[TESTABLE]

Each recipe's `Process` becomes an ordered list of steps `(processor, arguments,
recipe, index)`. The *effective chain* of a child recipe is its parent's chain
followed by its own, in the order AutoPkg runs them.

- AC-05.1: [TESTABLE] Order is preserved, and a step's arguments are available by
  name (e.g. the `pkg_request.pkgname` of the `PkgCreator` step).
- AC-05.2: [TESTABLE] `EndOfCheckPhase` splits the chain into "check" and "build".
- AC-05.3: [TESTABLE] Shared processors (`com.github.<author>.<repo>/<Processor>`) keep
  their full reference, and are recognised as not built in.

## FR-06 — Variable resolution: AutoPkg's view and the harness view

[TESTABLE]

`resolve(text, view)` substitutes `%VARIABLES%` statically, the way AutoPkg would.
It never runs a processor, makes a network call or runs a shell command.

**AutoPkg's view** (the default; what the linter and audits judge):

1. variables AutoPkg sets for every run (`NAME` when given, `RECIPE_DIR`,
   `RECIPE_CACHE_DIR`, `RECIPE_PATH`, `PARENT_RECIPES`, `RECIPE_SEARCH_DIRS`,
   `CACHE_DIR`, `verbose`);
2. `Input`, the child's over the parent's;
3. variables set by processors **earlier in the chain**, from the processor-output
   catalogue (FR-07), returned as symbolic values (`<set by URLTextSearcher: url>`).

**The harness view** adds `.overrides` values on top, because that is what
`bin/run-recipes.sh` runs with. It is never used to decide whether a recipe is valid
on its own.

- AC-06.1: [TESTABLE] `url: "%DOWNLOAD_URL%"` with
  `DOWNLOAD_URL: "file://%VENDOR_CACHE_ROOT%/…"` resolves to a `file://` URL (fixes
  KI-6b).
- AC-06.2: [TESTABLE] A variable used but neither declared nor set is
  `undeclared_variable` (the check `check_variables_declared.py` does today, now in
  one place).
- AC-06.3: [TESTABLE] A variable that only `.overrides` supplies is
  `harness_supplied` (information): legitimate for a pipeline that injects it, but a
  bare `autopkg run` would not have it.
- AC-06.4: [TESTABLE] A variable used before the step that sets it (e.g. `%version%`
  before `Versioner`) is `used_before_set`.
- AC-06.5: [TESTABLE] A variable that only a shared or unknown processor could have
  set is `unverifiable`, not `undeclared_variable`.

## FR-07 — The processor-output catalogue

[TESTABLE]

One table in the model lists the variables each built-in processor sets, following
AutoPkg's own `output_variables` (for example: `URLDownloader` sets `pathname` but
**not** `version`; `GitHubReleasesInfoProvider` sets `url` and `version`;
`URLTextSearcher` sets `result_output_var_name`, default `match`, plus the named
groups of its `re_pattern` after substituting `Input`; `Versioner` sets `version`, or
its `output_var_name`).

- AC-07.1: [TESTABLE] Every processor used in `customer/acme/output/recipes/` and
  `templates/` has an entry.
- AC-07.2: [STRUCTURAL] No consumer keeps its own copy of this table (AIP-05). The
  table in `check_variables_declared.py` moves here.
- AC-07.3: [ADVISORY] When AutoPkg adds or changes a processor's outputs, the table is
  updated from AutoPkg's source, and the change cites the AutoPkg version.

## FR-08 — Derived facts

[TESTABLE]

The model answers these questions. Each answer carries its **evidence**: the recipe,
step index and argument it was derived from.

| Fact | Values |
|---|---|
| `identity` | `Identifier`, `ParentRecipe`, `MinimumVersion` of each recipe in the chain |
| `claimed` | the `Comment:` text, raw — for consumers to *check against* the facts, never used to derive them |
| `source` | `sparkle`, `github_release`, `github_archive`, `url_scraped` (`URLTextSearcher` before the download), `url_stable`, `vendor_cache` (`file://` on `VENDOR_CACHE_ROOT`, or a `LOCAL_*` path), `recipe_dir` (payload committed next to the recipe), `none` |
| `artifact` | `pkg`, `dmg`, `zip`, `tar`, `app`, `files`, `unknown`, from the download filename, `asset_regex`, resolved URL, or the processors that consume it (`DmgMounter`, `Unarchiver`, `.dmg/` paths) |
| `signature` | `requirement` (noting whether it pins `subject.OU`), `authority_names` (noting whether the Apple chain is listed), `identifier_only`, `declared_unsigned` (`NO_CODE_SIGNATURE_REQUIRED`), `declared_no_team` (`teamid: UNSIGNED_NO_TEAMID` in `Input`), `missing` |
| `output` | `PkgCreator`, `PkgCopier`, `Copier` (to a `.pkg` destination), `AppPkgCreator`, `none` |
| `pkgname` | the resolved `pkg_request.pkgname`, if any |
| `version_source` | `processor` (which one), `input` (pinned), `harness_only` (only `.overrides`), `none` |
| `payload_paths` | install paths the package writes, from `Copier` destinations under the pkgroot, files in a `%RECIPE_DIR%` payload folder, and the `chown` list |
| `payload_complete` | `false` when part of the payload is unpacked or copied from the cache at build time, so `payload_paths` can't list it |
| `installs_app` | whether a `.app` is in the payload |
| `scripts` | `none`, or the scripts directory and which of `preinstall` / `postinstall` it holds |
| `extras` | payload paths that are **not** the vendor's app: license, config, LaunchAgent, … |
| `chown` | every `chown` entry of the `PkgCreator` step: path, user, group, mode, and whether the path is a shared macOS folder |
| `pkgroot_parents` | shared parent folders in the payload and the owner the `chown` list records for each (for the rules in `docs/package-ownership.md`) |

The recipe's **pattern is not a fact.** Mapping facts to a pattern (`2b`, `4d`, …)
is the classifier's job, so a change to the taxonomy never touches the model.

- AC-08.1: [TESTABLE] Every fact is covered by a unit test with a minimal fixture pair.
- AC-08.2: [TESTABLE] For every recipe under `customer/acme/output/recipes/` and
  `templates/*/example-*`, the derived facts match a checked-in expectation file.

## FR-09 — Findings

[TESTABLE]

For recipe *content*, the model never exits and never raises. It returns facts plus a
list of findings `(code, severity, file, line?, message)`, and the front ends decide
exit codes. Only programmer errors, such as bad arguments, raise.

| Code | Severity | Meaning |
|---|---|---|
| `recipe_invalid` | error | The file isn't valid YAML or plist |
| `pair_incomplete` | error | A download or pkg recipe has no partner |
| `parent_mismatch` | error | `ParentRecipe` names an identifier other than the sibling's |
| `parent_missing` | error | `ParentRecipe` matches no loaded recipe (a community parent must be adopted, not referenced) |
| `undeclared_variable` | error | Used, but nothing declares or sets it |
| `used_before_set` | error | Used before the step that sets it |
| `plist_recipe` | error | A plist recipe inside a customer recipe repo |
| `unverifiable` | warning | Only a shared or unknown processor could have set it |
| `unknown_processor` | warning | A processor with no catalogue entry |
| `harness_supplied` | info | Only `.overrides` supplies it |

- AC-09.1: [TESTABLE] Each code has a fixture that produces it and nothing else.
- AC-09.2: [TESTABLE] Codes are stable: renaming one is a breaking change to the spec.

## FR-10 — Command line

[TESTABLE]

`tk_python -m recipekit.facts <recipe-dir> [--view autopkg|harness] [--output text|json]`
prints the facts and findings for one recipe folder, so bash tools can use the model
before they are ported (`scan-placeholders.sh`, `run-recipes.sh`).

- AC-10.1: [TESTABLE] `--output json` prints only JSON on stdout; diagnostics go to
  stderr.
- AC-10.2: [TESTABLE] Exit 0 with no error findings, 1 with any error finding, 2 on
  usage errors.

## FR-11 — Testing

[TESTABLE]

- Unit tests use the standard library's `unittest`, so nothing needs installing under
  AutoPkg's Python. They live in `tests/python/test_*.py` and run with
  `tk_python -m unittest discover -s tests/python`.
- `tests/python_unittest_spec.sh` runs that command, so `shellspec` stays the
  single test entry point.
- Moving to `pytest` later is a planned conversion, not a rewrite: `pytest` runs
  `unittest.TestCase` classes unchanged.

---

## Architecture-Incompatible Patterns

- **AIP-01:** A consumer re-parsing recipe files itself instead of asking the model.
- **AIP-02:** Deriving facts from `Comment:`, `Description:` or README text. Labels are
  claims to be *checked against* the model (methodology lesson 26), never inputs to it.
- **AIP-03:** Any dependency beyond the standard library and PyYAML.
- **AIP-04:** Writing a plist recipe. The kit reads plist; it only ever writes YAML.
- **AIP-05:** A consumer with its own table of processor outputs.
- **AIP-06:** Judging a recipe valid because `.overrides` supplies something AutoPkg
  itself would never see.
- **AIP-07:** Following a parent outside the loaded folders (search paths, added
  repos, AutoPkg recipe overrides). Results would depend on the machine.

## Open Questions

- **OQ-01 (resolved 2026-09-27):** Read plist `.recipe` files? Yes, read-only, for
  review, research and audit. Adopted recipes become YAML (FR-03, AIP-04).
- **OQ-02:** Should `MinimumVersion` be checked against the AutoPkg features a recipe
  uses (e.g. YAML recipes need AutoPkg 2.3)? That needs a second catalogue: feature
  to minimum version.
- **OQ-03 (resolved 2026-09-27):** Follow parents outside the loaded folders? No,
  always `parent_missing` (FR-04, AIP-07). A House Special repo is self-contained:
  adopted community recipes are reproduced in full in house, rebadged with the org's
  identifiers and credited to their author in the recipe itself.

## Version History

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09-27 | Draft for review |
| 0.2 | 2026-09-27 | Review: pairing by `ParentRecipe`; AutoPkg view vs harness view (`.overrides` optional, `harness_supplied`); one processor-output catalogue; pattern is not a fact; finding codes; JSON command line; plist read-only; `.autopkg_config` not loaded |
| 0.3 | 2026-09-27 | OQ-03: the loaded folders are the whole world; no search paths (AIP-07) |
| 0.4 | 2026-09-27 | Implemented in `lib/python/recipekit/`; tests in `tests/python/` (unit tests per fact and finding, expectation files for every Acme recipe and template example). Also reports `payload_complete` (false when the payload is unpacked or copied from the cache at build time, so its contents can't be listed statically). |
