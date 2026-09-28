# run-recipes — Real AutoPkg run over every recipe pair in a repo

**Status:** Draft
**Date:** 2026-09-27
**Requires:** `specs/toolkit/00-constitution.md` (P-1 to P-7), `specs/toolkit/01-toolkit-common.md` (FR-03, FR-04, FR-05), `specs/toolkit/02-customers.md` (FR-02, FR-05)
**Implementation:** `bin/run-recipes.sh`

---

## Purpose

`run-recipes.sh` is the real-run harness. For each app in a recipe repo it runs
the download recipe and then the pkg recipe with `autopkg run`. If the app has an
`.overrides` file, it passes those values as `--key` arguments the same way a CI job
would. `.overrides` is optional and org-defined (Standards §3.4): upstream recipes
don't ship one, and AutoPkg itself never reads it. A typical use is a value the
pipeline writes at run time, such as a license key, that must never be committed. It prints a
block per app and a pass/fail/skip summary.

It answers one question: "do these recipes actually work on this Mac, with real
files?" The linter and the placeholder scanner check text. This tool is the only
one that runs AutoPkg.

It stays bash (toolkit constitution P-7): it is a thin wrapper around one system
command, `autopkg`, and reads no structured data except the optional, flat `key=value`
`.overrides` file.

### Normative vs. Informative

- **Normative:** which recipes are run and in what order, how `.overrides` values
  reach AutoPkg, the placeholder gate, what counts as pass, fail and skip, exit
  codes.
- **Informative:** the exact wording of progress lines, the separator lines, the
  `-v` verbosity passed to AutoPkg.

### Classification Key

- **[TESTABLE]** — automatable, mechanism named alongside.
- **[STRUCTURAL]** — enforced by layout or inspection.
- **[ADVISORY]** — review judgment.

`tests/run_recipes_spec.sh` covers part of this tool. Tests must stub `autopkg`
(and, for `--clear-cache`, `clear-autopkg-cache.sh`) with a script that records
its arguments; they must never run the real AutoPkg.

---

## FR-01 — Command line

[TESTABLE]

```
run-recipes.sh [--repo <recipe-repo> | --customer <name>] [--clear-cache] [filter]
```

| Argument | Meaning |
|---|---|
| `--repo <dir>` | The recipe repo to run. Resolved by toolkit-common (FR-03). |
| `--customer <name>` | Run that registered customer's recipe repo (FR-02). |
| `--clear-cache` | Before running each app, clear AutoPkg's cache for that app's two recipe identifiers (FR-06). |
| `filter` | A substring. Only apps whose folder name contains it are run. Case-sensitive. |
| `-h`, `--help` | Print a one-line usage and exit 0. |

Parsing happens in two passes. The first takes `--repo`, `--customer` and `-h`; everything else
is kept as positional. The second pass turns `--clear-cache` into the flag and
treats any other word as the filter. So:

- Flags and the filter may come in any order.
- If more than one filter is given, the **last** one wins; the others are
  silently dropped.
- An unknown option such as `--dry-run` is not rejected. It becomes the filter,
  matches no app, and the run reports `0 passed, 0 failed, 0 skipped`.

**Acceptance Criteria:**

- AC-01.1: [TESTABLE] `--help` prints a line starting `Usage:` and exits 0 without
  resolving a repo. **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)
- AC-01.2: [TESTABLE] `--repo` with no value, or followed by another option, exits
  2 with the message `--repo requires a directory path`. **Enforced via:** planned
  test `tests/run_recipes_spec.sh` (planned)
- AC-01.3: [TESTABLE] `run-recipes.sh --repo R Orchard` runs only apps whose folder
  name contains `Orchard`; `run-recipes.sh --repo R --clear-cache Orchard` and
  `run-recipes.sh Orchard --clear-cache --repo R` behave the same.
  **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)
- AC-01.4: [TESTABLE] The usage line printed by `--help` names every flag,
  including `--clear-cache`. (Not yet met: the usage line omits `--clear-cache`;
  see OQ-03.) **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)
- AC-01.5: [TESTABLE] An unrecognised option exits 2 rather than becoming the
  filter. (Not yet met; see OQ-03.) **Enforced via:** planned test
  `tests/run_recipes_spec.sh` (planned)

## FR-02 — Repo resolution

[TESTABLE]

The repo is resolved with toolkit-common's `resolve_repo_root` (toolkit-common
FR-03, FR-04): `--repo`, then `$AUTOPKG_TOOLKIT_REPO`,
then the current directory if it is a recipe repo. Recipes are searched under the
repo's `recipes/` directory. Failure exits 2 with toolkit-common's message.

