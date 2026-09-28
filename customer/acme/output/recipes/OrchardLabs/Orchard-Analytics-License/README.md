# Orchard Analytics site license (fictional)

> **EXAMPLE — no real download.** Orchard Labs is fictional; there is no license file
> to stage. This recipe shows a complete license **slice** and passes lint.

**Pattern 6c — slice: one file, exact owner and mode.** Delivers the site license for
[Orchard Analytics](../Orchard-Analytics/README.md) without touching the app's package.

| | |
|---|---|
| Installs | `/Library/Application Support/Orchard Labs/license.lic`, `root:wheel 0444` |
| Source | `vendor_cache/OrchardLabs/Orchard-Analytics-License/payload.zip` (from IT, not the vendor download) |
| Signature | None: an org-supplied file. `NO_CODE_SIGNATURE_REQUIRED: true`. No team ID. |
| Version | Pinned in the download recipe's `Input` (`version: "2026.1"`). Bump it when IT issues a new license. |
| Output | `Acme_Orchard-Analytics-License.pkg` |

## Install order

**Install after:** `Acme_Orchard-Analytics.pkg`.

This license sits outside the app bundle, in a folder the app doesn't create, so
strictly it only needs `/Library/Application Support` (always present). Deploy it after
the app anyway: that way the app never launches unlicensed, and the order stays the same
as for slices that *do* depend on the app's folders.

If a vendor requires the license **inside** the app bundle
(`/Applications/<App>.app/Contents/Resources/…`):
- the slice **must** install after the app package, because the folder doesn't exist
  until the app is installed;
- every app update replaces the bundle and **deletes** the license, so the slice must be
  re-run after every app update, not just once;
- adding a file to a signed bundle breaks its code signature. Ask the vendor for an
  outside-the-bundle location first.

## Why a slice

The license changes yearly and is owned by IT; the app changes several times a year
and is the vendor's. Keeping them apart means neither rebuild waits on the other, and
either can be rolled back alone. See
[`docs/build-your-first-recipe.md`](../../../../../../docs/build-your-first-recipe.md) step 3
and `reference/recipe-standards.md` §6.10.1.

<!-- VARIABLES-SPEC-START -->

filename_pattern=`payload.zip`

manufacturer_url=`https://it.acmefruit.example/`

drop_folder=`vendor_cache/OrchardLabs/Orchard-Analytics-License/`

upload_url=`vendor_cache/OrchardLabs/Orchard-Analytics-License/payload.zip`

<!-- VARIABLES-SPEC-END -->

<!-- DOWNLOAD-SPEC-START -->

## What to provide for a new license

**File format:** `payload.zip`, zipped from **inside** the tree so it unpacks to
`Library/Application Support/Orchard Labs/license.lic`:

```bash
(cd payload && zip -ry ../payload.zip .)
unzip -l payload.zip        # first entry must be Library/, not payload/
```

**Where:** `vendor_cache/OrchardLabs/Orchard-Analytics-License/payload.zip`, then bump
`version` in the download recipe's `Input`.

<!-- DOWNLOAD-SPEC-END -->
