# Recipe Patterns

The single reference for recipe pattern names in this kit. Every pattern label you see
elsewhere (a template directory, a plan's `pattern:` field, a recipe `Comment`, the
`pattern` column in `customer/acme/end_result.yaml`) means what this page says.

Authority: [`reference/recipe-standards.md`](../reference/recipe-standards.md) §6.8
(Master Pattern Table and Quick Reference). The worked recipe skeletons for each
pattern are in §6.2 of the same file; this page doesn't repeat them.

## How a label is built

A label is a **number** plus, for most patterns, a **letter**.

- The **number** is the **source**: how the installer is acquired.
- The **letter** is the **variant**: what file comes out of the source and how it
  becomes the output package. Letters are defined per pattern, so `2b` and `4b` are
  different things (GitHub DMG vs. distribution pkg).

Patterns 5, 7 and 8 have no letter: their source always produces the same artifact.

| # | Source | Use when |
|---|---|---|
| 1 | Sparkle appcast | The app has a Sparkle update feed (`SUFeedURL` in its `Info.plist`) |
| 2 | GitHub release | The vendor publishes releases as binary assets on GitHub |
| 3 | Direct URL | The vendor hosts the installer at a known URL, stable or scraped |
| 4 | Vendor-provided file | No public URL: behind a login wall, emailed, or an in-house build. Staged in the vendor cache |
| 5 | Vendor pkg via stable URL | A signed vendor `.pkg` at a stable redirect URL (common with Microsoft) |
| 6 | Rebuilt package | A built package exists but its source files don't. Extract it and rebuild |
| 7 | Faux vendor DMG | An in-house DMG (usually from a snapshot tool such as Jamf Composer) wrapping a vendor app or binary |
| 8 | Experimental | An unsigned dev/internal `.app` with no signed version. Temporary; needs a documented approver |

Patterns 6–8 are this kit's additions to the shapes most community recipes use. Say
"Pattern 6 (rebuilt package)" the first time you use the term with people outside
your team.

## The prefix rule

**The output `.pkg` filename gets the org prefix if, and only if, `PkgCreator`
(`pkgbuild`) built it.**

| Output processor | Output naming | Prefix? |
|---|---|---|
| `PkgCreator` | `pkgname: "Acme_%NAME%"` | Yes |
| `PkgCopier` (vendor pkg copied as-is) | `pkg_path: "%RECIPE_CACHE_DIR%/%NAME%.pkg"` | No |
| `Copier` (distribution pkg copied as-is) | `pkg_path: "%RECIPE_CACHE_DIR%/%NAME%.pkg"` | No |
| `AppPkgCreator` | **Forbidden** (no control over the output filename) | — |

The prefix says "we built this package". A vendor's signed package that we copy keeps
the vendor's name. The prefix value comes from `pkgname_prefix` in
[`config/org.yaml`](../config/org.yaml) (`Acme_` in this kit), so a fork changes it in
one place. Lint rule PKG-002 enforces it, and only for recipes that use `PkgCreator`
([KI-13](known-issues.md), fixed).

## Master pattern table

"Prefix" follows from the output processor. "Template" is the starting point under
[`templates/`](../templates/README.md); "—" means none yet. Examples marked
*(Acme)* are in the [Acme catalogue](../customer/acme/README.md).

