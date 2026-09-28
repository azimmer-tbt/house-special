# `normalize-vendor-cache.sh` — Vendor Cache Filename Normalizer

## What It Does

`bin/normalize-vendor-cache.sh` reads a YAML registry of known Vendor/App
directories and renames the files inside them to canonical, safe filenames.
It runs **before** any AutoPkg recipe executes, ensuring that
`URLDownloader` with a `file://` URI always finds a file whose name contains
only safe characters (`[A-Za-z0-9._-]`) and matches what the recipe expects.

---

## Why We Made It

AutoPkg recipes for vendor-provided packages (Patterns 2, 4, 5, 6 — any
recipe that uses `URLDownloader` with a `file://` URI) hardcode exact
filenames in their `DOWNLOAD_URL` Input field:

```yaml
DOWNLOAD_URL: "file://%VENDOR_CACHE_ROOT%/OrchardLabs/Orchard-Analytics/Orchard Analytics 3.1 Installer.dmg"
```

This works exactly once — until the next release changes the filename.

### Why URLDownloader?

`URLDownloader` is the right processor because it handles both `file://`
URIs for local files and `https://` URIs for internet-hosted files through
the same interface. It is the "universal download mechanism". Using a
separate processor for each URI scheme would duplicate logic and break
recipe pattern consistency.

### What URLDownloader cannot do

`URLDownloader` delegates to `curl` for the actual transfer. `curl` expects
URI-encoded paths in `file://` URIs. Characters like `@`, spaces, and
parentheses must be percent-encoded (`%40`, `%20`, `%28`/`%29`). When a
vendor drops a file named `AcmeSelfService_v2.3_08_20_2026 1.pkg`, the resulting
`file://` URI breaks because `curl` has no way to tell whether the `@` is a
URI delimiter or part of the path.

### Why explicit renaming is not a solution

Product owners ("Bob drops whatever Adobe gives him") cannot be expected to
manually rename files before placing them in the upload point. The CI/CD
pipeline must handle this automatically. Hardcoding exact names into recipes,
even if the current names are safe, creates a maintenance trap: the recipe
breaks silently the next time the vendor changes anything.

### The alternative considered — glob patterns in recipes

AutoPkg's `DOWNLOAD_URL` does not support glob or wildcard patterns. The
processor constructs an exact `file://` URI from the input string and passes
it directly to `curl`. There is no intermediate "find the file" step.

### Why a pre-scan normalization script is the right solution

1. **Separation of concerns.** The recipe knows what the canonical name
   *should be*. The pre-scan script ensures the file on disk *has* that name.
   Neither needs to know about the other's internals.

2. **Config-driven, not code-driven.** Adding a new vendor-drop app means
   adding one line to `vendor-drop-registry.yaml`. The script itself never
   changes. No shell script expertise required to onboard a new app.

3. **Cache directory is outside the git repo.** `/tmp/autopkg/vendor_cache/`
   is a CI artifact, not tracked content. Renaming files there does not
   pollute git history or trigger unnecessary CI runs. The config file is
   tracked, but it only changes when a genuinely new app is added — not on
   every vendor release.

4. **Idempotent.** Running the script against an already-normalized cache is
   a no-op. Running it again after a vendor updates the file works the same
   way. The script is safe to run on every CI invocation.

5. **Auditable.** The script produces structured output showing exactly what
   it renamed. This feeds into CI logs and can be monitored for unexpected
   changes in vendor filenames.

| Approach | Brittle? | Auto-fixes? | Config-driven? |
|----------|----------|-------------|----------------|
| Exact filename in recipe | Yes | No | N/A |
| Glob/wildcard in recipe | Not supported | N/A | N/A |
| Manual rename by PO | Yes | No | No |
| Pre-scan normalization script | No | Yes | Yes |

*Adapted from `specs/vendor-cache/JUSTIFICATION.md`.*

---

## How It Works

1. The script reads `vendor-drop-registry.yaml` from the recipe repo
   (provided via `--repo`). Each key must be `Vendor/App` and each canonical
   name a plain file name; anything else is an `ERROR` line and exit 1.
