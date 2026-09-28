# Recipe Templates

Starting points for new AutoPkg recipes, one directory per pattern. Each directory
holds a placeholder `TEMPLATE.*` set to copy from, and most also hold a filled worked
example to check yourself against.

Pattern definitions, the prefix rule and the code-signature decision tree are in
**[`docs/patterns.md`](../docs/patterns.md)**. This page covers only how to use the
templates.

## Template index

| Directory | Pattern | Output processor | Worked example |
|-----------|---------|------------------|----------------|
| `pattern-4-vendor-drop/` | 4a: vendor-drop flat pkg | `PkgCopier` | `example-Xerox-Drivers/` |
| `pattern-4b-distribution-package/` | 4b: vendor-drop distribution pkg | `Copier` (template); the example uses `PkgCopier`, see below | `example-Xerox-Drivers/` |
| `pattern-4c-vendor-drop-dmg/` | 4c: vendor-drop DMG, rebuilt | `PkgCreator` | — |
| `pattern-4d-vendor-drop-dmg-ridealong/` | 4d: vendor-drop DMG + ridealong | `PkgCreator` with `scripts:` | `example-Kiwi-Capture/` |
| `pattern-5-vendor-pkg-url/` | 5: vendor pkg at a stable URL | `PkgCopier` | `example-Microsoft-Word/` |
| `pattern-6-rebuilt-package/` | 6a: rebuilt, flat payload | `PkgCreator` | `example-AcmeSupport-Legacy/` (has install scripts, so a 6b; the blueprint-to-recipe output shape) |
| `pattern-6b-rebuilt-payload-scripts/` | 6b: rebuilt, payload + scripts | `PkgCreator` with `scripts:` | `example-QuarantineHelper/` |
| `pattern-6c-rebuilt-single-file/` | 6c: rebuilt, single file with a set mode | `PkgCreator` with `chown` `mode:` | `example-Audit-Control-Expiry/` |
| `pattern-6d-rebuilt-payloadless/` | 6d: rebuilt, script only | `PkgRootCreator` + `PkgCreator` | `example-UninstallAgent/` |
| `pattern-7-faux-vendor-dmg/` | 7: faux vendor DMG | `PkgCreator` | `example-Pomelo-Studio/` |

`recipe-comment-examples.yaml` has sample `Comment:` text for each pattern.

There are no templates for Patterns 1–3 or 8. Recipe Robot generates 1–3 through
`bin/rr-batch.sh`; generate, then lint. For 2c and 2d (GitHub release with ridealong
scripts, or a source ZIP), the live Acme recipes under
`customer/acme/output/recipes/` are the reference. Pattern 8 is deliberately not
templated.