A customer (`specs/toolkit/02-customers.md` FR-02) supplies the repo when nothing
more explicit does. `resolve_customer` looks it up in the registry, and its recipe
repo (`recipe_repo.root` in its `paths.yaml`, default `output`) is passed to
`resolve_repo_root`:

- `--customer <name>` or `$AUTOPKG_TOOLKIT_CUSTOMER` selects a customer. Its repo is
  used unless `--repo` or `$AUTOPKG_TOOLKIT_REPO` names one.
- With neither, no `--repo`, no `$AUTOPKG_TOOLKIT_REPO`, a current directory that
  is not a recipe repo, and a registry present, a customer is chosen as
  `specs/toolkit/02-customers.md` FR-02 steps 3 and 4 say: the registry's
  `default`, else the only customer. Several customers and no `default` exits 2,
  listing them.
- An unknown name exits 2 listing the registered names. `--customer` with no value,
  or followed by another option, exits 2 with `--customer requires a name`.

**Acceptance Criteria:**

- AC-02.1: [TESTABLE] With no repo argument, no environment variable, no customer
  registry and a current directory that is not a repo, the tool exits 2 and runs
  nothing.
  **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)
- AC-02.2: [TESTABLE] `--repo` naming a directory without `recipes/` exits 2, even
  when the environment variable names a valid repo (constitution P-5).
  **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)
- AC-02.3: [STRUCTURAL] The script has no repo-root logic of its own (AIP-02 of
  the constitution); it only chooses which path to hand `resolve_repo_root`.
  **Enforced via:** inspection.
- AC-02.4: [TESTABLE] `--customer <name>` runs that customer's recipe repo.
  **Enforced via:** `tests/customers_shell_spec.sh`, "--customer runs that
  customer's recipe repo".
- AC-02.5: [TESTABLE] With no repo given and a current directory that is not a
  recipe repo, the registry's default customer is run. **Enforced via:**
  `tests/customers_shell_spec.sh`, "uses the default customer when no repo is given".
- AC-02.6: [TESTABLE] `--repo` beats `--customer`: the named repo is resolved, and
  one without `recipes/` exits 2. **Enforced via:** `tests/customers_shell_spec.sh`,
  "--repo beats the customer".

## FR-03 — AutoPkg must be present

[TESTABLE]

After the repo is resolved, the tool checks that `autopkg` is on `PATH`. If it is
not, it prints `ERROR: autopkg not found on PATH. Install it first (brew install
autopkg).` to stderr and exits 1.

This check does not use toolkit-common's `tk_require` (toolkit-common FR-05), so
its exit code (1) differs from the kit's usual prerequisite exit (2). See OQ-01.

**Acceptance Criteria:**

- AC-03.1: [TESTABLE] With `autopkg` absent from `PATH`, the tool exits non-zero,
  prints the message above on stderr, and runs no recipe. **Enforced via:**
  planned test `tests/run_recipes_spec.sh` (planned)

## FR-04 — Which recipes run

[TESTABLE]

1. Find every file named `*.download.recipe.yaml` anywhere under `recipes/`.
2. Sort the paths (byte order, NUL-delimited, so names with spaces are safe).
3. For each, the **app folder** is the file's directory, the **app name** is that
   folder's name, and the **vendor name** is the name of the folder above it.
   Example: `recipes/OrchardLabs/Orchard-Analytics/Orchard-Analytics.download.recipe.yaml`
   gives vendor `OrchardLabs`, app `Orchard-Analytics`.
4. If a filter is set and the app name does not contain it, skip silently (no
   output, not counted).
5. The pkg recipe is `<app folder>/<app name>.pkg.recipe.yaml`. It is derived
   from the folder name, not from the download recipe's file name. If it does
   not exist, the app is **skipped** with reason `missing pkg recipe`.

Consequences of this design, which are current behaviour:

- A folder holding two download recipes runs twice, each time against the same
  pkg recipe.
- A download recipe whose file name differs from its folder name still runs, but
  its pkg recipe must be named after the folder.
- The vendor name is only meaningful for the `recipes/<Vendor>/<App>/` layout.

**Acceptance Criteria:**

- AC-04.1: [TESTABLE] Apps run in sorted path order. **Enforced via:** planned test
  `tests/run_recipes_spec.sh` (planned)
