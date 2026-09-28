# Package Reverse-Engineering Tool — Constitution

**Status:** Draft
**Date:** 2026-09-08
**Requires:** `specs/toolkit/00-constitution.md` (the toolkit frontend constitution applies to every tool in `bin/`)

---

## Purpose

This document establishes the non-negotiable principles of the package reverse-engineering tool (`pkg-reverse.sh`) and its companion driver (`blueprint-to-recipe.sh`). Every other spec in this directory must conform to these.

The constitution answers "what kind of tools are these?" — not "what features do they have?" Features change; principles don't.

**On enforcement.** Where a principle is the kind of rule an implementer could violate while believing they complied, an **Enforcement** line names the concrete mechanism — a test, a reviewer check, a configuration guard. An Enforcement line is a promise that the principle is checkable, not merely aspirational.

---

## 1. Ownership Fidelity

**1.1** Package ownership must be preserved. The extracted payload tree must match the original package's BOM ownership records, or the tool must document the discrepancy and generate a `chown` block that reconstructs it.

**1.2** Running without root is the primary cause of ownership loss. The tool MUST default to refusing to operate as non-root, and MUST require an explicit `--allow-unprivileged` override to proceed. When that override is used, the tool MUST warn prominently and generate BOM-derived ownership data that the downstream recipe can use.

**1.3** The BOM analysis for ownership reconstruction must be rolled up — one entry per uniquely-owned directory subtree, not one per file — because `PkgCreator`'s `chown` walks the tree recursively (`chown -R` semantics).

**1.4** Ownership reconstruction is strictly worse than preserving it via root extraction. The tool must communicate this rank ordering clearly.

**Enforcement:** automated test — run on a known package as root and as `--allow-unprivileged`; assert the non-root run produces a `chown-entries.txt` and the root run does not.

---

## 2. Signature Awareness

**2.1** The tool MUST check and report the package's signature status using `pkgutil --check-signature` (the only authoritative tool for `.pkg` signatures — see `reference/methodology.md` item #5). It MUST NOT use `codesign` for this purpose.

**2.2** When a signed package is detected, the tool MUST:
- Report the signing authority (first certificate in the chain)
- Emit a prominent warning that rebuilding discards that signature
- Recommend `PkgCopier` (Pattern 4 Variant A) as the correct alternative for packages not built by the operator

**2.3** The signature status and authority must be recorded in `blueprint.conf` so downstream tools and reviewers can see the original state without re-running the check.

**Enforcement:** reviewer check — signature output appears in the run log and in `blueprint.conf`. Automated test on a known-signed test package.

---

## 3. Transparent Output

**3.1** Every stage of the reverse-engineering process must report what it found, what it did, and what it skipped. Silence implies success — a stage that prints nothing must have succeeded.

**3.2** Output uses `tk_section` markers (`=== Section name ===`) from `lib/toolkit-common.sh` consistently.

**3.3** Warnings and errors are distinguished: `tk_warn` for recoverable issues, `tk_err` + `tk_die` for fatal ones, per the library contract.

**3.4** The `blueprint.conf` output is designed to be read and edited before use — it is a handoff artifact, not a machine-only intermediate. Comments explain each field.

**3.5** All paths in output and blueprint must be absolute. Relative paths in the blueprint would silently resolve differently depending on where `blueprint-to-recipe.sh` is invoked.

**Enforcement:** reviewer check — every field in `blueprint.conf` has a comment or is self-explanatory. All paths are absolute.

---

## 4. Clean Cleanup

**4.1** Temporary extraction directories must be removed before the tool exits normally. The intermediate `pkgutil --expand-full` output (`<out>/.expanded`) is a large tree — leaving it behind is a user-visible mess.

**4.2** Cleanup must happen on both success and error paths. A `tk_die` after an extraction has already happened is a bug unless the expanded tree is explicitly preserved (as in the multi-component distribution case, where leaving it for inspection is intentional).

**4.3** The tool must refuse to overwrite an existing output directory. If `--dest <dir>/<AppName>` already exists, the tool exits with an error explaining how to resolve it (`--name` for a different directory, or manual removal).

**Enforcement:** automated test — run twice against the same output directory; assert the second run fails with a clear message. Verify no `.expanded` directory remains after a successful run.

---

## 5. Composability

**5.1** `pkg-reverse.sh` is the first half of a two-tool pipeline. Its output (`blueprint.conf`) is the sole input to `blueprint-to-recipe.sh`. The two tools MUST be independently usable — each must work without the other having been run, as long as the required input format is present.

**5.2** The `blueprint.conf` format is the contract between the two tools. It must be documented, stable, and versioned. Any change to the format in one tool must be reflected in the other in the same commit.

