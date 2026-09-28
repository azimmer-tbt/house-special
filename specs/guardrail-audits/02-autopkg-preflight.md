# autopkg-preflight — Audit and Lint Front End

**Status:** Draft
**Date:** 2026-09-27
**Requires:** `specs/guardrail-audits/00-constitution.md`, `specs/guardrail-audits/01-audits.md`, `specs/toolkit/00-constitution.md`, `specs/toolkit/01-toolkit-common.md`, `specs/toolkit/02-customers.md`, `specs/recipe-linter/00-constitution.md`
**Implementation:** `bin/autopkg-preflight.py`, using `lib/python/recipekit/audits.py` and `lib/python/recipekit/repo.py`

---

## Purpose

`bin/autopkg-preflight.py` is the one command an author runs before
`autopkg run`. It runs the nine guardrail audits against one app folder, or
every app folder in a recipe repo, then runs `bin/recipe-linter.sh` over the
same target. It prints one PASS, FAIL or SKIP line per check and exits non-zero
if any check failed.

It is author-side tooling: it needs AutoPkg's Python. The linter on its own is the
CI-safe path (recipe-linter constitution §6).

Examples:

```bash
bin/autopkg-preflight.py --app recipes/Corkscrews/Fruit-Screensaver
bin/autopkg-preflight.py --repo ../acme-recipes
bin/autopkg-preflight.py --repo customer/acme/output --no-lint
```

### Normative vs. Informative

- **Normative:** flags, repo resolution semantics, which audits run on which
  file, the linter chain, exit codes.
- **Informative:** the banner layout, check labels (`no_pathdeleter`, …) and the
  closing reminder text.

### Classification Key

- **[TESTABLE]** — automatable, mechanism named alongside.
- **[STRUCTURAL]** — enforced by layout or inspection.
- **[ADVISORY]** — review judgment.

### Tests today

- `tests/guardrail_audits_spec.sh` runs `bin/autopkg-preflight.py` on the Acme
  example repo, and checks `--app` inside and outside the repo.
- `tests/python/test_repo.py` checks the shared repo resolution against
  `lib/toolkit-common.sh`'s `resolve_repo_root` (FR-03).
- `tests/python/test_audits.py` covers the audits preflight calls, and
  `PreflightTest` calls `main([...])` directly (repo errors, skips, parse
  errors).
- `tests/kit_hygiene_spec.sh` covers the shebang, the exec bit and the
  black/isort/flake8 style.

The other ACs below are planned for `tests/autopkg_preflight_spec.sh` (planned),
or for unittest cases calling `main([...])`.

---

## FR-01 — Command line

[TESTABLE]

```
autopkg-preflight.py [--repo <recipe-repo>] [--app <app-folder>] [--no-lint]
                     [--customer <name> | --all-customers] [-h]
```

| Flag | Meaning |
|---|---|
| `--repo <dir>` | The recipe repo. Optional; see FR-03 for the fallbacks. |
| `--app <dir>` | Check only this app folder instead of every app in the repo (FR-04). |
| `--no-lint` | Skip the linter pass (FR-06). |
| `--customer <name>` | Check this customer from `config/customers.yaml` (`specs/toolkit/02-customers.md` FR-02). Its recipe repo is used unless `--repo` or `$AUTOPKG_TOOLKIT_REPO` is set, and the linter pass lints as that customer. |
| `--all-customers` | Run once per registered customer, in name order, each on its own recipe repo, printing `=== Customer: <name>` before each. Exit code is the worst of the runs. Can't be combined with `--customer`, `--repo` or `--app` (exit 2). No registered customers is exit 2. |
| `-h`, `--help` | Print the module docstring and exit 0. |

Without `--customer`, a customer still applies from `$AUTOPKG_TOOLKIT_CUSTOMER`, or
from the registry's `default` when there is no `--repo`, no `$AUTOPKG_TOOLKIT_REPO`,
and the current directory isn't a recipe repo. With the shipped registry
(`default: acme`), preflight with no arguments checks Acme's recipe repo unless you
run it from inside a recipe repo. An unknown customer, a bad registry, or
several customers with no default and none selected exits 2 with an `ERROR:` line
listing the registered names.