| Label | Definition | Recognise it by | Output processor | Prefix | Template | Examples |
|---|---|---|---|---|---|---|
| **1a** | Sparkle feed → vendor `.pkg`, copied as-is | Appcast enclosure is a `.pkg` | `PkgCopier` | No | — | — |
| **1b** | Sparkle feed → DMG/app, rebuilt | Appcast enclosure is a DMG or ZIP holding a `.app` | `PkgCreator` | Yes | — | — |
| **2a** | GitHub release → vendor `.pkg`, copied as-is | Release asset is a `.pkg` | `PkgCopier` | No | — | dockutil, desktoppr, default-browser, Outset, swiftDialog, Nudge, icongrabber *(Acme; see [community-tools](community-tools.md))* |
| **2b** | GitHub release → DMG/app, rebuilt | Release asset is a DMG holding a `.app` | `PkgCreator` | Yes | — | Moonlight, Raspberry Pi Imager, Pearcleaner *(Acme)*; Zettlr, Hammerspoon, draw.io; Fruit screensaver *(Acme, tar.gz)* |
| **2c** *(new)* | GitHub release app + ridealong scripts/payload | As 2b, plus org scripts or files the vendor doesn't ship. By analogy with 4d | `PkgCreator` with `scripts:` | Yes | — | — (the Acme Fruit screensaver was split into a 2b package plus a 6b default-setting slice instead) |
| **2d** *(new)* | GitHub source ZIP, unpacked and reassembled | Asset is an archive, often the auto-generated source ZIP, not an installable app. By analogy with 4e | `PkgCreator` (usually with `scripts:`) | Yes | — | Fruta new-hire starter kit *(Acme)* |
| **3a** | Stable URL → vendor `.pkg`, copied as-is | `curl -sLI` redirects to a `.pkg`; no version in the URL | `PkgCopier` | No | — | — (consider Pattern 5 if the version must be read from inside the pkg) |
| **3b** | Stable URL → DMG/app, rebuilt | `curl -sLI` redirects to "latest" DMG; no version in the URL | `PkgCreator` | Yes | — | Firefox, Google Chrome *(Acme)*; VS Code |
| **3c** | Scraped URL → DMG/app, rebuilt | Version is baked into the link; `URLTextSearcher` finds it on the download page | `PkgCreator` | Yes | — | Orange Data Mining *(Acme)* |
| **4a** | Vendor-drop flat `.pkg`, copied as-is | `pkgutil --expand` shows a lone `PackageInfo`/`Payload` | `PkgCopier` | No | `pattern-4-vendor-drop/` | Xerox drivers (template example) |
| **4b** | Vendor-drop distribution `.pkg`, copied as-is | `pkgutil --expand` shows a `Distribution` file plus inner `*.pkg` dirs | `Copier` (see [open question b](#open-questions)) | No | `pattern-4b-distribution-package/` | HP printer drivers *(Acme)*; Citrix Workspace, Cisco Secure Client |
| **4c** | Vendor-drop DMG, app extracted and rebuilt | DMG holding a `.app`, nothing else to add | `PkgCreator` | Yes | `pattern-4c-vendor-drop-dmg/` | Orchard Analytics *(Acme)* |
| **4d** | Vendor-drop DMG + ridealong scripts/payload | As 4c, plus license files, config or a postinstall | `PkgCreator` with `scripts:` | Yes | `pattern-4d-vendor-drop-dmg-ridealong/` | Kiwi Capture *(Acme; template example)* |
| **4e** | Vendor-drop ZIP + ridealong config, reassembled | ZIP holding installer(s) plus site config | Depends: inner pkg passed through → `PkgCopier`; rebuilt → `PkgCreator` | Depends | — | — (e.g. a VPN client with site config) |
| **5** | Signed vendor `.pkg` at a stable redirect URL | fwlink/redirect URL resolving to a signed `.pkg`; version read from inside it | `PkgCopier` | No | `pattern-5-vendor-pkg-url/` | Microsoft Word *(Acme; template example)* |
| **6a** | Rebuilt: flat payload, no scripts | Existing pkg, source gone, no install scripts | `PkgCreator` | Yes | `pattern-6-rebuilt-package/` | Acme Login Banner. (The template folder's example, AcmeSupport-Legacy, carries install scripts, so it is a 6b.) |
| **6b** | Rebuilt: payload + install scripts | As 6a, but the original has preinstall/postinstall | `PkgCreator` with `scripts:` | Yes | `pattern-6b-rebuilt-payload-scripts/` | AcmeSupport *(Acme)*; Quarantine Helper, AcmeSupport-Legacy (template examples); Fruit screensaver default slice *(Acme)* |
| **6c** | Rebuilt: one file with a specific owner/mode | The payload is a single file with a non-default mode, e.g. `0400` | `PkgCreator` with `chown` `mode:` | Yes | `pattern-6c-rebuilt-single-file/` | Acme Wallpaper *(Acme)*; Audit-Control-Expiry (template example); Orchard Analytics license slice *(Acme)* |
| **6d** | Rebuilt: payloadless, script only | The original package installs no files | `PkgRootCreator` + `PkgCreator`, empty pkgroot | Yes | `pattern-6d-rebuilt-payloadless/` | Acme UninstallAgent *(Acme; template example)* |
| **7** | Faux vendor DMG, app extracted and rebuilt | Unsigned in-house DMG wrapping a vendor app or binary | `PkgCreator` | Yes | `pattern-7-faux-vendor-dmg/` | Pomelo Studio *(Acme; template example)* |
| **8** | Experimental unsigned `.app` | Dev/internal `.app`, no signed build exists | `PkgCreator` | Yes | — | — (nothing should stay here) |

Notes:

- **Patterns 1–3** are usually generated by Recipe Robot (`bin/rr-batch.sh`), which is
  why they have no templates. 2c and 2d need a hand-written pkg recipe; the live Acme
  recipes under `customer/acme/output/recipes/` (Corkscrews, AcmeFruitCo) are the
  reference.
- **Pattern 4** fetches a staged file with `URLDownloader` from a `file://` URI built on
  the `VENDOR_CACHE_ROOT` Input. Pin the version in the download recipe's `Input` unless the
  recipe can read it from the artifact. The shared rules are in recipe-standards §6.2.4.
- **Pattern 6** starts from `sudo bin/pkg-reverse.sh` then
  `bin/blueprint-to-recipe.sh`; the templates are for adjusting an extraction by hand.
  Check the rebuild with `bin/pkg-compare.sh`.
- **Pattern 7** is separate from 4c because the DMG isn't a vendor artifact and its
  wrapper has no signature. Check community recipes first (recipe-standards §6.10.2).
- **Pattern 8** recipes must record the approver, approval date and resolution plan in
  their `README.md` (recipe-standards §6.7 item 8).
- If a vendor-drop app is also publicly downloadable, prefer 3b for the app and ship
  the ridealong as its own slice (recipe-standards §6.10.1).
- **Slice by default.** Anything the org adds to a vendor's app (license, config,
  LaunchAgent, scripts) goes in its own recipe, usually 6c (one file) or 6b/6d
  (LaunchAgent and script), installed after the app's package.
  - **Required** when the vendor artifact is a sealed, signed `.pkg` deployed as-is
    (1a, 2a, 3a, 4a, 4b, 5, or the pass-through case of 4e): a sealed package is
    never opened.
  - **Preferred** when we rebuild the app (DMG, `.app` or ZIP holding just the app): a
    slice that drops the file in is far simpler than rebuilding the app package
    around it on every update.
  - The same-package ridealong variants (2c, 4d, 4e when rebuilt) are the
    **exception**, for an extra that can't work as a separate package. See
    [`build-your-first-recipe.md`](build-your-first-recipe.md) step 3 and
    recipe-standards §6.10.1.

## Code-signature decision tree

Work through the steps in order. Full rules: recipe-standards §6.7 item 5 and §3.7.

1. **Check the outer artifact.** If the download is a `.pkg`, run
   `pkgutil --check-signature` (never `codesign`, which doesn't understand flat-pkg
   signing). If it's signed, use `expected_authority_names` with the full
   three-entry chain.
2. **Check inside for a signed `.app`.** If the download is a DMG, archive, or an
   unsigned pkg with an `.app` inside, extract it and run `codesign -dvv`. If it's
   signed, use the `requirement` string extracted with
   `codesign --display --requirements -` (recipe-standards §6.5). Never hand-author it.
3. **Pattern carve-outs.** Patterns 6 and 7 may contain no `.app` at all: declare
   `NO_CODE_SIGNATURE_REQUIRED: true` with a comment saying why. Pattern 8 is the
   only carve-out for an unsigned `.app`, and needs approver documentation.

An unsigned wrapper doesn't make its contents unsigned. Step 2 still applies to a
signed `.app` inside a rebuilt or faux-DMG payload
([methodology lesson 16](../reference/methodology.md)). When nothing is signed, the
declared `NO_CODE_SIGNATURE_REQUIRED` satisfies lint rules CSV-001 and CSV-005. When an
app is ad-hoc signed (verified, but with no team ID), set `teamid: "UNSIGNED_NO_TEAMID"`
in the download recipe's `Input` with a comment saying why; CSV-005 accepts it (see
[KI-2](known-issues.md)).

## Quick reference

```
Vendor gave you a flat signed .pkg, no URL ......... Pattern 4a
Vendor gave you a distribution .pkg, no URL ........ Pattern 4b
Vendor publishes a signed .pkg at stable URL ...... Pattern 5
Vendor gave you a .dmg containing a .app ......... Pattern 4c/4d
  With ridealong scripts/payload ................. 4d
  Without ........................................ 4c
Vendor gave you a ZIP + config ................... Pattern 4e
Stable vendor URL to a DMG ....................... Pattern 3b
Version-in-URL, must scrape the download page .... Pattern 3c
GitHub release with DMG asset .................... Pattern 2b
  Plus org scripts/payload ....................... 2c
  Source ZIP, reassembled ........................ 2d
Sparkle appcast with DMG asset ................... Pattern 1b
Built package exists, source does not ............ Pattern 6 (a-d)
  Flat payload only .............................. 6a
  Payload + scripts .............................. 6b
  Single file with specific mode ................. 6c
  Script-only, no payload ........................ 6d
Snapshot (e.g. Jamf Composer) wrapped as DMG ..... Pattern 7
Unsigned dev .app with no upstream signing ....... Pattern 8 (temporary — must have approver)
```

## Finding the pattern of an existing recipe

- `bin/classify-recipe.sh recipes/<Vendor>/<App>/` reads the recipes and reports the
  label from this page, with its reasoning, and says whether it matches the
  `Comment:` claim. Where the recipes can't settle it (a faux DMG against an unsigned
  vendor DMG, say), it gives its best label, marks it uncertain and names the
  question that decides. Every Acme recipe and template example classifies as it
  claims (`tests/python/test_classify.py`).
- `bin/analyze-package.sh <file.pkg>` recommends a pattern for a package you haven't
  written a recipe for.
- Derive a label from the processors, not from a README or a filename
  ([methodology lesson 26](../reference/methodology.md)).
