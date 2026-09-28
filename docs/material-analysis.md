# Material Analysis

How to scan a directory of vendor materials (upstream packages, _Vendor directories, vendor shares) and identify candidate source files for your target recipes.

## Quick Reference

### Key Tools

| Tool | What It Does | Command |
|------|-------------|---------|
| `inspect-dmg.sh` | Mounts a .dmg, lists tree, extracts app versions | `bin/inspect-dmg.sh file.dmg [--output json]` |
| `inspect-app.sh` | Extracts metadata from an .app bundle | `bin/inspect-app.sh App.app [--output json]` |
| `inspect-archive.sh` | Lists contents of zip/tar without extraction | `bin/inspect-archive.sh file.zip [--max-entries 50]` |
| `capture-perms.sh` | Snapshot ownership/permissions of a tree | `bin/capture-perms.sh /path [--output json]` |
| `analyze-materials.sh` | Match source files against target recipes | `bin/analyze-materials.sh /source --targets end_result.yaml` |

### Common Flags

| Flag | Applies To | Effect |
|------|-----------|--------|
| `--output json` | All tools | Machine-readable JSON output |
| `--keep-mounted` | `inspect-dmg.sh` | Leave DMG mounted for manual inspection |
| `--relative` | `capture-perms.sh` | Output paths relative to target directory |
| `--max-entries N` | `inspect-archive.sh` | Limit listing to N entries |

---

## Walkthrough

### Using the micro-tools

Each tool does one deterministic thing well. They're designed to be composable — by you at the terminal, or by an LLM building analysis pipelines.

#### Inspect a disk image

```bash
bin/inspect-dmg.sh vendor_cache/KiwiSoft/kiwisoft_kiwi_capture_2026.1.dmg
```

Output: mount point, app bundles found (with versions and architectures), top-level tree structure. The DMG is unmounted automatically unless you pass `--keep-mounted`.

#### Inspect an .app bundle

```bash
bin/inspect-app.sh /Volumes/Example/Example.app --output json
```

Output: name, identifier, version, build, minimum OS, architectures (x86_64/arm64), whether it has a code signature directory.

#### List archive contents

```bash
bin/inspect-archive.sh vendor_cache/SomeApp.zip --max-entries 100
```

Auto-detects format (zip, tar.gz, tar.bz2, tar). Shows top-level contents and entry count. For `.zip`, shows per-file sizes. Use `--output json` for the full structured listing.

#### Capture permission snapshot

```bash
bin/capture-perms.sh payload/ --output json --relative
```

Records every file's mode, owner, group, and (for symlinks) target. Useful for documenting what an extracted package looks like before building a recipe.

### Scanning materials for source matching

When you have a directory full of vendor files and need to find which ones correspond to your target recipes:

```bash
# Must have end_result.yaml first
bin/analyze-materials.sh /path/to/_Vendor --targets customer/acme/end_result.yaml --output json
```

The tool scans for `.pkg`, `.dmg`, `.zip`, `.tar.gz`, `.tar.bz2`, `.tar` files and matches them against target recipes by name, vendor directory, and size correlation. It outputs candidate matches — it's the LLM's job to interpret them.

### Using the outputs in an LLM workflow

The JSON output from all micro-tools is designed to feed directly into an LLM prompt:

```markdown
I have a directory of vendor materials. Here are the contents:
[attach analyze-materials.sh --output json output]

For each target recipe, identify which source file is the origin.
```

The LLM has all the deterministic metadata and can focus on the messy interpretation — reading notes, correlating scattered docs, making judgment calls.

---

## Also See

- [`specs/analysis/inspect-tools/01-inspect-tools.md`](../specs/analysis/inspect-tools/01-inspect-tools.md) — micro-tools feature spec
- [`specs/analysis/analyze-materials/01-analyze-materials.md`](../specs/analysis/analyze-materials/01-analyze-materials.md) — source matcher spec
- [`specs/method/00-methodology.md`](../specs/method/00-methodology.md) — the 8-step per-package workflow