Arguments are parsed with `argparse`. There are no positional arguments.
`main(argv)` takes an argument list and returns the exit code, so tests can call
it directly.

**Acceptance Criteria:**

- AC-01.1: [TESTABLE] An unknown flag or a positional argument prints argparse's
  usage on stderr and exits 2.
  **Enforced via:** planned test (planned `tests/autopkg_preflight_spec.sh`).
- AC-01.2: [TESTABLE] `--help` prints the purpose, inputs and exit codes and exits 0.
  **Enforced via:** planned test (planned `tests/autopkg_preflight_spec.sh`).
- AC-01.3: [TESTABLE] The file starts with `#!/usr/local/autopkg/python`, is
  executable, and passes black, isort and flake8.
  **Enforced via:** `tests/kit_hygiene_spec.sh`.

## FR-02 — Toolkit assets

[TESTABLE]

The toolkit root is `Path(__file__).resolve().parent.parent`, so a symlinked entry
point still finds the real tree (toolkit P-1). Preflight imports the audits and the
repo routine from `<toolkit>/lib/python/recipekit/`, and runs the linter at
`<toolkit>/bin/recipe-linter.sh`. There is no override.

**Acceptance Criteria:**

- AC-02.1: [TESTABLE] Run from a folder unrelated to both the toolkit and the
  repo, with `--repo`, it still finds the audits and the linter.
  **Enforced via:** planned test (planned `tests/autopkg_preflight_spec.sh`).
- AC-02.2: [TESTABLE] Run through a symlink on `PATH`, it reports the real toolkit
  root in its banner.
  **Enforced via:** planned test (planned `tests/autopkg_preflight_spec.sh`).

## FR-03 — Repo resolution

[TESTABLE]

Preflight calls `resolve_repo_root()` in `lib/python/recipekit/repo.py`, the
Python twin of `lib/toolkit-common.sh`'s `resolve_repo_root` (toolkit-common
FR-02 to FR-04). It has the same precedence, the same refusals and the same
messages, but returns a result instead of exiting:

1. `--repo`, if given and non-empty;
2. else `$AUTOPKG_TOOLKIT_REPO`, if non-empty;
3. else the selected customer's recipe repo (`recipe_repo.root` in its
   `paths.yaml`, default `output`, relative to the customer folder;
   `specs/toolkit/02-customers.md` FR-03), when a customer is selected (FR-01);
4. else the current directory, **only if** it contains `recipes/`.

A recipe repo is a folder containing a `recipes/` folder. The chosen path is
checked for existence, then resolved with `Path.resolve()` (absolute and physical,
like `pwd -P`), then checked for `recipes/`. A bad `--repo` never falls back to
the variable, and a bad variable never falls back to the current directory.
Preflight prints each error line with an `ERROR:` prefix on stderr and exits 2.

| Case | Message (first line) |
|---|---|
| No source, CWD not a repo | `ERROR: No recipe repo specified, and the current directory is not one.` followed by the three remedies |
| Path does not exist | `ERROR: Repo path from <source> does not exist: <path>` |
| Path has no `recipes/` | `ERROR: Repo path from <source> does not look like an AutoPkg recipe repo:` |

**Conformance with toolkit P-2 / AIP-02: it conforms.** There is one Python
routine, shared by Python front ends, and a parity test keeps it in step with
the bash one.

**Acceptance Criteria:**

- AC-03.1: [TESTABLE] Each source works on its own: `--repo` alone, the variable
  alone, a repo CWD alone (toolkit P-6).
  **Enforced via:** `tests/python/test_repo.py`,
  `RepoParityTest.test_explicit_env_and_cwd`.
- AC-03.2: [TESTABLE] `--repo` wins over the variable; the variable wins over CWD.
  **Enforced via:** `tests/python/test_repo.py`, `RepoParityTest.test_refusals`
  (a bad `--repo` with a good variable); the variable over CWD is planned.
