# Package Analysis Tooling — Constitution

**Status:** Draft
**Date:** 2026-09-08
**Requires:** `specs/toolkit/00-constitution.md` (the toolkit frontend constitution applies to every analysis tool)

---

## Purpose

This document establishes the non-negotiable principles of the package analysis tooling — `analyze-package.sh`, `analyze-materials.sh`, and the inspection micro-tools (`inspect-dmg.sh`, `inspect-app.sh`, `inspect-archive.sh`, `capture-perms.sh`). Every other spec in this directory must conform to these.

The constitution answers "what kind of tools are these?" — not "what features do they have?" Features change; principles don't.

**On enforcement.** Where a principle is the kind of rule an implementer could violate while believing they complied, an **Enforcement** line names the concrete mechanism — a test, a reviewer check, a configuration guard. An Enforcement line is a promise that the principle is checkable, not merely aspirational.

---

## 1. Deterministic Classification

**1.1** Package classification must be deterministic: the same `.pkg` file and same `clues.yaml` always produce the same classification. No randomness, no state-dependent behavior.

**1.2** Classification rules are data-driven, not hardcoded. All heuristics — identifier patterns, team IDs, filename patterns, install locations — come from a `clues.yaml` file supplied at invocation. The tool is a generic engine that applies rules from data.

**1.3** Adding or changing a heuristic requires editing `clues.yaml` — never the tool code.

**Enforcement:** automated test — feed the same `.pkg` with the same `clues.yaml` twice; assert identical output.

---

## 2. Transparent Rationale

**2.1** Every classification decision must explain itself. The output includes a rationale section listing which signals contributed to the decision and at what confidence level.

**2.2** The rationale is structured, not free-text — each rationale entry names the specific signal (identifier pattern, signature status, install location, etc.) and the weight that determined it.

**2.3** When signals are contradictory (e.g., vendor-like identifier but unsigned), the tool must report the contradiction clearly and downgrade confidence accordingly.

**Enforcement:** automated test — feed a signed vendor package, a clearly custom package, and an ambiguous one; assert each rationale lists named signals.

---

## 3. Structured Output

**3.1** Every analysis tool must support at least two output modes:
- **Text mode** — human-readable, with section headers and aligned fields
- **JSON mode** (`--output json`) — machine-readable, single JSON object (or array for multi-result tools), suitable for consumption by AI agents and downstream scripts

**3.2** JSON output must be parseable without error by Python's `json.loads()` and by `jq`.

**3.3** Text output must be readable at a terminal without pagination — sections separated by `=== ... ===` markers consistent with `tk_section` from `lib/toolkit-common.sh`.

**Enforcement:** automated test — for each output mode, capture output and validate format.

---

## 4. Minimal Privilege

**4.1** Tools must prefer read-only analysis when sufficient. Metadata extraction (identifier, version, signature) does not require extraction and should work without root.

**4.2** If a tool requires temporary extraction (e.g., `pkgutil --expand-full` for payload inspection), it may require root — `pkgutil` grants file ownership on extraction, and on some macOS versions, expanding a flat package is gated on file read access that only root has. The tool must check and warn clearly, not fail cryptically.

**4.3** A tool that needs root for extraction must state so early in its output and explain why. It must offer `--allow-unprivileged` as an override (following the pattern established by `pkg-reverse.sh`), and when that flag is used, note that ownership data from the BOM may be unreachable.

**4.4** If a tool requires temporary extraction and succeeds, it must clean up temporary directories unless `--work-dir` is specified.

**4.5** If a tool mounts a volume (e.g., `hdiutil attach`), it must unmount it before exiting unless `--keep-mounted` is specified.

**Enforcement:** automated test — run analyze-package.sh as non-root in metadata-only mode; assert metadata extraction succeeds. Run with `--allow-unprivileged` for payload analysis; assert that analysis works but ownership data notes the limitation.

---

## 5. Graceful Degradation

**5.1** Tools must tolerate any valid or invalid file they are given. A non-package file, a corrupt archive, an unreadable path — all produce a clear error message and exit non-zero, never a crash.

**5.2** A `clues.yaml` that was named (`--clues <file>`) but is missing, or is invalid, is a configuration error (exit code 2 with a message saying what is wrong). When no clues are supplied, or a `--customer` folder has none (a warning), the tool may run its generic heuristics, but never silently: its output says no clues were used.

**5.3** A tool that cannot complete its analysis must still report whatever information it could determine, plus what it could not.

**5.4** Exit codes:
- 0 = analysis completed successfully
- 1 = analysis completed but issues found (e.g., classification low confidence)
- 2 = usage error (bad arguments, missing files, invalid config)

**Enforcement:** automated test — feed each tool a non-package file; assert exit 2 and clear error message.

---

