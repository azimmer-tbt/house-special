# Sync Script — `bin/sync-vendor-cache.sh`

**Spec ref:** `specs/vendor-cache/00-constitution.md`
**Status:** Draft
**Last updated:** 2026-09-27
**Implementation:** `lib/python/recipekit/vendor_cache.py` (`sync`); `bin/sync-vendor-cache.sh` is the front end. **Tests:** `tests/python/test_vendor_cache.py` `SyncTest`

---

## 1. Purpose

Copy only the files a manifest lists from a durable vendor-cache copy into the
working vendor cache (by default `/tmp/autopkg/vendor_cache`, cleared at
reboot; methodology lesson 24). Written from the existing implementation
(KI-12).

## 2. Interface

```
bin/sync-vendor-cache.sh [--dry-run] <index> <from_dir> <to_dir>
```

| Argument | Description |
|---|---|
| `index` | YAML file with a `files:` list of paths relative to the vendor-cache root (`customer/acme/output/files_to_copy.yaml`; schema in `docs/FORMATS.md`) |
| `from_dir` | Durable source vendor-cache root |
| `to_dir` | Target vendor-cache root; created if missing |
| `--dry-run` | Report what would be copied; create and copy nothing |

## 3. Behaviour

For each listed path, in order:

1. An entry that is absolute, empty, or contains a `..` component is refused
   (`ERROR <path>  (outside the vendor cache; not copied)`); it counts as an error.
2. A missing source is an error (`ERROR: Source not found: <path>`).
3. A file whose target exists with the same size and a modification time at
   least as new is skipped (`SKIP  <path>  (target is same size and newer or equal)`).
4. Otherwise a file is copied with its timestamps (`COPY  <path>`), so the next
   run skips it; a directory is copied recursively, replacing the target folder
   (`COPY  <path>  (directory)`). Symlinks inside a directory are copied as links.
5. Parent folders are created as needed.

Then a summary: `=== sync complete ===`, `Copied`, `Skipped (up-to-date)`,
`Errors`. With `--dry-run` the header adds `(dry run: nothing copied)` and each
`COPY` line ends `(dry run)`.

## 4. Exit Codes

| Code | Meaning |
|---|---|
| 0 | Every entry copied or skipped |
| 1 | One or more entries failed (missing source, refused entry, copy error) |
| 2 | Usage error: wrong arguments, index or source folder missing, index unreadable or empty, target folder can't be created |

## 5. Acceptance Criteria

- AC-01: [TESTABLE] Copies keep timestamps, so a second run skips unchanged files.
- AC-02: [TESTABLE] Entries outside the cache roots are refused and nothing is written outside `to_dir`.
- AC-03: [TESTABLE] `--dry-run` writes nothing.
- AC-04: [TESTABLE] Usage errors exit 2; entry failures exit 1.

## 6. Version History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-27 | Initial spec (KI-12), written with the Python port: timestamps kept (the bash `cp` reset them), unsafe entries refused, `--dry-run`; no `yq` (KI-21). |
