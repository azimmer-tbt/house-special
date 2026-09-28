# House Special — Usage Guide

A developer's guide to the toolkit: setup, the tools by task, and an end-to-end
walkthrough. The toolkit covers every recipe pattern, but it's strongest on the
vendor-drop (Pattern 4) and rebuilt-package (Pattern 6) work that Recipe Robot can't
do. Terms are defined in the [glossary](glossary.md).

---

## 1. Installation / Setup

### Clone requirements

Clone the toolkit beside your AutoPkg recipe repo. It operates **from outside** the
recipe repo, not inside it.

```
your-project/
├── house-special/             # ← this toolkit
└── autopkg-recipes/           # ← your recipe repo (recipes/, build/, etc.)
```

To try the tools first, use the worked example in
[`customer/acme/output/`](../customer/acme/README.md) as the recipe repo.

### Dependencies

| Dependency | Required for | Notes |
|------------|-------------|-------|
| `autopkg` | Running recipes | macOS only |
| bash 3.2+ | Linter and bash front ends | The linter (`bin/recipe-linter.sh`) must run on stock macOS bash |
| AutoPkg's Python (`/usr/local/autopkg/python`) | Every Python tool | Bundled with AutoPkg, includes PyYAML; override with `AUTOPKG_TOOLKIT_PYTHON` |
| `pkgutil`, `codesign`, `hdiutil` | Analysis tools | Ship with macOS |
| `shellspec` | Running the test suite | Only for toolkit development |

### Environment variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `AUTOPKG_TOOLKIT_REPO` | Default recipe repo for every front end | `~/Developer/autopkg-recipes` |
| `AUTOPKG_TOOLKIT_ORG` | Alternative org config file (default `config/org.yaml`) | `~/myorg/org.yaml` |
| `AUTOPKG_TOOLKIT_CUSTOMER` | Customer for the linter, preflight and `run-recipes.sh` (like `--customer`; the analysis tools and `check-sanitized.sh` take `--customer` only) | `widgets` |
| `AUTOPKG_TOOLKIT_CUSTOMERS` | Alternative customer registry (default `config/customers.yaml`) | `~/myorg/customers.yaml` |

