# pkg-reverse.sh — Package Reverse-Engineering Tool

**Status:** Draft
**Date:** 2026-09-08
**Requires:** `00-constitution.md`
**Implementation:** `lib/python/recipekit/pkg_reverse.py` and `pkg.py`; `bin/pkg-reverse.sh` is the front end (usage text, macOS and tool checks). Tests: `tests/pkg_reverse_spec.sh` (the command), `tests/python/test_pkg.py` (the logic).

---

## Purpose

Given a flat `.pkg` file, dismantle it into a working payload tree plus a `blueprint.conf` that captures its metadata. The output is ready for review, editing, and consumption by `blueprint-to-recipe.sh` to generate a first-draft Pattern 6 AutoPkg recipe pair.

This tool exists for **in-house packages whose source files are gone** — no build recipe, no pkgroot, and nobody left who has them. It is explicitly NOT for vendor packages you could ship as-is.

### Normative vs. Informative

- **Normative (MUST/MUST NOT):** CLI interface, output structure, exit codes, error messages, blueprint.conf field semantics, and all acceptance criteria.
- **Informative:** specific output formatting details, example values. A conforming implementation may format text output differently as long as the normative contracts are satisfied.

### Classification Key

- **[TESTABLE]** — Observable and automatable. Enforcement mechanism stated.
- **[STRUCTURAL]** — Enforced by schema, layout, or data model constraint.
- **[ADVISORY]** — Review judgment. Reserved for genuine non-checkables.

---

## 1. Command-Line Interface

### FR-1 — Argument Parsing

[STRUCTURAL]

The tool accepts a positional `.pkg` file path and optional flags:

| Flag | Argument | Required | Description |
|------|----------|----------|-------------|
| `path` (positional) | File path | Yes | Path to the `.pkg` file to reverse-engineer |
| `--dest` | Directory path | Yes | Output directory (the `vendor_cache` directory to write into, or similar staging area) |
| `--name` | String | No | Application name for the output subdirectory; defaults to the `.pkg` filename without extension, sanitised to `[A-Za-z0-9-]` |
| `--allow-unprivileged` | — | No | Proceed without root; ownership will be wrong and must be reconstructed from the BOM |
| `-h` / `--help` | — | No | Print usage and exit 0 |

**Acceptance Criteria:**

- AC-01.1: [TESTABLE] Running with a valid `.pkg` path and `--dest` succeeds.
- AC-01.2: [TESTABLE] Running without `--dest` fails with exit 2 and a message naming the missing flag.
- AC-01.3: [TESTABLE] Running without a positional path prints usage and exits 2.
- AC-01.4: [TESTABLE] Running with `--name MyApp` creates the output under `<dest>/MyApp/` instead of the derived name.
- AC-01.5: [TESTABLE] Running as non-root without `--allow-unprivileged` fails with exit 2 and a message naming `sudo` and the override flag.
- AC-01.6: [TESTABLE] `--help` prints the usage block from lines 3–28 of the script header and exits 0.
- AC-01.7: [TESTABLE] An unknown flag fails with exit 2 and a message identifying the unknown option.

---

## 2. Package Expansion

### FR-2 — Expand Flat Package

[TESTABLE]

Expand the input `.pkg` using `pkgutil --expand-full` into a temporary directory under the output tree.

**Behavior:**

1. Resolve the input package to an absolute path.
2. Derive `APP_NAME` from the basename if `--name` was not provided — strip `.pkg` extension, replace spaces and underscores with hyphens, strip non-alphanumeric-non-hyphen characters.
3. Check privilege (see §4 below).
4. Create output directory `<dest>/<AppName>/`.
5. Expand: `pkgutil --expand-full <pkg> <out>/.expanded`.
6. If expansion fails, exit 2 with a message noting that the file may not be a flat package.

**Acceptance Criteria:**

- AC-02.1: [TESTABLE] A valid flat package expands successfully.
- AC-02.2: [TESTABLE] A non-package file causes expansion failure and exit 2.
- AC-02.3: [TESTABLE] A bundle-style `.pkg` directory (not flat) is caught by the `-f` file check before expansion — exits 2 with "Not a file: ${PKG_PATH}".

---

## 3. Package Kind Detection

### FR-3 — Classify Package Type

[STRUCTURAL]

After expansion, classify the package by inspecting the expanded tree:

| Signal | File to check | Type | Handling |
|--------|---------------|------|----------|
| Component package | `<expanded>/PackageInfo` exists | `component` | Use this directory directly |
| Distribution package | `<expanded>/Distribution` exists | `distribution` | Count child `*.pkg` directories |
| Neither | Neither file exists | `unknown` | Exit 2 with message |

**Distribution package handling:**

1. Count child component directories: `find <expanded> -maxdepth 1 -type d -name '*.pkg' | sort`.
2. If **exactly 1** child: warn that the Distribution XML's choices, requirements, and JavaScript will NOT be reproduced, but proceed using that single component.
3. If **0 or >1** children: exit 3. List all child components found. Explain that `PkgCreator` cannot reproduce the Distribution XML. Leave the expanded tree in place for inspection.

**Acceptance Criteria:**

- AC-03.1: [TESTABLE] A component package classifies as `component`.
- AC-03.2: [TESTABLE] A distribution package with 1 component classifies as `distribution` with a warning and proceeds.
- AC-03.3: [TESTABLE] A distribution package with 2+ components exits 3, lists the components, and leaves the expanded tree.
- AC-03.4: [TESTABLE] A distribution package with 0 components exits 3.
- AC-03.5: [TESTABLE] `PKG_KIND` and `COMPONENT_COUNT` are recorded in `blueprint.conf`.

---

## 4. Privilege Check

### FR-4 — Root Check

[STRUCTURAL]

Before any destructive or extraction work begins:

1. If `$(id -u)` equals 0 (root): proceed normally.
2. If not root and `--allow-unprivileged` was passed:
   - Emit `tk_warn` lines stating that files will be owned by `$(id -un):$(id -gn)`, not by what the package specifies.
   - Note that the blueprint will carry a `chown` block so the recipe can restore ownership at build time.
   - Proceed.
3. If not root and `--allow-unprivileged` was NOT passed:
   - Emit `tk_err` explaining that `pkgutil` extracts as the invoking user, so ownership is lost.
   - Emit `tk_err` with the exact `sudo` command to re-run.
   - Emit `tk_err` naming the `--allow-unprivileged` override as an alternative.
   - Exit 2.

**Acceptance Criteria:**

- AC-04.1: [TESTABLE] Running as root proceeds without privilege warnings.
- AC-04.2: [TESTABLE] Running as non-root with `--allow-unprivileged` proceeds with ownership warnings.
- AC-04.3: [TESTABLE] Running as non-root without `--allow-unprivileged` exits 2 with a multi-line error message explaining the issue and remedies.

---

## 5. Metadata Extraction

### FR-5 — Read PackageInfo

[TESTABLE]

From the component's `PackageInfo` XML file, extract:

| Field | XPath | Default |
|-------|-------|---------|
| Package identifier | `/pkg-info/@identifier` | Empty string |
| Version | `/pkg-info/@version` | Empty string |
| Install location | `/pkg-info/@install-location` | `/` if absent |

All three are extracted via `xmllint --xpath` and must be reported in the output and written to `blueprint.conf`.

**Acceptance Criteria:**

- AC-05.1: [TESTABLE] A package with all three attributes reports them correctly.
- AC-05.2: [TESTABLE] A package with no `install-location` defaults to `/`.
- AC-05.3: [TESTABLE] A package with empty identifier reports `<none>`.
- AC-05.4: [TESTABLE] `pkg_id`, `version`, and `install_location` are written to `blueprint.conf`.

---

## 6. Signature Analysis

### FR-6 — Check Signature

[TESTABLE]

Run `pkgutil --check-signature` on the input `.pkg` file and determine:

| State | Detection | Output |
|-------|-----------|--------|
| Signed | Output contains `Status: signed` | Report signing authority (first line of certificate chain) |
| Unsigned | Output does not contain `Status: signed` | Report "unsigned (expected for in-house packages)" |

**Behavior:**

1. Run `pkgutil --check-signature "${PKG_PATH}" 2>/dev/null`.
2. If output contains `Status: signed`, the package IS signed:
   - Take the first authority name: the text after `1. ` on the first numbered certificate line.
   - Print `SIGNED by: <authority>`.
   - Emit two `tk_warn` lines: one explaining that rebuilding discards the signature, one recommending `PkgCopier` (Pattern 4 Variant A) as the correct approach for packages not built by the operator.
3. If not signed, report "unsigned (expected for in-house packages)".
4. Record `signature_status` and `signature_authority` in `blueprint.conf`.

**Acceptance Criteria:**

