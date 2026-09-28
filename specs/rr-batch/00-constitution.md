# AutoPKG Recipe Batcher — Constitution

**Status:** Draft
**Date:** 2026-08-02

---

## Purpose

This document establishes the non-negotiable principles of the AutoPKG Recipe
Batcher (`rr-batch.sh`). Every other spec for this tool must conform to these.
When a downstream design decision conflicts with the constitution, the
constitution wins and the decision is revised.

The constitution answers "what kind of tool is this?" — not "what features does
it have?" Features change; principles don't.

**On enforcement.** Where a principle is the kind of rule an implementer could
violate while believing they complied, an **Enforcement** line names the concrete
mechanism — a test, a reviewer check, a configuration guard. These lines point
at the mechanism; the detailed acceptance criteria live in the relevant feature
spec. An Enforcement line is a promise that the principle is checkable, not
merely aspirational.

---

## 1. Batch Input, Not Ad-Hoc Execution

**1.1** The batcher takes a declarative input file (CSV) that lists every app to
process, its download URL or identifier, and any per-app parameters. It never
accepts a single ad-hoc app argument for one-off generation — that is what
Recipe Robot itself is for.

**1.2** The input file is the source of truth for what will be generated. If an
app is not in the input file, the batcher will not generate recipes for it.

**1.3** The batcher must validate the input file before any recipe generation
begins. Malformed lines, missing fields, or other structural defects are
reported and cause early exit — not partial generation.

**Enforcement:** automated test — feed malformed CSV; assert tool exits before
any recipe generation; assert error message identifies the defect.

---

## 2. Deterministic, Idempotent Operation

**2.1** Running the batcher twice with the same input file and same flags
produces the same set of generated recipes (content may differ due to Recipe
Robot version differences — the batcher's own outputs are deterministic).

**2.2** The batcher does not mutate state outside its designated output
directory and log directory. It does not write to Recipe Robot's auto-discovery
repos or any other shared location.

**2.3** The batcher must tolerate re-running against an output directory that
already contains generated recipes. Existing files may be overwritten or left in
place depending on flags — the batcher never orphans partial output.

**Enforcement:** automated test — run batcher twice on same input; compare
output artifacts; assert identical. Automated test — remove output dir between
runs; assert isolated output.

---

## 3. Transparent Audit Trail

**3.1** Every batch run produces a structured log that records: invocation
arguments, timestamp, each app processed (including URL and app name), Recipe
Robot exit code, and the final output paths of generated recipes.

**3.2** Failed generations are reported individually alongside passing ones.
The exit code distinguishes total success (all passed), partial failure (some
failed), and usage error.

**3.3** Exit codes:
- 0 = all recipes generated successfully
- 1 = one or more recipe generations failed
- 2 = usage error (bad arguments, missing input file, invalid config)

**Enforcement:** automated test — run batcher on input with one known-failing
entry; assert exit code 1; assert log contains both PASS and FAIL entries.

---

## 4. Generated Output Must Be Linter-Valid

**4.1** Every recipe file produced by the batcher must pass the AutoPKG Recipe
Linter (`bin/recipe-linter.sh`) when invoked with its default specs. The
batcher may optionally run the linter on its own output as a post-generation
validation step.

**4.2** If the batcher includes a `--lint` flag to run post-generation
linting, a lint failure on a generated recipe must be reported as a batch
failure, not silently ignored.

**4.3** The batcher's output must conform to the directory and naming
conventions defined in the upstream spec (§3.1, §3.3 of AUTOPKG-STD-001).
Specifically: `recipes/<VendorName>/<AppName>/<AppName>.download.recipe.yaml`
and `<AppName>.pkg.recipe.yaml`.

**Enforcement:** automated test — generate recipes from a known input; run
linter on the output; assert zero lint errors.

---

## 5. Stock macOS Toolchain Constraint

**5.0** Amended 2026-09-27: the batcher is AutoPkg's Python (standard library and
PyYAML) behind the `bin/rr-batch.sh` front end (toolkit constitution P-7, P-10).
Recipe Robot is the one outside tool it runs. §5.1–5.4 apply to the front end.

**5.1** The batcher implementation must limit itself
to command-line utilities available in a standard macOS installation.
"Standard" means: present in `/usr/bin/` or `/bin/` on a clean install of the
current macOS release at the time of development, without any optional installs
(Xcode CLT, Homebrew, MacPorts, etc.).

**5.2** Where the implementation needs behavior that requires a non-stock
utility, it must either:
- Implement the logic in pure Bash (shell builtins, parameter expansion,
  variable substitution, etc.), or
- Provide a documented fallback path with a clear error message when a
  required non-stock utility is absent.

**5.3** The following are known to be acceptable stock utilities
(non-exhaustive): `grep` (BSD grep, no `-P`), `sed` (BSD sed, `-E` for ERE),
`awk`, `sort`, `find`, `xargs`, `tr`, `cut`, `head`, `tail`, `basename`,
`dirname`, `tee`, `comm`, `diff`, `uniq`, `cat`, `echo`, `printf`, `test`/`[`,
`[[ ]]`.

**5.4** The following are explicitly NOT stock and require a fallback or
pure-Bash alternative if used: `grep -P` (PCRE), `sed -r` (GNU-only),
`realpath`, `readlink -f`, `sort -V`, `xargs -d`.

**Enforcement:** Shellcheck flags GNU-specific flags under `shell=sh`/`shell=bash`
directives. CI jobs run on a macOS runner with only the base system.

---

## 6. Post-Generation Recipe Normalization

**6.1** Recipe Robot output is treated as a starting point, not a final
artifact. The batcher must normalize generated recipes to conform to the naming
conventions, identifier namespaces, and directory layout defined in the upstream
spec (§3 of AUTOPKG-STD-001).

**6.2** Normalization includes but is not limited to: renaming files from
Recipe Robot's default names to `AppName.{download,pkg}.recipe.yaml` (AppName from
the input file), setting Identifier, ParentRecipe and NAME from the org prefix and
AppName (which also fixes `…pkg.download.*`), and placing recipes in the
`VendorName/AppName/` directory hierarchy.

**Enforcement:** automated test — capture Recipe Robot output for a known app;
run batcher normalization; assert filename, Identifier, and directory path
comply with §3 conventions.

---

## 7. Graceful Degradation on Recipe Robot Failure

**7.1** Recipe Robot may fail for many reasons (unreachable URL, unsupported
download pattern, timeouts). The batcher must handle each failure gracefully:
log the error with the exit code and any stderr output, record the app as
FAILED, and continue to the next entry.

**7.2** A single Recipe Robot failure must never abort the entire batch.

**7.3** After all entries are processed, the batcher must report a summary
with counts of pass/fail/total, and list all failed apps.

**Enforcement:** automated test — feed input with a known-broken URL alongside
valid entries; assert the valid ones succeed and the broken one fails; assert
summary correctly counts both.

---

## 8. Amendment

**8.1** This constitution may be amended, but amendments are explicit, dated,
and require re-review of any downstream specs that depended on the amended
clause.

**8.2** During design, if a constitution clause appears to block a reasonable
feature, the correct response is to surface the conflict for discussion — not to
quietly work around the clause.

**8.3** Amendment history:
- 2026-09-27: §5.0 (Python behind a bash front end); §6.2 (names and identifiers
  set from the input file; `rr-rename-postprocess.sh` folded in).
- 2026-08-02: Initial release — 7 principles derived from the upstream
  AUTOPKG-STD-001 specification and the linter constitution pattern.