Org naming (identifier prefix, package-name prefix) comes from
[`config/org.yaml`](../config/org.yaml). A fork edits that one file. A kit serving
several orgs registers them in `config/customers.yaml` instead (gitignored; start it
from [`config/customers.example.yaml`](../config/customers.example.yaml);
[FORMATS §10](FORMATS.md#10-configcustomersyaml-the-customer-registry)).

---

## 2. The Frontend Contract

> Toolkit assets resolve from the script's own location. Work targets resolve
> from `--repo`. The current working directory is never load-bearing.

The recipe repo is resolved from `--repo <path>`, then `$AUTOPKG_TOOLKIT_REPO`, then
the current directory, but only if it contains `recipes/`. The linter, preflight and
`run-recipes.sh` check the selected customer's recipe repo before the current directory: from
`--customer`, `$AUTOPKG_TOOLKIT_CUSTOMER`, or the registry's `default` (Acme, as
shipped). If none of these resolve,
the tool fails loudly and names every remedy. It never guesses. The one deliberate
exception is `bin/clear-autopkg-cache.sh`, which takes no `--repo` because its safety
rests on a hard-coded cache root.

Full rules: [`specs/toolkit/00-constitution.md`](../specs/toolkit/00-constitution.md).

---

## 3. Quick Start — End-to-End Walkthrough

### Step 1: Analyze a package

```bash
bin/analyze-package.sh /path/to/package.pkg --customer acme --output json
```

This classifies the package as vendor-built or custom-built, recommends a pattern,
and extracts metadata (identifier, version, signature, install location).

### Step 2: Choose a pattern

Use the Quick Reference in [`docs/patterns.md`](patterns.md#quick-reference). As a
rule of thumb, a signed vendor pkg with no URL is Pattern 4, a vendor pkg at a stable
URL is Pattern 5, and an existing package whose source is gone is Pattern 6.

### Step 3: Build a recipe

**From a template** (Patterns 4, 5, 7). Copy the template set and fill every
`REPLACE_*` token:

```bash
TPL=<toolkit>/templates/pattern-4-vendor-drop
mkdir -p <repo>/recipes/Vendor/App
cp "$TPL/TEMPLATE.download.recipe.yaml" <repo>/recipes/Vendor/App/App.download.recipe.yaml
cp "$TPL/TEMPLATE.pkg.recipe.yaml"      <repo>/recipes/Vendor/App/App.pkg.recipe.yaml
cp "$TPL/TEMPLATE.README.md"            <repo>/recipes/Vendor/App/README.md
bin/scan-placeholders.sh --repo <repo> App
```

**Pattern 6**: use the reverse-engineering pipeline. `sudo` is required, or the
extracted ownership is wrong:

```bash
sudo bin/pkg-reverse.sh /path/to/package.pkg --dest <repo>/build/vendor_cache/Vendor/
bin/blueprint-to-recipe.sh --blueprint <blueprint.conf> --out <repo>/recipes/Vendor/App
```

**Patterns 1–3**: generate with Recipe Robot through `bin/rr-batch.sh` (Lane A), then
lint.

### Step 4: Check and run

```bash
bin/autopkg-preflight.py --repo <repo> --app <repo>/recipes/Vendor/App
autopkg run -v <repo>/recipes/Vendor/App/App.pkg.recipe.yaml
```

The preflight runs the guardrail audits and then the linter. A clean preflight
doesn't replace a real `autopkg run`.

### Step 5: Validate a rebuild

```bash
bin/pkg-compare.sh --old-pkg /path/to/original.pkg \
    --new-pkg ~/Library/AutoPkg/Cache/com.acmefruit.autopkg.pkg.App/Acme_App.pkg
```

Exit code 0 = pass. Non-zero = investigate the mismatch.

### Step 6: Verify the handoff (before any cross-session handoff)

```bash
bin/generate-manifest.sh        # regenerates manifest.sha256
bin/verify-manifest.sh          # checks on-disk state against the manifest
```

---

## 4. Available Tools by Task

### Analysis

| Tool | What it does | Command |
|------|-------------|---------|
| [`analyze-package.sh`](../bin/analyze-package.sh) | Classify a `.pkg` as vendor/custom, recommend a pattern | `bin/analyze-package.sh file.pkg --customer acme --output json` |
| [`analyze-materials.sh`](../bin/analyze-materials.sh) | Match vendor source files against target recipes | `bin/analyze-materials.sh /source --customer acme` |
| [`inspect-dmg.sh`](../bin/inspect-dmg.sh) | Mount a DMG, list contents, extract app versions | `bin/inspect-dmg.sh file.dmg` |
| [`inspect-app.sh`](../bin/inspect-app.sh) | Extract metadata from an `.app` bundle | `bin/inspect-app.sh App.app --output json` |
| [`inspect-archive.sh`](../bin/inspect-archive.sh) | List zip/tar contents without extracting | `bin/inspect-archive.sh file.zip` |
| [`capture-perms.sh`](../bin/capture-perms.sh) | Snapshot ownership/permissions of a tree | `bin/capture-perms.sh /path --output json --relative` |
| [`classify-recipe.sh`](../bin/classify-recipe.sh) | Report the pattern of an existing recipe from its YAML | `bin/classify-recipe.sh recipes/Vendor/App/` |

Details: [`docs/package-analysis.md`](package-analysis.md),
[`docs/material-analysis.md`](material-analysis.md). `classify-recipe.sh` reports the
labels in [`patterns.md`](patterns.md) and compares them with each recipe's `Comment:`.

### Build

| Tool | What it does | Command |
|------|-------------|---------|
| [`pkg-reverse.sh`](../bin/pkg-reverse.sh) | Expand an existing flat `.pkg` into a working tree + blueprint | `sudo bin/pkg-reverse.sh file.pkg --dest vendor_cache/Vendor/` |
| [`blueprint-to-recipe.sh`](../bin/blueprint-to-recipe.sh) | Draft a recipe pair from a blueprint | `bin/blueprint-to-recipe.sh --blueprint bp.conf --out recipes/V/App` |
| [`init-recipe-repo.sh`](../bin/init-recipe-repo.sh) | Create a new recipe repo with the standard layout | `bin/init-recipe-repo.sh --vendor-cache vendor_cache` |
| [`rr-batch.sh`](../bin/rr-batch.sh) | Batch-generate recipes with Recipe Robot (Lane A) | `bin/rr-batch.sh -i apps.csv --log-dir ./logs -o ./out --lint` |

### Validation

| Tool | What it does | Command |
|------|-------------|---------|
| [`recipe-linter.sh`](../bin/recipe-linter.sh) | Config-driven YAML linting (identifiers, naming, prefix, signature, version) | `bin/recipe-linter.sh --repo <repo> --pair-check` |
| [`autopkg-preflight.py`](../bin/autopkg-preflight.py) | Guardrail audits + linter for one app or a whole repo | `bin/autopkg-preflight.py --repo <repo> --app <app-dir>` |
| [`scan-placeholders.sh`](../bin/scan-placeholders.sh) | Find unfilled `REPLACE_*` tokens | `bin/scan-placeholders.sh --repo <repo> AppName` |
| [`pkg-compare.sh`](../bin/pkg-compare.sh) | Compare original vs rebuilt package (inventory, perms, scripts) | `bin/pkg-compare.sh --old-pkg a.pkg --new-pkg b.pkg` |
| [`run-recipes.sh`](../bin/run-recipes.sh) | Real-run harness | `bin/run-recipes.sh --repo <repo> --clear-cache` or `--customer <name>` |

`bin/recipe-linter.sh --list-rules` prints every rule. VER-001, CSV-001 and CSV-005
accept a version pinned in `Input`, a declared `NO_CODE_SIGNATURE_REQUIRED: true`, and
`teamid: "UNSIGNED_NO_TEAMID"` in `Input` respectively, so vendor-drop and unsigned
recipes don't false-fail them. The remaining rule gaps are in KI-2 and KI-13.

### Vendor cache and handoff

| Tool | What it does | Command |
|------|-------------|---------|
| [`normalize-vendor-cache.sh`](../bin/normalize-vendor-cache.sh) | Rename staged vendor files to their registry names; move stale ones aside to `relocated/` | `bin/normalize-vendor-cache.sh --repo <repo> --vendor-cache <path> [--dry-run]` |
| [`sync-vendor-cache.sh`](../bin/sync-vendor-cache.sh) | Copy indexed files from a durable source into a vendor cache, keeping timestamps | `bin/sync-vendor-cache.sh [--dry-run] files_to_copy.yaml <from> <to>` |
| [`generate-manifest.sh`](../bin/generate-manifest.sh) | Regenerate `manifest.sha256` | `bin/generate-manifest.sh` |
| [`verify-manifest.sh`](../bin/verify-manifest.sh) | Verify on-disk state against `manifest.sha256` | `bin/verify-manifest.sh` |

### Utilities

| Tool | What it does | Command |
|------|-------------|---------|
| [`clear-autopkg-cache.sh`](../bin/clear-autopkg-cache.sh) | Safety-checked cache clearer | `bin/clear-autopkg-cache.sh <identifier>...` |
| [`check-sanitized.sh`](../bin/check-sanitized.sh) | Scan the tree for org-specific content before it goes upstream; each customer's `.leak-patterns` applies outside its own folder | `bin/check-sanitized.sh --path docs`, `--customer <name>`, `--all-customers` |
| [`make-dist.sh`](../bin/make-dist.sh) | Build a function-only copy for another repo | `bin/make-dist.sh --tar` |

---

## 5. Recipe Patterns

A pattern label is a number (the source: Sparkle, GitHub, direct URL, vendor drop,
vendor pkg URL, rebuilt, faux DMG, experimental) plus a per-pattern letter (the
variant, e.g. `4b` distribution pkg, `6c` single file). The output package gets the
`Acme_` prefix only when `PkgCreator` builds it. All definitions, the prefix rule, the
code-signature decision tree and the Quick Reference are in
**[`docs/patterns.md`](patterns.md)**.

One check people get wrong: `codesign` doesn't understand flat-pkg signing, so use
`pkgutil --check-signature` for any `.pkg`.

---

## 6. The Per-Package Workflow

Work through each package in eight steps: CSV inventory → analyze the on-server
package → set the target → plan (easy wins first) → build → `autopkg run` → debug →
`pkg-compare`. Answer the Q1–Q5 research questions in a plan of attack at
`customer/<name>/plans/<App>.md` before writing the recipe.

Details, including the plan front-matter format:
[`specs/method/00-methodology.md`](../specs/method/00-methodology.md). Overview:
[`docs/round-trip-workflow.md`](round-trip-workflow.md). Example plan:
[`customer/acme/plans/orchard-analytics.md`](../customer/acme/plans/orchard-analytics.md).

---

## 7. Templates

`templates/` has one directory per pattern. Each directory holds `TEMPLATE.*` files
with `REPLACE_*` tokens, and most also hold a filled `example-*/` to check yourself
against. Which template to use, the vendor-cache path depth, and the expected lint
findings are in [`templates/README.md`](../templates/README.md).

---

## 8. Pitfalls, Guardrails and the Vendor Cache

- **Pitfalls.** [`reference/methodology.md`](../reference/methodology.md) has 27
  lessons from real recipe runs. Read it before guessing at a failure. The most
  common mistakes are wrong vendor-cache path depth (count three levels), opening a
  download recipe with `PathDeleter`, referencing `%pathname%` after `Copier`,
  incomplete `expected_authority_names` chains, and a missing `Input` declaration for
  a `%variable%`.
- **Guardrails.** [`guardrails/CHECKLIST.md`](../guardrails/CHECKLIST.md) lists the
  must-haves that `bin/autopkg-preflight.py` enforces, plus the good-to-haves and
  footguns that need a human eye. For how to run the audit in a session, see
  [`guardrails/EXECUTION.md`](../guardrails/EXECUTION.md).
- **Vendor cache.** Vendor files arrive with unpredictable names.
  `bin/normalize-vendor-cache.sh` renames them to the canonical names in the recipe
  repo's `vendor-drop-registry.yaml`. It renames only files of the canonical name's
  type, leaves `protected_files` alone, and moves stale extras aside to `relocated/`
  rather than deleting them (`--dry-run` to preview). Configuration and usage:
  [`docs/normalize-vendor-cache.md`](normalize-vendor-cache.md).

Two footguns that cost the most time: AutoPkg's cache persists between runs, so clear
it (`bin/clear-autopkg-cache.sh`) before deciding a fix didn't work. And work outside
OneDrive/iCloud folders, which cause misleading file-visibility failures.

---

## 9. Testing the Toolkit

The test suite is ShellSpec, in [`tests/`](../tests/). It runs under `/bin/bash`
3.2, the same shell stock macOS has:

```bash
shellspec                                   # whole suite (config in .shellspec)
shellspec tests/org_config_spec.sh         # one file
```

Known coverage gaps are listed under KI-11.

---

## 10. Getting Help

| Topic | Document |
|-------|----------|
| Toolkit overview, Lane A / Lane B | [`README.md`](../README.md) |
| Terms | [`docs/glossary.md`](glossary.md) |
| Pattern definitions | [`docs/patterns.md`](patterns.md) |
| Recipe standards (the "Standards §" citations) | [`reference/recipe-standards.md`](../reference/recipe-standards.md) |
| Lessons from real recipe runs | [`reference/methodology.md`](../reference/methodology.md) |
| 8-step per-package workflow | [`specs/method/00-methodology.md`](../specs/method/00-methodology.md) |
| Package classification | [`docs/package-analysis.md`](package-analysis.md) |
| Material analysis | [`docs/material-analysis.md`](material-analysis.md) |
| Updating existing recipes | [`docs/updating-existing-recipes.md`](updating-existing-recipes.md) |
| Templates | [`templates/README.md`](../templates/README.md) |
| Guardrails checklist | [`guardrails/CHECKLIST.md`](../guardrails/CHECKLIST.md) |
| Agent setup | [`docs/agent-integration.md`](agent-integration.md) |
| Worked example customer | [`customer/acme/README.md`](../customer/acme/README.md) |

**Known issues:** [`docs/known-issues.md`](known-issues.md). "KI-n" references in this
guide point there.
