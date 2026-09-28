# REPLACE_APPNAME — Recipe Notes

## Pattern 7 — Faux Vendor DMG

REPLACE_BRIEF_DESCRIPTION

A "faux vendor DMG" is an in-house constructed disk image that wraps a vendor
application's .app bundle. This approach is used when the vendor's original
installer is a non-standard format (custom `.app` installer, third-party
installer tool, etc.) that cannot be ingested directly by AutoPkg. The
workflow:

1. Capture the installed application via a **Jamf Composer** before/after
   snapshot (or equivalent)
2. Extract the `.app` payload from the snapshot
3. Wrap that payload into a DMG with the Composer-snapshot payload structure
   (typically `Applications/AppName/AppName.app`)
4. Stage the DMG in `vendor_cache` for recipe ingestion

This recipe:

1. Stages the faux DMG from `vendor_cache` with `URLDownloader` (file:// URI)
2. Mounts the DMG and extracts the `.app` with `Copier`
3. Reads the version from the `.app` bundle with `Versioner`
4. Rebuilds into a org-prefixed flat package with `PkgCreator`

## Why NO_CODE_SIGNATURE_REQUIRED

The faux vendor DMG is an **in-house constructed artifact**. The DMG wrapper is
unsigned by design — it was assembled by the packaging team, not by the vendor.
The `.app` inside may carry a different team ID than what a direct vendor
download would have, or may itself be unsigned.

**Do not silently omit CodeSignatureVerifier.** Declare
`NO_CODE_SIGNATURE_REQUIRED: true` with an explicit comment explaining why.
This signals to the next reader that the omission is intentional and
documented, not an oversight. The trust boundary is Jamf MDM, not code
signature verification.

## The `_RW.dmg` convention

In-house DMGs typically have two variants in vendor_cache:

```
vendor_cache/REPLACE_VENDORDIR/REPLACE_APPNAME/
├── REPLACE_FILENAME              ← recipe ingests this (read-only compressed)
└── REPLACE_FILENAME_WITHOUT_dmg  ← writable version for app owner to update
```

The `_RW.dmg` variant is a writable disk image that the app owner can open,
drag a new version of the `.app` into, and save — without needing Composer or
any other tooling. The app owner then notifies the packaging team to compress
it to `filename.dmg` for ingestion.

## Status: confirmed working

Built and verified in REPLACE_BATCH. Produces `Acme_REPLACE_APPNAME.pkg`.

## What's in vendor_cache

```
vendor_cache/REPLACE_VENDORDIR/REPLACE_APPNAME/
├── REPLACE_FILENAME      ← recipe ingests this
└── REPLACE_FILENAME_RW   ← writable version for app owner to update
```

<!-- VARIABLES-SPEC-START -->

filename_pattern=`REPLACE_APPNAME`

writeable_filename=`REPLACE_FILENAME_RW`

manufacturer_url=`REPLACE_DOWNLOAD_URL`

drop_folder=`vendor_cache/REPLACE_VENDORDIR/REPLACE_APPNAME/`

upload_url=`vendor_cache/REPLACE_VENDORDIR/REPLACE_APPNAME/REPLACE_FILENAME`

<!-- VARIABLES-SPEC-END -->


<!-- DOWNLOAD-SPEC-START -->

## What to provide for a new version

**File format:** DMG (writable disk image) containing the application `.app`
bundle in a `Applications/<AppName>/` payload structure.

**Naming:** Save the writable DMG, ensuring that `filename_pattern` is in the
filename. Rename it to `writeable_filename` and put it in the `drop_folder`
directory. If one is present, overwrite the existing one.

**Where to get it:** Download from REPLACE_VENDOR's website at
`manufacturer_url` — the macOS disk image option.

**How to update it:**

1. Install the newest REPLACE_APPNAME on your device.
2. Copy `writeable_filename` from `drop_folder` to your Mac.
3. Double-click to mount it. A new disk will appear in Finder.
4. Drag the new `REPLACE_APPNAME.app` from your Mac into the disk image,
   replacing the old one.
5. Eject the disk.
6. Upload the updated `writeable_filename` to `drop_folder`.
7. Notify the packaging team so they can compress it to `filename_pattern.dmg`.

**Also needed (org-proprietary):**
REPLACE_PROPRIETARY_ITEMS

**Need help?** Contact your IT support team.

<!-- DOWNLOAD-SPEC-END -->
