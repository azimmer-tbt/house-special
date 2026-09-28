# REPLACE_APPNAME — Recipe Notes

## Pattern 4b — Distribution Vendor Package

REPLACE_BRIEF_DESCRIPTION

This recipe:

1. Stages the distribution `.pkg` from `vendor_cache` with `URLDownloader` (file:// URI)
2. Verifies the REPLACE_VENDOR signature (team ID: `REPLACE_TEAMID`)
3. Copies the distribution pkg bit-for-bit with `Copier` (not `PkgCopier` — distribution format)

## Why Copier, not PkgCopier

Distribution packages contain a `Distribution` file with child component references,
not a single flat `Payload`. `PkgCopier` expects a flat package and crashes with
"list index out of range." `Copier` copies the file as-is, preserving the vendor's
distribution structure and signature.

## Status: confirmed working

Built and verified in REPLACE_BATCH. Produces `REPLACE_APPNAME.pkg` (vendor
distribution, no `Acme_` prefix).

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

**File format:** Signed distribution package (`.pkg`)

**Naming:** Save the file, ensuring that `filename_pattern` is in the filename.
Put it in the `drop_folder` directory. If the downloaded file has a different
name (e.g. `App_2026.pkg`), rename it to include `filename_pattern` before
placing it.

**Where to get it:** Download from REPLACE_VENDOR's website at
`manufacturer_url` — the macOS option.

**Upload it here:** `upload_url`
<!-- UPLOAD-PLACEHOLDER: Replace with actual upload URL when known -->

**Also needed (org-proprietary):**
REPLACE_PROPRIETARY_ITEMS

**Need help?** Contact your IT support team.

<!-- DOWNLOAD-SPEC-END -->