**4b is under review.** The "distribution packages crash `PkgCopier`" rationale
behind this template is disputed by `reference/methodology.md` lesson 14, and the 4b
example itself uses `PkgCopier`. Until that's decided, read
[open question (b) in docs/patterns.md](../docs/patterns.md#open-questions) before
picking 4b over 4a.

**Pattern 6 is this kit's addition** to the common AutoPkg shapes. Say "Pattern 6
(rebuilt package)" the first time you use the term outside this repo. It is separate
from Pattern 4 because the work is different: identifier fidelity, install-location
fidelity, installer scripts and file ownership are decisions Pattern 4 never faces,
and three of the four fail silently. See `pattern-6-rebuilt-package/README.md`.

Patterns 6a–6d are normally generated with `sudo bin/pkg-reverse.sh` and then
`bin/blueprint-to-recipe.sh`. Their templates are for adjusting an existing
extraction by hand.

**Pattern 7** is separate from 4c because the DMG is built in-house from a snapshot,
not provided by a vendor, and has no signature on its wrapper. The recipe uses
`Copier` to mount the DMG and extract the `.app` by glob, then `PkgCreator`. If the
wrapped `.app` is vendor-signed, verify it anyway.

## How to use

```bash
mkdir -p <recipe-repo>/recipes/VendorName/AppName
cd <recipe-repo>/recipes/VendorName/AppName

TPL=<toolkit>/templates/pattern-4-vendor-drop
cp "$TPL/TEMPLATE.download.recipe.yaml" AppName.download.recipe.yaml
cp "$TPL/TEMPLATE.pkg.recipe.yaml"      AppName.pkg.recipe.yaml
cp "$TPL/TEMPLATE.README.md"            README.md   # where the template has one
```

Then fill every `REPLACE_*` token and finish the app's `README.md`, including the
publisher's Team ID. Vendor-drop and rebuilt recipes also need a pinned `version`
Input in the download recipe (the template comments say where). No `.overrides` is
needed; it's an optional, org-defined file (Standards §3.4). Find anything you missed:

```bash
<toolkit>/bin/scan-placeholders.sh --repo <recipe-repo> AppName
```

The `REPLACE_` prefix is deliberate: `scan-placeholders.sh` already detects it, so an
unfilled template is caught by tooling rather than by a failed build.

Then check your work:

```bash
<toolkit>/bin/autopkg-preflight.py --repo <recipe-repo> --app <recipe-repo>/recipes/VendorName/AppName
autopkg run ./AppName.pkg.recipe.yaml
```

A clean preflight doesn't replace a real `autopkg run`. Every lesson in
`reference/methodology.md` passed review and was only found by running.

If the recipe verifies no signature (Patterns 6 and 7, or a genuinely unsigned
vendor file), declare `NO_CODE_SIGNATURE_REQUIRED: true` in `Input` with a comment.
If a signed `.app` is inside, verify it anyway. If an app is ad-hoc signed (no team
ID), verify it with an identifier-only requirement and set
`teamid: "UNSIGNED_NO_TEAMID"` in `Input` with a comment saying why.

## Vendor cache path

Pattern 4 templates ship with `../../../build/vendor_cache/`, the layout
`reference/recipe-standards.md` documents for a production repo. A local repo
created with `init-recipe-repo.sh --vendor-cache vendor_cache` uses
`../../../vendor_cache/` instead. Edit `VENDOR_CACHE_ROOT` (or `LOCAL_FILE_PATH`) to
match the repo you are writing into, or let `blueprint-to-recipe.sh --vendor-cache`
do it.

Either way it is three levels up from `recipes/<Vendor>/<App>/`. Only the segment
after that varies.

## Vendor cache normalization

Vendor-drop templates (Patterns 4a–4d, 7) stage files in `build/vendor_cache/`.
After dropping a new vendor file into the cache, run
`bin/normalize-vendor-cache.sh` to rename it to the canonical name the recipe
expects:

```bash
bin/normalize-vendor-cache.sh --repo <repo> --vendor-cache <repo>/build/vendor_cache/
```

The canonical names are defined in `vendor-drop-registry.yaml` at the recipe repo
root. The script renames only files of the canonical name's type and moves stale
extras aside to `<vendor-cache>/relocated/`; add `--dry-run` to preview. Details:
[`docs/normalize-vendor-cache.md`](../docs/normalize-vendor-cache.md).

## Test whether a URL is genuinely stable

```bash
curl -sLI "<url>" | grep -i '^location:'
```

A redirect that resolves to "latest" is stable (Pattern 3b, or 5 for a pkg). A
version baked into the path isn't stable. That's Pattern 3c: scrape the link with
`URLTextSearcher`, or pin a `VERSION` Input and template `%VERSION%` into the URL.

## Expected lint findings

Run `bin/recipe-linter.sh --dir templates`. The worked `example-*/` recipes have no
FAIL or WARN findings. VER-001 and CSV-001 no longer false-fail pinned-version or
unsigned recipes (KI-2). Everything that still appears is either expected or a known
linter gap:

| Rule | Where | Why | Status |
|------|-------|-----|--------|
| `VER-001` | `TEMPLATE.download.recipe.yaml` in 4, 4b, 6, 6b, 6c, 6d | No version source until you add the pinned `version` Input | Expected; clears once filled |
| `CMT-002` / `CMT-003` (WARN) | Most `TEMPLATE.*` recipes | No `Comment`, or one that doesn't start with "Pattern N" | Fill it in from `recipe-comment-examples.yaml` |
| `PKG-001` / `PRO-001` | `TEMPLATE.pkg.recipe.yaml` in 5, 6, 6b, 6c, 6d | The rule matches the word `AppPkgCreator` in the template's "do not add AppPkgCreator" comment | Linter false positive (untracked) |
| `PKG-002` | 4b `TEMPLATE.pkg.recipe.yaml` | The prefix rule is enforced even on `Copier`/`PkgCopier` recipes | Rule gap; KI-13 |
| `SRC-003`, `DIR-001` (INFO) | Every template and example | Only `URLDownloader` with no dynamic provider (expected for `file://` and fwlink URLs); nothing in `templates/` sits under `<Vendor>/<App>/` | Informational; KI-2 (SRC-003 message) |

Don't change a correct recipe just to silence a rule gap.

## Copying from an existing recipe

Lint it first. A recipe being in production doesn't make it a good example. The most
common inherited defect: Recipe Robot emits download identifiers of the form
`com.acmefruit.autopkg.pkg.download.AppName`. The standard is
`com.acmefruit.autopkg.download.AppName`, and the linter flags the wrong form as
`IDN-003`. The Microsoft-Word example uses the correct form.

## Known duplication

`blueprint-to-recipe.sh` writes its recipes from inline heredocs rather than filling
the Pattern 6 templates, so the two describe the same structure in two places and can
drift. This is the same kind of problem as the duplicate digest implementation that
`specs/manifest/01-manifest.md` FR-01 prohibits. It's unresolved. The fix is to have
the generator fill the template, which also means including `templates/` in dist
builds.
