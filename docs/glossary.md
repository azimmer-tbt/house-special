# Glossary

Terms used across the kit's docs, specs and tools, in alphabetical order. Each entry
links to the document that defines it. "Standards" means
[`reference/recipe-standards.md`](../reference/recipe-standards.md).

**AppPkgCreator** — An AutoPkg processor that builds a pkg from an `.app`. **Forbidden**
in this kit: you can't control the output filename. Use `Copier` + `PkgCreator`.
Lint rules PKG-001 / PRO-001; see [patterns.md](patterns.md#the-prefix-rule).

**Blueprint** — The `blueprint.conf` file `bin/pkg-reverse.sh` writes next to an
extracted package (name, version, identifier, install location, scripts).
`bin/blueprint-to-recipe.sh` drafts a recipe pair from it. Check its values against
the payload ([methodology lesson 22](../reference/methodology.md)).

**CodeSignatureVerifier** — The AutoPkg processor in every download recipe that checks
the download's signature, using a `requirement` string for an `.app` or
`expected_authority_names` for a `.pkg`. Standards §3.7;
[decision tree](patterns.md#code-signature-decision-tree).

**Copier** — AutoPkg processor that copies a file or directory, mounting a DMG when the
path contains `.dmg/`. Used to extract apps from DMGs and, in Pattern 4b, to copy a
distribution pkg as-is (no prefix). Methodology lessons 11 and 15.

**Designated requirement** — The code-signing rule an app must satisfy, printed by
`codesign --display --requirements -`. Copy it verbatim into
`CodeSignatureVerifier`'s `requirement`; never hand-author it. Standards §6.5.

**Download recipe / pkg recipe (pair)** — Every app has two recipes:
`<App>.download.recipe.yaml` fetches and verifies the installer;
`<App>.pkg.recipe.yaml` builds or copies the output package. Standards §3.2.

**Easy win** — A package that's fast to do: a sealed vendor package (Pattern 4) or one
with a public download URL (Pattern 5). Done first, in step 4b of
[`specs/method/00-methodology.md`](../specs/method/00-methodology.md).

**EndOfCheckPhase** — An AutoPkg processor marking where `autopkg run --check` stops:
after the download, before verification and packaging. Put it right after the
download step. [AutoPkg wiki](https://github.com/autopkg/autopkg/wiki/Processor-EndOfCheckPhase).

**Identifier prefix** — The reverse-DNS namespace for recipe `Identifier` and
`ParentRecipe` values (`com.acmefruit.autopkg`), giving
`<prefix>.download.<App>` and `<prefix>.pkg.<App>`. Set by `identifier_prefix` in
the org config. Standards §3.3; lint IDN-001 / IDN-002.

**Kit vs customer** — The *kit* is this repo's tools, templates, config and docs. A
*customer* is one org's working area under `customer/<name>/` (catalogue, clues,
plans, recipe repo). The kit never hard-codes customer data. Rules:
[customer-contract.md](customer-contract.md); example:
[`customer/acme/`](../customer/acme/README.md).

**Known issue (KI-n)** — A numbered toolkit bug or gap in
[`docs/known-issues.md`](known-issues.md). Numbers are stable, so specs and docs cite
them.

**Lane A / Lane B** — The two ways of working. **Lane A** is batch generation with
Recipe Robot (`bin/rr-batch.sh`) for apps with a real download URL (Patterns 1–3).
**Lane B** is hands-on work for vendor-drop and rebuilt recipes (Patterns 4–8) and
may assume Python 3. [README](../README.md#two-lanes).

**NO_CODE_SIGNATURE_REQUIRED** — An `Input` key (`true`) that a download recipe
declares, with a comment explaining why, when it has no `CodeSignatureVerifier`.
Allowed for Patterns 6, 7 and 8 and for artifacts that really are unsigned.
Standards §3.7 and §6.7 item 5.

**Org config** — [`config/org.yaml`](../config/org.yaml): the one file a fork edits
to set its org name, identifier prefix, pkgname prefix, internal domain and in-house
vendor folder. Override per run with `--org` or `$AUTOPKG_TOOLKIT_ORG`.

**`.overrides`** — An optional, org-defined `key=value` file next to a recipe pair.
When it exists, `bin/run-recipes.sh` (or your CI job) passes each line to `autopkg run`
as `--key=KEY=VALUE`. Not the same as AutoPkg's own recipe overrides. AutoPkg never
reads it by itself, so a version or anything else a recipe needs goes in `Input`.
Typical use: a pipeline-supplied secret, generated at run time or gitignored, never
committed. Standards §3.4.

**Package-name (pkgname) prefix** — The prefix (`Acme_`) on packages the org builds
with `PkgCreator`, and only those. Set by `pkgname_prefix` in the org config; lint
PKG-002. [The prefix rule](patterns.md#the-prefix-rule).

**ParentRecipe** — The key in a pkg recipe naming the download recipe's identifier.
AutoPkg runs the parent first and shares its variables (including
`%RECIPE_CACHE_DIR%`) with the child.
[AutoPkg wiki](https://github.com/autopkg/autopkg/wiki/Parent-Child-Relationships); methodology
lesson 4.

**Pattern** — A recipe's number + letter classification (source + variant), e.g. `2b`,
`4d`, `6c`. Defined in [patterns.md](patterns.md).

**PkgCopier** — AutoPkg processor that copies a vendor `.pkg` unchanged. The output
keeps the vendor's name (no prefix). Patterns 1a, 2a, 3a, 4a, 5.

**PkgCreator** — AutoPkg processor that runs `pkgbuild` on a pkgroot. The only
processor whose output gets the org prefix. Patterns 1b, 2b–2d, 3b, 3c, 4c, 4d, 6, 7, 8.

**Plan of attack** — The per-package plan written before building a recipe:
`customer/<name>/plans/<App>.md`, with YAML front matter and answers to the Q1–Q5
research questions. Format in
[`specs/method/00-methodology.md`](../specs/method/00-methodology.md); example:
[`orchard-analytics.md`](../customer/acme/plans/orchard-analytics.md).

**Relocated folder** — Where `bin/normalize-vendor-cache.sh` moves stale vendor-cache
files instead of deleting them: `<vendor-cache>/relocated/<Vendor>/<App>/`, the same
tree as the cache, or the folder given with `--relocate-dir`. The default sits inside
the vendor cache, so under `/tmp` it is cleared at reboot.

**Ridealong** — Files the org adds to a vendor's app, packed into the *same* package
(Patterns 2c, 4d, 4e when rebuilt). The **exception**, not the default: use a
**Slice** unless the extra genuinely can't work as a separate package. Never possible
for a sealed vendor `.pkg`. Standards §6.2.4.4.

**Slice** — A separate recipe (and package) for one part of what gets deployed with
an app: its license file, a config file, a LaunchAgent. It installs after the app's
package — it installs *after* whatever creates the folder it writes into. **The
default** for anything the org adds: required when the vendor ships a sealed `.pkg`,
preferred otherwise. Usually Pattern 6c (one file) or 6b/6d. Standards
§6.10.1; walkthrough in [build-your-first-recipe.md](build-your-first-recipe.md).

**Sentinel files** — Zero-byte trigger files in an app directory. `.check_this` asks CI
to watch the public URL for new versions; `.rebuild_this` triggers a rebuild and is
deleted afterwards. Standards §3.6.

**Standards § citation** — A reference such as "Standards §6.7 item 5" to a numbered
section of the recipe standards. Lint rules cite them in `prompted_by:`. Numbers are
stable. Standards "Document conventions".

**Team ID** — The 10-character Apple Developer Team ID in a signature (`subject.OU`).
Enforced by the recipe itself: the requirement string pins it, or
`expected_authority_names` lists the chain. The recipe's README records it for humans.
Standards §3.7.

**UNSIGNED_NO_TEAMID** — The download recipe `Input` value `teamid: "UNSIGNED_NO_TEAMID"`,
set with a comment when the publisher has no team ID (an ad-hoc signed app). Lint rule
CSV-005 accepts it.
[KI-2](known-issues.md).

**Vendor cache / VENDOR_CACHE_ROOT** — Where vendor-drop and rebuilt inputs are staged,
laid out as `<Vendor>/<App>/`. Recipes locate it through the `VENDOR_CACHE_ROOT`
Input, by default `%RECIPE_DIR%/../../../build/vendor_cache`; CI can override it with
`-k`. It isn't a backup ([methodology lesson 24](../reference/methodology.md)).
Standards §6.2.4 and §9.

**Vendor drop** — An installer handed over directly (emailed, behind a login wall, or
built in-house) with no public URL. Staged in the vendor cache; Pattern 4.

**Vendor-drop registry** — `vendor-drop-registry.yaml` at the recipe repo root. It maps
each `<Vendor>/<App>` to the canonical filename its recipe expects.
`bin/normalize-vendor-cache.sh` renames incoming files of the same type to match and
relocates stale ones. [normalize-vendor-cache.md](normalize-vendor-cache.md).