- AC-04.2: [TESTABLE] An app folder with a download recipe and no
  `<app>.pkg.recipe.yaml` is reported as `SKIP: no matching pkg recipe found at
  <path>`, counted as skipped, and `autopkg` is not called for it. **Enforced
  via:** planned test `tests/run_recipes_spec.sh` (planned)
- AC-04.3: [TESTABLE] A folder with a pkg recipe and no download recipe is not
  run and not reported. **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)

## FR-05 — Overrides and the placeholder gate

[TESTABLE]

`.overrides` is optional. If `<app folder>/.overrides` exists, it is read line by
line as `key=value`:

- Empty lines and lines whose key starts with `#` are ignored.
- The last line is read even when the file has no trailing newline.
- The key is everything before the first `=`; the value is the rest, including
  any further `=`. Nothing is trimmed: `version = 1.0` gives key `version ` and
  value ` 1.0`.
- Each line becomes one AutoPkg argument, `--key=<key>=<value>`, in file order.

A value is treated as an **unresolved placeholder** when it starts with `REPLACE`,
contains `PENDING`, or starts with `TEAMID_`. For each one the tool prints
`WARNING: <key>=<value> looks like an unresolved placeholder`. If any were found,
the app is **skipped** with reason `unresolved .overrides placeholder(s)`, and
AutoPkg is not called.

`UNSIGNED_NO_TEAMID` is not a placeholder here. Upstream records it in a download
recipe's `Input`, not in `.overrides`, but a fork's `.overrides` may still carry
`teamid=UNSIGNED_NO_TEAMID`, and it must not cause a skip.

This placeholder list is narrower than `bin/scan-placeholders.sh`'s (see
`specs/scan-placeholders/01-scan-placeholders.md` FR-04) and is checked only in
`.overrides`, not in the recipes. See OQ-02.

**Acceptance Criteria:**

- AC-05.1: [TESTABLE] An `.overrides` of `LICENSE_KEY=ABCDE12345` and `version=2.1`
  results in `autopkg run <download> --key=LICENSE_KEY=ABCDE12345 --key=version=2.1 -v`.
  **Enforced via:** `tests/run_recipes_spec.sh`, "passes every .overrides line,
  including a last line without a newline" (with `version=1.2.3`).
- AC-05.2: [TESTABLE] A value containing `=` is passed whole
  (`url=https://example.invalid/a?b=c` gives `--key=url=https://example.invalid/a?b=c`).
  **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)
- AC-05.3: [TESTABLE] `version=REPLACE_ME`, `teamid=TEAMID_ACME` or
  `version=PENDING` each produce a WARNING line and a skip, and AutoPkg is not
  called for that app. **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)
- AC-05.4: [TESTABLE] `teamid=UNSIGNED_NO_TEAMID` does not cause a skip.
  **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)
- AC-05.5: [TESTABLE] The last line of an `.overrides` file is used even when the
  file has no trailing newline. **Enforced via:** `tests/run_recipes_spec.sh`,
  "passes every .overrides line, including a last line without a newline".
- AC-05.6: [TESTABLE] An app with no `.overrides` file, or an empty one, runs with
  no `--key` arguments. **Enforced via:** `tests/run_recipes_spec.sh`, "runs an
  app that has no .overrides under bash 3.2 (KI-27)" (no file; an empty file is
  planned).

## FR-06 — Clearing the cache

[TESTABLE]

With `--clear-cache`, after the placeholder gate passes and before the download
recipe runs, the tool:

1. Reads the first line starting `Identifier:` from each of the two recipes,
   strips the key, then strips one leading and one trailing single or double
   quote. The rest of the line is the identifier.
2. Calls `bin/clear-autopkg-cache.sh <download-id> <pkg-id>`.

Deletion itself belongs to `bin/clear-autopkg-cache.sh`, which only ever touches
AutoPkg's own cache folder (constitution P-8). This tool never deletes anything
itself. The exit status of the clear step is ignored: the run continues either way.

The identifier is read with `grep` and `sed`, not a YAML parser (constitution
AIP-08). A quoted value (`Identifier: "com.acmefruit.autopkg.download.Orchard"`)
is passed without its quotes. An indented or missing `Identifier:` still gives
an empty argument, which `bin/clear-autopkg-cache.sh` refuses. A trailing
comment on the line is kept. See OQ-06.

**Acceptance Criteria:**

- AC-06.1: [TESTABLE] With `--clear-cache`, the cache tool is called once per
  app with the download identifier then the pkg identifier, before the first
  `autopkg run`. **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)
- AC-06.2: [TESTABLE] Without `--clear-cache`, the cache tool is never called.
  **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)
