# QuarantineHelper

## Pattern: Pattern 6b — Rebuilt (Payload + Scripts)

Reverse-engineered from an existing package with `bin/pkg-reverse.sh`.
**This recipe is a draft and has not been run.**

## Origin

| Field | Value |
|-------|-------|
| Source package | `QuarantineHelper-legacy.pkg` |
| Identifier | `com.acmefruit.QuarantineHelper` |
| Version | 1.0.0 |
| install-location | `/` |
| Signature | unsigned |
| Payload | 2 files |
| Scripts | none |

Source files for this package were not available; the payload was extracted from
a built package rather than rebuilt from source.

## Before trusting this

1. Compare against the original: `pkgutil --files com.acmefruit.QuarantineHelper`
2. Confirm install-location — PkgCreator has no install-location argument, so the
   structure inside `pkgroot` **is** the install location. If the original was
   not `/`, the payload tree must be rooted to match.
3. Read any extracted scripts. They may reference paths, receipts, or versions
   that no longer hold.
4. `bin/autopkg-preflight.py --app <this directory>`
5. `autopkg run ./QuarantineHelper.pkg.recipe.yaml`
6. Install the result on a test Mac and compare against the original's receipt.

## Known gaps

- No signature. The rebuilt package is unsigned regardless of the original.
- A Distribution wrapper, if the original had one, is not reproduced — install
  choices, requirements, and any JavaScript are gone.
- Version is pinned in the download recipe's `Input`; there is nothing to detect a new one.

<!-- VARIABLES-SPEC-START -->

filename_pattern=`QuarantineHelper`

manufacturer_url=`https://it.acmefruit.example/`

drop_folder=`vendor_cache/AcmeFruitCo/QuarantineHelper/`

upload_url=`vendor_cache/AcmeFruitCo/QuarantineHelper/payload.zip`

<!-- VARIABLES-SPEC-END -->


<!-- DOWNLOAD-SPEC-START -->

## What to provide for a new version

**File format:** Payload archive (zip) extracted from existing
`QuarantineHelper-legacy.pkg`.

**Naming:** Place the payload archive at
`vendor_cache/AcmeFruitCo/QuarantineHelper/payload.zip`.

**Where to get it:** Extracted from the existing on-server package.
Use `pkgutil --expand` to extract, then locate and zip the Payload file.

**Need help?** Contact your IT support team.

<!-- DOWNLOAD-SPEC-END -->