- AC-06.1: [TESTABLE] A signed package reports the signing authority correctly.
- AC-06.2: [TESTABLE] A signed package emits the signature-discard warning.
- AC-06.3: [TESTABLE] An unsigned package reports "unsigned" with no authority.
- AC-06.4: [TESTABLE] Signature status and authority are written to `blueprint.conf`.

---

## 7. Payload Extraction

### FR-7 — Extract Payload Tree

[TESTABLE]

Copy the expanded payload directory to `<out>/payload/` using `/usr/bin/ditto`.

**Behavior:**

1. Verify the payload source directory exists: `<component_dir>/Payload`.
2. Create `<out>/payload/`.
3. Run `ditto <payload_src> <out>/payload`.
4. If ditto fails, exit 2.
5. Count and report:
   - File count: `find <out>/payload -type f | wc -l`
   - Directory count: `find <out>/payload -type d | wc -l`
   - Payload size: `du -sh <out>/payload | cut -f1`

**Acceptance Criteria:**

- AC-07.1: [TESTABLE] Payload is extracted to `<out>/payload/` correctly.
- AC-07.2: [TESTABLE] File count, directory count, and size are reported.
- AC-07.3: [TESTABLE] File count, directory count, and size are written to `blueprint.conf`.
- AC-07.4: [TESTABLE] A package with no Payload directory exits with an error.

---

## 8. Script Preservation

### FR-8 — Extract and Fix Scripts

[TESTABLE]

If the expanded package contains a `Scripts` directory with content, copy it to `<out>/scripts/` and ensure executable bits.

**Behavior:**

1. If `<component_dir>/Scripts` exists and is non-empty:
   - Create `<out>/scripts/`.
   - `ditto <scripts_src> <out>/scripts`.
   - For each of `preinstall` and `postinstall` that exist: `chmod +x`.
   - List all script files found.
   - Record the list in `blueprint.conf` (space-separated).
2. If no scripts: report "none".

**Why `chmod +x` is applied:** `PkgCreator` rejects a build if `preinstall`/`postinstall` exist but are not executable. The default extraction permissions may not preserve the executable bit. Fixing it here prevents a recipe failure downstream.

**Acceptance Criteria:**

- AC-08.1: [TESTABLE] Scripts are extracted to `<out>/scripts/` when present.
- AC-08.2: [TESTABLE] `preinstall` and `postinstall` are executable after extraction.
- AC-08.3: [TESTABLE] No scripts directory produces "none" output and `scripts=` in `blueprint.conf` has an empty value (the key is always present).
- AC-08.4: [TESTABLE] Script names are recorded in `blueprint.conf` (space-separated).

---

## 9. BOM Analysis

### FR-9 — Read and Analyze Bill of Materials

[TESTABLE]

Process the package's BOM file using `lsbom` and perform ownership comparison.

**Behavior:**

1. If `<component_dir>/Bom` exists:
   - Run `lsbom -p mugsfl <Bom> > <out>/bom.txt`: numeric mode, uid, gid, size (empty for directories), path and symlink target, **tab-separated** (KI-4).
   - If `lsbom` fails, emit a warning and continue (bom.txt may be incomplete).
   - Report the number of entries recorded.
   - Run an ownership check: compare the numeric UIDs in `bom.txt` with the invoking user's:
     - If running as root: report "ownership preserved (extracted as root)".
     - If not root: report "ownership NOT preserved — recipe will need a chown block".
     - If every entry's UID matches the current user: note "BOM records all files as uid <n> anyway".
   - If ownership is NOT preserved, set `CHOWN_NEEDED=true`.
2. If no BOM file: emit a warning and continue without ownership verification.

**Acceptance Criteria:**

- AC-09.1: [TESTABLE] BOM is written to `bom.txt` when present.
- AC-09.2: [TESTABLE] BOM entry count is reported and written to output.
- AC-09.3: [TESTABLE] Ownership mismatch is detected and flagged.
- AC-09.4: [TESTABLE] Missing BOM produces a warning, not a failure.
- AC-09.5: [TESTABLE] `ownership_preserved` and `chown_block_needed` are recorded in `blueprint.conf`.

---

## 10. Ownership Analysis (chown Rollup)

### FR-10 — Generate Rolled-Up Ownership Entries

[TESTABLE]

When a `chown` block is needed (not root, `--allow-unprivileged`), analyze the BOM to produce the fewest ownership entries that reproduce it.

**Behavior:**