2. For each `Vendor/App` key in the registry's `canonical_filenames` map:
   - Resolves the target directory under `VENDOR_CACHE_ROOT`.
   - Lists the non-dotfile files (subfolders in `ignored_subdirs` are
     reported as `IGNORE`).
   - Only files of the canonical name's **type** are versions of it: same
     extension, case-insensitive, with `.tar.gz` and `.tar.bz2` counted whole.
     Any other file is left where it is and reported as `KEEP … Different
     type — left in place`.
   - Files in `protected_files` are never renamed or moved (`SKIP … Protected
     — kept`).
   - Applies one of the following actions to the rest:

   | Condition | Action |
   |-----------|--------|
   | No files exist | Reports `MISSING` and continues (non-fatal) |
   | A file matches the canonical name | Relocates other same-type files (`PRUNE`); reports `SKIP` if nothing to do |
   | No file matches, one same-type file exists | Renames it to the canonical name (`RENAME`) |
   | No file matches, several same-type files exist | Renames the newest (by modification time) to the canonical name, warns about the rest (`WARN`) |
   | No file matches, no same-type file | Reports `MISSING` (`No .pkg file to rename …`) |

   If the renamed file contained unsafe characters (`[^-._A-Za-z0-9]`), the
   message is flagged `UNSAFE_CHARS`.

**Nothing is deleted.** A pruned file is moved aside to the same place in a
`relocated/` folder at the top of the vendor cache:
`<vendor-cache>/HP/HP-Printer-Drivers/old.pkg` goes to
`<vendor-cache>/relocated/HP/HP-Printer-Drivers/old.pkg`. A name that is already
taken there gets `-2`, `-3`… before its extension, so nothing is overwritten.
`--relocate-dir <dir>` puts the tree somewhere else. The default lives in the
vendor cache, so under `/tmp` it is cleared at reboot like everything else there;
pass a durable folder if you may want the files back. A registry vendor named
`relocated` is refused (use `--relocate-dir`).

When a new version arrives, just drop it in beside the old canonical file. The
newest file of the canonical type wins: the old canonical file is relocated
("Superseded by …") and the new one renamed into place (`DONE|REPLACED`). On
equal timestamps the canonical file stays.

The script never modifies tracked git content — only files under the vendor
cache directory (including its `relocated/` folder).

---

## Usage

```bash
bin/normalize-vendor-cache.sh \
  --repo /path/to/recipe-repo \
  --vendor-cache /tmp/autopkg/vendor_cache --dry-run
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--repo` | Yes | Path to the recipe repo root. The script looks for `vendor-drop-registry.yaml` here. |
| `--vendor-cache` | Yes | Root path of the vendor cache directory (e.g., `/tmp/autopkg/vendor_cache`). |
| `--dry-run` | No | Report what would change; change nothing. `RENAME` lines say `DRY RUN`, `PRUNE` lines `DRY RUN: would move to …`. |
| `--relocate-dir <dir>` | No | Where pruned files go, mirroring `<Vendor>/<App>/`. Default `<vendor-cache>/relocated/`. |

Run with `--dry-run` first after staging new files, then without.

The script is a front end for `lib/python/recipekit/vendor_cache.py` and runs on
AutoPkg's Python with PyYAML. Nothing else to install.

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | All entries processed (warnings are OK, e.g., missing directories) |
| `1` | Bad arguments, config file not found or unparsable, vendor cache root not found, a bad registry key or canonical name, or a rename/move failed |

### Output format

Tab-separated, one line per action:

```
ACTION\tVENDOR/APP\tOLD_NAME\tNEW_NAME\tMESSAGE
```

| Field | Description |
|-------|-------------|
| `ACTION` | `SKIP`, `RENAME`, `PRUNE`, `KEEP`, `MISSING`, `IGNORE`, `WARN`, `ERROR` |
| `VENDOR/APP` | Registry key, e.g. `OrchardLabs/Orchard-Analytics` |
| `OLD_NAME` | Previous filename (empty for `SKIP` when already in place) |
| `NEW_NAME` | Canonical filename after rename |
| `MESSAGE` | Human-readable status, warning, or error detail (`DONE`, `DRY RUN`, `Moved to <path>`, …) |

