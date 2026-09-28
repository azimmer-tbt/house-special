# Updating Existing Recipes

A guide for IT support staff and app owners who need to update existing recipes
to build new package versions, without needing the full developer toolkit.

---

## What This Guide Covers

This guide explains how to:

1. Update a **vendor-drop recipe** (Pattern 4) — when the vendor provides a new
   installer file
2. Update a **rebuilt recipe** (Pattern 6) — when an existing package needs a
   new payload
3. Add a **new app** to the vendor-drop registry
4. Troubleshoot common recipe failures

It does **not** cover creating recipes from scratch, recipe pattern selection,
or running the full development pipeline. For those, see
[`docs/usage-guide.md`](usage-guide.md).

---

## The Recipe Repo Layout

```
autopkg-iac/                          # ← the recipe repo
├── recipes/                          # All recipe pairs live here
│   └── VendorName/
│       └── AppName/
│           ├── AppName.download.recipe.yaml
│           ├── AppName.pkg.recipe.yaml
│           ├── README.md             # App-specific notes
│           └── .overrides            # Optional, org-defined; pipeline-supplied values
├── build/
│   └── vendor_cache/                 # Vendor-provided installer files
│       └── VendorName/
│           └── AppName/
│               └── Installer.pkg
├── bin/                              # Toolkit scripts
├── guardrails/                       # Audit check scripts
├── vendor-drop-registry.yaml         # Maps vendor file names (Pattern 4 only)
├── manifest.sha256                   # Checksum file for handoff verification
└── README.md
```

All `bin/` scripts accept `--repo <path-to-repo>` to point at the recipe repo.
You can set `export AUTOPKG_TOOLKIT_REPO=/path/to/autopkg-iac` to avoid typing
it every time.

---

## Recipe Patterns (Simple Table)

| Pattern | What it means | How to update |
|---------|---------------|---------------|
| 4a | Vendor provides a `.pkg` file — we copy it as-is | Drop new `.pkg` in vendor cache, run `autopkg` |
| 4b | Vendor provides a **distribution** `.pkg` — we copy it as-is with `Copier` | Drop new `.pkg` in vendor cache, run `autopkg` |
| 4c | Vendor provides a `.dmg` — we extract and rebuild | Drop new `.dmg` in vendor cache, run `autopkg` |
| 4d | Vendor provides `.dmg` + we inject scripts/payload | Drop new `.dmg` in vendor cache, run `autopkg` |
| 5 | Vendor publishes at a stable URL — we download and copy | Run `autopkg` (it downloads from the URL) |
| 6a–d | Rebuilt from existing package — no source available | Extract payload from new pkg, zip it, drop in vendor cache, run `autopkg` |
| 7 | In-house DMG wrapping a vendor app | Update the DMG in vendor cache, run `autopkg` |

Check the app's `README.md` to see which pattern it uses.

---

## How to Update a Vendor-Drop Recipe (Patterns 4a, 4b, 4c, 4d, 5)

### Pattern 4a — Vendor Provides a `.pkg` File (Standard, PkgCopier-safe)

**Step 1: Get the new file from the vendor.**

The vendor sends you a new version of the installer (usually via email, portal,
or shared drive).

**Step 2: Place it in the vendor cache.**

```bash
# Copy the new installer into the vendor cache
cp ~/Downloads/Vendor-Installer-2.0.pkg \
    build/vendor_cache/VendorName/AppName/
```

Leave the old `AppName.pkg` where it is: the normalizer sees the newer file,
relocates the old one and renames the new one into place.

**Step 3: Normalize the filename (if using vendor-drop-registry).**

```bash
# This renames the file you dropped to the canonical name the recipe
# expects (e.g., "AppName.pkg"). Only files of that type (.pkg) are renamed;
# stale ones go to build/vendor_cache/relocated/<Vendor>/<App>/, never deleted.
bin/normalize-vendor-cache.sh --repo . --vendor-cache build/vendor_cache/ --dry-run
bin/normalize-vendor-cache.sh --repo . --vendor-cache build/vendor_cache/
```

**Step 4: Clear the AutoPkg cache (important!).**

