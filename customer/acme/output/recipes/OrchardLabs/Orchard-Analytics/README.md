# Orchard Analytics (fictional)

> **EXAMPLE — no real download.** Orchard Labs and Orchard Analytics don't exist. This
> recipe shows a complete Pattern 4c recipe and passes lint; there is no DMG to stage,
> so it can't run. The plan that produced it is
> `customer/acme/plans/orchard-analytics.md`.

**Pattern 4c — vendor-drop DMG, app only.** The site license is **not** in this
package. It ships as its own slice,
[`Orchard-Analytics-License`](../Orchard-Analytics-License/README.md) (Pattern 6c),
which installs after this one.

| | |
|---|---|
| Source | The vendor emails a DMG to IT; it is dropped into the vendor cache |
| Signature | Developer ID (team ID `ORCHARD000` is a placeholder — a real recipe copies the requirement from `codesign -dr -`) |
| Version | Read from the app bundle |
| Output | `Acme_Orchard-Analytics.pkg`, installs `/Applications/Orchard Analytics.app` |
| Slices | `Orchard-Analytics-License` — install **after** this package |

## Why the license is a slice

The app updates several times a year; IT renews the license once a year. As a slice,
neither one forces a rebuild of the other, each can be rolled back on its own, and this
package stays exactly what the vendor shipped. See
[`docs/build-your-first-recipe.md`](../../../../../../docs/build-your-first-recipe.md) step 3.

<!-- VARIABLES-SPEC-START -->

filename_pattern=`Orchard Analytics*.dmg`

manufacturer_url=`https://orchardlabs.example/`

drop_folder=`vendor_cache/OrchardLabs/Orchard-Analytics/`

upload_url=`vendor_cache/OrchardLabs/Orchard-Analytics/Orchard-Analytics.dmg`

<!-- VARIABLES-SPEC-END -->

<!-- DOWNLOAD-SPEC-START -->

## What to provide for a new version

**File format:** the vendor's DMG, unchanged.

**Naming:** drop it into `vendor_cache/OrchardLabs/Orchard-Analytics/` under any name;
`bin/normalize-vendor-cache.sh --repo customer/acme/output --vendor-cache <VENDOR_CACHE_ROOT>` renames it to
`Orchard-Analytics.dmg` (see `customer/acme/output/vendor-drop-registry.yaml`).

**License file:** unchanged between versions; lives at
`vendor_cache/OrchardLabs/Orchard-Analytics/payload/Library/Application Support/Orchard Labs/license.lic`.
If the vendor issues a new one, replace that file.

<!-- DOWNLOAD-SPEC-END -->