`ERROR` and `WARN` lines go to stderr; the rest of the action log goes to stdout
and can be piped into monitoring or alerting.

---

## CI/CD Integration

The script runs **before** `autopkg run` in any CI/CD pipeline that consumes
vendor-drop recipes:

```yaml
# GitHub Actions workflow snippet
jobs:
  test-recipes:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          brew install autopkg

      - name: Normalize vendor cache filenames
        run: |
          bin/normalize-vendor-cache.sh \
            --repo customer/acme/output \
            --vendor-cache /tmp/autopkg/vendor_cache

      - name: Test all recipes
        run: |
          autopkg run -v customer/acme/output/recipes/AcmeFruitCo/AcmeSupport/AcmeSupport.download.recipe.yaml
```

Key integration points:

- Nothing beyond AutoPkg is needed on the runner: the script uses AutoPkg's
  Python and PyYAML.
- The `--vendor-cache` path must match the `VENDOR_CACHE_ROOT` that the
  recipes reference.
- The normalization step uses the same `REPO` root where
  `vendor-drop-registry.yaml` lives.

---

## Adding a New App

To add a new vendor-drop app to the pipeline:

1. **Add an entry to the registry.** Edit `vendor-drop-registry.yaml` in your
   recipe repo, adding a line under `canonical_filenames`:
   ```yaml
   VendorName/AppName: "Canonical_Name.pkg"
   ```
   The key is `Vendor/App` (used as the subdirectory path under
   `VENDOR_CACHE_ROOT`). The value is the safe canonical filename the recipe
   will reference.

2. **Update the recipe.** Set `DOWNLOAD_URL` to the canonical form:
   ```yaml
   DOWNLOAD_URL: "file://%VENDOR_CACHE_ROOT%/VendorName/AppName/Canonical_Name.pkg"
   ```

3. **Commit both changes.** No script changes needed.

That's it. The script never changes when adding a new app — only the
config file does.

---

## Canonical Filename Rules

Canonical filenames MUST:

- Contain **only** `[A-Za-z0-9._-]` — no spaces, no `@`, no parentheses, no
  commas, no special characters.
- Be **unique** within a single `Vendor/App` directory.
- Use an **extension that reflects the actual file type** (`.pkg`, `.dmg`,
  `.zip`, `.plist`, `.sh`). The script only renames or prunes files of that
  type, so the extension decides what counts as a version of the file.

Files with unsafe characters in their original names are flagged as
`UNSAFE_CHARS` in the output after being renamed.

---

## Registry Reference

An example registry: the one in `specs/vendor-cache/00-constitution.md` §3.
Your recipe repo's `vendor-drop-registry.yaml` holds your own; Acme's is
`customer/acme/output/vendor-drop-registry.yaml`.

| Key | Canonical Filename |
|-----|--------------------|
| `Adobe/Adobe-Creative-Cloud` | `Adobe_Creative_Cloud.pkg` |
| `AnthropicPBC/Claude` | `Claude.pkg` |
| `CitrixSystems/Citrix-Workspace` | `Citrix-Workspace.pkg` |
| `Sophos/Sophos-Endpoint` | `Sophos_Endpoint.payload.zip` |
| `XeroxCorporation/Xerox-Drivers` | `Xerox_Drivers.pkg` |
| `HP/HP-Printer-Drivers` | `HP-Printer-Drivers.pkg` |
| `OrchardLabs/Orchard-Analytics` | `Orchard-Analytics.dmg` |
| `OrchardLabs/Orchard-Analytics-License` | `payload.zip` |
| `AcmeFruitCo/AcmeSupport` | `payload.zip` |
| `AcmeFruitCo/Acme-Wallpaper` | `payload.zip` |
| `AcmeFruitCo/Acme-UninstallAgent` | `scripts.zip` |
| `PomeloSoftware/Pomelo-Studio` | `Pomelo-Studio.dmg` |