- AC-06.3: [TESTABLE] A skipped app (FR-04, FR-05) never has its cache cleared.
  **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)
- AC-06.4: [TESTABLE] A quoted `Identifier:` value is passed without its quotes.
  **Enforced via:** planned example in `tests/run_recipes_spec.sh` (planned; the
  fixture already has a quoted identifier, but no example passes `--clear-cache`)

## FR-07 — Running the pair

[TESTABLE]

For each app that was not skipped:

1. `autopkg run <download recipe> <override args…> -v`. If it exits non-zero, the
   app **fails** with reason `download recipe failed`; the pkg recipe is not run.
2. `autopkg run <pkg recipe> <override args…> -v`. If it exits non-zero, the app
   **fails** with reason `pkg recipe failed`.
3. Otherwise the app **passes**.

AutoPkg's own output streams straight through to the terminal. The same override
arguments go to both runs. Because the pkg recipe names the download recipe as
its parent, AutoPkg runs the download steps a second time inside step 2; that is
expected.

One app failing does not stop the run. The next app is tried.

**Acceptance Criteria:**

- AC-07.1: [TESTABLE] A stubbed `autopkg` that fails on the download recipe gives
  `FAIL: download recipe`, one failure, and no call for the pkg recipe.
  **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)
- AC-07.2: [TESTABLE] A stub that fails only on the pkg recipe gives
  `FAIL: pkg recipe` and one failure. **Enforced via:** planned test
  `tests/run_recipes_spec.sh` (planned)
- AC-07.3: [TESTABLE] With two apps where the first fails, the second still runs.
  **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)

## FR-08 — Output

[TESTABLE]

Everything goes to stdout except the missing-`autopkg` error. Per app:

```

=== OrchardLabs/Orchard-Analytics ===
  Running download recipe...
  <AutoPkg output>
  Running pkg recipe...
  <AutoPkg output>
  PASS
```

A skipped app shows its `WARNING:` lines (if any) and one `SKIP:` line. A failed
app shows `FAIL: download recipe` or `FAIL: pkg recipe`.

After the last app:

```

==========================================
Results: 3 passed, 1 failed, 2 skipped
==========================================

Failures:
  - OrchardLabs/Orchard-Analytics: pkg recipe failed

Skipped:
  - OrchardLabs/Orchard-Analytics-License: unresolved .overrides placeholder(s)   (a fork whose pipeline hasn't written its key yet)
```

The `Failures:` and `Skipped:` lists appear only when non-empty.

**Acceptance Criteria:**

- AC-08.1: [TESTABLE] The `Results:` line always appears, with counts that equal
  the number of `PASS`, `FAIL:` and `SKIP:` lines above it. **Enforced via:**
  planned test `tests/run_recipes_spec.sh` (planned)
- AC-08.2: [TESTABLE] Each failure and skip is listed as `<vendor>/<app>: <reason>`.
  **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)
- AC-08.3: [TESTABLE] A filter that matches nothing still prints the summary with
  all counts zero. **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)

## FR-09 — Exit codes and runtime

[TESTABLE]

| Exit | Meaning |
|---|---|
| 0 | No app failed. Skips do not count as failures. |
| 1 | At least one app failed, or `autopkg` is not on `PATH`. |
| 2 | Usage error, unknown customer, or repo resolution failed (toolkit-common FR-04). |

The script must run under the system bash, 3.2 on stock macOS (constitution
P-7). Its shebang is `#!/bin/bash`, so it runs under the system bash even when a
newer bash is earlier on `PATH`. It sets `-u` and `pipefail` but not `-e`, so a failing command
inside the loop does not end the run. An empty override list expands to nothing
under `set -u` (`${override_args[@]+"${override_args[@]}"}`).

**Acceptance Criteria:**

- AC-09.1: [TESTABLE] All apps pass or skip → exit 0; one app fails → exit 1.
  **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)
- AC-09.2: [TESTABLE] The whole harness, including an app with no `.overrides`,
  completes under `/bin/bash` 3.2. **Enforced via:** `tests/run_recipes_spec.sh`,
  "runs an app that has no .overrides under bash 3.2 (KI-27)" (runs the script
  with `/bin/bash`).
- AC-09.3: [STRUCTURAL] No bash 4 constructs (constitution AIP-05). **Enforced
  via:** ShellSpec runs under `/bin/bash` (`.shellspec`); inspection.
- AC-09.4: [TESTABLE] Toolkit assets (`lib/toolkit-common.sh`,
  `bin/clear-autopkg-cache.sh`) are found from the script's own location when run
  from any directory (constitution P-1). **Enforced via:** planned test
  `tests/run_recipes_spec.sh` (planned)

