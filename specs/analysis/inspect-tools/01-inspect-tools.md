# Inspection Micro-Tools — Deterministic Utilities

**Status:** Draft
**Date:** 2026-09-08
**Requires:** `specs/analysis/00-constitution.md`
**Implementation:** Tools 1–3: `lib/python/recipekit/inspect_tools.py` behind the `bin/inspect-*.sh` front ends (tests: `tests/python/test_inspect_tools.py`). Tool 4, `capture-perms.sh`, stays bash.

---

## Purpose

Define the four deterministic micro-tools that support Phase 1 material analysis. Each does one thing well, outputs structured text and JSON, and is composable — by both humans and AI agents.

### Classification Key

- **[TESTABLE]** — Observable and automatable. Enforcement mechanism stated.
- **[STRUCTURAL]** — Enforced by schema, layout, or data model constraint.
- **[ADVISORY]** — Review judgment.

---

## Tool 1: `bin/inspect-dmg.sh` — DMG Tree + Version Extractor

### Purpose

Mount a `.dmg` file (read-only), capture its tree structure, find `.app` bundles, extract version and identifier from each app's Info.plist, then unmount.

### CLI

| Flag | Argument | Required | Description |
|------|----------|----------|-------------|
| `path` (positional) | File path | Yes | Path to the `.dmg` file |
| `--output` | `text` or `json` | No | Output format; default `text` |
| `--keep-mounted` | — | No | Leave the DMG mounted (for manual inspection) |
| `-h` / `--help` | — | No | Print usage and exit 0 |

### Behavior

1. Mount the DMG read-only at a temporary mount point via `hdiutil attach -nobrowse -readonly -mountrandom /tmp -plist`. A DMG that asks to accept a license agreement is not mounted (the tool never answers the prompt): it exits 2 saying so.
2. Walk the mounted volume, not following symlinks (the usual `Applications` link): top-level items (without `.DS_Store`) and a count of every item below the root
3. Find the outermost `.app` bundles, up to 10 levels deep; helper apps inside an app are counted but not listed
4. For each `.app`, read its Info.plist (plistlib) for the identifier, version and build, and `lipo -archs` for its architectures
5. Unmount via `hdiutil detach` (unless `--keep-mounted`)
6. Output results

### JSON Output Structure

```json
{
  "file": "/path/to/package.dmg",
  "size_bytes": 104857600,
  "mount_point": "/private/tmp/dmg-XXXXX",
  "apps": [
    {
      "path": "/Volumes/Example/Example.app",
      "name": "Example",
      "identifier": "com.example.app",
      "version": "2.1.0",
      "build": "2100",
      "architectures": ["arm64", "x86_64"]
    }
  ],
  "top_level_items": ["Applications", "Example.app", "README.txt"],
  "total_items": 15,
  "kept_mounted": false
}
```

### Acceptance Criteria

- AC-T1.1: [TESTABLE] Mounts, analyzes, and unmounts a valid `.dmg` — no orphaned mounts.
- AC-T1.2: [TESTABLE] Extracts version from `.app` bundles correctly.
- AC-T1.3: [TESTABLE] `--keep-mounted` leaves the DMG mounted and prints the mount point.
- AC-T1.4: [TESTABLE] A DMG with no `.app` bundles reports empty apps list.
- AC-T1.5: [TESTABLE] A non-DMG file fails with exit 2 and a clear message.
- AC-T1.6: [TESTABLE] Apps with spaces in their names are reported whole, and a helper app inside an app is not listed.

---

## Tool 2: `bin/inspect-app.sh` — .app Metadata Extractor

### Purpose

Given a path to a `.app` bundle (or any bundle with Info.plist), extract its metadata.

### CLI

| Flag | Argument | Required | Description |
|------|----------|----------|-------------|
| `path` (positional) | Directory path | Yes | Path to the `.app` bundle |
| `--output` | `text` or `json` | No | Output format; default `text` |
| `-h` / `--help` | — | No | Print usage and exit 0 |

