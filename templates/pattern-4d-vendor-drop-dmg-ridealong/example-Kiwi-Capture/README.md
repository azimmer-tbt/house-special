# Kiwi Capture

Pattern 4d (vendor-drop DMG with ridealong scripts/payload). Kiwi Capture is a
fictional screen recorder from the fictional vendor KiwiSoft, part of the Acme
Fruit Co. worked example. KiwiSoft delivers a DMG with the `.app` at its root;
Acme adds a postinstall script and a license key file that ride along in the
same package.

## Origin

| Field | Value |
|-------|-------|
| Source DMG | `Kiwi-Capture.dmg`, dropped into `vendor_cache` by whoever holds the KiwiSoft license |
| Recipe pattern | 4d (vendor-drop DMG with ridealong scripts/payload) |
| Bundle identifier | `com.kiwisoft.capture` |
| Code signature | KiwiSoft (Team ID `KIWISOFT00`, fictional) |
| Payload | `Kiwi Capture.app`, plus the license key under `/Users/Shared/KiwiSoft/Kiwi-Capture/` |
| Scripts | `postinstall` (Acme's default preferences) |

## What it installs

`Kiwi Capture.app` into `/Applications/`, verified by CodeSignatureVerifier in
the download recipe, and the license key file, owned by `root:wheel`.

## Why a ridealong and not a slice

The license key and preferences could be a separate 6c/6b slice
([`reference/recipe-standards.md`](../../../reference/recipe-standards.md)
§6.10.1 prefers that). This example keeps them in the same package to show the
4d shape: the vendor's `.app` rebuilt with Acme's extras beside it. Document the
reason in the README whenever you choose a ridealong over a slice.

## Known caveats

- **Review the postinstall script** before trusting it; it runs as root.
- **The DMG wrapper is unsigned.** Only the `.app` inside is KiwiSoft-signed,
  which is what CodeSignatureVerifier checks.

## What's in vendor_cache

```
vendor_cache/KiwiSoft/Kiwi-Capture/
├── Kiwi-Capture.dmg   ← recipe ingests this
├── scripts/           ← postinstall script
└── payload/           ← org license key files
```

<!-- VARIABLES-SPEC-START -->

filename_pattern=`Kiwi-Capture`

manufacturer_url=`https://kiwisoft.example/capture`

drop_folder=`vendor_cache/KiwiSoft/Kiwi-Capture/`

upload_url=`vendor_cache/KiwiSoft/Kiwi-Capture/Kiwi-Capture.dmg`

<!-- VARIABLES-SPEC-END -->


<!-- DOWNLOAD-SPEC-START -->

## What to provide for a new version

**File format:** DMG (disk image) containing `Kiwi Capture.app`, plus `scripts/` and `payload/` subdirectories.

**Naming:** Save the file as `Kiwi-Capture.dmg` in the
`vendor_cache/KiwiSoft/Kiwi-Capture/` directory. If the downloaded file has a
different name (e.g. `Kiwi Capture 2026.1 Installer.dmg`), rename it to
`Kiwi-Capture.dmg` before placing it. Also update the `scripts/` and `payload/`
subdirectories if the postinstall script or license key file change.

**Where to get it:** Download from KiwiSoft's customer portal at
`manufacturer_url` — the macOS DMG option.

**Upload it here:** `upload_url`
<!-- UPLOAD-PLACEHOLDER: Replace with actual upload URL when known -->

**Need help?** Contact your IT support team.

<!-- DOWNLOAD-SPEC-END -->