1. Only run when `CHOWN_NEEDED=true` AND `bom.txt` exists.
2. Read every BOM entry (files, directories and symlinks; paths with spaces included), tab-separated.
3. `PkgCreator`'s `chown` is recursive on a directory and entries apply in order. So walk the paths **parent first** (component by component, so `a` comes before `a/b` and `a b`), and list a path only when its `uid:gid` differs from the one its nearest listed ancestor sets. A top-level path is always listed. The payload root `.` never is.
4. The result: a uniform subtree is one entry at its top; inside a mixed directory, the directory is listed with its own owner and each child that differs follows it.
5. Output format: one `OWN\t<path>\t<uid>:<gid>` per entry, numeric ids, in that order.
6. Write to `<out>/chown-entries.txt`.

*(Changed 2026-09-27: the bash version rolled up a directory when its direct children agreed, split fields on whitespace, and read owner names as uids; directories and spaced paths were skipped and files in mixed directories were lost. KI-4.)*
9. Report the count of rolled-up entries.

**Why mode is NOT included in the rollup:** `PkgCreator` applies one octal mode to every child, files and directories alike. A rolled-up mode of `0755` makes every file executable; of `0644` makes every subdirectory untraversable. Mode rollup is only safe on a genuinely uniform subtree. The BOM-based chown rollup therefore outputs ownership only — mode is a separate concern handled by the recipe author reviewing the output.

**Acceptance Criteria:**

- AC-10.1: [TESTABLE] Rolled-up entries are written to `chown-entries.txt` when `CHOWN_NEEDED=true`.
- AC-10.2: [TESTABLE] Running as root produces NO `chown-entries.txt`.
- AC-10.3: [TESTABLE] Each entry has format `OWN\t<path>\t<uid>:<gid>`, numeric. **Enforced via:** `tests/pkg_reverse_spec.sh` "AC-10.3"; `test_pkg.py` `test_reverse_writes_numeric_bom_and_rollup`.
- AC-10.4: [TESTABLE] Inside a directory with mixed ownership, the directory and each child that differs are listed, parent first. **Enforced via:** `test_pkg.py` `RollupTest`.

---

## 11. Blueprint Output

### FR-11 — Write blueprint.conf

[STRUCTURAL]

Write a `blueprint.conf` file to `<out>/` with all accumulated metadata. The format is `key=value` lines, with comments. The file is designed to be human-readable and human-edit-able before being fed to `blueprint-to-recipe.sh`.

**Required fields:**

| Key | Source | Example |
|-----|--------|---------|
| `app_name` | `--name` or derived | `MyApp` |
| `source_pkg` | Absolute path to input | `/path/to/MyApp-1.0.pkg` |
| `source_pkg_basename` | `basename` of input | `MyApp-1.0.pkg` |
| `pkg_kind` | FR-3 classification | `component` or `distribution` |
| `component_count` | FR-3 count | `1` |
| `pkg_id` | FR-5 identifier | `com.example.app` |
| `version` | FR-5 version | `1.0.0` |
| `install_location` | FR-5 install-location | `/` or `/Applications` |
| `signature_status` | FR-6 status | `signed` or `unsigned` |
| `signature_authority` | FR-6 authority | `Developer ID Installer: Vendor (TEAMID)` |
| `payload_files` | FR-7 file count | `142` |
| `payload_dirs` | FR-7 directory count | `23` |
| `payload_size` | FR-7 human-readable size | `12M` |
| `scripts` | FR-8 script list (space-separated) | `preinstall postinstall` or empty |
| `ownership_preserved` | FR-9 ownership status | `true` or `false` |
| `chown_block_needed` | FR-9 chown flag | `true` or `false` |

**Header comment:** The file begins with a comment block:

```
# blueprint.conf — generated by pkg-reverse.sh on <date>
#
# Input to blueprint-to-recipe.sh. Edit anything that is wrong BEFORE generating
# the recipe — this file is meant to be reviewed, not trusted blindly.
```

**Post-blueprint cleanup:** After writing `blueprint.conf`, remove the expanded directory (`rm -rf "${EXPANDED}"`).

**Acceptance Criteria:**

- AC-11.1: [TESTABLE] `blueprint.conf` exists and contains all required fields.
- AC-11.2: [TESTABLE] The expanded directory is removed after `blueprint.conf` is written.
- AC-11.3: [TESTABLE] The `blueprint.conf` header comment includes the generation date in UTC.

---

## 12. Output Summary

