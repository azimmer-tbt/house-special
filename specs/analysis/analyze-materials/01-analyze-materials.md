# analyze-materials.sh — Source Matcher

**Status:** Draft
**Date:** 2026-09-08
**Requires:** `specs/analysis/00-constitution.md`, `specs/analysis/analyze-package/01-analyze-package.md`
**Implementation:** `lib/python/recipekit/analyze_materials.py`; `bin/analyze-materials.sh` is the front end. **Tests:** `tests/python/test_analyze_materials.py`, `tests/analyze_materials_spec.sh`, `tests/customers_shell_spec.sh`.

---

## Purpose

Given a source directory (e.g., `_Vendor/` folders, a vendor share, or a dump of upstream packages), recursively scan for distributable files and determine which ones are candidate sources for target recipes. This is the **deterministic** part of Phase 1 Research step 1c — it produces structured data that an LLM or human interprets to make the final call.

**What this tool is NOT:** a general-purpose analyzer that reads messy human notes or interprets PDFs. That is LLM territory. This tool does what's deterministic — compare files, match names, find candidates.

### Classification Key

- **[TESTABLE]** — Observable and automatable. Enforcement mechanism stated.
- **[STRUCTURAL]** — Enforced by schema, layout, or data model constraint.
- **[ADVISORY]** — Review judgment.

---

## 1. Command-Line Interface

### FR-1 — Argument Parsing

[STRUCTURAL]

| Flag | Argument | Required | Description |
|------|----------|----------|-------------|
| `path` (positional) | Directory path | Yes | Source directory to scan |
| `--output` | `text` or `json` | No | Output format; default `text` |
| `--targets` | File path | No | Path to `end_result.yaml` — enables source matching against target recipes |
| `--clues` | File path | No | Path to `clues.yaml` for classification during scan |
| `--customer` | String | No | Customer name, looked up in `config/customers.yaml` (the folder may be inside or outside the kit) — reads `clues.yaml` and `end_result.yaml` from that folder unless `--clues` / `--targets` is given. With no registry, `customer/<name>/` in the kit. Unknown name: exit 2, listing the registered names |
| `--depth` | Integer ≥ 1 | No | Max depth of files to report, as `find -maxdepth` counts it (1 = the top level); default unlimited. Anything else exits 2 |
| `-h` / `--help` | — | No | Print usage and exit 0 |

**Acceptance Criteria:**

- AC-01.1: [TESTABLE] Running with only a valid directory path scans and reports all distributable files.
- AC-01.2: [TESTABLE] Running with `--output json` produces valid JSON.
- AC-01.3: [TESTABLE] Running with `--targets end_result.yaml` matches found files against target recipes.
- AC-01.4: [TESTABLE] Running with `--depth 1` only scans the top-level directory.
- AC-01.5: [TESTABLE] A non-existent directory, a bad `--depth`, a missing or invalid `--targets` file (not YAML, or no `recipes:` list), or an unknown customer exits 2. **Enforced via:** `test_analyze_materials.py` `test_usage_errors_exit_2`.
- AC-01.6: [TESTABLE] `--customer <name>` for a registered customer outside the kit matches against that folder's `end_result.yaml` (`tests/customers_shell_spec.sh`).

---

## 2. File Discovery

### FR-2 — Scan for Distributable Files

[TESTABLE]

Recursively scan the source directory, following symlinks (vendor shares are
often assembled from them) without looping, for files with these extensions
(case-insensitive, longest suffix first):

| Extension | Type |
|-----------|------|
| `.pkg` | Flat macOS installer package |
| `.dmg` | Disk image |
| `.zip` | Zip archive |
| `.tar.gz`, `.tgz` | Gzip-compressed tar archive |
| `.tar.bz2`, `.tbz2` | Bzip2-compressed tar archive |
| `.tar` | Uncompressed tar archive |

For each file found, record:

| Field | Source |
|-------|--------|
| Path | Full absolute path |
| Size | Size of the file, through any symlink (the bash version reported the link's own size) |
| Basename | `basename` |
| Extension | Extension from filename |
| Last modified | Modification time of the file, through any symlink |
| Vendor hint | Directory name two levels above (e.g., `KiwiSoft/` from `.../KiwiSoft/Kiwi-Capture/pkg.dmg`), only when that directory is inside the source directory; otherwise empty |

**Acceptance Criteria:**

- AC-02.1: [TESTABLE] Scans recursively and finds all distributable files.
- AC-02.2: [TESTABLE] Ignores non-distributable files (.txt, .md, .rtf, .pdf, .html, etc.).
- AC-02.3: [TESTABLE] Empty directory reports 0 files found.
- AC-02.4: [TESTABLE] Files with no recognized extension are excluded.
- AC-02.5: [TESTABLE] A symlinked file reports the target's size; a symlink loop is scanned once. **Enforced via:** `test_symlinks_are_followed_with_real_sizes_and_no_loops`.

---

## 3. Source Matching

### FR-3 — Match Sources to Target Recipes

[TESTABLE]

When `--targets end_result.yaml` is supplied, match discovered files against target recipes using these heuristics:

| Match Signal | Weight | Detection |
|--------------|--------|-----------|
| App name match (`app_name_match`) | +2 | The basename contains the target's `app_name`, both lowercased with everything but letters and digits removed (`Orchard-Analytics` ~ `Orchard Analytics 7.2.dmg`) |
| Vendor match (`vendor_match`) | +2 | The vendor hint equals the target's `vendor`, compared the same way |
| Version in filename (`version_in_filename`) | +1 | A version-like pattern (`\d+\.\d+\.\d+` or `\d+\.\d+`), counted only alongside a name or vendor match |

A file with any points is a candidate: 4 or more is **strong**, 2–3 **moderate**,
1 **weak**; 2 or more also adds `archivable_file`. Size and file-type
correlation are not implemented: `end_result.yaml` records neither.

Match results are **candidates** — the tool reports which source files are most likely to be the origin for each target recipe. It does not make a final determination.

### JSON Output Structure (with --targets)

```json
{
  "source_dir": "/path/to/_Vendor",
  "files_found": 45,
  "unmatched": 5,
  "unmatched_files": ["/path/to/_Vendor/Orphan/file.zip", "…"],
  "target_matches": [
    {
      "target_app": "Kiwi-Capture",
      "target_vendor": "KiwiSoft",
      "candidates": [
        {
          "path": "/path/to/_Vendor/KiwiSoft/kiwisoft_kiwi_capture_2026.1.0.dmg",
          "size": 524288000,
          "match_signals": ["app_name_match", "vendor_match", "version_in_filename"],
          "match_strength": "strong"
        },
        {
          "path": "/path/to/_Vendor/Archives/kiwi-capture-old.dmg",
          "size": 503316480,
          "match_signals": ["app_name_match"],
          "match_strength": "weak"
        }
      ]
    }
  ],
  "summary": {
    "total_targets": 10,
    "targets_with_candidates": 8,
    "targets_without_candidates": 2
  }
}
```

### Acceptance Criteria:

- AC-03.1: [TESTABLE] A file with the exact app name in the correct vendor directory matches with "strong" strength.
- AC-03.2: [TESTABLE] A target with no matching source file reports empty candidates.
- AC-03.3: [TESTABLE] Unmatched source files (files that don't correspond to any target) are listed separately.
- AC-03.4: [TESTABLE] Multiple candidates for one target are ordered by match strength descending.

---

## 4. Classification

### FR-4 — Classify Each Found Package

[TESTABLE]

When clues are supplied (`--clues`, or the customer's `clues.yaml`), each `.pkg`
discovered is classified in-process exactly as `analyze-package.sh` would
(`recipekit.analyze_package`), and the file entry gains `"classifiable": true` and
`"classification": {"origin", "confidence", "pattern"}`, or `{"error": …}` when the
file can't be expanded. The text listing appends `[origin, confidence, pattern N]`.
Without clues, `classifiable` is false and nothing is classified.

**Acceptance Criteria:**

- AC-04.1: [TESTABLE] With clues, a `.pkg` is classified; a broken one reports an error instead; without clues nothing is. **Enforced via:** `test_fr_4_packages_are_classified_with_clues`.

This enables a single scan to both classify and match — the LLM or human has a complete picture of what each source file is.

---

## 5. Output Structure

### FR-5 — Text Output Format

Progress goes to stderr (`=== Scanning <dir> ===`, depth, files found, `=== Done ===`),
so `--output json` is pure JSON on stdout. Stdout in text mode:

```
=== Files found ===
  Total: 3
  kiwisoft_kiwi_capture_2026.1.0.dmg  (500 MB, vendor: KiwiSoft)
  Acme_Helper.pkg  (2 MB, vendor: Acme)  [custom-build, high, pattern 6]

=== Target matches ===
  KiwiSoft/Kiwi-Capture (2 candidates)
    [STRONG  ] kiwisoft_kiwi_capture_2026.1.0.dmg
    [WEAK    ] kiwi-capture-old.dmg

=== Unmatched source files ===
  /path/to/_Vendor/Orphan/file.zip
```

The last two sections, and the summary below, appear only with targets.

**Acceptance Criteria:**

- AC-05.1: [TESTABLE] Unmatched files are listed by path (AC-03.3). **Enforced via:** `test_text_lists_unmatched_files`.

### FR-6 — Summary Output

[STRUCTURAL]

At the end of text mode, print a summary table:

```
=== Summary ===
  Targets with candidates:    8 of 10
  Targets without candidates: 2
  Unmatched source files:     5
```

---

## 6. Exit Codes

### FR-7 — Exit Code Contract

[STRUCTURAL]

| Code | Meaning |
|------|---------|
| 0 | Scan completed (with or without matches) |
| 2 | Usage error, missing file, invalid config (the bash version hid errors from its Python step and still exited 0) |

---

## 7. Artifacts

| File | Purpose |
|------|---------|
| `specs/analysis/analyze-materials/artifacts/example-source-dir.txt` | Sample directory listing (mock vendor share) |
| `specs/analysis/analyze-materials/artifacts/example-end-result.yaml` | Sample end_result.yaml for testing |
| `specs/analysis/analyze-materials/artifacts/example-materials-output.txt` | Sample text output |
| `specs/analysis/analyze-materials/artifacts/example-materials-output.json` | Sample JSON output |

---

## 8. Version History

| Version | Date | Change |
|---------|------|--------|
| 1.2 | 2026-09-27 | Ported to Python (`recipekit.analyze_materials`), checked side by side with the bash version. FR-4 implemented (in-process classification); unmatched files listed (AC-03.3); matching rules written as implemented (no size/type signals); symlinked files report real sizes; vendor hint only from inside the source; `--depth` validated; errors exit 2. |
| 1.1 | 2026-09-27 | `--customer` resolves through the customer registry; AC-01.6. |
| 1.0 | 2026-09-08 | Initial release. Scoped as deterministic source matcher, not general analyzer. |