- AC-03.3: [TESTABLE] No source and a non-repo CWD exits 2, and stderr names all
  three remedies.
  **Enforced via:** `tests/python/test_repo.py`, `RepoParityTest.test_refusals`
  (the routine's messages); preflight's exit 2 is planned
  (planned `tests/autopkg_preflight_spec.sh`).
- AC-03.4: [TESTABLE] A non-existent `--repo` fails even when a valid
  `$AUTOPKG_TOOLKIT_REPO` is set; a folder without `recipes/` fails and says
  `recipes/` was expected.
  **Enforced via:** `tests/python/test_repo.py`, `RepoParityTest.test_refusals`;
  `tests/python/test_audits.py`, `PreflightTest.test_repo_errors_exit_2`
  (preflight exits 2 on a missing `--repo`).
- AC-03.5: [TESTABLE] The same inputs give the same result and messages as
  `lib/toolkit-common.sh`'s `resolve_repo_root` (parity, toolkit P-10).
  **Enforced via:** `tests/python/test_repo.py`, `RepoParityTest`.
- AC-03.6: [STRUCTURAL] Repo resolution is not implemented in this file; it calls
  the shared routine (toolkit P-2).
  **Enforced via:** reviewer check.

## FR-04 — Which app folders are checked

[TESTABLE]

- **With `--app`:** an absolute path is used as given. A relative path is looked
  up in the repo first, then in the current directory. It must be a folder, else
  `ERROR: --app <path>: not a directory (looked in the repo and the current
  directory)`. It must be the repo or inside it, else `ERROR: --app <path> is
  outside the repo (<repo>)`. Both exit 2.
- **Without `--app`:** the recipe model loads the repo (`RecipeSet.load_repo`):
  every folder under `recipes/`, at any depth, holding a recipe file
  (`*.recipe.yaml`, `*.recipe` or `*.recipe.plist`), in sorted order.

Pairs come from the model: a download and a pkg recipe in one folder with the
same file stem (`<App>.download.recipe.yaml`, `<App>.pkg.recipe.yaml`). A folder
with several apps gives several pairs. A pair with neither a download nor a pkg
recipe is left out.

**Acceptance Criteria:**

- AC-04.1: [TESTABLE] A repo with apps at `recipes/<Vendor>/<App>/` checks each
  one, in sorted order.
  **Enforced via:** planned test (planned `tests/autopkg_preflight_spec.sh`).
- AC-04.2: [TESTABLE] Folders with no recipe file are skipped.
  **Enforced via:** planned test (planned `tests/autopkg_preflight_spec.sh`).
- AC-04.3: [TESTABLE] `--app` naming a missing folder exits 2.
  **Enforced via:** planned test (planned `tests/autopkg_preflight_spec.sh`).
- AC-04.4: [TESTABLE] A relative `--app` is found in the repo from any current
  directory.
  **Enforced via:** `tests/guardrail_audits_spec.sh`, "bin/autopkg-preflight.py
  finds --app relative to the repo".
- AC-04.5: [TESTABLE] `--app` outside the repo exits 2 and says so.
  **Enforced via:** `tests/guardrail_audits_spec.sh`, "bin/autopkg-preflight.py
  refuses an --app outside the repo (exit 2)".

A recipe that does not parse is not part of any pair. Preflight reports each one
as its own check, `[FAIL] recipe_parse`, under a `Checking: <folder>` line (repo-relative, like the pair blocks),
with `<file>:<line>: <message>`, before the pairs.

- AC-04.6: [TESTABLE] A recipe that does not parse makes preflight print
  `[FAIL] recipe_parse` and exit 1.
  **Enforced via:** `tests/python/test_audits.py`,
  `PreflightTest.test_skips_do_not_fail_and_parse_errors_do`.

**Known gaps:**

- A folder with several pairs prints one `Checking:` block per pair, under the
  same folder label, and runs `readme_exists` once per pair.

## FR-05 — Which audits run

[TESTABLE]

For each pair, preflight calls `recipekit.audits.run_all(pair)` in-process (no
subprocess per audit). It runs, in this order:

| Audit | Label |
|---|---|
| `recipe_pairing` | `recipe_pairing` |
| `no_pathdeleter` | `no_pathdeleter` |
| `vendor_cache_path` | `vendor_cache_path` |
| `cert_chain_complete` | `cert_chain_complete` |
| `unsigned_declared` | `unsigned_declared` |
| `copier_overwrite` | `copier_overwrite` |
| `no_pathname_reliance` | `no_pathname_reliance` |
| `variables_declared` | `variables_declared` |
| `readme_exists` (on the pair's folder) | `readme_exists` |

Every audit runs on every pair, including half a pair; an audit that needs both
recipes reports SKIP (`01-audits.md` FR-04, FR-07), and `recipe_pairing` fails
it (FR-10). The audit list is the
`PAIR_AUDITS` table in `audits.py`; adding a file to `guardrails/audit/` does not
add a check.

Manifest verification is deliberately not one of the checks, although
`guardrails/GUARDRAILS.md` lists it as a must-have. It belongs to
`bin/verify-manifest.sh` (manifest spec FR-01: one implementation).

**Acceptance Criteria:**

- AC-05.1: [TESTABLE] Every pair gets nine results.
  **Enforced via:** `tests/python/test_audits.py`,
  `RunAllAndCliTest.test_run_all_covers_every_audit`.
- AC-05.2: [TESTABLE] A pair with only a pkg recipe gets SKIP from
  `no_pathname_reliance` and `variables_declared`, not a pass.
  **Enforced via:** `tests/python/test_audits.py`,
  `PathnameTest.test_ac_04_2_missing_download_is_skip` (the audit side);
  preflight's output is planned (planned `tests/autopkg_preflight_spec.sh`).
- AC-05.3: [STRUCTURAL] Preflight decides no verdict itself; each result comes
  from `recipekit.audits`.
  **Enforced via:** inspection.
- AC-05.4: [STRUCTURAL] Preflight does not compute or compare manifest checksums.
  **Enforced via:** inspection.

## FR-06 — Linter chain

[TESTABLE]

Unless `--no-lint` is given, after the audits preflight runs:

- `recipe-linter.sh --dir <app>` when `--app` was given (the resolved folder), or
- `recipe-linter.sh --repo <repo>` otherwise.

With a customer selected, `--customer <name>` is added, so the linter uses that
customer's org and rules.

It runs even when no app folders were found. It is counted as one check,
labelled `recipe_linter`. Exit 0 is PASS. Exit 1 (lint findings) is FAIL with the
linter's output. Exit 2 is FAIL with the line `the linter itself failed (exit
2), not a lint finding:` above the linter's output. A missing linter is a FAIL:
`linter not found at <path>`.

**Acceptance Criteria:**

- AC-06.1: [TESTABLE] A recipe with a lint error but clean audits makes preflight
  exit 1, with the linter's output indented under `[FAIL] recipe_linter`.
  **Enforced via:** planned test (planned `tests/autopkg_preflight_spec.sh`).
- AC-06.2: [TESTABLE] `--no-lint` runs no linter and prints no `recipe_linter`
  line.
  **Enforced via:** planned test (planned `tests/autopkg_preflight_spec.sh`).
- AC-06.3: [TESTABLE] A repo with no app folders still runs the linter.
  **Enforced via:** planned test (planned `tests/autopkg_preflight_spec.sh`).
- AC-06.4: [TESTABLE] Linter exit 2 is reported as the linter failing, not as a
  lint finding.
  **Enforced via:** planned test (planned `tests/autopkg_preflight_spec.sh`).

## FR-07 — Output

[TESTABLE]

Everything except resolution and usage errors goes to stdout:

```
==================================================================
AUTOPKG PREFLIGHT
  toolkit: <toolkit root>
  repo:    <repo root>
  customer: <name>              (only when a customer is selected)
==================================================================

Checking: recipes/Corkscrews/Fruit-Screensaver
  [PASS] recipe_pairing
  [PASS] no_pathdeleter
  [SKIP] vendor_cache_path
         SKIP: DOWNLOAD_URL: the vendor cache (/tmp/autopkg/vendor_cache) isn't on this machine
  [FAIL] cert_chain_complete
         FAIL: Fruit-Screensaver.download.recipe.yaml:12 (step 3): expected_authority_names is missing …
  …

Checking: static lint rules (recipe-linter.sh)
  [PASS] recipe_linter

------------------------------------------------------------------
Result: 147/154 PASSED  |  1 FAILED  |  6 SKIPPED (could not check on this machine)

A clean preflight is not a substitute for a real `autopkg run`.
See reference/methodology.md -- every bug it catalogs passed review first.
==================================================================
```

- The app label is the folder relative to the repo.
- A passing check prints only its `[PASS]` line. A failing or skipped check
  prints its FAIL and SKIP lines, indented nine spaces; its PASS lines are left
  out.
- The summary counts PASS, FAIL and SKIP. The `| N FAILED` and `| M SKIPPED …`
  parts appear only when non-zero.
- The two reminder lines always print.
- With no app folders: `WARNING: no app folders with recipes found; only the
  linter runs.`, then the linter.

**Acceptance Criteria:**

- AC-07.1: [TESTABLE] The summary counts every audit result plus the linter, and
  PASSED + FAILED + SKIPPED equals the number of `[PASS]`/`[FAIL]`/`[SKIP]` lines.
  A `recipe_parse` failure is counted.
  **Enforced via:** planned test (planned `tests/autopkg_preflight_spec.sh`).
- AC-07.2: [TESTABLE] A failing or skipped check's lines appear indented under
  it; a passing check's do not.
  **Enforced via:** planned test (planned `tests/autopkg_preflight_spec.sh`).
- AC-07.3: [TESTABLE] Every run prints the summary and the "not a substitute for
  a real `autopkg run`" reminder.
  **Enforced via:** `tests/guardrail_audits_spec.sh`, "bin/autopkg-preflight.py
  reports a summary and the autopkg-run reminder".

## FR-08 — Exit codes

[TESTABLE]

| Exit | When |
|---|---|
| 0 | no check failed (skips don't fail), or there was nothing to check |
| 1 | at least one audit or the linter failed |
| 2 | usage error (argparse), repo resolution failure (FR-03), a bad `--app` (FR-04) |

**Acceptance Criteria:**

- AC-08.1: [TESTABLE] `--repo customer/acme/output` fails no check, except that
  `vendor_cache_path` depends on this machine's vendor cache: with no cache it
  skips, and with a cache that lacks Acme's fictional drops it fails. Every Acme
  pair passes `recipe_pairing`.
  **Enforced via:** `tests/guardrail_audits_spec.sh`, "bin/autopkg-preflight.py
  fails no check on the Acme repo except, possibly, the machine-dependent vendor
  cache".
- AC-08.2: [TESTABLE] Each exit-2 case in the table exits 2 and prints nothing on
  stdout.
  **Enforced via:** `tests/guardrail_audits_spec.sh`, "bin/autopkg-preflight.py
  refuses an --app outside the repo (exit 2)"; `tests/python/test_audits.py`,
  `PreflightTest.test_repo_errors_exit_2`; the rest planned
  (planned `tests/autopkg_preflight_spec.sh`).
- AC-08.3: [TESTABLE] A run with SKIP results and no failures exits 0, and the
  summary shows `SKIPPED`.
  **Enforced via:** `tests/python/test_audits.py`,
  `PreflightTest.test_skips_do_not_fail_and_parse_errors_do`.

## FR-09 — Read-only

[STRUCTURAL]

Preflight writes nothing. Its only subprocess is the linter, which is read-only
itself. The audits run in-process and are read-only (constitution G-3).

**Acceptance Criteria:**

- AC-09.1: [STRUCTURAL] No file writes, no network, and a subprocess only for the
  linter.
  **Enforced via:** inspection.

---

## Architecture-Incompatible Patterns

**AIP-01: A second repo-resolution copy.** See FR-03. Any Python front end that
needs a repo imports `recipekit.repo`. **Enforced via:** toolkit P-2 review;
`tests/python/test_repo.py`.

**AIP-02: Re-implementing an audit inline.** Preflight runs audits; it never
decides a verdict itself. It calls the functions in `recipekit.audits`, and the
verdict logic stays there. **Enforced via:** reviewer check (AC-05.3).

**AIP-03: Folding manifest verification in.** See FR-05. **Enforced via:**
AC-05.4.

---

## Open Questions

**OQ-1:** **(Resolved 2026-09-27)** In `lib/python/recipekit/repo.py`, returning a
result, with the parity test `tests/python/test_repo.py` (FR-03). Original
question: Where should the shared Python repo resolution live, and when?
Proposed: `lib/python/recipekit/repo.py` (planned), added with the recipe model,
returning a result instead of exiting, with a parity test against
`lib/toolkit-common.sh`. Until then FR-03 is a documented P-2 exception.

**OQ-2:** **(Resolved 2026-09-27)** Yes: repo first, then the current directory,
and it must be inside the repo (FR-04). Original question: Should `--app` be resolved against the repo when it is relative
(`--app recipes/Vendor/App` from anywhere), and rejected when it is outside the
repo? Today it is relative to CWD, which is load-bearing (toolkit P-3).

**OQ-3:** **(Resolved 2026-09-27)** The linter still runs, after a WARNING; the
exit code follows the linter. Original question: With no app directories, should the linter still run (FR-06, AC-06.3),
and should "nothing to check" be exit 0 or an error?

**OQ-4:** **(Resolved 2026-09-27)** Yes, on every run (FR-07). Original
question: Print the "not a substitute for a real `autopkg run`" reminder on every
run, not only on failure?

**OQ-5:** **(Resolved 2026-09-27)** Exit 2 is reported as "the linter itself
failed" (FR-06). Original question: Distinguish linter exit 1 from exit 2 in the output. The code comment
says "the output says which", but the result line is `[FAIL] recipe_linter` in
both cases.

**OQ-6:** **(Resolved 2026-09-27)** Fixed in `guardrails/CHECKLIST.md` and
`guardrails/EXECUTION.md`. Original question: Documentation drift found while writing this spec (not fixed here):
`guardrails/CHECKLIST.md` shows a positional `<app-directory>` (which exits 2)
and lists manifest verification under "bin/autopkg-preflight.py checks these";
`guardrails/EXECUTION.md` points to `references/methodology.md` (the directory is
`reference/`).

**OQ-7:** **(Resolved 2026-09-27)** Fixed: `main(argv)` returns a code, no
`sys.exit` inside functions, the docstring names this spec, typed returns,
`check=False`. Original question: Deviations from `.devagent/standards/python-code-standards.md`:
- `main()` takes no `argv` and calls `parse_args()` on `sys.argv`, so tests can't
  call `main([...])`.
- `sys.exit(2)` inside `resolve_repo_root` and `discover_app_dirs`.
- The module docstring doesn't name its governing spec (this file).
- Return types are bare `tuple`, `list`, `dict`.
- `subprocess.run` is called without an explicit `check=` argument, which the
  standards' example shows.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-09-27 | Initial spec, written from the existing implementation. |
| 0.2 | 2026-09-27 | Updated for the fixes to KI-30 and KI-8c. |
| 0.3 | 2026-09-27 | Ported onto the recipe model: shared repo resolution (`recipekit/repo.py`), pairs from the model, audits in-process, SKIP results, `--app` inside the repo. OQ-1 to OQ-7 resolved. |
| 0.4 | 2026-09-27 | Added the `recipe_pairing` audit and the `recipe_parse` check; ACs point at `PreflightTest`. |
| 0.5 | 2026-09-27 | FR-01: `--customer` and `--all-customers` (`specs/toolkit/02-customers.md`); FR-03: the customer's recipe repo before the current directory; FR-06: the linter pass lints as the customer; the header prints the customer. |
