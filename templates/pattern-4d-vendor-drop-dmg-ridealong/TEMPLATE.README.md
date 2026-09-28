# REPLACE_APPNAME — Recipe Notes

## Pattern 4d — Vendor-Drop DMG with Ridealong Scripts/Payload

REPLACE_BRIEF_DESCRIPTION

This recipe:

1. Stages the DMG, scripts, and payload from `vendor_cache` with `URLDownloader` + `Copier`
2. Mounts the DMG natively and extracts the `.app` with `Copier`
3. Verifies the code signature on the extracted `.app` (team ID: `REPLACE_TEAMID`)
4. Reads the version from the `.app` bundle with `Versioner`
5. Rebuilds into a org-prefixed flat package with `PkgCreator`, bundling scripts and payload

## Status: confirmed working

Built and verified in REPLACE_BATCH. Produces `Acme_REPLACE_APPNAME.pkg`.

## What's in vendor_cache

```
vendor_cache/REPLACE_VENDORDIR/REPLACE_APPNAME/
├── REPLACE_FILENAME      ← recipe ingests this
├── scripts/              ← ridealong postinstall scripts
├── payload/              ← org-specific files (license keys, configs, etc.)
└── REPLACE_FILENAME_RW   ← writable version for app owner to update (if applicable)
```

<!-- VARIABLES-SPEC-START -->

filename_pattern=`REPLACE_APPNAME`

manufacturer_url=`REPLACE_DOWNLOAD_URL`

drop_folder=`vendor_cache/REPLACE_VENDORDIR/REPLACE_APPNAME/`

upload_url=`vendor_cache/REPLACE_VENDORDIR/REPLACE_APPNAME/REPLACE_FILENAME`

<!-- VARIABLES-SPEC-END -->


<!-- DOWNLOAD-SPEC-START -->

## What to provide for a new version

**File format:** DMG containing a `.app` bundle, plus `scripts/` and `payload/` subdirectories.

**Naming:** Save the main DMG file, ensuring that `filename_pattern` is in the filename.
Put it in the `drop_folder` directory. If the downloaded file has a different
name (e.g. `App_2026.dmg`), rename it to include `filename_pattern` before
placing it. Also update the `scripts/` and `payload/` subdirectories if the
postinstall script or license files change.

**Where to get it:** Download from REPLACE_VENDOR's website at
`manufacturer_url` — the macOS DMG option.

**Upload it here:** `upload_url`
<!-- UPLOAD-PLACEHOLDER: Replace with actual upload URL when known -->

**Also needed (org-proprietary):**
REPLACE_PROPRIETARY_ITEMS

**Need help?** Contact your IT support team.

<!-- DOWNLOAD-SPEC-END -->