**5.3** The tool may be integrated into a larger workflow (`analyze-package.sh` → `pkg-reverse.sh` → `blueprint-to-recipe.sh` → `autopkg run` → `pkg-compare.sh`), but must not depend on any other tool in that chain having been run first.

**5.4** Output targets (`--dest`) must be independent of toolkit and repo resolution — the extracted tree goes wherever the user says, without reference to `REPO_ROOT` or `TOOLKIT_ROOT`.

**Enforcement:** automated test — run `pkg-reverse.sh` → edit `blueprint.conf` → run `blueprint-to-recipe.sh`; assert each step succeeds independently.

---

## 6. Idempotent Extraction

**6.1** Given the same input `.pkg` and the same `--dest`, `--name` arguments, the tool must produce a functionally identical output tree (same payload content, same blueprint values). Timestamps in the blueprint comment are the only expected difference.

**6.2** The tool does not modify the input package. It is read-only with respect to its source file.

**Enforcement:** automated test — run twice with different output directories; diff the payload trees (excluding timestamps).

---

## 7. Correct Package Classification

**7.1** The tool must correctly classify a flat `.pkg` as either a **component package** (has `PackageInfo` at the top level of the expanded tree) or a **distribution package** (has `Distribution` instead of `PackageInfo`).

**7.2** A distribution package with exactly one child component may be demoted to "distribution wrapper around a single component" — the tool warns and proceeds using that single component.

**7.3** A distribution package with zero or multiple components MUST be refused outright. `PkgCreator` cannot reproduce the `Distribution` XML's install choices, requirements, or embedded JavaScript, and a recipe that silently dropped them would be dangerously wrong.

**7.4** Bundle-style `.pkg` directories (not flat packages) must be detected and refused with a clear error message.

**Enforcement:** automated test — feed a distribution package with 2+ components; assert exit 3 and message naming each component.

---

## 8. Minimal Privilege

**8.1** The tool requires root for correct ownership preservation. This is enforced by default.

**8.2** `--allow-unprivileged` is provided as an escape hatch for circumstances where root is genuinely unavailable (CI, non-admin machine). When used, the tool must still extract and analyze everything it can — only ownership will be wrong and must be noted.

**8.3** The privilege check happens before any work is done — before expansion, before directory creation — so the user is not left with a half-finished extraction if they cancel and retry with `sudo`.

**Enforcement:** reviewer check — the privilege check is the first operational code after argument parsing.

---

## 9. Graceful Degradation

**9.1** The tool must tolerate any valid or invalid file it is given. A non-package file, a corrupt archive, an unreadable path — all produce a clear error message and exit non-zero, never a crash.

**9.2** A tool that cannot complete its analysis must still report whatever information it could determine, plus what it could not.

**9.3** Exit codes:
- 0 = reverse-engineering completed successfully
- 1 = (reserved — no partial-success case currently defined)
- 2 = usage error (bad arguments, missing files, not found)
- 3 = package structure error (multi-component distribution, unhandled format)

**Enforcement:** automated test — feed a non-package file; assert exit 2 and clear error message.

---

## 10. Stock macOS Toolchain

**10.1** `pkg-reverse.sh` uses stock macOS utilities (`pkgutil`, `lsbom`, `ditto`, `du`) and AutoPkg's Python with the standard library (toolkit constitution P-7). It installs nothing.

**10.2** `pkgutil` is the authoritative tool for extracting flat packages and checking signatures. The tool calls `require_command` for each prerequisite with a clear remediation message.

**10.3** The front end `bin/pkg-reverse.sh` runs under `/bin/bash` 3.2; the work is done in `lib/python/recipekit/pkg_reverse.py` (toolkit constitution P-7, P-9, P-10).

**Enforcement:** Shellcheck on the front end; black, isort and flake8 on the Python (`tests/kit_hygiene_spec.sh`).

---

## 11. Amendment

**11.1** This constitution may be amended, but amendments are explicit, dated, and require re-review of any downstream specs that depended on the amended clause.

**11.2** During design, if a constitution clause appears to block a reasonable feature, the correct response is to surface the conflict for discussion — not to quietly work around the clause.

**11.3** Amendment history:
- 2026-09-27: §10 amended for the Python port (toolkit P-7/P-10); `awk` and `xmllint` no longer used.
- 2026-09-08: Initial release — 10 principles derived from the existing `bin/pkg-reverse.sh` implementation, `reference/methodology.md`, Pattern 6 templates, and guardrails.

---

## Appendix A — Audit Discrepancies

Discrepancies found during a line-by-line audit of the existing `bin/pkg-reverse.sh` implementation against this spec document. None require code changes; they are recorded here so implementers know what the current implementation does vs. what the spec says, and to decide whether to update the spec or the code.

| # | Location | Spec Claim | Actual Behavior | Resolution |
|---|----------|------------|-----------------|------------|
| — | (no discrepancies found) | | | |
