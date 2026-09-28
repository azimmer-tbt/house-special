---
ready_draft: true
ready_test: false
ready_compare: false
ref_file: Orchard Analytics.app
ref_version: 7.2
team_id: ORCHARD000
public_download: false
download_url: ""
vendor_name: OrchardLabs
app_name: Orchard-Analytics
pattern: "4c"  # + license slice Orchard-Analytics-License, pattern 6c
---

# Plan of attack — Orchard Analytics (fictional)

A worked example of the per-package plan from `specs/method/00-methodology.md`,
step 3. Orchard Labs is fictional; the reasoning is the real process.

## Research Notes

- **What we received:** the vendor's sales rep emailed `Orchard Analytics 7.2.dmg`
  and a `license.lic`. There is no public download: the vendor portal needs a
  customer login, so AutoPkg can't fetch it → **Pattern 4 (vendor drop)**.
- **What's in the DMG:** `hdiutil attach -nobrowse -readonly` shows one
  `Orchard Analytics.app` at the volume root plus the usual `Applications` alias.
  No `.pkg` → not 4a/4b. A single app → 4c at minimum.
- **The license file:** the vendor's install guide says the app reads
  `/Library/Application Support/Orchard Labs/license.lic` and must not be able to
  write it. Owner/mode from the vendor's guide: `root:wheel 0444`. (Methodology
  lesson 17: take modes from the source of truth, never from memory.)
- **Ridealong or slice?** **Slice.** The license comes from IT, not the vendor; it
  changes yearly while the app changes several times a year; and it lives outside the
  app bundle. Packing it into the app package (4d) would mean rebuilding the app
  package for every license renewal. So: the app is **4c** (DMG, app only) and the
  license is its own **6c** recipe, `Orchard-Analytics-License`.
- **Install order:** the license slice installs **after** the app package, so the
  app never launches unlicensed. (The license's folder doesn't depend on the app, so
  this is about user experience, not a hard dependency.)
- **Signature:** `codesign -dvv` on the mounted app shows a Developer ID team
  (`ORCHARD000` stands in for it here). Copy the designated requirement verbatim
  from `codesign -dr -` (Standards §6.5). The license file is org-supplied and
  unsigned by nature; that's fine — the verifier checks the app.
- **Version:** `CFBundleShortVersionString` in the bundle → `Versioner`, no pin.
- **Existing deployment?** None — new app, so there is no original package to
  `pkg-compare.sh` against. `ready_compare` stays false by design.

## Source Location

- App: `vendor_cache/OrchardLabs/Orchard-Analytics/Orchard-Analytics.dmg`
- License slice: `vendor_cache/OrchardLabs/Orchard-Analytics-License/payload.zip`
  (the tree `Library/Application Support/Orchard Labs/license.lic`, zipped from inside)

See `customer/acme/output/files_to_copy.yaml` for what the durable source must
contain, and `vendor-drop-registry.yaml` for the canonical filenames.

## Actions

- [x] Classify: app 4c (vendor DMG, app only) + license slice 6c
- [x] App: copy the 4c template (`templates/pattern-4c-vendor-drop-dmg/`)
- [x] License slice: copy the 6c template (`templates/pattern-6c-rebuilt-single-file/`);
      stage `payload.zip` exactly as it installs
- [x] Fill placeholders; `bin/scan-placeholders.sh --repo customer/acme/output Orchard`
- [x] Lint: `bin/recipe-linter.sh --repo customer/acme/output`
- [ ] Stage the DMG; `bin/normalize-vendor-cache.sh --repo customer/acme/output --vendor-cache <VENDOR_CACHE_ROOT>`
- [ ] `autopkg run -v -k VENDOR_CACHE_ROOT=<cache> customer/acme/output/recipes/OrchardLabs/Orchard-Analytics/Orchard-Analytics.pkg.recipe.yaml`
- [ ] Same for `Orchard-Analytics-License/Orchard-Analytics-License.pkg.recipe.yaml`
- [ ] Deployment: license package scoped to install **after** the app package
- [ ] Install on a test Mac; confirm the app starts licensed and can't modify `license.lic`
- [ ] Sign-off (`.devagent/rules/11-per-package-signoff.md`)