## 6. Composability

**6.1** Micro-tools (`inspect-dmg.sh`, `inspect-app.sh`, `inspect-archive.sh`, `capture-perms.sh`) must accept a file or directory path as an argument and output to stdout. They must not require interactive input.

**6.2** Micro-tools must support `--output json` so an AI agent can chain their outputs programmatically.

**6.3** Every micro-tool must produce text and JSON output that another tool or an LLM can parse without knowledge of the internal implementation.

**Enforcement:** reviewer check — each micro-tool's JSON output is a single valid JSON object.

---

## 7. Stock macOS Toolchain (Bash Tools)

**7.0** An analysis tool may instead be written in AutoPkg's Python with the standard library and PyYAML, behind a bash front end that keeps the command (toolkit constitution P-7, P-9, P-10). `bin/analyze-package.sh` is (`recipekit.analyze_package`). The rest of this section applies to the bash tools.

**7.1** Bash-based analysis tools must prefer stock macOS utilities first. Reach for a non-stock tool only when the stock alternative is genuinely inadequate, and the non-stock tool provides unambiguous value that justifies the external dependency.

**7.2** Acceptable stock utilities: `grep` (BSD grep, no `-P`), `sed` (BSD sed, `-E` for ERE), `awk`, `sort`, `find`, `xargs`, `tr`, `cut`, `head`, `tail`, `basename`, `dirname`, `tee`, `comm`, `diff`, `uniq`, `cat`, `echo`, `printf`, `test`/`[`, `[[ ]]`, `plutil`, `hdiutil`, `pkgutil`, `lsbom`, `stat`, `readlink`, `mdls`, `file`, `unzip`, `tar`, `ditto`, `python3`.

**7.3** The following are NOT stock but acceptable with a `require_command` check: `tree` (commonly available, structured directory dumps).

**7.4** A non-stock tool may be proposed if the implementer can demonstrate that:
- The stock equivalent produces wrong or ambiguous results for the specific use case
- The non-stock tool solves a real problem that cannot be practically solved with stock tools
- The proposal is surfaced to the operator for approval, not silently added

*Example: `ripgrep` over BSD `grep` for searching plain-text notes in a large upstream repo — the operator evaluates and decides.*

**7.5** Not stock, require fallback, default to avoiding: `grep -P` (PCRE), `sed -r` (GNU-only), `realpath`, `readlink -f`, `sort -V`, `xargs -d`, `jq`, `yq`.

**7.6** Bash dialect: tools run under `/bin/bash` (macOS 3.2 in current releases). Prohibited constructs include:
- `declare -A` / associative arrays
- `mapfile` / `readarray`
- `${var,,}` / `${var^^}` (case modification)
- `**` globstar
- Process substitution `<(...)` where compatibility issues arise

**Enforcement:** Shellcheck flags GNU-specific flags under `shell=sh`/`shell=bash` directives. Reviewer check for bash 3.2 incompatible constructs.

**7.4** The tools may assume macOS (`uname -s` = Darwin) and check via `require_macos` from `lib/toolkit-common.sh`. They are macOS-only tools.

**Enforcement:** Shellcheck flags GNU-specific flags. Tools call `require_macos` at entry.

---

## 8. No Side Effects on Input

**8.1** Analysis tools must not modify the files they analyze. Read-only operations only.

**8.2** Temporary files must be cleaned up. The only persistent output is what the tool explicitly writes or the tool's stdout.

**Enforcement:** automated test — run tool on a file; verify file modification time and checksum unchanged.

---

## 9. Customer Awareness

**9.1** Tools that read `clues.yaml` must accept it via `--clues <path>` or discover it from `customer/<CustomerName>/clues.yaml`. They must not require the file to be in a fixed global location.

**9.2** Tools that produce per-customer output must accept `--customer <CustomerName>` or read it from paths.yaml.

**9.3** If no customer context is supplied, tools must still function for ad-hoc analysis — they simply lack customer-specific heuristics and will report accordingly.

**Enforcement:** automated test — run with `--clues`, without, and with a missing clues file; assert appropriate behavior for each.

---

## 10. Amendment

**10.1** This constitution may be amended, but amendments are explicit, dated, and require re-review of any downstream specs that depended on the amended clause.

**10.2** During design, if a constitution clause appears to block a reasonable feature, the correct response is to surface the conflict for discussion — not to quietly work around the clause.

**10.3** Amendment history:
- 2026-09-27: §5.2 aligned with analyze-package FR-1/AC-04.4 (no clues → generic heuristics, stated in the output).
- 2026-09-27: §7.0 added — Python analysis tools behind bash front ends (toolkit P-7/P-10).
- 2026-09-08: Initial release — 9 principles derived from the Master Enhancement Plan and architecture spec discussions.