### Extracted Fields

| Field | plist Key | Notes |
|-------|-----------|-------|
| Bundle name | `CFBundleName` | |
| Display name | `CFBundleDisplayName` | Optional |
| Identifier | `CFBundleIdentifier` | |
| Version | `CFBundleShortVersionString` | |
| Build | `CFBundleVersion` | |
| Minimum OS | `LSMinimumSystemVersion` | Optional |
| Architecture | `CFBundleExecutable` → `lipo -archs` (`file` as a fallback) | Binary architectures |

Info.plist is read with plistlib (XML or binary); only top-level keys count. A non-string value is shown as text.

### JSON Output Structure

```json
{
  "path": "/path/to/Example.app",
  "name": "Example",
  "display_name": "Example Application",
  "identifier": "com.example.app",
  "version": "2.1.0",
  "build": "2100",
  "minimum_os": "10.15",
  "architectures": ["x86_64", "arm64"],
  "has_code_signature": true
}
```

### Acceptance Criteria

- AC-T2.1: [TESTABLE] Extracts all fields from a valid `.app`.
- AC-T2.2: [TESTABLE] Reports missing optional fields gracefully (empty string).
- AC-T2.3: [TESTABLE] Non-bundle path fails with exit 2.
- AC-T2.4: [TESTABLE] Detects whether the bundle has a `_CodeSignature` directory.

---

## Tool 3: `bin/inspect-archive.sh` — Archive Content Lister

### Purpose

List the contents of a compressed archive (.zip, .tar.gz, .tgz, .tar.bz2, .tbz2, .tar) without extracting it, with Python's zipfile and tarfile. For `.zip`, each entry also has its compressed size.

### CLI

| Flag | Argument | Required | Description |
|------|----------|----------|-------------|
| `path` (positional) | File path | Yes | Path to the archive file |
| `--output` | `text` or `json` | No | Output format; default `text` |
| `--max-entries` | Integer | No | Stop listing after this many entries; default 200 |
| `-h` / `--help` | — | No | Print usage and exit 0 |

### Detection Logic

| Archive Type | Detection | Command |
|--------------|-----------|---------|
| `.zip` | Extension, or zip content | `zipfile` |
| `.tar.gz` / `.tgz` | Extension, or gzip'd tar content | `tarfile` |
| `.tar.bz2` / `.tbz2` | Extension, or bzip2'd tar content | `tarfile` |
| `.tar` | Extension, or tar content | `tarfile` |

Anything else exits 2 with `file -b`'s description in the message. Directory entries end in `/`.

### JSON Output Structure

```json
{
  "file": "/path/to/archive.zip",
  "size_bytes": 52428800,
  "archive_type": "zip",
  "entry_count": 145,
  "entries": [
    {"path": "Example.app/", "size": 0, "compressed_size": 0},
    {"path": "Example.app/Contents/Info.plist", "size": 1245, "compressed_size": 512}
  ],
  "top_level_items": ["Example.app/", "README.txt"],
  "truncated": false
}
```

`entry_count` is the archive's full count. If it exceeds `--max-entries`, `truncated` is `true` and `entries` holds the first `--max-entries`. `top_level_items` are the distinct first path components, from every entry.

### Acceptance Criteria

- AC-T3.1: [TESTABLE] Lists contents of a `.zip` archive correctly.
- AC-T3.2: [TESTABLE] Lists contents of a `.tar.gz` archive correctly.
- AC-T3.3: [TESTABLE] Lists contents of a `.tar` archive correctly.
- AC-T3.4: [TESTABLE] Unknown format fails with exit 2 and detected type in message.
- AC-T3.5: [TESTABLE] `--max-entries 10` limits listing to 10 entries and sets `truncated: true`.
- AC-T3.6: [TESTABLE] Names with spaces, quotes or `|` are listed exactly; a corrupt archive exits 2.

