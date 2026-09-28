# REPLACE_APPNAME — Recipe Notes

## Pattern 4 — Vendor-Drop REPLACE_FILEFORMAT

REPLACE_BRIEF_DESCRIPTION

This recipe:

1. Stages the file from `vendor_cache` with `Copier`
2. REPLACE_ADDITIONAL_STEPS
3. Verifies the REPLACE_VENDOR signature (team ID: `REPLACE_TEAMID`)
4. Packages with `PkgCreator`/`PkgCopier`

## Status: confirmed working

Built and verified in REPLACE_BATCH. Produces `Acme_REPLACE_APPNAME.pkg`
(in-house build = `Acme_` prefix) or `REPLACE_APPNAME.pkg` (vendor redist,
no prefix).

## What's in vendor_cache

```
vendor_cache/REPLACE_VENDORDIR/REPLACE_APPNAME/
├── REPLACE_FILENAME      ← recipe ingests this
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

**File format:** REPLACE_FILEFORMAT_DESCRIPTION

**Naming:** Save the file, ensuring that `filename_pattern` is in the filename.
Put it in the `drop_folder` directory. If the downloaded file has a different
name (e.g. `App_2026.dmg`), rename it to include `filename_pattern` before
placing it.

**Where to get it:** Download from REPLACE_VENDOR's website at
`manufacturer_url` — the REPLACE_PLATFORM option.

**Upload it here:** `upload_url`
<!-- UPLOAD-PLACEHOLDER: Replace with actual upload URL when known -->

**Also needed (org-proprietary):**
REPLACE_PROPRIETARY_ITEMS

**Need help?** Contact your IT support team.

<!-- DOWNLOAD-SPEC-END -->