### FR-12 — Print Final Summary

[STRUCTURAL]

After successful completion, print a summary of the output tree:

```
=== Done ===
  <out>/
    payload/         <N> files, <size>
    scripts/         <list>
    blueprint.conf
    bom.txt
    chown-entries.txt
```

The `chown-entries.txt` line only appears when it was produced. The final line shows the next command the user should run:

```
  Review blueprint.conf, then:
    bin/blueprint-to-recipe.sh --blueprint <out>/blueprint.conf --out <recipe-dir>
```

**Acceptance Criteria:**

- AC-12.1: [TESTABLE] Final summary lists all created directories and files.
- AC-12.2: [TESTABLE] `chown-entries.txt` is only listed when created.
- AC-12.3: [TESTABLE] The `blueprint-to-recipe.sh` invocation line is printed with the correct path.

---

## 13. Exit Codes

### FR-13 — Exit Code Contract

[STRUCTURAL]

| Code | Meaning |
|------|---------|
| 0 | Reverse-engineering completed successfully |
| 2 | Usage error (bad arguments, missing file, no sudo, expansion failure, unrecognised format) |
| 3 | Package structure error (multi-component distribution, unsupported format left for inspection) |

**Acceptance Criteria:**

- AC-13.1: [TESTABLE] A successful run exits 0.
- AC-13.2: [TESTABLE] Missing `--dest` exits 2.
- AC-13.3: [TESTABLE] Missing positional argument exits 2.
- AC-13.4: [TESTABLE] Non-root without `--allow-unprivileged` exits 2.
- AC-13.5: [TESTABLE] Multi-component distribution exits 3.

---

## 14. Edge Cases

### FR-14 — Handle Boundary Conditions

[TESTABLE]

| Case | Expected Behavior |
|------|------------------|
| Output directory already exists | Exit 2 with message naming the conflict and `--name` as remedy |
| Input file not found | Exit 2 |
| Input file is a directory (bundle-style pkg) | `pkgutil --expand-full` fails; exit 2 |
| Package with no payload (payloadless) | `pkgutil --expand-full` succeeds but no Payload/ dir — error caught at payload extraction |
| Package with scripts but no payload | Not physically possible in a valid flat pkg; handled by individual component checks |
| Package with BOM but all files owned by uid 0 anyway | "BOM records all files as uid 0 anyway" note |
| Package with non-ASCII app name from `--name` | Sanitised to `[A-Za-z0-9-]` — verify no truncation of multi-byte characters |
| Symlinks in payload | `ditto` preserves them; bom.txt carries each target in its sixth field (`lsbom -p mugsfl`) |
| Empty output directory path (e.g., `--dest ""`) | Treated as missing — exit 2 |

**Acceptance Criteria:**

- AC-14.1: [TESTABLE] Existing output directory exits 2.
- AC-14.2: [TESTABLE] Non-existent input file exits 2.
- AC-14.3: [TESTABLE] Package with no Bom produces "no Bom file" warning.
- AC-14.4: [TESTABLE] Package with all-root-owner BOM produces the note.

---

## 15. bluepring.conf — Reference Specification

### FR-15 — blueprint.conf Format Contract

[STRUCTURAL]

`blueprint.conf` is a flat key-value file consumed by `blueprint-to-recipe.sh`. This section documents the exact contract.

`blueprint-to-recipe.sh` writes three files into the recipe folder: `<App>.download.recipe.yaml`, `<App>.pkg.recipe.yaml` and `README.md`. The version is pinned in the **download** recipe's `Input` (FR-15 `version`), where lint rule VER-001 looks for it; the pkg recipe inherits it. Both recipes get a `Comment:` naming the Pattern 6 letter from the blueprint: 6d when `payload_files` is 0, 6b when `scripts` is set, otherwise 6a. The output lints clean (enforced by `tests/blueprint_to_recipe_spec.sh`). It writes no `.overrides` or `.autopkg_config`: `.overrides` is optional and org-defined, and upstream has no pipeline-metadata file (Standards §3.4–3.5).

**Format rules:**
- One `key=value` per line.
- No quoting around values — values are literal strings.
- Lines starting with `#` are comments.
- Keys are lowercase with underscores.
- Values do not contain newlines.

**Involved fields and their semantics for `blueprint-to-recipe.sh`:**