---

## Tool 4: `bin/capture-perms.sh` — Directory Permission Snapshot

### Purpose

Given a directory tree, capture ownership and permissions for every file, similar to how `lsbom` reports BOM contents but for arbitrary trees. Useful for comparing payload structures or documenting what an extracted package looks like.

### CLI

| Flag | Argument | Required | Description |
|------|----------|----------|-------------|
| `path` (positional) | Directory path | Yes | Path to the directory tree to snapshot |
| `--output` | `text` or `json` | No | Output format; default `text` |
| `--relative` | — | No | Output paths relative to the input directory (not absolute) |
| `-h` / `--help` | — | No | Print usage and exit 0 |

### Output Fields Per Entry

| Field | Source |
|-------|--------|
| Path | From find |
| Type | file, directory, or symlink |
| Octal mode | `stat -f %Lp` |
| Owner (UID) | `stat -f %u` |
| Group (GID) | `stat -f %g` |
| Owner (name) | `stat -f %Su` |
| Group (name) | `stat -f %Sg` |
| Size | `stat -f %z` |
| Symlink target | `readlink` (if symlink) |

### JSON Output Structure

```json
{
  "root": "/path/to/tree",
  "entries": [
    {
      "path": "Library/LaunchDaemons/com.example.plist",
      "type": "file",
      "mode": "0644",
      "uid": 0,
      "gid": 0,
      "owner": "root",
      "group": "wheel",
      "size": 342,
      "symlink_target": null
    }
  ],
  "total_entries": 156,
  "files": 134,
  "directories": 21,
  "symlinks": 1
}
```

### Acceptance Criteria

- AC-T4.1: [TESTABLE] Captures permissions of a known directory correctly.
- AC-T4.2: [TESTABLE] `--relative` outputs paths relative to the input directory.
- AC-T4.3: [TESTABLE] Symlinks are identified with their target.
- AC-T4.4: [TESTABLE] A non-existent directory fails with exit 2.
- AC-T4.5: [TESTABLE] Empty directory produces an empty entries list.

---

## 7. Common Contracts

All four micro-tools share these contracts:

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Operation completed successfully |
| 2 | Usage error, missing file, invalid input |

### Cleanup Contract

Every tool cleans up its temporary resources on exit:
- DMG mounts are detached
- Temporary extraction directories are removed

Unless the user explicitly opts out (`--keep-mounted`, `--work-dir`).

### Help Output

`-h`/`--help` prints the usage block from the script header (same pattern as existing tools: `sed -n '3,NNp' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'`).

---

## 8. Artifacts

| File | Purpose |
|------|---------|
| `specs/analysis/inspect-tools/artifacts/example-dmg-output.txt` | Sample inspect-dmg.sh text output |
| `specs/analysis/inspect-tools/artifacts/example-app-output.txt` | Sample inspect-app.sh text output |
| `specs/analysis/inspect-tools/artifacts/example-archive-output.txt` | Sample inspect-archive.sh text output |
| `specs/analysis/inspect-tools/artifacts/example-perms-output.txt` | Sample capture-perms.sh text output |

---

## 9. Version History

| Version | Date | Change |
|---------|------|--------|
| 1.1 | 2026-09-27 | Tools 1–3 ported to Python and checked against the bash versions on real apps, DMGs and archives. Fixed: inspect-app JSON crashed on signed apps; inspect-dmg split app names at spaces, broke its JSON into one entry per field, and failed silently on some DMGs; inspect-archive's JSON crashed, names with spaces broke the zip listing, and "truncated" was always shown. Added `mount_point`, `build`, `kept_mounted`, `compressed_size`. The unused DMG/plist helpers in `lib/toolkit-common.sh` are removed. |
| 1.0 | 2026-09-08 | Initial release. Four micro-tools derived from the Master Enhancement Plan discussion. |
