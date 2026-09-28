# Getting started

Set up the kit, then take a 15-minute tour of what it does, using
`customer/acme/`: the worked example for Acme Fruit Co., a fictional org. Every
step below is a command you can paste into a terminal at the root of this repo.

## Prerequisites

**Recommended: install these four apps.**

| App | Why |
|---|---|
| [AutoPkg](https://github.com/autopkg/autopkg/releases) ≥ 2.3 | Runs the recipes. Its bundled Python runs the kit's Python tools. |
| [Recipe Robot](https://github.com/homebysix/recipe-robot) | Drafts a first recipe from a download URL or an app (Lane A, `bin/rr-batch.sh`). |
| [Suspicious Package](https://www.mothersruin.com/software/SuspiciousPackage/) | Opens a `.pkg` without installing it: files, scripts, signature, notarization. |
| [Apparency](https://www.mothersruin.com/software/Apparency/) | The same for an `.app`: signature, Team ID, notarization, entitlements. |

Suspicious Package and Apparency (both from Mothers Ruin Software) are a **second
opinion**: whatever the kit's scripts report about a package or app, check it by eye
in one of them.

**Strongly recommended: a local copy of the AutoPkg wiki.**

```bash
git clone https://github.com/autopkg/autopkg.wiki.git reference/autopkg-wiki
```

The kit doesn't ship it, but its docs and agent rules look processors up there
(`reference/autopkg-wiki/Processor-<Name>.md`). If you work with a coding agent,
this is what stops it guessing at a processor's arguments. Git ignores the folder;
refresh it with `git -C reference/autopkg-wiki pull`.

In detail, including what else a task may need:

| Need | For | Notes |
|---|---|---|
| macOS | everything | The inspection tools use `pkgutil`, `hdiutil`, `codesign`, `stat -f`. |
| [AutoPkg](https://github.com/autopkg/autopkg/releases) ≥ 2.3 | running recipes, and its Python for the tools | The recipes declare `MinimumVersion: "2.3"`. Tested with 2.9. |
| AutoPkg's bundled Python | every Python tool (`bin/*.py`, `guardrails/audit/`, the `analyze-*` and `inspect-*` scripts, the vendor-cache scripts) | Comes with AutoPkg at `/usr/local/autopkg/python` and always has PyYAML. Nothing to install. |
| Suspicious Package and Apparency | checking packages and apps by eye | A second opinion on what our scripts report. |
| Recipe Robot | Lane A (`bin/rr-batch.sh`), first drafts | Recommended. The kit's own tools work without it. |
| `shellspec` ≥ 0.28.1, `shellcheck` | contributing to the kit | The test suite runs under `/bin/bash` 3.2 (see `.shellspec`). |

The linter, `bin/recipe-linter.sh`, needs only AutoPkg's Python. To lint in CI where
AutoPkg isn't installed, set `AUTOPKG_TOOLKIT_PYTHON` to any Python 3.10+ that has
PyYAML (`pip install pyyaml`).

The Python tools run AutoPkg's own interpreter, never whatever `python3` is first on
your `PATH` (Apple's `/usr/bin/python3` has no PyYAML). To use a different
interpreter — a venv, say — point `AUTOPKG_TOOLKIT_PYTHON` at it; `requirements.txt`
lists what it needs.

Org naming (identifier prefix `com.acmefruit.autopkg`, package prefix `Acme_`)
comes from [`config/org.yaml`](../config/org.yaml). The tour uses those defaults
unchanged. When you make the kit your own, see [forking.md](forking.md).

## Two lanes

The kit supports two ways to produce recipes (the [README](../README.md) has the
details):

- **Lane A, batch generation**: for apps with a real download URL. It feeds a
  CSV of apps to Recipe Robot, then lints the results:
  `bin/rr-batch.sh -i apps.csv --log-dir ./logs -o ./out --lint`
  (CSV columns: `"Status","Vendor","AppName","URL"`).
- **Lane B, hands-on**: for vendor-drop recipes (Pattern 4), where the
  installer is a local file you were sent, and for rebuilt in-house packages.
  This lane follows [`reference/methodology.md`](../reference/methodology.md)
  and the per-package workflow in
  [`specs/method/00-methodology.md`](../specs/method/00-methodology.md).

The tour covers the tools both lanes share and ends with a Lane B plan.

## The tour

### 1. Lint the example recipe repo

`customer/acme/output` is laid out as a recipe repo (it has `recipes/`), so
every front end accepts it as `--repo`:

```bash
bin/recipe-linter.sh --repo customer/acme/output --pair-check
```

What you should see (colour codes and most recipes left out):

```text
AutoPKG Recipe Linter (config-driven) — using specs from: …/config/checks.yaml
  org naming from: …/config/org.yaml
  27 rules loaded

═══ Checking download/pkg recipe pairs in: …/customer/acme/output/recipes

  ✓ All recipe pairs are complete

═══ Checking: …/recipes/OrchardLabs/Orchard-Analytics/Orchard-Analytics.download.recipe.yaml
  [INFO] SRC-003: Only URLDownloader present (no Sparkle/GitHub/URLTextSearcher) — verify with curl -LI
  [INFO] DIR-001: Recipe 'Orchard-Analytics.download.recipe.yaml' should be placed under <VendorName>/<AppName>/ hierarchy
  0 errors, 0 warnings, 2 info
…
✓ All 16 recipe(s) passed lint checks
```

`bin/recipe-linter.sh --customer acme --pair-check` lints the same repo, since a
customer's recipe repo is its `output/` folder. To make Acme the default customer,
start your customer registry from the example (git ignores the real one, so it stays
yours):

```bash
cp config/customers.example.yaml config/customers.yaml
```

Then plain `bin/recipe-linter.sh --pair-check`, from any directory that isn't itself
a recipe repo, lints Acme too. The header then gains a
`customer: acme (…/customer/acme)` line.

`[INFO]` lines are advice; they never fail a run. Only errors do, and the exit
code is non-zero when there are any. (`DIR-001` currently prints on every recipe,
even ones that are correctly placed. Ignore it.)

### 2. Read a recipe pair

Moonlight is the reference example for the most common shape: a DMG you open
and drag to Applications (Pattern 2b).

```bash
ls customer/acme/output/recipes/MoonlightGameStreaming/Moonlight/
cat customer/acme/output/recipes/MoonlightGameStreaming/Moonlight/README.md
cat customer/acme/output/recipes/MoonlightGameStreaming/Moonlight/Moonlight.download.recipe.yaml
cat customer/acme/output/recipes/MoonlightGameStreaming/Moonlight/Moonlight.pkg.recipe.yaml
```

The directory has three files:

- a **download recipe**: finds the newest GitHub release, downloads the DMG, and
  checks the app's code signature.
- a **pkg recipe**: copies the app into a package root and builds the package
  with `PkgCreator`.
- a **README**: explains what the recipe does, its signature, and how to update
  it.

Every recipe in the kit comes as a download/pkg pair with a README.

The identifiers (`com.acmefruit.autopkg.download.Moonlight`,
`com.acmefruit.autopkg.pkg.Moonlight`) and the package name (`Acme_%NAME%`)
follow `config/org.yaml`. Lint rules IDN-001, IDN-002 and PKG-002 enforce that.

### 3. Run it (optional; downloads about 60 MB)

```bash
autopkg run -v --search-dir customer/acme/output/recipes \
  customer/acme/output/recipes/MoonlightGameStreaming/Moonlight/Moonlight.pkg.recipe.yaml
```

`--search-dir` lets AutoPkg find the parent download recipe by its identifier.
AutoPkg then does the following:

1. It resolves the latest release and downloads `Moonlight-<version>.dmg`.
2. It verifies the signature against team `45U78722YL`.
3. It reads the version from the app bundle and builds the package.

The run ends with AutoPkg's "The following packages were built" summary. The
package lands at:

```text
~/Library/AutoPkg/Cache/com.acmefruit.autopkg.pkg.Moonlight/Acme_Moonlight.pkg
```

The last recorded live run built 6.1.0. The six **live** recipes in the
[Acme catalogue](../customer/acme/README.md#the-catalogue) all run this way.
The **example** recipes (Orchard Analytics, AcmeSupport) are for fictional apps
and only lint.

### 4. Classify a recipe

```bash
bin/classify-recipe.sh customer/acme/output/recipes/MoonlightGameStreaming/Moonlight
```

The script reads the processor chain and reports which pattern the recipe
follows and why. What you should see (abbreviated):

```text
Recipe: MoonlightGameStreaming/Moonlight

Observed characteristics:
  Source:           GitHub release (%GITHUB_REPO%)
  Pkg processor:    PkgCreator
  Signature:        CodeSignatureVerifier present (requirement — .app signing)

Classification: Pattern 2b

Reasoning:
  First processor is GitHubReleasesInfoProvider → GitHub release asset
  PkgCreator without scripts or empty pkgroot → flat payload rebuild → variant b
  Output naming: Acme_%NAME% prefix expected (PkgCreator rule — rebuilt package)
```

A detailed breakdown of every processor step follows. The script's variant
letters don't always agree with the letters in [patterns.md](patterns.md)
([KI-14](known-issues.md)).

### 5. Analyse a package

Point `bin/analyze-package.sh` at any `.pkg`, such as the one step 3 built.
`--customer acme` loads the hints in
[`customer/acme/clues.yaml`](../customer/acme/clues.yaml):

```bash
bin/analyze-package.sh \
  ~/Library/AutoPkg/Cache/com.acmefruit.autopkg.pkg.Moonlight/Acme_Moonlight.pkg \
  --customer acme
```

What you should see (abbreviated):

```text
=== Package metadata ===
  Identifier:   com.acmefruit.pkg.Moonlight
  Version:      6.1.0
  Install loc:  /
  Kind:         component
  Signature:    unsigned

=== Classification ===
  Origin:       custom-build
  Confidence:   medium
  Pattern:      6
  Rationale:
- Identifier 'com.acmefruit.pkg.Moonlight' is in the org's own namespace (com.acmefruit) — built in-house
- Identifier contains an org code
- Package is unsigned — cannot confirm vendor by cert
- Filename contains org code
- Payload contains .app bundles: Moonlight.app

=== Payload summary ===
  Files:        892
  Apps found:   Moonlight.app

=== Heuristic notes ===
- clues source: …/customer/acme/clues.yaml
- vendor strong=0 medium=1 custom strong=1 medium=3 low=0
```

The package is Acme's own rebuild, and the tool says so: an identifier in the
org's own `com.acmefruit.*` namespace counts as in-house. The verdict is still a
heuristic, so read the rationale, not only the verdict. The tool is built for
packages you inherit, where the question is whether a vendor or someone in-house
built them. See
[package-analysis.md](package-analysis.md).

To match a folder of received vendor files against the catalogue, use the
companion tool, which reads
[`customer/acme/end_result.yaml`](../customer/acme/end_result.yaml):

```bash
bin/analyze-materials.sh customer/acme/input --customer acme
```

On a fresh clone `input/` holds only its README, so the script lists every
catalogue target with `(0 candidates)`. Drop a few installers in and run it
again to see matches.

### 6. Browse a template

Every pattern has a template directory. Each one holds placeholder `TEMPLATE.*`
files to copy and a filled worked example to check yourself against:

```bash
cat templates/README.md
ls templates/pattern-4d-vendor-drop-dmg-ridealong/
```

[patterns.md](patterns.md) defines every pattern (2b, 3c, 4d, 6b …) and helps you
choose one.

### 7. Read a plan of attack

In Lane B, every package starts with a written plan before any recipe is
drafted:

```bash
cat customer/acme/plans/orchard-analytics.md
```

Orchard Analytics is fictional, but the plan follows the real process. It covers:

- what the vendor sent;
- why that makes it Pattern 4d (a vendor DMG plus a license file that rides along);
- where the file modes came from;
- what the signature check needs;
- a checklist of the remaining steps.

The front matter is machine-readable; see [FORMATS.md §6](FORMATS.md#6-customernameplansappnamemd-plan-of-attack).

### 8. Where next

- [build-your-first-recipe.md](build-your-first-recipe.md): **the walkthrough for
  turning a package you've been handed into a recipe**, with decision flowcharts.
- [customer-contract.md](customer-contract.md): what goes in `customer/<name>/`
  and which tool reads each file.
- [forking.md](forking.md): making the kit your org's own, and keeping up with
  upstream.
- [FORMATS.md](FORMATS.md): schemas for every customer data file.
- [`specs/method/00-methodology.md`](../specs/method/00-methodology.md): the
  per-package workflow.
- [`reference/methodology.md`](../reference/methodology.md): lessons learned the
  hard way.
- [`reference/recipe-standards.md`](../reference/recipe-standards.md): the
  standards the linter enforces.
- [glossary.md](glossary.md): terms used throughout the docs.
