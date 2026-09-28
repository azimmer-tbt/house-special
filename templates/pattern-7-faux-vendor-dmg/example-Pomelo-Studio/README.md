# Pomelo Studio — Recipe Notes

## Pattern 7 — Faux Vendor DMG

Pomelo Studio is a fictional licensed app from the fictional vendor
PomeloSoftware, part of the Acme Fruit Co. worked example. Its installer is a
custom `Install Pomelo Studio.app` inside a DMG, not a `.pkg` or a plain `.app`
drop, and AutoPkg can't run it. Rather than reverse-engineer that installer, the
packaging team captured the installed app with a before/after snapshot tool
(for example Jamf Composer) and wrapped it in a faux vendor DMG that the recipe
ingests.

This recipe stages the faux DMG from `vendor_cache`, extracts the `.app` with
Copier's native DMG mounting, and packages it with PkgCreator.

The snapshot also caught a LaunchAgent and user preferences. Those are separate
recipe sets, not part of this one:
[`reference/recipe-standards.md`](../../../reference/recipe-standards.md) §6.9
tells that story.

## Why NO_CODE_SIGNATURE_REQUIRED

The faux vendor DMG is an in-house constructed artifact. The DMG wrapper is
unsigned by design — it was assembled by the packaging team, not by
PomeloSoftware. The `.app` inside may carry a different team ID than what a
direct vendor download would have. The trust boundary is the MDM, not code
signature verification.

## The `_RW.dmg` convention

```
vendor_cache/PomeloSoftware/Pomelo-Studio/
├── Pomelo-Studio.dmg      ← recipe ingests this (read-only compressed)
└── Pomelo-Studio_RW.dmg   ← writable version for app owner to update
```

## Status

A worked example: produces `Acme_Pomelo-Studio.pkg` (in-house build, so the
`Acme_` prefix).

## About the faux DMG

The DMG contains the app payload extracted from the snapshot package. The
recipe globs `Applications/Pomelo Studio*/Pomelo Studio*.app` to find the app
regardless of version suffix.

<!-- VARIABLES-SPEC-START -->

filename_pattern=`Pomelo-Studio`

writeable_filename=`Pomelo-Studio_RW.dmg`

manufacturer_url=`https://pomelosoftware.example/downloads/`

drop_folder=`vendor_cache/PomeloSoftware/Pomelo-Studio/`

upload_url=`vendor_cache/PomeloSoftware/Pomelo-Studio/Pomelo-Studio.dmg`

<!-- VARIABLES-SPEC-END -->


<!-- DOWNLOAD-SPEC-START -->

## What to provide for a new version

**File format:** DMG (writable disk image) containing the Pomelo Studio `.app` bundle.

**Naming:** Save the writable DMG, ensuring that `filename_pattern` is in the
filename. Rename it to `writeable_filename` and put it in the `drop_folder`
directory. If one is present, overwrite the existing one.

**Where to get it:** Download from PomeloSoftware's customer portal at
`manufacturer_url` — the macOS disk image option.

**How to update it:**

1. Install the newest Pomelo Studio on your device.
2. Copy `writeable_filename` from `drop_folder` to your Mac.
3. Double-click to mount it. A new disk will appear in Finder.
4. Drag the new Pomelo Studio.app from your Mac into the disk image, replacing the old one.
5. Eject the disk.
6. Upload the updated `writeable_filename` to `drop_folder`.
7. Notify the packaging team so they can compress it to `Pomelo-Studio.dmg`.

**Need help?** Contact your IT support team.

<!-- DOWNLOAD-SPEC-END -->