```bash
# AutoPkg caches previous build results — always clear before a fresh build
bin/clear-autopkg-cache.sh com.acmefruit.autopkg.download.AppName com.acmefruit.autopkg.pkg.AppName
```

Or use the run-recipes helper:

```bash
bin/run-recipes.sh --repo . --clear-cache
```

**Step 5: Run autopkg.**

```bash
autopkg run ./recipes/VendorName/AppName/AppName.pkg.recipe.yaml
```

**Step 6: Verify the output.**

Check that:
- The build completed without errors (exit code 0)
- The output package exists at `~/Library/AutoPkg/Cache/.../Acme_AppName.pkg`
  (or just `AppName.pkg` for Pattern 4a/5 where we don't add the `Acme_` prefix)

### Pattern 4b — Vendor Provides a Distribution `.pkg` File

Same as Pattern 4a, but uses `Copier` in the pkg recipe instead of `PkgCopier`
(because distribution packages crash `PkgCopier`):

```bash
cp ~/Downloads/Vendor-Installer-2.0.pkg build/vendor_cache/VendorName/AppName/
bin/normalize-vendor-cache.sh --repo . --vendor-cache build/vendor_cache/
bin/clear-autopkg-cache.sh com.acmefruit.autopkg.download.AppName com.acmefruit.autopkg.pkg.AppName
autopkg run ./recipes/VendorName/AppName/AppName.pkg.recipe.yaml
```

### Pattern 4c — Vendor Provides a `.dmg` File

Same as Pattern 4a, but the vendor cache file is a `.dmg` instead of a `.pkg`:

```bash
cp ~/Downloads/App-2.0.dmg build/vendor_cache/VendorName/AppName/
bin/normalize-vendor-cache.sh --repo . --vendor-cache build/vendor_cache/
bin/clear-autopkg-cache.sh com.acmefruit.autopkg.download.AppName com.acmefruit.autopkg.pkg.AppName
autopkg run ./recipes/VendorName/AppName/AppName.pkg.recipe.yaml
```

### Pattern 4d — Vendor Provides a `.dmg` + Scripts/Payload

Same as 4c. The ridealong scripts and payload files are already part of the
recipe — they don't need to be placed manually unless they change.

### Pattern 5 — Vendor Publishes at a Stable URL

No files to place — the recipe downloads from the URL automatically:

```bash
bin/clear-autopkg-cache.sh com.acmefruit.autopkg.download.AppName com.acmefruit.autopkg.pkg.AppName
autopkg run ./recipes/VendorName/AppName/AppName.pkg.recipe.yaml
```

---

## How to Update a Rebuilt Recipe (Pattern 6)

These recipes rebuild an existing package from its payload. When the package
is updated, you need to extract the new payload.

### Step 1: Get the new .pkg file

```bash
cp ~/Downloads/AppName-2.0.pkg build/vendor_cache/VendorName/AppName/
```

### Step 2: Extract and zip the payload

For **Pattern 6a** (flat payload — no scripts):

```bash
mkdir -p /tmp/pkg-work
pkgutil --expand build/vendor_cache/VendorName/AppName/AppName.pkg /tmp/pkg-work/expanded

# Find the payload (usually Payload or Payload.pkg)
PAYLOAD=$(find /tmp/pkg-work -name "Payload*" -type f | head -1)
if [ -n "$PAYLOAD" ]; then
    # Create a zip of the payload directory
    cd /tmp/pkg-work
    mkdir payload
    cd payload
    cat "$PAYLOAD" | gzip -d | cpio -id
    zip -r /tmp/AppName_payload.zip .
    mv /tmp/AppName_payload.zip build/vendor_cache/VendorName/AppName/
fi

# Clean up
rm -rf /tmp/pkg-work
```

For **Pattern 6b** (payload + scripts):

Extract the payload as above, then also extract scripts:

```bash
# After expanding with pkgutil --expand:
SCRIPTS=$(find /tmp/pkg-work -name "Scripts*" -type f | head -1)
if [ -n "$SCRIPTS" ]; then
    mkdir /tmp/pkg-work/scripts
    cd /tmp/pkg-work/scripts
    cat "$SCRIPTS" | gzip -d | cpio -id
    zip -r /tmp/AppName_scripts.zip .
    mv /tmp/AppName_scripts.zip build/vendor_cache/VendorName/AppName/
fi
```

For **Pattern 6c** (single file with specific mode):

Extract, find the single file, zip it:

```bash
pkgutil --expand .../AppName.pkg /tmp/pkg-work
# find the Payload, extract to find the single file
cat /tmp/pkg-work/Payload | gzip -d | cpio -id
# Find the file and zip it
find payload -type f -exec zip -j /tmp/AppName_singlefile.zip {} \;
```

For **Pattern 6d** (payloadless — scripts only):

These recipes have no payload to update. If scripts change, extract the
`Scripts` archive from the new package as shown in 6b above.

### Step 3: Run normalize + clear cache + autopkg

```bash
bin/normalize-vendor-cache.sh --repo . --vendor-cache build/vendor_cache/
bin/clear-autopkg-cache.sh com.acmefruit.autopkg.download.AppName com.acmefruit.autopkg.pkg.AppName
autopkg run ./recipes/VendorName/AppName/AppName.pkg.recipe.yaml
```

---

## When a Recipe Fails — Common Failure Modes

### Build fails immediately

**"PathDeleter: No matching path found"**
The download recipe tries to delete something that doesn't exist on a first run.
→ Check if `PathDeleter` is the first step. If so, remove it — `Copier`
already overwrites its destination.

**"PkgCopier: list index out of range"**
The package is a **distribution** format (contains `Distribution` + inner
component pkgs). `PkgCopier` can't handle this format.
→ Replace `PkgCopier` with `Copier` in the pkg recipe.

**"File not found" / "No such file or directory" for vendor cache paths**
The vendor cache path is wrong.
→ Verify path arithmetic: `recipes/Vendor/App/file.yaml` is 3 levels deep,
so the relative path to repo root is `../../../`, not `../..`.

### Build runs but outputs wrong content

**Wrong output filename (missing `Acme_` prefix or has it when it shouldn't)**
→ Check the `pkgname` vs `pkg_path` field. `PkgCreator` recipes should use
`pkgname: "Acme_%NAME%"`. `PkgCopier`/`Copier` recipes should not.

**"CodeSignatureVerifier mismatch"**
→ The `expected_authority_names` list is missing the full 3-entry chain.
Should include: vendor cert + `Developer ID Certification Authority` + `Apple Root CA`.

### Build fails on second run but passed the first

**"Copier: [Errno 17] File exists"**
→ The `Copier` step is copying a directory, and on a fresh cache the
directory doesn't exist yet (first run succeeds). On a second run the
destination already exists, and directory copies don't overwrite by default.
→ Add `overwrite: true` to the `Copier` arguments.

**Stale cache from previous failed attempt**
→ Run `bin/clear-autopkg-cache.sh <identifier>` to clear before retrying.

### Preflight audit fails

Run `bin/autopkg-preflight.py --app recipes/VendorName/AppName` and fix
every item it reports as `FAIL`.

---

## The Vendor-Drop Registry (How to Add a New App)

The `vendor-drop-registry.yaml` file at the recipe repo root maps
vendor/app directory names to canonical filenames. Add a new app by editing
the file:

```yaml
canonical_filenames:
  "ExistingVendor/ExistingApp": "ExistingApp.pkg"
  "NewVendor/NewApp": "NewApp.dmg"
```

The canonical filename is what the recipe expects the installer to be named.
When you drop a new vendor file into the cache, run
`normalize-vendor-cache.sh` to rename it automatically. The extension of the
canonical filename decides which files it renames; others are left alone.

---

## Getting Help

| Issue | Where to look |
|-------|---------------|
| Recipe fails to build | Check the app's `README.md` for known issues |
| Preflight audit failure | `bin/autopkg-preflight.py --app recipes/Vendor/App` |
| Known bugs | `reference/methodology.md` (lessons from real runs) |
| Open issues | `BUGFIX.md` |
| Agent setup | `docs/agent-integration.md` |
| Full developer guide | `docs/usage-guide.md` |

If the issue isn't covered here, contact the recipe development team with:

- The recipe name and app name
- The full error output from `autopkg run`
- Whether you cleared the cache before retrying
- Whether the app is Pattern 4 (vendor-drop) or Pattern 6 (rebuilt)
