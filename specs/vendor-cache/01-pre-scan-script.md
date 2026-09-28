# Pre-Scan Script Design — `bin/normalize-vendor-cache.sh`

**Spec ref:** `specs/vendor-cache/00-constitution.md` §2
**Status:** Draft
**Last updated:** 2026-09-27
**Implementation:** `lib/python/recipekit/vendor_cache.py` (`normalize`); `bin/normalize-vendor-cache.sh` is the front end. **Tests:** `tests/python/test_vendor_cache.py`

---

## 1. Overview

A tool that normalizes filenames in the vendor cache before AutoPkg recipes run.
Driven by `vendor-drop-registry.yaml` located in the recipe repo.

## 2. Interface

```
bin/normalize-vendor-cache.sh \
  --repo /path/to/recipe-repo \
  --vendor-cache /tmp/autopkg/vendor_cache [--dry-run] [--relocate-dir <dir>]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--repo` | Yes | — | Path to the recipe repo root (looks for `vendor-drop-registry.yaml` here) |
| `--vendor-cache` | Yes | — | Root path of the vendor cache directory |
| `--dry-run` | No | off | Report every action; rename and move nothing |
| `--relocate-dir` | No | `<vendor-cache>/relocated` | Where stale files are moved, mirroring the cache: `<dir>/<Vendor>/<App>/<name>`; a taken name gets `-2`, `-3`… before its extension |

The config file path is derived as `$REPO/vendor-drop-registry.yaml`.

Exit codes:
- `0` — All entries processed successfully (warnings are OK)
- `1` — Error reading config or accessing vendor cache, bad arguments, a bad registry entry, or a rename/move that failed

## 3. Algorithm

For each entry `Vendor/App: canonical_name` in the registry, in key order:

1. Check the entry: the key must be `Vendor/App` (two non-empty parts, no `..`)
   and the canonical name a plain file name. Otherwise report `ERROR` and exit 1
   at the end.
2. Compute the target directory `VENDOR_CACHE_ROOT/Vendor/App/`. If it is
   missing, report `MISSING` when the vendor folder exists (silence otherwise).
3. List its regular, non-dot files. Subdirectories are skipped; those named in
   `ignored_subdirs` are reported as `IGNORE`.
4. Split the files by **type**: the canonical name's extension (lowercased;
   `.tar.gz` and `.tar.bz2` whole). Other files are reported `KEEP` and never
   touched (KI-7: a text sidecar must not become `payload.zip`). A canonical name
   without an extension makes every file a candidate.
5. Apply rules:

   | Condition | Action |
   |-----------|--------|
   | Canonical file exists, nothing else | `SKIP … Already in place` |
   | Canonical file exists and is the newest non-protected same-type file (it wins ties) | Each other non-protected one is relocated: `PRUNE … Relocated to <path>`; protected ones: `SKIP … Protected — kept` |
   | Canonical file exists but a newer same-type file was dropped beside it (a vendor update) | The old canonical file is relocated (`PRUNE … Superseded by <new>; Relocated to <path>`), the newest is renamed into place (`RENAME … DONE|REPLACED`), other stale versions are relocated |
   | No canonical file; one or more non-protected same-type files | Rename the newest (by mtime, then name) to the canonical name: `RENAME … DONE`; `WARN` on stderr listing any others (a later run prunes them) |
   | No canonical file; only protected or other-type files | `MISSING … No <ext> file to rename in <dir>` |
   | No files at all | `MISSING … No files found in <dir>` |

6. If the renamed file had unsafe characters (regex `[^-._A-Za-z0-9]`), the
   message gains `|UNSAFE_CHARS`.
7. With `--dry-run`, nothing changes: a rename's message is `DRY RUN`, a prune's
   `DRY RUN: would relocate to <path>`.

The relocate folder is `relocated/` at the top of the vendor cache by default, a
mirror of the cache tree. Under `/tmp` it is cleared at reboot, like the cache
itself; pass `--relocate-dir` for a durable place. A registry vendor with the
relocate folder's name (when it sits in the cache root) is refused, exit 1.

## 4. Output Format

Tab-separated, one line per action:

```
ACTION<TAB>VENDOR/APP<TAB>OLD_NAME<TAB>NEW_NAME<TAB>MESSAGE
```

| Field | Description |
|-------|-------------|
| `ACTION` | SKIP, RENAME, PRUNE, KEEP, IGNORE, MISSING on stdout; WARN, ERROR on stderr |
| `VENDOR/APP` | Registry key, e.g. `OrchardLabs/Orchard-Analytics` |
| `OLD_NAME` | Previous filename (empty for SKIP) |
| `NEW_NAME` | Canonical filename after rename |
| `MESSAGE` | Human-readable status or warning |

## 5. Constraints

- AutoPkg's Python with the standard library and PyYAML, behind a bash front
  end (toolkit constitution P-7, P-10). No `yq` (KI-21).
- Never deletes or overwrites; only renames within a Vendor/App folder and moves
  files aside to the relocate folder.

## 6. Error Handling

| Condition | Behavior |
|-----------|----------|
| Config file not found at `$REPO/vendor-drop-registry.yaml` | Exit 1, stderr: `ERROR: Vendor-drop registry not found at: <path>` |
| Vendor cache root not found | Exit 1, stderr: `ERROR: Vendor cache root not found: <path>` |
| Config key has no matching directory | `MISSING` line, continue |
| Registry key or canonical name malformed | `ERROR` line on stderr, continue, exit 1 |
| File rename or move fails | `ERROR` line on stderr, continue, exit 1 |
| YAML parse error, or not a mapping | Exit 1, stderr: `ERROR: Failed to parse config: <path> (…)` |

## 7. Integration

The script is designed to run in a CI/CD pipeline:

```yaml
# GitHub Actions workflow snippet
- name: Normalize vendor cache filenames
  run: |
    bin/normalize-vendor-cache.sh \
      --repo customer/acme/output \
      --vendor-cache /tmp/autopkg/vendor_cache

- name: Test all recipes
  run: |
    # For each recipe...
    autopkg run -v <recipe> --search-dir <dir>
```

## 8. Acceptance Criteria

- AC-01: [TESTABLE] Only same-type files are renamed or pruned; other files stay (KI-7).
- AC-02: [TESTABLE] Protected files are never renamed or moved.
- AC-03: [TESTABLE] Stale files are moved aside to the same Vendor/App path under the relocate folder, never deleted or overwritten.
- AC-04: [TESTABLE] `--dry-run` changes nothing and reports every action.
- AC-05: [TESTABLE] Malformed keys or names, and config errors, exit 1.
- AC-06: [TESTABLE] A newer drop beside the canonical file replaces it; the old one is relocated (the bash version deleted the new drop).

**Enforced via:** `tests/python/test_vendor_cache.py` `NormalizeTest`.

## 9. Version History

| Version | Date | Change |
|---|---|---|
| 1.2 | 2026-09-27 | Stale files go to `relocated/<Vendor>/<App>/` at the top of the vendor cache (`--relocate-dir`), never overwritten; replaces the hidden, timestamped `.quarantine/` and `--quarantine`. |
| 1.1 | 2026-09-27 | Ported to Python; KI-7 fixed (type-matched candidates, protected files never renamed, quarantine, `--dry-run`, `KEEP` lines, key checks); a newer drop replaces the canonical file; no `yq` (KI-21). Checked side by side with the bash version. |