## FR-10 — Side effects and scope

[ADVISORY]

Side effects are those of AutoPkg itself: downloads, files in AutoPkg's cache and
build folders, and built packages. With `--clear-cache`, AutoPkg cache folders for
the run's identifiers are removed through `bin/clear-autopkg-cache.sh`. The tool
writes nothing into the recipe repo and changes no AutoPkg preference.

Prerequisites the tool does **not** set up or check (listed in its header):

- `recipes/` must be on AutoPkg's `RECIPE_SEARCH_DIRS`, or `ParentRecipe`
  identifiers will not resolve.
- Vendor-cache recipes need their real files in the vendor cache first; a recipe
  still pointing at a placeholder file will fail, correctly.

Out of scope: linting (`bin/recipe-linter.sh`), scanning recipe text for
placeholders (`bin/scan-placeholders.sh`), uploading or importing packages,
running recipes in parallel, and a dry-run mode.

**Acceptance Criteria:**

- AC-10.1: [TESTABLE] After a run with a stubbed `autopkg`, the recipe repo's files
  are unchanged. **Enforced via:** planned test `tests/run_recipes_spec.sh` (planned)
- AC-10.2: [STRUCTURAL] The script contains no `rm` and passes no path to the
  cache tool, only identifiers. **Enforced via:** inspection.

---

## Architecture-Incompatible Patterns

**AIP-01: Deleting caches directly.** Removing any folder from this script instead
of through `bin/clear-autopkg-cache.sh`. That tool's hard-coded root is the whole
safety model (constitution P-8). **Enforced via:** AC-10.2.

**AIP-02: Feeding placeholders to AutoPkg.** Passing a value the placeholder gate
flags. A run with `REPLACE_ME` as a version looks like a recipe bug and wastes the
reader's time. **Enforced via:** AC-05.3.

**AIP-03: Stopping at the first failure.** The harness exists to report every
app's state in one run. **Enforced via:** AC-07.3.

**AIP-04: Running real AutoPkg in tests.** Tests stub `autopkg`; the real tool
downloads from vendors and needs the operator's Mac. **Enforced via:** reviewer
check.

---

## Open Questions

**OQ-01:** Should the `autopkg` check use `tk_require` and exit 2, like every
other front end's prerequisite check (toolkit-common FR-05)? Today it exits 1,
which is also the "an app failed" code, so a caller cannot tell them apart.

**OQ-02:** Should the placeholder gate share its token list with
`bin/scan-placeholders.sh`? Today they differ: this tool catches `REPLACE*`,
`*PENDING*` and `TEAMID_*` in `.overrides` only; the scanner also catches
`PLACEHOLDER` and `NOT_APPLICABLE_SEE_README`, in recipes too. Once the scanner
moves to the recipe model, this gate could call it.

**OQ-03:** Should unknown options be rejected (exit 2) instead of becoming the
filter, and should more than one filter be an error? Also, `--help` should list
`--clear-cache`.

**OQ-04:** **(Resolved 2026-09-27)** The loop now keeps an unterminated last
line (`|| [[ -n "${key}" ]]`). Original question: an `.overrides` file without a
trailing newline lost its last line. Still open: should spaces around `=` be
trimmed or rejected?

**OQ-05:** **(Resolved 2026-09-27)** Fixed with
`${override_args[@]+"${override_args[@]}"}`, as the script already does for
positional arguments. Original question: under `/bin/bash` 3.2, an app with no
`.overrides` (or one with only comments) aborted the whole run with
`override_args[@]: unbound variable`.

**OQ-06:** Reading `Identifier:` with `grep`/`sed` misses indented keys and keeps
trailing comments. (Quotes are now stripped, 2026-09-27.) Should `--clear-cache` get identifiers from the shared recipe model
(`specs/recipekit/01-recipe-model.md`) instead, and should a failed clear stop the
app?

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-09-27 | Initial spec, written from the existing implementation. |
| 0.2 | 2026-09-27 | Updated for the fixes to KI-27. |
| 0.3 | 2026-09-27 | .overrides optional; .autopkg_config removed from upstream. Purpose and FR-05 describe `.overrides` as optional and org-defined; harness behavior unchanged. |
| 0.4 | 2026-09-27 | FR-01/FR-02: `--customer <name>`, `$AUTOPKG_TOOLKIT_CUSTOMER` and the registry default select the recipe repo; AC-02.4 to AC-02.6. |