| Field | Semantics | Consumed by |
|-------|-----------|-------------|
| `app_name` | The sanitised application name → `NAME` in recipe Input | blueprint-to-recipe.sh |
| `source_pkg` | Absolute path to the source package (informational only) | Human reviewer |
| `source_pkg_basename` | The original filename (informational only) | Human reviewer |
| `pkg_kind` | `component` or `distribution` — affects recipe structure | blueprint-to-recipe.sh |
| `component_count` | Number of components — >1 means "refused, not generated" | Human reviewer |
| `pkg_id` | The original package identifier → `PKG_ID` in recipe Input | blueprint-to-recipe.sh |
| `version` | The original version → `version` in the download recipe's Input | blueprint-to-recipe.sh |
| `install_location` | Decorates the generated recipe header as a note | blueprint-to-recipe.sh |
| `signature_status` | Determines whether `NO_CODE_SIGNATURE_REQUIRED` is set | blueprint-to-recipe.sh |
| `signature_authority` | Documented for historical traceability | blueprint-to-recipe.sh |
| `payload_files` | Informational count | Human reviewer |
| `payload_dirs` | Informational count | Human reviewer |
| `payload_size` | Informational | Human reviewer |
| `scripts` | Space-separated list of script names → adds `Copier` step for scripts and `scripts:` entry in `PkgCreator` | blueprint-to-recipe.sh |
| `ownership_preserved` | If `true` → skip `chown` block. If `false` → include `chown` block | blueprint-to-recipe.sh |
| `chown_block_needed` | If `true` → include `chown` block in pkg recipe | blueprint-to-recipe.sh |

**Acceptance Criteria:**

- AC-15.1: [TESTABLE] `blueprint.conf` is parsable by a `while IFS= read -r line` loop splitting on the first `=` character.
- AC-15.2: [TESTABLE] Every field that `blueprint-to-recipe.sh` needs is present.
- AC-15.3: [TESTABLE] No extra fields beyond those documented above.

---

## 16. Security Considerations

### FR-16 — Safe Operation

[ADVISORY]

| Concern | Mitigation |
|---------|------------|
| Symlink traversal in payload | `ditto` follows symlinks by default — the payload tree reflects what `PkgCreator` will see. Callers should review any symlinks in `bom.txt` for absolute paths pointing outside the intended tree. |
| Command injection via filename | The tool reads input via `--name` and the filename — both are sanitised. The `.pkg` path is resolved to absolute before use. |
| Temporary file cleanup | See §4 of the constitution — the expanded tree is always removed on success, and left for inspection on error only when that is explicitly useful. |
| Sensitive content in output | The blueprint contains metadata extracted from the package. If the package identifier, version, or file listing is sensitive, the output inherits that sensitivity. |

**Acceptance Criteria:**

- AC-16.1: [ADVISORY] Caller reviews symlinks in `bom.txt` before shipping a recipe.
- AC-16.2: [TESTABLE] Filenames containing spaces, shell metacharacters, or non-ASCII characters are handled without injection.

---

## 17. Version History

| Version | Date | Change |
|---------|------|--------|
| 1.1 | 2026-09-27 | .overrides optional; .autopkg_config removed from upstream. FR-15 states what `blueprint-to-recipe.sh` writes (recipe pair and README only). |
| 1.2 | 2026-09-27 | FR-15: version pinned in the download recipe; Pattern 6 letter in each `Comment:`; output lints clean. |
| 1.3 | 2026-09-27 | Ported to Python (`recipekit.pkg_reverse`), same command, flags, exit codes and output. KI-4 fixed: `bom.txt` is `lsbom -p mugsfl` (numeric, tab-separated); FR-10 rollup is parent-first and complete; AC-10.3/10.4 enforced. |
| 1.0 | 2026-09-08 | Initial release. 16 feature requirements reverse-engineered from the existing `bin/pkg-reverse.sh` implementation, Pattern 6 templates, and `reference/methodology.md` items #5 (signature check), #11 (Copier overwrite), #12 (version Input declaration). |

---

## Appendix A — Audit Discrepancies (Resolved)

The 4 discrepancies found during the initial line-by-line audit (D-01 through D-04) have been resolved in the corresponding acceptance criteria. No discrepancies remain.

See the resolved AC entries:
- D-01 → [`AC-02.3`](#fr-2--expand-flat-package)
- D-02 → [`AC-04.3`](#fr-4--root-check)
- D-03 → [`AC-08.3`](#fr-8--extract-and-fix-scripts)
- D-04 → [`AC-15.1`](#fr-15--blueprintconf-format-contract)
