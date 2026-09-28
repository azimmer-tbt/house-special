# AutoPkg Recipe Standards

This is the standard that this toolkit's linter (`config/checks.yaml`, run by `bin/recipe-linter.sh`) and templates (`templates/`) implement.
It is written for **Acme Fruit Co.**, a fictional organization used as the worked example throughout the toolkit.
Forks adapt it mainly by changing the §3.3 naming values in `config/org.yaml`; the environment, region, and deployment details describe one reasonable setup, not a requirement.

## Document conventions

- **Section citations.** Lint rules (`prompted_by:` in `config/checks.yaml`), specs, and templates cite this document as "Standards §x.y" (for example "Standards §6.7 item 1"). Older text may say "Upstream §x.y" — the numbering is the same. Section numbers are stable and must not be renumbered. "Item N" refers to the numbered sub-headings of the Review Checklist (§6.7).
- **Pattern IDs.** Recipe patterns are named by number + letter (e.g. `4b`, `6c`). The authoritative list is the Master Pattern Table in §6.8.
- **Org-configured values.** Wherever this document shows `com.acmefruit.autopkg`, `Acme_`, `acmefruit.example`, or `AcmeFruitCo`, read "the org's configured value" from `config/org.yaml`:

  | `config/org.yaml` key | Acme Fruit Co. value | Used for |
  |---|---|---|
  | `org_name` | `Acme Fruit Co.` | Display name in generated Descriptions and lint messages |
  | `identifier_prefix` | `com.acmefruit.autopkg` | Recipe `Identifier` / `ParentRecipe` namespace |
  | `pkgname_prefix` | `Acme_` | Prefix for packages the org builds itself (§6.7 item 3) |
  | `internal_domain` | `acmefruit.example` | Internal hosts, addresses, and in-house package identifiers |
  | `vendor_dir` | `AcmeFruitCo` | `vendor_cache/` folder for in-house (org-built) inputs |

- **`XXXXXXXXXX`** in code-signing examples is a placeholder for a real 10-character Apple Developer Team ID.
- **Working copy vs. production repo.** Many orgs keep a development working copy of the recipe repo where new patterns and checklist changes are tried before they reach the production recipe repo that CI builds from. This document describes the production shape; the working copy has the same layout.

---

## 1. Purpose

This standard describes how an organization's local AutoPkg recipes, overrides, build infrastructure, and tooling are laid out and written so that a CI workflow (here, a GitHub Actions "AutoPkg — Build Package" workflow) can build, version, verify, and stage macOS application packages for deployment through an MDM such as Jamf Pro. The recipe repository is the single source of truth for how packages are built.

## 2. Directory Structure

A recipe repository has this shape (`bin/init-recipe-repo.sh` in this toolkit creates it):

```
autopkg/
├── recipes/                        # Recipe source tree (<Vendor>/<App>/)
│   ├── _templates/                 # Optional: starter templates (see this toolkit's templates/)
│   ├── MicrosoftCorporation/
│   │   ├── Microsoft-Word/
│   │   └── …
│   └── AcmeFruitCo/                # In-house apps (vendor_dir from config/org.yaml)
│       └── AcmeSupport/
├── recipe_overrides/               # Override files for community recipes (§7)
├── build/
│   ├── vendor_cache/               # Vendor-provided inputs (Git LFS for large files)
│   │   ├── <Vendor>/<App>/…
│   │   └── AcmeFruitCo/            # In-house inputs
│   └── output/                     # Built .pkg files (.gitignore'd)
├── environments/                   # Per-environment .env files (org-defined, e.g. dev/poc/prod)
├── tools/                          # The repo's own build & lint helpers
└── README.md
```

The vendor cache location is per repo: `build/vendor_cache/` is the default and the layout a CI pipeline expects; a local-only repo may use `vendor_cache/` at the repo root (`init-recipe-repo.sh --vendor-cache vendor_cache`). Recipes locate it through the `VENDOR_CACHE_ROOT` Input (§6.7 item 2), so the choice only has to be consistent within one repo.

## 3. Standards

All recipes must conform to the following standards. The Review Checklist (§6.7) tests against these rules.

### 3.1 Directory Layout

Each app lives under `recipes/<VendorName>/<AppName>/` and contains:

| File | Required | Purpose |
|------|----------|---------|
| `AppName.download.recipe.yaml` | Yes | Downloads (or stages) and verifies the installer |
| `AppName.pkg.recipe.yaml` | Yes | Produces the output .pkg — built with the org prefix, or the vendor's package copied as-is (§6.7 item 3) |
| `README.md` | Yes | Sidecar README: pattern, design decisions, signature status, known gaps (§6.7 item 8) |
| `.overrides` | Optional | Org-defined `key=value` values a pipeline supplies at run time (§3.4). Usually generated or gitignored, not committed. |
| `.check_this` | Auto | Sentinel — signals the check workflow to look for new versions of this app via its public URL. Apps behind login walls or with no public download URL do not have this file. |
| `.rebuild_this` | Auto | Sentinel — triggers a package rebuild in the next workflow run |
| `scripts/` | Optional | `preinstall` / `postinstall` for patterns that carry scripts (§6.4) |
| `*_ERRATA.md` | Optional | Documents Recipe Robot failures or non-obvious fixes for this app |

### 3.2 Recipe Types

| Suffix | Purpose |
|--------|---------|
| `.download.recipe.yaml` | Downloads the app installer, verifies code signature |
| `.pkg.recipe.yaml` | Builds (or copies) a .pkg from the download |

### 3.3 Naming Conventions

Identifiers use the org's configured identifier prefix (`identifier_prefix` in `config/org.yaml`, e.g. `com.acmefruit.autopkg`). Packages the org builds itself use the org's configured prefix (`pkgname_prefix` in `config/org.yaml`, e.g. `Acme_`).

| Element | Convention | Example |
|---------|-----------|---------|
| Vendor directory | `VendorName` (PascalCase, no spaces) | `MicrosoftCorporation`, `MozillaCorporation` |
| App directory | `AppName` (hyphenated if multi-word) | `Microsoft-Word`, `Firefox` |
| Recipe filename | `AppName.{download,pkg}.recipe.yaml` | `Microsoft-Word.download.recipe.yaml` |
| Download identifier | `<identifier_prefix>.download.AppName` | `com.acmefruit.autopkg.download.MicrosoftWord` |
| Pkg identifier | `<identifier_prefix>.pkg.AppName` | `com.acmefruit.autopkg.pkg.MicrosoftWord` |
| `pkgname` (built by `PkgCreator`) | `<pkgname_prefix>%NAME%` | `Acme_%NAME%` |
| Output .pkg name (built) | `<pkgname_prefix>AppName.pkg` | `Acme_Firefox.pkg` |
| Output .pkg name (vendor copy) | `%NAME%.pkg` — no prefix | `Microsoft-Word.pkg` |
| `NAME` Input variable | Matches the app directory name | `Microsoft-Word` |
| `APP_FILENAME` Input | The `.app` bundle name when it differs from `NAME` | `Microsoft Word` |

The `AppName` segment of an identifier is the full app directory name with hyphens removed — never a truncation (`MicrosoftWord`, not `Word`).

Avoid dots in filenames (e.g. `drawio.download.recipe.yaml` not `draw.io.download.recipe.yaml`). Use the `NAME` Input variable for the canonical app name; use `APP_FILENAME` when the vendor's `.app` bundle name contains spaces or differs from `NAME`.

> **Static vs. versioned output filenames.** This standard uses a static filename (`Acme_%NAME%`) so infrastructure-as-code references to the package don't change on every version bump. Some orgs prefer versioned filenames (`Acme_%NAME%-%version%`) so every build is distinguishable on disk and in the MDM. Either works; pick one per org and apply it consistently to §3.8, §6.3, §6.7 (item 3), and every `pkgname` value. The linter only requires the prefix.

### 3.4 The `.overrides` File

`.overrides` is optional and org-defined. Nothing in this standard requires it, the linter has no rules about it, and the Acme catalogue and the templates don't ship one.

It is a `key=value` text file next to a recipe pair. Lines starting with `#` and blank lines are ignored. AutoPkg itself never reads it. When the file exists, the harness (`bin/run-recipes.sh` in this toolkit, or your CI job) passes each line to `autopkg run` as `--key=KEY=VALUE`, which sets or replaces that Input for the run.

It is useful when a pipeline must supply a value the recipe can't hold. The usual case is a secret. Say a recipe's postinstall script activates a license:

1. The recipe carries a placeholder Input (`LICENSE_KEY: "REPLACE_AT_RUN_TIME"`), so the key is never in the recipe or in git.
2. The pipeline writes `LICENSE_KEY=<real key>` into `.overrides` just before the run, from its secret store.
3. The harness passes it as `--key=LICENSE_KEY=…`, and the script gets the real value.

Rules:

- An `.overrides` that holds a secret or a deployment detail (for example, which Jamf server to push to) is generated by the pipeline at run time or gitignored. It is never committed. Add those values to your fork's `.leak-patterns` so `bin/check-sanitized.sh` catches a slip.
- A version, or anything AutoPkg must see for the recipe to work, belongs in the recipe's `Input`, not in `.overrides`. A bare `autopkg run` never reads `.overrides`, so a value that lives only there breaks the recipe for anyone running it directly.
- The Team ID is not an `.overrides` value. It is enforced in the recipe itself: the `requirement` string pins `subject.OU`, or `expected_authority_names` lists the chain (§3.7). The recipe's README records it for humans.

### 3.5 Deployment-Pipeline Metadata

This standard defines no deployment-pipeline metadata file. Values such as which environments a recipe is promoted to, which regions build it, or its resource name in your IaC layer are org-specific. A fork may keep its own sidecar files for them next to each recipe pair and add its own lint rules for those files: the linter engine supports `related_type: "overrides"` and `related_type: "autopkg_config"` checks (reading `.overrides` and `.autopkg_config` next to the recipe) in a fork's `config/checks.yaml`.

### 3.6 Sentinel Files

The workflow uses zero-byte (or short-message) files as triggers:

| File | Created by | Consumed by | Purpose |
|------|-----------|-------------|---------|
| `.check_this` | Human or onboarding workflow | `autopkg-check` workflow | Persistent flag — tells the check workflow to monitor this app for new versions via its public download URL. Apps with no public URL (vendor-drop, login wall) do not have this file. |
| `.rebuild_this` | `autopkg-check` workflow or human | `autopkg-build` workflow | Triggers a package rebuild on the next run. Consumed (deleted) after the build completes. |

### 3.7 Code Signature Requirements

Every download recipe must include `CodeSignatureVerifier`, or declare `NO_CODE_SIGNATURE_REQUIRED: true` with a comment explaining why (§6.7 item 5). The publisher's Team ID is enforced in the recipe itself, by the `requirement` string or the `expected_authority_names` chain. The recipe's README records it for humans.

| Requirement | Detail |
|-------------|--------|
| `CodeSignatureVerifier` present | In the download recipe |
| `input_path` correct | Points to the `.app` bundle inside the download artifact (DMG/ZIP sources) or to the `.pkg` file itself (vendor `.pkg` sources, e.g. 4a, 4b, 5) |
| `requirement` string populated | For `.app` bundles — extracted from a signed copy (§6.5), never hand-authored |
| `expected_authority_names` populated | For `.pkg` installers — full certificate chain list |
| `subject.OU` present | Team ID in the requirement string. If the publisher has no team ID (ad-hoc signed), set `teamid: "UNSIGNED_NO_TEAMID"` in the download recipe's `Input`, with a comment saying why |

### 3.8 Terraform Integration

The recipe repo feeds a deployment pipeline — Terraform in this example, but any infrastructure-as-code or MDM upload process works the same way.

| Rule | Detail |
|------|--------|
| Output filename | Stable per app (`Acme_AppName.pkg` or `AppName.pkg`; see §3.3 note) so pipeline references don't drift |
| Resource name | How a recipe maps to its resource in your deployment pipeline is org-specific (§3.5) |
| Build output is ephemeral | `build/output/` is `.gitignore`'d — built artifacts are never committed |
| Vendor input is committed | `build/vendor_cache/` is committed (Git LFS for files >100MB) |

---

## 4. Recipe Inventory

Keep an inventory of the repo's recipes here, preferably generated from the recipe tree rather than maintained by hand. Acme Fruit Co.'s example catalogue (the worked example in `customer/acme/`) covers most patterns:

| Vendor dir | App | Pattern | Source | Notes |
|---|---|---|---|---|
| `MoonlightGameStreaming` | `Moonlight` | 2b | GitHub release, DMG | `GitHubReleasesInfoProvider` + `PkgCreator` |
| `RaspberryPiLtd` | `Raspberry-Pi-Imager` | 2b | GitHub release, DMG | |
| `Pearcleaner` | `Pearcleaner` | 2b | GitHub release, DMG | |
| `FruitScreensaver` | `Fruit-Screensaver` | 2b | GitHub release (`.tar.gz`), rebuilt | Installs the screensaver only |
| `FruitScreensaver` | `Fruit-Screensaver-Default` | 6b | Config slice: makes it the default, installed after | Split out per §6.10.1 |
| `AcmeFruitCo` | `Fruta-Starter-Kit` | 2d | GitHub source ZIP, reassembled + scripts | Fruta New-Hire Starter Kit; by analogy with 4e (§6.2.2.4) |
| `MozillaCorporation` | `Firefox` | 3b | Stable direct URL, DMG | |
| `GoogleLLC` | `Google-Chrome` | 3b | Stable direct URL, DMG | |
| `OrangeDataMining` | `Orange` | 3c | Scraped direct URL, DMG | `URLTextSearcher` on the download page |
| `HPInc` | `HP-Printer-Drivers` | 4b | Vendor-provided distribution .pkg | Copied as-is with `Copier` |
| `OrchardLabs` | `Orchard-Analytics` | 4c | Vendor-provided DMG, app only | Fictional |
| `OrchardLabs` | `Orchard-Analytics-License` | 6c | License slice for the app above, installed after it | Fictional |
| `MicrosoftCorporation` | `Microsoft-Word` | 5 | Vendor .pkg via stable fwlink URL | |
| `AcmeFruitCo` | `AcmeSupport` | 6b | Rebuilt from existing package, payload + scripts | Fictional in-house app |
| `AcmeFruitCo` | `Acme-Wallpaper` | 6c | Rebuilt, single file with specific mode | Fictional |
| `AcmeFruitCo` | `Acme-UninstallAgent` | 6d | Rebuilt, payloadless (script-only) | Fictional |
| `PomeloSoftware` | `Pomelo-Studio` | 7 | Faux vendor DMG from a snapshot | Fictional |

A correctly normalized recipe pair for one of these:

| Recipe | Type | Identifier |
|--------|------|------------|
| `Firefox.download.recipe.yaml` | download | `com.acmefruit.autopkg.download.Firefox` |
| `Firefox.pkg.recipe.yaml` | pkg | `com.acmefruit.autopkg.pkg.Firefox` |

> **Note:** Recipe Robot–generated identifiers often contain the `.pkg.download.` namespace collision (e.g. `com.acmefruit.autopkg.pkg.download.Edge`). See §6.9 Errata. The correct download namespace is `com.acmefruit.autopkg.download.AppName`.

---

## 5. Prerequisites

Before writing or modifying recipes, ensure:

- [ ] AutoPkg >= 2.3 installed (`brew install autopkg` or download from [github.com/autopkg/autopkg](https://github.com/autopkg/autopkg))
- [ ] Recipe Robot installed (`brew install --cask recipe-robot` or download from [github.com/homebysix/recipe-robot](https://github.com/homebysix/recipe-robot))
- [ ] Git configured with your org email (e.g. `git config user.email "you@acmefruit.example"`)
- [ ] Access to your org's recipe repository
- [ ] A Mac with Xcode Command Line Tools installed (for `codesign` and `pkgutil`)

---

## 6. How to Make Recipes

### 6.1 Recipe Patterns Overview

Every download recipe follows the same skeleton: resolve the download URL, fetch the file, verify its code signature, and extract the version. The differences come down to *how the URL is resolved* (the pattern **number**) and *what file format the vendor ships and how it becomes the output package* (the pattern **letter**). §6.8 has the full two-axis reference.

| Pattern | Name | Source | Key processor(s) |
|---------|------|--------|------------------|
| 1 | Sparkle Appcast | App has a Sparkle update feed | `SparkleUpdateInfoProvider` |
| 2 | GitHub Release | Releases as binary assets on GitHub | `GitHubReleasesInfoProvider` |
| 3 | Direct URL | Vendor hosts installer at a known HTTP/FTP URL (stable or scraped) | `URLDownloader` / `URLTextSearcher` |
| 4 | Vendor-Provided File | No public URL; file handed directly to you | `URLDownloader` with a `file://` URI into `vendor_cache` |
| 5 | Vendor PKG via Stable URL | Vendor ships a signed `.pkg` at a stable URL | `URLDownloader` + `FlatPkgUnpacker` |
| 6 | Rebuilt Package | Existing installer found, source files unavailable | `pkg-reverse.sh` + `PkgCreator` |
| 7 | Faux Vendor DMG | In-house constructed DMG wrapping a vendor app/binary | `Copier` + `PkgCreator` |
| 8 | Experimental | Unsigned dev/internal `.app` with no upstream signature | `PkgCreator` with `NO_CODE_SIGNATURE_REQUIRED` |

Starter templates for the vendor-drop and rebuilt patterns live in this toolkit's `templates/`; `bin/classify-recipe.sh` reports which pattern an existing recipe directory follows.

### 6.2.1 Pattern 1 — Sparkle Appcast

Use when the app ships with a Sparkle update feed. Most Mac apps that show "Check for Updates…" in their menu have one. You can find the URL in the app's `Info.plist` under the `SUFeedURL` key, or check for a well-known path like `https://example.com/appcast.xml`.

**Download recipe:**

```yaml
Comment: Sparkle-based download recipe.
Description: Downloads the latest version of ExampleApp.
Identifier: com.acmefruit.autopkg.download.ExampleApp
MinimumVersion: "2.3"

Input:
  NAME: ExampleApp

Process:
  - Processor: SparkleUpdateInfoProvider
    Arguments:
      appcast_url: "https://example.com/appcast.xml"

  - Processor: URLDownloader
    Arguments:
      filename: "%NAME%-%version%.zip"

  - Processor: EndOfCheckPhase

  # If the download is a ZIP, unpack it first
  - Processor: Unarchiver
    Arguments:
      archive_path: "%pathname%"
      destination_path: "%RECIPE_CACHE_DIR%/%NAME%"
      purge_destination: true

  - Processor: CodeSignatureVerifier
    Arguments:
      input_path: "%RECIPE_CACHE_DIR%/%NAME%/ExampleApp.app"
      requirement: >-
        anchor apple generic
        and identifier "com.example.app"
        and certificate leaf[subject.OU] = XXXXXXXXXX
```

Notes:
- `SparkleUpdateInfoProvider` sets both `%url%` and `%version%` itself — no `Versioner` step needed.
- The `Unarchiver` step is only needed for ZIP downloads. For DMGs, skip it — the mounted DMG is accessible at `%pathname%/`.

#### 6.2.1.1 1a — Sparkle — Vendor .pkg (PkgCopier)

When the Sparkle appcast resolves to a vendor `.pkg` file (rare). Use `PkgCopier` in the pkg recipe; no org prefix on the output.

#### 6.2.1.2 1b — Sparkle — DMG/ZIP (PkgCreator)

Standard case. Download is a DMG or ZIP containing a `.app`. Extract and rebuild with `PkgCreator` (§6.3). Adjust `input_path` based on archive type: ZIP → `%RECIPE_CACHE_DIR%/%NAME%/ExampleApp.app`, DMG → `%pathname%/ExampleApp.app`.

---

### 6.2.2 Pattern 2 — GitHub Release

Use when the app distributes releases as binary assets on GitHub (DMG, ZIP, or pkg files attached to tagged releases).

**Download recipe (2b):**

```yaml
Comment: GitHub Releases download recipe.
Description: Downloads the latest version of ExampleApp (Apple Silicon DMG).
Identifier: com.acmefruit.autopkg.download.ExampleApp
MinimumVersion: "2.3"

Input:
  NAME: ExampleApp
  GITHUB_REPO: owner/repo-name
  ASSET_REGEX: "ExampleApp-.*-arm64\\.dmg$"
  # Change to "ExampleApp-.*-x64\\.dmg$" for Intel builds

Process:
  - Processor: GitHubReleasesInfoProvider
    Arguments:
      github_repo: "%GITHUB_REPO%"
      asset_regex: "%ASSET_REGEX%"
      include_prereleases: false

  - Processor: URLDownloader
    Arguments:
      filename: "%NAME%.dmg"

  - Processor: EndOfCheckPhase

  - Processor: CodeSignatureVerifier
    Arguments:
      input_path: "%pathname%/ExampleApp.app"
      requirement: >-
        identifier "com.example.app"
        and anchor apple generic
        and certificate 1[field.1.2.840.113635.100.6.2.6] /* exists */
        and certificate leaf[field.1.2.840.113635.100.6.1.13] /* exists */
        and certificate leaf[subject.OU] = XXXXXXXXXX

  - Processor: Versioner
    Arguments:
      input_plist_path: "%pathname%/ExampleApp.app/Contents/Info.plist"
      plist_version_key: CFBundleShortVersionString
```

Notes:
- `GitHubReleasesInfoProvider` sets `%url%` and `%version%`. The `Versioner` step is a belt-and-suspenders check that reads the version from the actual app bundle — useful when the GitHub tag format doesn't match the app's marketing version.
- **Find the right repo.** Some projects use a separate `-desktop` repo for their Electron/native builds (e.g. `jgraph/drawio-desktop` not `jgraph/drawio`).
- Set `include_prereleases: false` unless you explicitly want betas.

#### 6.2.2.1 2a — GitHub — Vendor .pkg (PkgCopier)

When the GitHub release asset is a vendor `.pkg`. Use `PkgCopier`; no org prefix.

#### 6.2.2.2 2b — GitHub — DMG (PkgCreator)

Standard case, shown above. Examples: Zettlr, Hammerspoon, draw.io; in the Acme catalogue, Moonlight, Raspberry Pi Imager, Pearcleaner.

##### Writing the `asset_regex`

The regex must match exactly one asset from the release. Get it wrong and AutoPkg downloads the wrong file (or nothing). The quick method:

1. Go to the repo's **Releases** page on GitHub.
2. Look at the **Assets** list on the latest release and note the exact filenames.
3. Paste all the asset filenames into a regex tester such as [regex101.com](https://regex101.com) (one per line). These are public filenames, not company data.
4. Write a pattern and confirm it highlights only the one file you want.
5. Anchor with `$` at the end so partial matches on `.dmg.sha256` or `.dmg.blockmap` don't sneak in.

Common building blocks:

| Piece | What it matches | Example |
|-------|-----------------|---------|
| `AppName-` | Literal app prefix | `Zettlr-` |
| `[\\d.]+` | Version numbers | `4.2.1` |
| `.*` | Anything (greedy) | version + arch combined |
| `-arm64` | Apple Silicon | literal |
| `-x64` or `-x86_64` | Intel | literal |
| `\\.dmg$` | DMG file, end of string | escaped dot + anchor |

#### 6.2.2.3 2c — GitHub — DMG + Ridealong Scripts (PkgCreator)

**New variant, by analogy with 4d.** The app comes from a GitHub release (as 2b), and the org adds its own scripts or payload — for example a postinstall that sets a screensaver as the default. The download recipe is identical to 2b; the pkg recipe adds `scripts:` to `pkg_request` (§6.4) and `chown` entries for any extra payload.

**Example:** none in the Acme catalogue. Its Fruit screensaver was split instead — a 2b package that installs the screensaver plus a 6b slice that makes it the default (§6.10.1): installing a tool and choosing a default are separate decisions.

#### 6.2.2.4 2d — GitHub — Source ZIP, Reassembled (PkgCreator)

**New variant, by analogy with 4e.** The release is a ZIP (often GitHub's auto-generated source archive) rather than a ready-to-install app. Unpack with `Unarchiver`, copy the needed pieces into a pkgroot with `Copier`, and build with `PkgCreator`, adding `scripts:` where the org's setup logic is needed. There is usually no `.app` to verify — confirm what, if anything, is signed and declare `NO_CODE_SIGNATURE_REQUIRED: true` with a comment when nothing is (§6.7 item 5).

**Example:** Fruta New-Hire Starter Kit (Acme catalogue; fictional).

---

### 6.2.3 Pattern 3 — Direct URL

Use when the vendor hosts the installer at a known HTTP/FTP URL on their own download server — no Sparkle feed, no GitHub.

#### 6.2.3.1 3a — Stable URL — Vendor .pkg (PkgCopier)

When the vendor's stable URL resolves to a `.pkg`. Use `PkgCopier`; no org prefix. (A signed vendor `.pkg` at a stable URL whose version must be read from inside the package is usually better treated as Pattern 5.)

#### 6.2.3.2 3b — Stable URL — DMG/app — Rebuild (PkgCreator)

The vendor provides a URL that always points to the current version (e.g. `https://vendor.example.com/download/ExampleApp-latest.dmg`). This is the ideal case — the URL never changes, only the file behind it does.

```yaml
Comment: Direct URL download recipe (stable redirect).
Description: Downloads the latest version of ExampleApp.
Identifier: com.acmefruit.autopkg.download.ExampleApp
MinimumVersion: "2.3"

Input:
  NAME: ExampleApp
  DOWNLOAD_URL: "https://vendor.example.com/download/ExampleApp-latest.dmg"

Process:
  - Processor: URLDownloader
    Arguments:
      url: "%DOWNLOAD_URL%"
      filename: "%NAME%.dmg"

  - Processor: EndOfCheckPhase

  - Processor: CodeSignatureVerifier
    Arguments:
      input_path: "%pathname%/ExampleApp.app"
      requirement: >-
        anchor apple generic
        and identifier "com.vendor.app"
        and certificate leaf[subject.OU] = XXXXXXXXXX

  - Processor: Versioner
    Arguments:
      input_plist_path: "%pathname%/ExampleApp.app/Contents/Info.plist"
      plist_version_key: CFBundleShortVersionString
```

**Examples:** VS Code, Smartsheet; in the Acme catalogue, Firefox and Google Chrome.

#### 6.2.3.3 3c — Scraped URL — DMG/app — Rebuild (PkgCreator)

The vendor's download page has a link containing the current version number, and the URL changes with each release. Use `URLTextSearcher` to scrape the page for the real URL, then `URLDownloader`:

```yaml
Comment: Direct URL download recipe (scraped from download page).
Description: Downloads the latest version of ExampleApp.
Identifier: com.acmefruit.autopkg.download.ExampleApp
MinimumVersion: "2.3"

Input:
  NAME: ExampleApp
  DOWNLOAD_PAGE_URL: "https://vendor.example.com/downloads/"
  DOWNLOAD_URL_RE: "https://vendor\\.example\\.com/releases/ExampleApp-[\\d.]+\\.dmg"

Process:
  - Processor: URLTextSearcher
    Arguments:
      url: "%DOWNLOAD_PAGE_URL%"
      re_pattern: "%DOWNLOAD_URL_RE%"
      result_output_var_name: url

  - Processor: URLDownloader
    Arguments:
      filename: "%NAME%.dmg"

  - Processor: EndOfCheckPhase

  - Processor: CodeSignatureVerifier
    Arguments:
      input_path: "%pathname%/ExampleApp.app"
      requirement: >-
        anchor apple generic
        and identifier "com.vendor.app"
        and certificate leaf[subject.OU] = XXXXXXXXXX

  - Processor: Versioner
    Arguments:
      input_plist_path: "%pathname%/ExampleApp.app/Contents/Info.plist"
      plist_version_key: CFBundleShortVersionString
```

**Example:** Orange Data Mining (Acme catalogue).

**Key notes:**
- Neither 3b nor 3c gives `%version%` automatically — always add a `Versioner` step.
- For stable URLs, `URLDownloader` follows redirects transparently; verify with `curl -LI` before writing the recipe.
- For scraped URLs, `URLTextSearcher` writes the first capture group (or the whole match if there is no group) to `result_output_var_name`. Test the regex against the page source (view-source, then a regex tester).
- If the URL is versioned but predictable and you already know the version, skip scraping and template it: `https://vendor.example.com/releases/ExampleApp-%VERSION%.dmg` with `VERSION` set in `Input`. This sits halfway between Pattern 3c and Pattern 4.

---

### 6.2.4 Pattern 4 — Vendor-Provided File (No URL)

Use when the vendor hands you a file directly — behind a login wall, emailed, or otherwise with no stable public URL — or for an in-house build (staged under `vendor_cache/AcmeFruitCo/`). The file is staged in the repo's vendor cache (§9) and fetched with `URLDownloader` from a `file://` URI built on the `VENDOR_CACHE_ROOT` Input (§6.7 item 2).

Common rules for every Pattern 4 variant:

- **Path arithmetic.** `recipes/<Vendor>/<App>/` is three levels below the repo root, so the default is `VENDOR_CACHE_ROOT: "%RECIPE_DIR%/../../../build/vendor_cache"` (or `…/../../../vendor_cache` for a repo with a root-level cache). Count the levels; a wrong depth fails at runtime, not at lint time. CI can override the value with `-k VENDOR_CACHE_ROOT=…`.
- **No `PathDeleter` at the top of the download recipe.** It errors when its target doesn't exist, which is exactly the first-run state; `URLDownloader` and `Copier` (with `overwrite: true`) already replace their destinations.
- **Check `.pkg` signatures with `pkgutil --check-signature`, never `codesign`.** Many vendor-drop installers turn out to be genuinely unsigned; see §6.7 item 5 for the decision tree.
- **Versions** are pinned in the download recipe's `Input` (`version: "1.2.3"`) unless the recipe can read them from the artifact.

See `reference/methodology.md` in this toolkit for the failures behind these rules.

| Variant | Vendor file | Output processor | Org prefix? |
|---|---|---|---|
| 4a | Flat vendor `.pkg` | `PkgCopier` | No |
| 4b | Distribution vendor `.pkg` | `Copier` | No |
| 4c | Vendor DMG containing a `.app` | `PkgCreator` | Yes |
| 4d | Vendor DMG + ridealong scripts/payload | `PkgCreator` with `scripts:` | Yes |
| 4e | ZIP + ridealong config | Depends | Depends |

#### 6.2.4.1 4a — Vendor .pkg, Copied As-Is (PkgCopier)

**When:** The vendor provides a signed, **flat** (single-component) `.pkg`. Copy it as-is, no rebuild, no org prefix. If the package is a distribution package, use 4b instead — `PkgCopier` crashes on those.

**Examples:** none in the Acme catalogue; most vendor-drop `.pkg` files in practice are distribution packages (4b).

```yaml
# Download recipe
Identifier: com.acmefruit.autopkg.download.AppName
Input:
  NAME: AppName
  VENDOR_CACHE_ROOT: "%RECIPE_DIR%/../../../build/vendor_cache"
  DOWNLOAD_URL: "file://%VENDOR_CACHE_ROOT%/Vendor/AppName/AppName.pkg"
Process:
  - Processor: URLDownloader
    Arguments:
      url: "%DOWNLOAD_URL%"
      filename: "download_%NAME%.pkg"
  - Processor: EndOfCheckPhase
  - Processor: CodeSignatureVerifier
    Arguments:
      input_path: "%pathname%"
      expected_authority_names:
        - "Developer ID Installer: Vendor Name (XXXXXXXXXX)"
        - Developer ID Certification Authority
        - Apple Root CA

# Pkg recipe
Identifier: com.acmefruit.autopkg.pkg.AppName
ParentRecipe: com.acmefruit.autopkg.download.AppName
Process:
  - Processor: PkgCopier
    Arguments:
      source_pkg: "%RECIPE_CACHE_DIR%/downloads/download_%NAME%.pkg"
      pkg_path: "%RECIPE_CACHE_DIR%/%NAME%.pkg"
```

Version: extract it in the pkg recipe with `FlatPkgUnpacker` + `PkgPayloadUnpacker` + `Versioner` (as in Pattern 5), or pin it in `Input`.

#### 6.2.4.2 4b — Distribution Vendor .pkg, Copied As-Is (Copier)

**When:** The vendor provides a **distribution-format** `.pkg` — a multi-component package with a `Distribution` file and inner component packages. This is the most common vendor-drop case. `PkgCopier` is not safe here: it looks for a single flat component and fails with "list index out of range". Use `Copier` for a bit-for-bit copy instead. No org prefix — the output is the vendor's signed artifact.

**Examples:** printer drivers (HP in the Acme catalogue; Xerox), Citrix Workspace, Cisco Secure Client, Claude.

**Telling the two apart:** `pkgutil --expand Vendor.pkg /tmp/x && ls /tmp/x` — a `Distribution` file plus one or more `*.pkg` directories means distribution (4b); a lone `PackageInfo`/`Payload` means flat (4a).

```yaml
# Download recipe
Comment: Pattern 4b vendor-drop distribution pkg. Copier bit-for-bit copy.
Description: Imports a locally staged copy of AppName.
Identifier: com.acmefruit.autopkg.download.AppName
MinimumVersion: "2.3"
Input:
  NAME: AppName
  teamid: "XXXXXXXXXX"
  authority_name: "Vendor Name"
  VENDOR_CACHE_ROOT: "%RECIPE_DIR%/../../../build/vendor_cache"
  DOWNLOAD_URL: "file://%VENDOR_CACHE_ROOT%/Vendor/AppName/AppName.pkg"
  filename: "download_%NAME%.pkg"
Process:
  - Processor: URLDownloader
    Arguments:
      url: "%DOWNLOAD_URL%"
      filename: "%filename%"
  - Processor: EndOfCheckPhase
  - Processor: CodeSignatureVerifier
    Arguments:
      input_path: "%pathname%"
      expected_authority_names:
        - "Developer ID Installer: %authority_name% (%teamid%)"
        - Developer ID Certification Authority
        - Apple Root CA

# Pkg recipe
Description: Pattern 4b distribution package. Copier bit-for-bit copy of vendor pkg.
Identifier: com.acmefruit.autopkg.pkg.AppName
ParentRecipe: com.acmefruit.autopkg.download.AppName
MinimumVersion: "2.3"
Input:
  NAME: AppName
  PKG_ID: com.vendor.pkg.AppName   # the vendor's own identifier, read from the Distribution file
Process:
  - Processor: Copier
    Arguments:
      source_path: "%RECIPE_CACHE_DIR%/downloads/download_%NAME%.pkg"
      destination_path: "%RECIPE_CACHE_DIR%/%NAME%.pkg"
      overwrite: true
```

Notes:
- **Reference the literal cache path in the pkg recipe, not `%pathname%`.** `%RECIPE_CACHE_DIR%` is shared across the parent→child chain, and `URLDownloader` always writes to `%RECIPE_CACHE_DIR%/downloads/<filename>`. `Copier` does not set `%pathname%`, so any later step relying on it gets a stale or wrong value.
- **`PKG_ID`**: read the vendor's identifier from the real package (`grep -o 'identifier="[^"]*"' /tmp/x/Distribution`). If you can't confirm it, invent one and say so in the app's README.
- **Unsigned variant.** If `pkgutil --check-signature` reports the package is unsigned, delete the `CodeSignatureVerifier` step and the `teamid` / `authority_name` Inputs, and add `NO_CODE_SIGNATURE_REQUIRED: true` with a comment recording that it was confirmed unsigned (and when) and what the trust boundary is (usually the MDM).
- **Version** is pinned in the download recipe's `Input`; distribution packages rarely expose a single app version reliably.
- Template: `templates/pattern-4b-distribution-package/` in this toolkit.

#### 6.2.4.3 4c — Vendor DMG, Extract and Rebuild (PkgCreator)

**When:** The vendor provides a DMG containing a `.app`. Extract the app and rebuild with the org prefix.

**Examples:** Orchard Analytics in the Acme catalogue (fictional).

```yaml
# Download recipe
Identifier: com.acmefruit.autopkg.download.AppName
Input:
  NAME: AppName
  VENDOR_CACHE_ROOT: "%RECIPE_DIR%/../../../build/vendor_cache"
  DOWNLOAD_URL: "file://%VENDOR_CACHE_ROOT%/Vendor/AppName/AppName.dmg"
Process:
  - Processor: URLDownloader
    Arguments:
      url: "%DOWNLOAD_URL%"
      filename: "%NAME%.dmg"
  - Processor: EndOfCheckPhase
  - Processor: Copier
    Arguments:
      source_path: "%pathname%/AppName.app"     # Copier mounts DMGs natively; globs allowed
      destination_path: "%RECIPE_CACHE_DIR%/%NAME%/Applications/AppName.app"
      overwrite: true
  - Processor: CodeSignatureVerifier
    Arguments:
      input_path: "%RECIPE_CACHE_DIR%/%NAME%/Applications/AppName.app"
      requirement: "..."                        # from codesign, §6.5
  - Processor: Versioner
    Arguments:
      input_plist_path: "%RECIPE_CACHE_DIR%/%NAME%/Applications/AppName.app/Contents/Info.plist"
      plist_version_key: CFBundleShortVersionString
```

The pkg recipe is the standard `PkgCreator` recipe in §6.3, with `pkgroot: "%RECIPE_CACHE_DIR%/%NAME%"`. Template: `templates/pattern-4c-vendor-drop-dmg/`.

#### 6.2.4.4 4d — Vendor DMG + Ridealong Scripts/Payload (PkgCreator)

**When:** Vendor DMG containing a `.app`, plus org-specific scripts, license files, or additional payload. Identical to 4c except the pkg recipe adds `scripts:` in `pkg_request` and extra `chown` entries for the ridealong files.

**Examples:** Kiwi Capture (fictional; license ridealong, the template example). Prefer a slice (§6.10.1): the Acme catalogue ships Orchard Analytics as a 4c app package plus a 6c license slice.

If the vendor also publishes the app at a public URL, consider downloading it as 3b and shipping the license as its own slice (§6.10.1) — the app then updates automatically and only the slice stays vendor-drop. Template: `templates/pattern-4d-vendor-drop-dmg-ridealong/`.

#### 6.2.4.5 4e — Vendor ZIP with Ridealong Config

**When:** The vendor provides a ZIP containing one or more installer files plus org-specific config files. Unpack with `Unarchiver` and reassemble. Whether the output carries the org prefix depends on what is produced: an inner vendor `.pkg` passed through unchanged gets none; a package rebuilt with `PkgCreator` gets the prefix.

**Example:** a VPN client (e.g. Cisco Secure Client) delivered as a ZIP with site configuration.

---

### 6.2.5 Pattern 5 — Vendor PKG via Stable URL

Use when the vendor distributes a signed `.pkg` installer (not a DMG containing a `.app`) at a stable URL. The download is a flat package — you don't rebuild it, you reuse it. The unpack steps in the pkg recipe exist solely to extract the version number from the embedded `.app` bundle.

This pattern is common with Microsoft Office apps, which ship signed `.pkg` installers via stable `fwlink` redirect URLs.

**Download recipe:**

```yaml
Comment: Vendor PKG download recipe (stable redirect URL).
Description: Downloads the latest version of Microsoft Word.
Identifier: com.acmefruit.autopkg.download.MicrosoftWord
MinimumVersion: "2.3"

Input:
  APP_FILENAME: Microsoft Word
  NAME: Microsoft-Word

Process:
  - Processor: URLDownloader
    Arguments:
      url: "https://go.microsoft.com/fwlink/?linkid=525134"
      filename: "%NAME%.pkg"

  - Processor: EndOfCheckPhase

  - Processor: CodeSignatureVerifier
    Arguments:
      expected_authority_names:
        - "Developer ID Installer: Microsoft Corporation (UBF8T346G9)"
        - Developer ID Certification Authority
        - Apple Root CA
      input_path: "%pathname%"
```

**Pkg recipe:**

```yaml
Description: Downloads the latest version of Microsoft Word and creates a package.
Identifier: com.acmefruit.autopkg.pkg.MicrosoftWord
ParentRecipe: com.acmefruit.autopkg.download.MicrosoftWord
MinimumVersion: "2.3"

Input:
  APP_FILENAME: Microsoft Word
  NAME: Microsoft-Word

Process:
  - Processor: FlatPkgUnpacker
    Arguments:
      flat_pkg_path: "%pathname%"
      destination_path: "%RECIPE_CACHE_DIR%/unpacked"

  - Processor: PkgPayloadUnpacker
    Arguments:
      pkg_payload_path: "%RECIPE_CACHE_DIR%/unpacked/Microsoft_Word.pkg/Payload"
      destination_path: "%RECIPE_CACHE_DIR%/payload"
      purge_destination: true

  - Processor: Versioner
    Arguments:
      input_plist_path: "%RECIPE_CACHE_DIR%/payload/%APP_FILENAME%.app/Contents/Info.plist"
      plist_version_key: CFBundleShortVersionString

  - Processor: PkgCopier
    Arguments:
      source_pkg: "%pathname%"
      pkg_path: "%RECIPE_CACHE_DIR%/%NAME%.pkg"

  - Processor: PathDeleter
    Arguments:
      path_list:
        - "%RECIPE_CACHE_DIR%/payload"
        - "%RECIPE_CACHE_DIR%/unpacked"
```

Notes:
- **You are not rebuilding the package.** The vendor's signed `.pkg` is the output. `PkgCopier` copies it as-is — no `PkgCreator` step, no org prefix.
- `CodeSignatureVerifier` uses `expected_authority_names` (certificate chain) instead of `requirement`, because the input is a `.pkg` installer, not a `.app` bundle. The `input_path` points to the `.pkg` file itself.
- `APP_FILENAME` is needed when the `.app` bundle name inside the package differs from `NAME`. Microsoft Word's bundle is `Microsoft Word.app` but `NAME` is `Microsoft-Word` (hyphenated for filesystem safety).
- The `FlatPkgUnpacker` → `PkgPayloadUnpacker` → `Versioner` chain is only there to read the version from the app's `Info.plist`. If the inner `.pkg` component name is predictable and static (like `Microsoft_Word.pkg`), you can hardcode the path. If it contains a version number that changes between releases, use `FileFinder` instead — see §6.9 (Microsoft Edge).
- **No `Versioner` in the download recipe.** Unlike DMG-based patterns, you can't read a version from the download artifact directly — it's a flat `.pkg`, not a mountable DMG. Version extraction happens in the pkg recipe after unpacking.

> **Hardcoded paths vs. `FileFinder`.** Neither approach is bulletproof. Hardcoded paths break when vendors add version numbers to internal package components. `FileFinder` glob patterns break when vendors change naming schemes entirely. Pick the one that matches what the vendor *currently* ships, and monitor for breakage. When a recipe fails after an upstream update, `FileFinder` is the first tool to reach for — see §6.9 (Microsoft Edge) for the full story.

---

### 6.2.6 Pattern 6 — Rebuilt Package

Patterns 6–8 are extensions beyond the download patterns most community recipes use — say "Pattern 6 (rebuilt package)" when first using the term with people outside your team.

Use when an installed package exists but its source files do not — a legacy in-house package with no build recipe, no pkgroot, and nobody left who has it. Extract the built package and rebuild.

**Generate the starting point** with this toolkit:

```bash
sudo bin/pkg-reverse.sh /path/to/Legacy.pkg --dest <repo>/build/vendor_cache/<Vendor>
bin/blueprint-to-recipe.sh --blueprint <repo>/build/vendor_cache/<Vendor>/.../blueprint.conf --out <repo>/recipes/<Vendor>/<App>
```

`sudo` is mandatory — without it, extracted file ownership is wrong. Use `bin/pkg-compare.sh` afterwards to confirm the rebuilt package matches the original.

#### 6.2.6.1 6a — Flat Payload, No Scripts

A payload directory with no installer scripts.

**Examples:** Acme Login Banner (fictional), a Defender LaunchDaemon config.

```yaml
# Pkg recipe
Identifier: com.acmefruit.autopkg.pkg.AppName
Process:
  - Processor: PkgCreator
    Arguments:
      pkg_request:
        pkgroot: "%RECIPE_CACHE_DIR%/payload"
        pkgname: "Acme_%NAME%"
        pkgdir: "%RECIPE_CACHE_DIR%"
        id: "%PKG_ID%"
        version: "%version%"
```

#### 6.2.6.2 6b — Payload + Installer Scripts

Same as 6a, but the pkg recipe adds `scripts:` in `pkg_request`.

**Examples:** AcmeSupport, Acme Quarantine Helper (both fictional), Pomelo Studio user data (fictional; §6.9).

#### 6.2.6.3 6c — Single File with Specific Mode

A single file with non-default ownership or permissions.

**Examples:** Acme Wallpaper, Acme Audit Control (both fictional — the latter installs a locked-down `audit_control`).

```yaml
        chown:
          - path: private/etc/security/audit_control
            user: root
            group: wheel
            mode: "0400"
```

#### 6.2.6.4 6d — Payloadless (Script-Only)

No files to install — only a script. Uses `PkgRootCreator` + `PkgCreator` with an empty pkgroot (§6.4).

**Examples:** Acme UninstallAgent, the Pomelo Studio LaunchAgent (both fictional; §6.9).

**Key Pattern 6 rules:**
- `NO_CODE_SIGNATURE_REQUIRED: true` always — rebuilt packages have no upstream signature to verify.
- Version pinned as an `Input` (`version: "1.2.3"`) — `%version%` referenced without an Input declaration fails at runtime.
- A `chown` block may be needed if extraction did not run as root.

Templates: `templates/pattern-6-rebuilt-package/`, `pattern-6b-…`, `pattern-6c-…`, `pattern-6d-…`.

---

### 6.2.7 Pattern 7 — Faux Vendor DMG

An in-house constructed DMG (typically from a before/after snapshot tool such as Jamf Composer) wrapping a vendor app or binary. The DMG itself is unsigned.

**Examples:** Pomelo Studio in the Acme catalogue (fictional; see §6.9).

```yaml
# Download recipe
Identifier: com.acmefruit.autopkg.download.AppName
Input:
  NAME: AppName
  VENDOR_CACHE_ROOT: "%RECIPE_DIR%/../../../build/vendor_cache"
  LOCAL_FILE_PATH: "%VENDOR_CACHE_ROOT%/Vendor/AppName/AppName.dmg"
  # Faux vendor DMG — built in-house from a snapshot; no upstream signature on the wrapper.
  NO_CODE_SIGNATURE_REQUIRED: true
Process:
  - Processor: Copier
    Arguments:
      source_path: "%LOCAL_FILE_PATH%"
      destination_path: "%RECIPE_CACHE_DIR%/%NAME%.dmg"
      overwrite: true
  - Processor: EndOfCheckPhase
```

**Key points:**
- `NO_CODE_SIGNATURE_REQUIRED: true` — the DMG is in-house constructed. If the wrapped `.app` is itself vendor-signed, verify it anyway.
- Output gets the org prefix (`Acme_%NAME%`) — `PkgCreator` builds it.
- `Copier` supports glob patterns inside DMGs natively.
- Use this only when the vendor installer is unworkable for AutoPkg — and check community recipes first (§6.10.2) and adopt one that passes the audit (§6.10.3).
- If a snapshot contains multiple independent components, split them into separate recipe sets (see the Pomelo Studio case in §6.9 and §6.10.1).

Template: `templates/pattern-7-faux-vendor-dmg/`.

---

### 6.2.8 Pattern 8 — Experimental

Reserved for unsigned `.app` bundles for dev/internal purposes where no signed version is available. Nothing should permanently live here.

Not a standard workflow. See §6.7 item 5 for the signature carve-out rules and §6.7 item 8 for README requirements.

```yaml
Identifier: com.acmefruit.autopkg.download.AppName
Input:
  NAME: AppName
  VENDOR_CACHE_ROOT: "%RECIPE_DIR%/../../../build/vendor_cache"
  # Pattern 8 — unsigned dev build. Approver, date and resolution plan in README.md.
  NO_CODE_SIGNATURE_REQUIRED: true
  LOCAL_FILE_PATH: "%VENDOR_CACHE_ROOT%/Vendor/AppName/AppName.app"
Process:
  - Processor: Copier
    Arguments:
      source_path: "%LOCAL_FILE_PATH%"
      destination_path: "%RECIPE_CACHE_DIR%/%NAME%/Applications/AppName.app"
      overwrite: true
  - Processor: EndOfCheckPhase
```

Pattern 8 recipes must document the approver, approval date, and resolution plan in the README.

---

### 6.3 The Pkg Recipe (Cross-Pattern Reference)

The `.pkg` recipe is classified by which processor creates the output, not by the download source:

| Processor | Output naming | When | Patterns |
|-----------|--------------|------|----------|
| `PkgCreator` | `pkgname: "Acme_%NAME%"` | We built the output from a payload | 1b, 2b, 2c, 2d, 3b, 3c, 4c, 4d, 6a–6d, 7, 8 (and 4e when rebuilt) |
| `PkgCopier` | `pkg_path: "%RECIPE_CACHE_DIR%/%NAME%.pkg"` | Flat vendor `.pkg` copied as-is | 1a, 2a, 3a, 4a, 5 |
| `Copier` | `destination_path: "%RECIPE_CACHE_DIR%/%NAME%.pkg"` | Distribution vendor `.pkg` copied as-is | 4b |
| `AppPkgCreator` | N/A | **Forbidden** | Prevents control over output naming |

For the common DMG-sourced case (the download is a DMG containing a `.app`, and the output carries the org prefix):

```yaml
Description: Packages ExampleApp with Acme Fruit Co. naming convention.
Identifier: com.acmefruit.autopkg.pkg.ExampleApp
ParentRecipe: com.acmefruit.autopkg.download.ExampleApp
MinimumVersion: "2.3"

Input:
  NAME: ExampleApp
  PKG_ID: com.example.app

Process:
  - Processor: Copier
    Arguments:
      source_path: "%pathname%/ExampleApp.app"
      destination_path: "%RECIPE_CACHE_DIR%/%NAME%/Applications/ExampleApp.app"
      overwrite: true

  - Processor: PkgCreator
    Arguments:
      pkg_request:
        id: "%PKG_ID%"
        version: "%version%"
        pkgname: "Acme_%NAME%"
        pkgdir: "%RECIPE_CACHE_DIR%"
        chown:
          - path: Applications
            user: root
            group: admin
        pkgroot: "%RECIPE_CACHE_DIR%/%NAME%"
```

**ZIP-sourced:** Omit the `Copier` step; point `pkgroot` at where `Unarchiver` placed the app.

**Already extracted in the download recipe (4c, 4d):** Omit the `Copier` step; the app is already under `%RECIPE_CACHE_DIR%/%NAME%/Applications/`.

**Flat vendor .pkg (1a, 2a, 3a, 4a, 5):** Use `PkgCopier` only; no org prefix.

**Distribution vendor .pkg (4b):** Use `Copier` only; no org prefix (§6.2.4.2).

**Rebuilt packages (6a–6d, 7):** Use `PkgCreator` with `Acme_%NAME%`; adjust `chown` per payload.

### 6.4 Additional Patterns

The download patterns and the standard pkg recipe cover most apps. Below are optional situations that layer on top.

#### Renaming Vendor Files

Sometimes vendors ship installers with hideous filenames (`SomeVendor Premium Customer 13098 StableVersion_works-this-time.dmg`) or have such filenames inside their ZIP or DMG. This is bothersome when your recipe has steps that reference that file. Use `Copier` in the download recipe to normalize the name before it reaches the pkg step:

```yaml
  # After the file is staged in RECIPE_CACHE_DIR
  - Processor: Copier
    Arguments:
      source_path: "%RECIPE_CACHE_DIR%/SomeVendor Premium Customer 13098 StableVersion_works-this-time.dmg"
      destination_path: "%RECIPE_CACHE_DIR%/%NAME%.dmg"
      overwrite: true
```

This way the pkg recipe always sees a predictable `%NAME%.dmg` regardless of what the vendor called it this quarter. If the vendor filename includes a version string you want to capture, use a `Versioner` or `FileFinder` step before the rename. For vendor-drop files, `bin/normalize-vendor-cache.sh` in this toolkit can rename them to canonical names before AutoPkg runs.

#### Running a Script in the Package

Some deployments need a postinstall script — setting permissions, loading a launch daemon, running a vendor setup tool, etc. Use `PkgCreator` with a `scripts` directory:

```yaml
  - Processor: PkgCreator
    Arguments:
      pkg_request:
        id: "%PKG_ID%"
        version: "%version%"
        pkgname: "Acme_%NAME%"
        pkgdir: "%RECIPE_CACHE_DIR%"
        pkgroot: "%RECIPE_CACHE_DIR%/%NAME%"
        scripts: "%RECIPE_DIR%/scripts"
```

The `scripts` directory sits alongside the recipe file and contains the standard macOS installer script names:

```
recipes/VendorName/ExampleApp/
├── ExampleApp.pkg.recipe.yaml
└── scripts/
    ├── preinstall      # runs before payload is written
    └── postinstall     # runs after payload is written
```

Both scripts must be executable (`chmod +x`) and use a shebang (`#!/bin/bash` or `#!/bin/zsh`). The installer runs them as root.

#### Payloadless Packages (Script-Only)

Sometimes you need a package that runs a script but installs no files — a configuration change, a cache clear, a one-shot remediation. Use `PkgCreator` with an empty pkgroot and a `scripts` directory:

```yaml
Description: Runs ExampleApp post-configuration (no payload).
Identifier: com.acmefruit.autopkg.pkg.ExampleAppConfig
MinimumVersion: "2.3"

Input:
  NAME: ExampleAppConfig
  PKG_ID: example.acmefruit.config.ExampleApp
  VERSION: "1.0.0"

Process:
  - Processor: PkgRootCreator
    Arguments:
      pkgroot: "%RECIPE_CACHE_DIR%/empty"
      pkgdirs: {}

  - Processor: PkgCreator
    Arguments:
      pkg_request:
        id: "%PKG_ID%"
        version: "%VERSION%"
        pkgname: "Acme_%NAME%"
        pkgdir: "%RECIPE_CACHE_DIR%"
        pkgroot: "%RECIPE_CACHE_DIR%/empty"
        scripts: "%RECIPE_DIR%/scripts"
```

Payloadless packages don't have a parent download recipe — they're standalone. Version is static and bumped manually when the script changes. They're useful for deploying a configuration workaround, clearing a vendor cache, or running a one-time migration.

---

### 6.5 Getting Code Signature Info

The `requirement` string in `CodeSignatureVerifier` looks intimidating, but you don't write it by hand — you extract it from a signed copy of the app. Install the app on your Mac, then run:

```bash
codesign --display --requirements - /Applications/ExampleApp.app
```

This prints something like:

```
designated => identifier "com.example.app" and anchor apple generic
and certificate 1[field.1.2.840.113635.100.6.2.6] /* exists */
and certificate leaf[field.1.2.840.113635.100.6.1.13] /* exists */
and certificate leaf[subject.OU] = XXXXXXXXXX
```

Copy everything after `designated => ` — that's your `requirement` value, verbatim. It includes the bundle identifier, certificate chain assertions, and Team ID. Don't try to author these by hand.

To grab just the Team ID separately (useful for sanity-checking):

```bash
codesign -dvv /Applications/ExampleApp.app 2>&1 | grep TeamIdentifier
```

The requirement string looks slightly different between apps — some include a `certificate leaf[field.1.2.840.113635.100.6.1.9]` check (Mac App Store path), others don't. This depends on how the vendor signed the app (Developer ID vs. App Store vs. both). Trust what `codesign` gives you.

You only need to redo this if the vendor changes their signing certificate, which is rare and would break existing installs anyway.

> **For `.pkg` installers (4a, 4b, 5):** Use `expected_authority_names` instead of `requirement`. Extract the certificate chain with `pkgutil --check-signature /path/to/installer.pkg`. The `input_path` in `CodeSignatureVerifier` points to the `.pkg` file itself, not to an app inside it.

---

### 6.6 Using Recipe Robot

Recipe Robot can generate a starting-point recipe from an app, a download URL, or a GitHub repo page.

**When:** You are onboarding a new app that uses Patterns 1–3 (Sparkle, GitHub, or direct URL). Recipe Robot does not handle Pattern 4 (vendor-drop) or Pattern 5 (vendor `.pkg`).

**Install:**

```bash
brew install --cask recipe-robot
```

Or download from [github.com/homebysix/recipe-robot](https://github.com/homebysix/recipe-robot).

**Run from the command line** (not the GUI — gives you more control over output):

```bash
/Applications/Recipe\ Robot.app/Contents/Resources/scripts/recipe-robot \
  --ignore-existing ARG1
```

Where `ARG1` is one of:
- A path to an installed `.app` (e.g. `/Applications/Zettlr.app`)
- A download page URL (e.g. `https://www.zettlr.com/download`)
- A GitHub repo URL (e.g. `https://github.com/Zettlr/Zettlr`)

Use `--ignore-existing` so Recipe Robot always generates fresh recipes even if it finds existing ones in known repos. Without this flag it may skip generation and point you at someone else's recipe — which won't follow these conventions. For many apps at once, see `bin/rr-batch.sh` in this toolkit.

**Tip: prefer URLs over local .app paths as input.** When you feed Recipe Robot a download page or GitHub URL, it has a much better chance of detecting the update mechanism (Sparkle appcast, GitHub Releases API) and wiring up a dynamic download processor. When you point it at a local `.app` it often falls back to capturing the specific URL you originally downloaded from — which for GitHub releases means an ephemeral signed blob URL that expires within minutes.

Recipe Robot outputs plist (`.recipe`). Convert before committing:

```bash
autopkg convert-recipe-format --yaml AppName_download.recipe
autopkg convert-recipe-format --yaml AppName_pkg.recipe
```

Then rename to match conventions (§3.3), normalize identifiers, and review against the Review Checklist (§6.7). Pay particular attention to the download source check — even with URL input, Recipe Robot can still capture expired GitHub URLs that need rewriting to `GitHubReleasesInfoProvider`.

> **Recipe Robot and Microsoft `.pkg` installers.** Do not use Recipe Robot for apps distributed as vendor `.pkg` files (Pattern 5). Recipe Robot inspects package payloads to infer app identity and frequently misidentifies them — see §6.9 Errata. Hand-write Pattern 5 recipes from the skeleton in §6.2.5.

---

### 6.7 Review Checklist

Use this checklist when reviewing a new or modified recipe. Recipe Robot gets you 70% of the way — these checks catch the remaining 30%. Standards are defined in §3; this checklist verifies compliance. Most items are automated by `bin/recipe-linter.sh` (rules in `config/checks.yaml`) and `bin/autopkg-preflight.py`.

#### 1. Identifier Normalization

- [ ] Download: `com.acmefruit.autopkg.download.AppName` — never `.pkg.` in the download namespace (§3.3)
- [ ] Pkg: `com.acmefruit.autopkg.pkg.AppName`
- [ ] `ParentRecipe` in the pkg recipe matches the download Identifier exactly, character-for-character
- [ ] AppName in the identifier matches the **full app directory name** — no truncation (`MicrosoftWord` not `Word`, `MicrosoftEdgeBrowser` not `Edge`)
- [ ] No doubled segments like `com.acmefruit.pkg.pkg.X` (Recipe Robot default bug)

#### 2. Download Source + URL Scheme

`URLDownloader` is the universal download processor — it handles `https://`, `file://`, `ftp://`, and `s3://` schemes. This means the same recipe works for local staging (`file://` URIs pointing at `vendor_cache`) and remote blob stores (`https://` pointing at a CDN). Only the Input variable changes.

Inspect the download `Process` and identify which pattern and URL scheme it uses:

| What you see | Verdict |
|---|---|
| `SparkleUpdateInfoProvider` with an appcast URL | **Good.** Dynamically resolves latest. Ship it. |
| `GitHubReleasesInfoProvider` with `github_repo` | **Good.** Dynamically resolves latest. Ship it. |
| `URLDownloader` with a stable fwlink/redirect URL | **Acceptable.** Verify the URL redirects to the expected file. |
| `URLDownloader` with a `file://` URI | **Acceptable.** Valid for local vendor staging. Verify `VENDOR_CACHE_ROOT` is set. |
| `URLDownloader` with a GitHub `release-assets.githubusercontent.com` URL | **Broken.** Ephemeral signed blob URLs — expire in minutes. Rewrite to `GitHubReleasesInfoProvider`. |
| `URLDownloader` with a hardcoded versioned URL | **Fragile.** Works once, breaks on next release. Rewrite to use Sparkle/GitHub/`URLTextSearcher`. |

**`VENDOR_CACHE_ROOT` rule:** For recipes using `file://` URIs (or local vendor-cache paths), the path MUST be constructed from an Input variable `VENDOR_CACHE_ROOT` (e.g. `file://%VENDOR_CACHE_ROOT%/Vendor/App/App.pkg`). Never hardcode absolute filesystem paths — `VENDOR_CACHE_ROOT` is the single tunable that changes between environments.

#### Rewriting GitHub downloads

Replace the `URLDownloader` block with:

```yaml
- Processor: GitHubReleasesInfoProvider
  Arguments:
    github_repo: "owner/repo"
    asset_regex: "AppName-.*-arm64\\.dmg$"
    include_prereleases: false
```

#### 3. Pkg Naming — Org Prefix Rule

**Rule:** The output `.pkg` gets the org's configured prefix (`pkgname_prefix` in `config/org.yaml`, e.g. `Acme_`) if and ONLY if `PkgCreator` (i.e. `pkgbuild`) produced it. `PkgCopier` (flat vendor pkg copied as-is) = never. `Copier` (distribution vendor pkg copied as-is) = never. The prefix identifies packages the org built — it signals "this package was constructed in-house." Vendor packages that we rename or copy as-is are the vendor's signed artifact, not ours.

| Processor | Output naming | When | Examples |
|---|---|---|---|
| `PkgCreator` (pkgbuild) | `pkgname: "Acme_%NAME%"` | We built this from a payload tree | Pomelo Studio, Kiwi Capture, Orchard Analytics, AcmeSupport, Acme Audit Control |
| `PkgCopier` (flat vendor copy) | `pkg_path: "%RECIPE_CACHE_DIR%/%NAME%.pkg"` | Vendor's flat artifact, just renamed | Microsoft apps (Pattern 5) |
| `Copier` (distribution pkg copy) | `destination_path: "%RECIPE_CACHE_DIR%/%NAME%.pkg"` | Vendor's distribution artifact, copied bit-for-bit | Xerox and HP drivers, Claude, Citrix, Cisco Secure Client |
| `AppPkgCreator` | **Forbidden** | Prevents control over output filename and prefix | VS Code as generated by Recipe Robot (must fix) |

- [ ] Recipe uses `PkgCreator`? → `pkgname: "Acme_%NAME%"`
- [ ] Recipe uses `PkgCopier` or `Copier` for the output? → `%NAME%.pkg` — no prefix
- [ ] `AppPkgCreator` is NOT present in any recipe
- [ ] Version in output filename (`%version%` in `pkgname` or `pkg_path`) is NOT present — it makes deployment-pipeline references drift on every version bump (orgs that choose versioned filenames per §3.3 invert this item)
- [ ] For DMG-sourced downloads: `Copier` step present before `PkgCreator` (unless the download recipe already extracted the app)

#### 4. Architecture Targeting

- [ ] Check which architecture the recipe downloads (arm64 / x64 / universal)
- [ ] Match to your fleet (Apple Silicon Macs = `arm64`)

#### 5. Code Signature Verification — Decision Tree

Not every recipe needs `CodeSignatureVerifier`, but skipping it is always a deliberate choice. The decision tree, in order:

**Step 1 — Check the outer artifact (`.pkg` or `.dmg`):**
- [ ] If the download is a `.pkg`: run `pkgutil --check-signature <pkg>` (never `codesign` — it reports "not signed at all" on signed flat packages)
  - **Signed** → use `CodeSignatureVerifier` with `expected_authority_names` (full certificate chain from `pkgutil --check-signature` output)
  - **Unsigned** → proceed to Step 2

**Step 2 — Check for a signed `.app` inside:**
- [ ] If the download is a DMG (or an unsigned PKG containing an app): extract and run `codesign -dvv /path/to/App.app 2>&1`
  - **Has a signing authority** → use `CodeSignatureVerifier` with a `requirement` string (extracted via `codesign --display --requirements -`, never hand-authored)
  - **Not signed at all** → proceed to Step 3

**Step 3 — Pattern-based carve-out:**
- [ ] Is this Pattern 6 (rebuilt) or Pattern 7 (faux DMG)? → `NO_CODE_SIGNATURE_REQUIRED: true` — these packages may not even contain `.app` bundles; they are assembled in-house with no upstream signature to verify
- [ ] Is this Pattern 8 (Experimental)? → `NO_CODE_SIGNATURE_REQUIRED: true` — MUST document in the README an approver who signed off, date of approval, and plan for resolution. Pattern 8 is for temporary/dev unsigned `.app` bundles only; nothing should permanently live there
- [ ] Is this some other pattern where the artifact is genuinely unsigned? → `NO_CODE_SIGNATURE_REQUIRED: true` with a comment explaining WHY (e.g. "faux vendor DMG — in-house constructed", "confirmed vendor ships unsigned via `pkgutil --check-signature`")

**Rules:**
- [ ] `CodeSignatureVerifier` is present OR `NO_CODE_SIGNATURE_REQUIRED: true` is declared in Input — no silent omission
- [ ] `NO_CODE_SIGNATURE_REQUIRED: true` always has a comment explaining why
- [ ] The standard carve-out for unsigned artifacts is Patterns 6/7. Pattern 8 is reserved for unsigned `.app` bundles that have no signed version available — temporary, documented, and assigned an approver
- [ ] The publisher is pinned: the `requirement` string includes `subject.OU` (the Team ID), or `expected_authority_names` lists the chain. If the publisher has no team ID (ad-hoc signed), `teamid: "UNSIGNED_NO_TEAMID"` is set in the download recipe's `Input` with a comment saying why
- [ ] The README records the Team ID (or "no team ID") for humans
- [ ] `input_path` correct for download type:
  - `.app` bundle → DMG/ZIP sources (1b, 2b–2d, 3b, 3c, 4c, 4d)
  - `.pkg` file → vendor-pkg sources (1a, 2a, 3a, 4a, 4b, 5)
  - Payload directory → Pattern 6 (no signature by definition)
- [ ] `requirement` (`.app` sources) extracted via `codesign --display --requirements -`, never hand-authored
- [ ] `expected_authority_names` (`.pkg` sources) includes the full certificate chain (vendor leaf + Developer ID Certification Authority + Apple Root CA) — omitting the standard Apple entries produces "Mismatch in authority names" (`reference/methodology.md` item #6)

#### 6. Version Extraction

- [ ] Version is extracted somewhere in the recipe chain
- [ ] Pattern 5: version extraction happens in the pkg recipe (not the download recipe — a flat .pkg cannot be read from a mount)
- [ ] DMG/ZIP sources (1–4): version extraction happens in the download recipe via `Versioner` (Sparkle and GitHub providers also set it)
- [ ] 4a vendor-drop flat PKG: version extracted in the pkg recipe after `FlatPkgUnpacker` + `PkgPayloadUnpacker`, OR pinned in `Input`
- [ ] 4b distribution PKG: version pinned in `Input`
- [ ] Pattern 6: version is pinned as an `Input` — `%version%` referenced without an Input declaration fails at runtime (`reference/methodology.md` item #12)
- [ ] Pattern 7: version extracted from the .app inside the DMG, or pinned

#### 7. Config Files

No config file is required next to a recipe pair. If your org uses the optional `.overrides` file (§3.4):

- [ ] Everything AutoPkg needs (`version`, `authority_name`, and so on) is in the recipe's `Input`, so a bare `autopkg run` works without `.overrides`
- [ ] An `.overrides` holding a secret or deployment detail is generated by the pipeline or gitignored, never committed, and its values are in the fork's `.leak-patterns`
- [ ] Format: `key=value` lines (not YAML), `#` for comments, blank lines ignored

Deployment-pipeline metadata files are org-specific (§3.5); a fork that keeps them checks them with its own lint rules.

#### 8. Sidecar README.md

- [ ] `README.md` present in every app recipe directory
- [ ] Documents: pattern used (e.g. "Pattern 4b — distribution vendor PKG, copied as-is"), design decisions, signature status, known gaps
- [ ] For vendor-drop recipes: documents what's in `vendor_cache`, how to get new versions, and what file needs to be placed where
- [ ] For recipes with `NO_CODE_SIGNATURE_REQUIRED`: explains why (e.g. "confirmed unsigned via pkgutil --check-signature", "rebuilt package — no signature by definition")
- [ ] For recipes with non-obvious identifier choices: documents the rationale
- [ ] **Pattern 8** recipes additionally document: approver who signed off, date of approval, and plan for resolution (e.g. "waiting for vendor to sign the .app — tracked in the issue tracker")

#### 9. Pre-Commit Smoke Test

```bash
autopkg verify-trust-info AppName.download.recipe.yaml
autopkg run --check AppName.download.recipe.yaml -v
autopkg run AppName.pkg.recipe.yaml -v
```

Confirm the output file (adjust for vendor packages, which carry no prefix):

```bash
ls ~/Library/AutoPkg/Cache/*/Acme_AppName*.pkg
```

**Additional checks before committing** (this toolkit):

```bash
# Scan for unfilled template tokens
bin/scan-placeholders.sh --repo <repo> AppName

# Run preflight checks (static rules + methodology bug patterns)
bin/autopkg-preflight.py --app <app-dir>
```

---

### 6.8 Pattern Reference

The pattern system uses **two-axis classification**: the **number** describes the **source** (how the artifact is acquired), and the **letter** describes the **output artifact type** (what kind of file emerges and how it is processed).

**Axis 1 — Number = Source:**

| # | Source | When to use |
|---|--------|-------------|
| 1 | Sparkle appcast | App has a Sparkle update feed (most native Mac apps) |
| 2 | GitHub release | Vendor publishes releases as binary assets on GitHub |
| 3 | Direct URL | Vendor hosts the installer at a known URL — 3a/3b stable URL (pkg / DMG), 3c scraped URL |
| 4 | Vendor-provided file | Vendor hands you a file directly — no public URL, behind a login wall, emailed, etc. |
| 5 | Vendor PKG via stable URL | Vendor publishes a signed `.pkg` at a stable fwlink/redirect URL (common with Microsoft) |
| 6 | Rebuilt package | An installed package exists but its source files do not — extract and rebuild from the payload |
| 7 | Faux vendor DMG | An in-house constructed DMG (typically from a snapshot tool such as Jamf Composer) wrapping a vendor app or binary |
| 8 | Experimental | Unsigned `.app` bundle for dev/internal purposes with no signed version available. **Nothing should permanently live here** — requires a documented approver and resolution plan |

**Axis 2 — Letter = Output Artifact Type.** Pattern 4 uses the full letter set, which serves as the reference:

| Letter | Output type | Output processor | Org prefix? |
|---|---|---|---|
| a | Vendor `.pkg` — carried through as-is | `PkgCopier` | No |
| b | Distribution vendor `.pkg` — copied as-is (not `PkgCopier`-safe) | `Copier` | No |
| c | DMG or app bundle — extracted and rebuilt | `PkgCreator` | Yes |
| d | DMG/app + ridealong scripts/payload | `PkgCreator` with `scripts:` | Yes |
| e | ZIP with ridealong config | Depends | Depends |

Other sources only get the variants that make sense for them, lettered in order — so `2b` and `3b` are "DMG/app, rebuilt" (Pattern 4's `c`), and Pattern 6's letters describe payload shape rather than the table above. Patterns 5, 7, and 8 have no sub-variant because their source always produces the same artifact type. When in doubt, the Master Pattern Table below is authoritative.

#### The org prefix rule

**The output `.pkg` filename gets the org prefix (`Acme_%NAME%`) if and ONLY if `PkgCreator` (i.e. `pkgbuild`) produced it.** `PkgCopier` (flat vendor copy) = never. `Copier` (distribution pkg copy) = never. The processor table and checklist are in §6.7 item 3.

#### Master Pattern Table

| # | Source | Variant | Output artifact | Output processor | Org prefix? | Examples |
|---|---|---|---|---|---|---|
| 1a | Sparkle appcast | Vendor .pkg | Vendor .pkg | `PkgCopier` | No | — |
| 1b | Sparkle appcast | DMG/app | DMG/app bundle | `PkgCreator` | Yes | — |
| 2a | GitHub release | Vendor .pkg | Vendor .pkg | `PkgCopier` | No | — |
| 2b | GitHub release | DMG/app | DMG/app bundle | `PkgCreator` | Yes | Zettlr, Hammerspoon, draw.io, Moonlight, Raspberry Pi Imager, Pearcleaner |
| 2c | GitHub release | DMG/app + ridealong | DMG/app + scripts/payload | `PkgCreator` with `scripts:` | Yes | — |
| 2d | GitHub release | Source ZIP + ridealong | ZIP → unpack + reassemble | `PkgCreator` | Yes | Fruta New-Hire Starter Kit (new; by analogy with 4e) |
| 3a | Stable direct URL | Vendor .pkg | Vendor .pkg | `PkgCopier` | No | — |
| 3b | Stable direct URL | DMG/app | DMG/app bundle | `PkgCreator` | Yes | VS Code, Smartsheet, Firefox, Google Chrome |
| 3c | Scraped direct URL | DMG/app | DMG/app bundle | `PkgCreator` | Yes | Orange Data Mining |
| 4a | Vendor-provided file | Vendor .pkg | Vendor .pkg, copied as-is | `PkgCopier` | No | (no dedicated examples yet) |
| 4b | Vendor-provided file | Distribution vendor .pkg | Distribution .pkg, copied as-is | `Copier` | No | Most vendor-drop PKGs: HP and Xerox drivers, Claude, Citrix, Cisco Secure Client |
| 4c | Vendor-provided file | Vendor DMG | DMG → extract + rebuild | `PkgCreator` | Yes | Orchard Analytics (Acme) |
| 4d | Vendor-provided file | DMG + ridealong | DMG → extract + scripts/payload | `PkgCreator` with `scripts:` | Yes | Kiwi Capture (Acme template) |
| 4e | Vendor-provided file | ZIP + ridealong | ZIP → unpack + reassemble | Depends | Depends | (none currently; e.g. a VPN client with site config) |
| 5 | Vendor PKG via stable URL | — | Vendor .pkg, copied as-is | `PkgCopier` | No | Microsoft apps |
| 6a | Rebuilt from existing | Flat payload | Payload directory → rebuild | `PkgCreator` | Yes | Acme Login Banner, a Defender LaunchDaemon config |
| 6b | Rebuilt from existing | Payload + scripts | Payload + scripts → rebuild | `PkgCreator` with `scripts:` | Yes | AcmeSupport, Acme Quarantine Helper, Pomelo Studio user data |
| 6c | Rebuilt from existing | Single file | One file, specific mode | `PkgCreator` with `chown mode:` | Yes | Acme Wallpaper, Acme Audit Control |
| 6d | Rebuilt from existing | Payloadless | Script-only, empty pkgroot | `PkgCreator` with empty pkgroot | Yes | Acme UninstallAgent, Pomelo Studio LaunchAgent |
| 7 | Faux vendor DMG | — | DMG wrapping vendor app/binary | `PkgCreator` | Yes | Pomelo Studio (Acme template) |
| 8 | **Experimental** | — | Unsigned .app for dev/internal | `PkgCreator` | Yes | — |

#### Code signature verification (summary)

**Step 1 — Check the outer artifact:** If the download is a `.pkg`, run `pkgutil --check-signature`. If signed, use `expected_authority_names`.

**Step 2 — Check inside for a signed `.app`:** If the download is a DMG (or an unsigned PKG with an .app inside), extract and run `codesign -dvv`. If signed, use a `requirement` string.

**Step 3 — Pattern carve-out:** Patterns 6 and 7 (rebuilt/faux DMG) may not even contain `.app` bundles — use `NO_CODE_SIGNATURE_REQUIRED: true`. Pattern 8 (Experimental) is the only carve-out for unsigned `.app` bundles, and requires approver documentation. Full rules: §6.7 item 5.

#### Quick Reference

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
Snapshot (e.g. Jamf Composer) wrapped as DMG ..... Pattern 7
Unsigned dev .app with no upstream signing ....... Pattern 8 (temporary — must have approver)
```

---

### 6.9 Errata & Troubleshooting

Real failures encountered during recipe development. Each entry describes what went wrong, why, and the fix.

#### Recipe Robot Misidentifies Microsoft PKG Installers

**Affected apps:** Microsoft Teams, Microsoft 365 Copilot, Microsoft Company Portal.

**What happened:** Recipe Robot v2.5.0 inspects package payloads to infer app identity. Several Microsoft `.pkg` installers bundle AutoUpdate components alongside the primary app. Recipe Robot picks AutoUpdate because it appears first in the payload scan, generating recipes with wrong Identifiers and app references. For Company Portal specifically, this broke autochecking — the recipe was monitoring the wrong app's version.

**Fix:** Hand-write the recipe following the Pattern 5 skeleton (§6.2.5). Do not trust Recipe Robot output for Microsoft `.pkg` installers. Record the specific misidentification in an `*_ERRATA.md` file in the app's recipe directory.

#### Microsoft Edge — Versioned Internal Package Path

**Affected apps:** Microsoft Edge (and any vendor whose inner `.pkg` component name includes a version number).

**What happened:** Recipe Robot v2.5.0 hardcoded the internal package path including the version number:

```
pkg_payload_path: '%RECIPE_CACHE_DIR%/unpacked/MicrosoftEdge-147.0.3912.86.pkg/Payload'
```

When Microsoft released Edge 147.0.3912.98, the internal directory changed to `MicrosoftEdge-147.0.3912.98.pkg` and `PkgPayloadUnpacker` failed because the hardcoded path no longer existed. Other Microsoft apps (Word, Excel, Outlook) use static internal names (`Microsoft_Word.pkg`) and were unaffected.

**What didn't work:**
- Glob patterns in `PkgPayloadUnpacker` — the processor treats `*` as a literal character, not a wildcard.
- `VariableGenerator` processor — does not exist in standard AutoPkg.
- Custom `ShellScriptProcessor` — does not exist in standard AutoPkg; custom processors also undermine the recipes-as-code model.

**Fix:** Insert a `FileFinder` step between `FlatPkgUnpacker` and `PkgPayloadUnpacker`:

```yaml
  - Processor: FileFinder
    Arguments:
      pattern: "%RECIPE_CACHE_DIR%/unpacked/*MicrosoftEdge*.pkg"

  - Processor: PkgPayloadUnpacker
    Arguments:
      pkg_payload_path: "%found_filename%/Payload"
```

`FileFinder` accepts glob patterns and stores the matched path in `%found_filename%`. The recipe now works with any Edge version without manual updates.

**Lesson:** If any path inside a package structure contains a version number, use `FileFinder`. Neither hardcoded paths nor `FileFinder` patterns are bulletproof — hardcoded paths break when vendors add version numbers, glob patterns break when vendors change naming schemes. Pick the one that matches the vendor's current structure and monitor for breakage.

#### VS Code — The Odd One Out

**Affected apps:** Microsoft Visual Studio Code.

**What happened:** VS Code is the only common Microsoft app that ships as a DMG, not a `.pkg` — and it doesn't use a Microsoft fwlink. There is no obvious stable download URL on Microsoft's own pages. Finding the correct stable URL (`https://code.visualstudio.com/sha/download?build=stable&os=darwin-universal-dmg`) required testing multiple candidate URLs, cross-referencing a public community AutoPkg recipe as a sanity check, and verifying that re-running the recipe with that URL returned the expected app.

On top of the download URL issue, Recipe Robot generated the pkg recipe using `AppPkgCreator`, which controls the output filename and prevents org-prefix naming.

**Fix:** Use the stable VS Code download URL above. Replace `AppPkgCreator` with `Copier` + `PkgCreator` as documented in the Review Checklist (§6.7, item 3). Since VS Code is a DMG at a stable URL, it follows Pattern 3b — not Pattern 5.

#### AppPkgCreator Prevents Org-Prefix Naming

**Affected apps:** Any Recipe Robot–generated pkg recipe (VS Code above is the typical case).

**What happened:** `AppPkgCreator` derives the output filename from the app bundle itself. There is no `pkgname` argument, so the org prefix (§6.7 item 3) cannot be applied and the output name is outside the recipe author's control.

**Fix:** Replace it with `Copier` + `PkgCreator` (§6.3). The linter rejects `AppPkgCreator` in any recipe.

#### Download Identifier Namespace Collision

**Affected apps:** Microsoft Edge, Microsoft Word, Microsoft Visual Studio Code, and any Recipe Robot–generated recipe where the download produces a `.pkg` or DMG.

**What happened:** Recipe Robot v2.5.0 generates download recipe Identifiers as `com.acmefruit.autopkg.pkg.download.AppName` — inserting `.pkg` into the namespace because it detects the download artifact is a `.pkg` file. This collides with the `com.acmefruit.autopkg.pkg.AppName` namespace reserved for pkg recipes. The same generator also produces doubled segments such as `com.acmefruit.pkg.pkg.AppName`.

**Correct Identifier:** `com.acmefruit.autopkg.download.AppName` — the download Identifier never contains `.pkg` regardless of what file type is downloaded.

**Fix:** Correct the Identifier after Recipe Robot generation (`bin/rr-batch.sh` in this toolkit sets every Identifier from the org prefix and the app name as it files the recipes). The linter flags both forms.

#### Expired GitHub Blob URLs

**Affected apps:** Any recipe generated by pointing Recipe Robot at a GitHub Releases download.

**What happened:** Recipe Robot captures the specific `release-assets.githubusercontent.com` URL from the asset you downloaded. These are ephemeral signed URLs that expire within minutes. The recipe works exactly once.

**Fix:** Replace `URLDownloader` with `GitHubReleasesInfoProvider`. See Pattern 2 (§6.2.2) and the Review Checklist (§6.7, item 2).

#### Microsoft Fwlink Confusion

**Affected apps:** Microsoft Teams, Microsoft Company Portal.

**What happened:** Microsoft offers multiple `fwlink` redirect URLs for the same product — different variants, different macOS version targets, different eras. Two specific problems:

- **Teams — Classic vs. New.** Microsoft maintains separate fwlinks for Classic Teams (`com.microsoft.teams`, deprecated) and New Teams (`com.microsoft.teams2`). Using the wrong `linkid` downloads an outdated or incompatible variant. Direct CDN URLs (`statics.teams.cdn.office.net`) are version-specific and don't auto-update.
- **Company Portal — bad fwlink.** The initial fwlink used for Company Portal pointed to the wrong package. Finding the correct stable endpoint required digging through Microsoft's documentation.

**Fix:** Verify fwlink targets with `curl -LI <url>` before committing — confirm the redirect chain ends at the expected file. Document the confirmed `linkid` in the recipe's `Comment` field. Known good fwlinks:

| App | linkid | Notes |
|-----|--------|-------|
| Teams (New) | `869428` | All supported macOS versions |
| Company Portal | — | Confirm the current linkid against Microsoft's documentation before use |

#### Pomelo Studio — Non-Standard Vendor Installer, Snapshot Workaround

**Affected apps:** Pomelo Studio (PomeloSoftware; fictional, the Acme worked example).

**What happened:** Pomelo Studio's vendor installer is not a standard DMG containing a simple .app. It ships as a wrapper installer app ("Install Pomelo Studio.app") inside a DMG — an installer program, not the app itself. AutoPkg's standard processors (`Copier` with glob, DMG extraction) cannot pull the real .app out of that format.

**Workaround (original):** Capture the installed state with a before/after snapshot tool (e.g. Jamf Composer) and wrap the snapshot in a DMG. This became a Pattern 7 (Faux Vendor DMG) recipe that stages the DMG from `vendor_cache`, extracts the .app via `Copier`, and rebuilds with `PkgCreator`.

**Later:** if a public community recipe for the app appears — one that downloads directly from the vendor, supports auto-versioning and removes the need for snapshots — audit it (§6.10.2) and, if it passes, adopt it in place of the faux DMG. Keep the audit alongside the recipe (§6.10.4).

**Lesson:** Not all vendor installers are AutoPkg-compatible. Check community recipes first before building a Pattern 7 faux DMG. If a community recipe passes the §6.10.2 audit, adopt it (§6.10.3).

#### Pomelo Studio — Three Independent Components in One Snapshot

**Affected apps:** Pomelo Studio (fictional).

**What happened:** The snapshot taken for the workaround above held three unrelated components, not just the app:
- The Pomelo Studio app (a `.app` bundle installed under `/Applications/Pomelo Studio 4/`)
- A LaunchAgent plist (`/Library/LaunchAgents/com.pomelosoftware.studio.helper.plist`)
- User preference files (`~/Library/Preferences/PomeloSoftware/*`)

All three had different update cycles, different owners, and different maintenance needs. Combining them into one recipe would require rebuilding the entire snapshot for any change to any component.

**Solution:** Split into three independent recipe sets:
- **Pomelo Studio** (Pattern 7 — Faux Vendor DMG): the .app wrapped as a faux DMG, as above.
- **Pomelo Studio LaunchAgent** (Pattern 6d — Payloadless/Script-Only): the plist deployed as a standalone package.
- **Pomelo Studio user data** (Pattern 6b — Payload + Scripts): user preferences deployed via a postinstall script from `/tmp/` to each user's home directory.

**Lesson:** When a snapshot contains multiple components with independent update cycles, split them into separate recipe sets. Any one can then change without rebuilding the others.

---

### 6.10 Design Patterns: Slices, Equivalence Audit and Adoption

These are not recipe-level decisions — they are design choices that affect how you structure an entire app's recipe set.

#### 6.10.1 Slicing Complex Apps

**Purpose:** Complex apps often bundle content with different origins, install targets, or update cadences into a single package. Slicing splits them into independent recipe sets so each component can be maintained, updated, and deployed independently.

**Slice by default.** Anything the org adds to a vendor's app — a license file, a config file, a LaunchAgent, a setup script — gets its own recipe whose package installs after the app's:

- **Required** when the vendor artifact is a sealed, signed `.pkg` deployed as-is (1a, 2a, 3a, 4a, 4b, 5, or a vendor `.pkg` inside a DMG/ZIP). A sealed vendor package is never opened; rebuilding it discards the vendor's signature.
- **Preferred** when the app is rebuilt from a DMG, `.app` or ZIP that holds only the app. A slice that drops the license or config into place is far simpler than rebuilding the app package around it on every app update.
- A same-package ridealong (2c, 4d, 4e when rebuilt) is the exception, for an extra that cannot work as a separate package; document why in the recipe README.

**Install order.** A slice installs after the package that establishes the folder it writes into — normally the app package first, then the slices that add to it. Record it in the slice's README as **Install after:** `<org prefix><App>.pkg`. Extras normally live outside the app bundle. In the rare case a vendor insists on a file inside `/Applications/<App>.app/…`, the slice must also be re-run after every app update (the update replaces the bundle), and writing into a signed bundle invalidates its code signature — note both in the slice's README.

**Reasons to slice:**

| Reason | Example |
|--------|---------|
| **Different update cadence** | The .app releases quarterly; support data files rarely change between versions. Pomelo Studio vs. its LaunchAgent (stable for years). |
| **Different install volume** | Recent macOS releases reject flat packages that span the sealed system volume and the data volume (`/Users/`). Splitting into per-volume packages avoids this restriction. |
| **Different origin** | The .app can be downloaded from the manufacturer (automated, code-signed). Support files exist only as snapshot artifacts (vendor-drop). |
| **Different ownership** | Each team owns its component. Slicing lets each deploy independently without coordinating releases. |
| **Independent rollback** | Each slice can be rolled back independently if a component causes issues. |

**How each reason maps to a practical decision:**

```
Upstream package contains → .app (from vendor) + license (from IT) + launchagent (created internally)
                                 ↓
                     Split because? Different origins, different install paths, different owners
                                 ↓
Slices:   App recipe (download from vendor, CodeSignatureVerifier)     ← Pattern 2b, 3b, 4c, or adapted community
          License recipe (vendor-drop from vendor_cache)               ← Pattern 4d / 6c
          LaunchAgent recipe (vendor-drop payload)                     ← Pattern 6d
```

**Slice recipe patterns by content type:**

| Content type | Likely pattern | Examples |
|-------------|---------------|----------|
| .app bundle (downloadable from vendor) | 2b, 3b, or community-adapted | Microsoft apps, community-adopted recipes |
| .app bundle (vendor-drop DMG) | 4c, 7 | Orchard Analytics, Pomelo Studio |
| License / config file (vendor-drop) | 4d ridealong or 6c | Kiwi Capture license (4d), Orchard Analytics license (6c) |
| LaunchAgent / script-only | 6d | Pomelo Studio LaunchAgent, a VPN client's LaunchDaemon |
| User data payload | 6b | Pomelo Studio user data |

#### 6.10.2 Equivalence Audit

**What it answers:** "Is the package this recipe builds the same product, from the same
vendor, as the thing we're replacing or trusting?" Three checks do most of the work:
**signature** (same vendor), **contents** (the bill of materials) and **version** (same
product family).

**When:** optional, and worth doing whenever you have something to compare against:

| Situation | Prior art (what you compare against) |
|---|---|
| Adopting a community recipe (§6.10.3) | The package your org deploys today, if any; otherwise mode B below |
| Replacing a package your org already deploys (Pattern 6, 7, or a vendor drop) | The old package |
| A new recipe, no prior art | The vendor's own download, fetched and installed by hand (mode B) |

Skipping it is a choice, not an oversight: if you skip, say so in the recipe's README.
It matters most for anything more involved than "stable URL → pre-cut pkg/dmg/zip",
and it can save a faux DMG entirely (§6.9).

**The checks and their tolerance:**

| # | Check | Tolerance | Passes | Raise with a person |
|---|---|---|---|---|
| 1 | **Signature** (same vendor) | **None** | Same Team ID and the same signing chain on both | Any difference: stop. A different Team ID is a different publisher. |
| 2 | **Contents** (bill of materials) | **Directional** | The prior package has *more* files (an old custom build usually added a license, config or LaunchAgent). Files differ *inside* the app bundle (a newer version changes its insides). | Every file only in the prior package is an **org addition**: name it and give it a slice (§6.10.1). Any file only in the candidate and **outside** the app bundle is possible hidden payload: find out what it is. |
| 3 | **Version** (same product family) | **Same major line** | 26.0.1 → 26.3.3, 2026.0.1 → 2026.3.3 | A jump across lines (14.x → 2027.2.1). Check before building: does the new version still run on your fleet (its `LSMinimumSystemVersion` against `fleet_min_macos` in `config/org.yaml`)? Does your license cover it? Was the product renamed, rebased or split into editions? |
| 4 | **Source** (community recipes only) | **None** | The download resolves to the vendor's own domain | Anything else (mirrors, re-hosts, shorteners) |

A version jump is the dangerous one: a "latest" recipe will happily package something
the fleet can't run or the org isn't licensed for. If the answer is "stay on the old
line", **pin** the line in the recipe (an `asset_regex`, URL or search pattern that only
matches it) and say why in the README.

**Mode A: with prior art**

```bash
# 1. Signature: both must show the same Team ID
pkgutil --check-signature old.pkg                 # a .pkg
pkgutil --check-signature new.pkg
codesign -dvv "/path/Old.app" 2>&1 | grep -E 'Authority|TeamIdentifier'   # an .app
codesign -dvv "/path/New.app" 2>&1 | grep -E 'Authority|TeamIdentifier'

# 2. Contents: file lists, owners and scripts, side by side
bin/pkg-compare.sh --old-pkg old.pkg --new-pkg new.pkg
#    or by hand: only-in-old = org additions; only-in-new outside the .app = look closer
pkgutil --expand old.pkg /tmp/old && find /tmp/old -name Bom -exec lsbom -s {} \; | sort > /tmp/old.txt
pkgutil --expand new.pkg /tmp/new && find /tmp/new -name Bom -exec lsbom -s {} \; | sort > /tmp/new.txt
comm -23 /tmp/old.txt /tmp/new.txt                # only in the old package
comm -13 /tmp/old.txt /tmp/new.txt | grep -v '\.app/'   # only in the new one, outside the app

# 3. Version: same major line?
/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "/path/Old.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "/path/New.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Print :LSMinimumSystemVersion'     "/path/New.app/Contents/Info.plist"
```

For a `.app` inside a package or DMG, expand or mount it first (`pkgutil --expand-full`,
`hdiutil attach -nobrowse -readonly`), and detach afterwards.

**Mode B: no prior art**

Compare what AutoPkg built with what the vendor gives anyone who downloads it by hand.

1. **Fetch by hand.** Download the vendor's file yourself, from the vendor's page. Check 1
   and 3 against the file AutoPkg downloaded (in
   `~/Library/AutoPkg/Cache/<identifier>/downloads/`): same Team ID, same version.
2. **Install both ways** on two clean test Macs (or one, restored between runs): the
   vendor's installer or drag-to-Applications on one, your built package on the other.
3. **Compare what landed:** `pkgutil --pkgs | grep -i <vendor>` then
   `pkgutil --files <package-id>`; `bin/capture-perms.sh "/Applications/<App>.app"
   --relative` on both, then `diff` the two outputs; the file count of the app bundle.
4. **Run it:** the app launches, and `spctl -a -vv "/Applications/<App>.app"` reports it
   accepted (notarized). Anything the vendor's install did that yours didn't (a helper,
   a LaunchDaemon, a first-run prompt for privileges) is a finding for the README.

**Outcome:** all checks pass → adopt or replace. A check raised → a person decides, and
the decision goes in the README (pin the major line, get the license, add the slice).
The signature check fails → don't use it; fall back to a vendor drop or faux DMG.

**Why it's worth the effort:** examining prior art never hurts, provided it is correctly
licensed and can be adapted without black boxes you can't prove equivalent. The cost is
one `autopkg run` plus a comparison; the savings are the hours of faux-DMG
construction, vendor-cache upkeep and version-update busywork a working recipe
eliminates, and the fleet incident a wrong-version build would have caused.

#### 6.10.3 Adoption Rule: Duplicate, Don't Override

When a community recipe passes the audit (§6.10.2):

1. **Copy** the community recipe files into your recipe tree — do NOT create AutoPkg overrides. Copy **the whole chain**: every parent recipe it needs is reproduced here too. A House Special repo runs on its own; it never references a recipe that lives elsewhere (lint rule IDN-006).
2. **Convert** plist recipes to `.yaml` format if they aren't already
3. **Adapt** to this standard:
   - Rename identifiers **and** `ParentRecipe` to `com.acmefruit.autopkg.{download,pkg}.AppName` (the org's configured `identifier_prefix`)
   - Add a `VENDOR_CACHE_ROOT` Input variable if a vendor-drop fallback is needed
   - Apply the org prefix convention via `PkgCreator` (§6.7 item 3)
   - Record the **stock** owner of shared folders in `chown`, e.g. `Applications` as `root:admin` (see `docs/package-ownership.md`)
   - Add the sidecar README (§6.7 item 8)
4. **Commit** the full copy — the recipe is now yours to maintain and modify

**Credit the original in two places:**
- a comment at the top of each adopted recipe, naming the original author, the source
  repo, the original identifier and its license, e.g.
  ```yaml
  # Adapted from com.github.<author>.download.<App> by <author>
  # (github.com/autopkg/<author>-recipes, <license>). Rebadged and changed for
  # House Special; see README.md for what changed.
  ```
- the sidecar README, with what you changed and why.

**Why duplicate instead of override:**
- Overrides depend on the community repo being added and reachable at build time
- Overrides can't modify `Process:` steps, only `Input:` variables — you can't adapt the recipe logic itself
- A copied recipe can be freely modified to add slices, change processors, or fix version-extraction paths without being constrained by the original's structure
- The community recipe becomes a reference; your copy is the source of truth

If the community recipe's download URL ever breaks, you can fall back to vendor-drop by pointing `VENDOR_CACHE_ROOT` at your `vendor_cache` file — the recipe structure stays the same; only the download source changes.

#### 6.10.4 Audit Artifacts

Every equivalence audit (§6.10.2) produces structured documentation in an `audit/` directory kept next to the adopted recipe (or in a separate research area of the repo, e.g. `research/<Vendor>/<App>/audit/`):

```
recipes/<Vendor>/<App>/audit/
├── 00-upstream-bom.md          ← Upstream BOM summary
├── 01-upstream-codesign.md     ← Upstream codesign findings
├── 02-upstream-packageinfo.md  ← Upstream PackageInfo
├── 03-community-bom.md         ← Community BOM summary
├── 04-community-codesign.md    ← Community codesign findings
├── 05-community-packageinfo.md ← Community PackageInfo
└── 06-comparison.md            ← Side-by-side with a verdict per §6.10.2
```

"Upstream" is the prior art: the package your org deploys today. "Community" is the
candidate: the community recipe's output, or your own new recipe's. For mode B (no
prior art), the record is shorter:

```
recipes/<Vendor>/<App>/audit/
├── 00-vendor-download.md       ← The hand-fetched file: signature, version
├── 01-autopkg-build.md         ← What the recipe downloaded and built: signature, version
├── 02-install-compare.md       ← What each install put on disk; launch and Gatekeeper
└── 03-comparison.md            ← Verdict per §6.10.2
```

Each artifact is a short Markdown file — one key finding per doc, not a novel. For BOMs with 10k+ files, collapse directories to one representative entry per subtree type and record the total count. Example:

```markdown
# Upstream BOM — Pomelo Studio
- Total payload files: 20,077
- Total payload size: ~89 MB

## /Applications/Pomelo Studio 4/
### Pomelo Studio 4.app/
- 1 app bundle (~30 MB binary)
- Code-signed (see 01-upstream-codesign.md)

### Support directories (collapsed — 15k+ files total)
| Path | File count | Type |
|------|-----------|------|
| Brushes/ | ~2,100 | .pbrush brush files |
| Palettes/ | ~400 | .ppal palette files |
| Templates/ | ~800 | .ptpl template files |
| Fonts/ | ~400 | .otf font files |
| Share Extension/ | 1 | .appex |
| ... | ... | ... |

### Documents
- Pomelo Studio User Guide.pdf (7.3 MB), License Agreement.txt, Readme.txt
```

---

### Common Processors Quick Reference

| Processor | When to use |
|---|---|
| `SparkleUpdateInfoProvider` | App has a Sparkle appcast |
| `GitHubReleasesInfoProvider` | GitHub Releases with binary assets |
| `URLDownloader` | Fetch a resolved URL — `https://` or `file://` into `vendor_cache` |
| `URLTextSearcher` | Scrape a webpage for a download link (3c) |
| `FileFinder` | Discover paths with glob patterns when internal structure varies between releases |
| `Copier` | Copy files between paths (DMG → pkgroot, rename, distribution-pkg output for 4b) |
| `Unarchiver` | Downloaded file is .zip / .tar.gz |
| `FlatPkgUnpacker` | Extract a flat `.pkg` to inspect its contents (Pattern 5, 4a) |
| `PkgPayloadUnpacker` | Extract an inner package's Payload to read the `.app` bundle (Pattern 5, 4a) |
| `Versioner` | Read the version from an `Info.plist` |
| `CodeSignatureVerifier` | Always include unless a documented carve-out applies (§6.7 item 5) |
| `PkgRootCreator` | Create an empty pkgroot for payloadless packages (6d). There is no core `PathCreator`. |
| `PkgCreator` | Build a .pkg with the org prefix (use instead of `AppPkgCreator`) |
| `PkgCopier` | Copy a flat vendor `.pkg` as-is (1a, 2a, 3a, 4a, 5) — not for distribution packages |
| `AppPkgCreator` | **Do not use** — no control over output filename |

---

## 7. Overrides

Use `recipe_overrides/` for overrides of community recipes that you run unmodified (customized Input variables like download URLs or package names). If you need to change a community recipe's `Process`, copy it instead (§6.10.3).

Generate an override on your Mac:

```bash
autopkg make-override Firefox.pkg -d autopkg/recipe_overrides/
```

---

## 8. Workflow

The build workflow (in this example, a GitHub Actions "AutoPkg — Build Package" workflow) runs on a macOS runner and:

1. Installs AutoPkg
2. Adds the repo's `recipes/` directory as a search directory
3. Runs the specified recipe
4. Uploads the .pkg as a build artifact
5. Optionally uploads it to the org's MDM (e.g. Jamf Pro)

Promotion between environments (org-specific, §3.5) goes through your deployment pipeline and your org's change process.

---

## 9. Staging Vendor Binaries

**When:** You are using Pattern 4 (vendor-provided file) recipes, or any recipe that reads from `vendor_cache` (6, 7, 8). The file must be checked into the repo's vendor cache before the recipe can run — that is the only way to get vendor-drop installers onto the CI runner. In-house inputs go under `vendor_cache/AcmeFruitCo/` (the org's `vendor_dir`).

**Steps:**

1. Obtain the installer from the vendor (DMG, PKG, or ZIP).
2. Rename it to match the recipe's expected filename — the path in the recipe's `DOWNLOAD_URL` / `LOCAL_FILE_PATH` Input, usually `<Vendor>/<App>/<App>.dmg` or `.pkg`.
3. Drop the file into `build/vendor_cache/<Vendor>/<App>/`.
4. If the download recipe pins `version` in its `Input`, update it. A recipe that reads the version from the file (with `Versioner`) needs no change. Add `.rebuild_this` if the workflow uses sentinels.
5. Commit and push:

```bash
cd <your-recipe-repo>
git add build/vendor_cache/OrchardLabs/Orchard-Analytics/Orchard-Analytics.dmg
git commit -m "Orchard Analytics 3.2.1 — vendor binary update"
git push
```

The CI workflow picks up the file on the runner because it's checked into the repo. The recipe's `VENDOR_CACHE_ROOT` (default `%RECIPE_DIR%/../../../build/vendor_cache`) resolves to it at build time. `bin/sync-vendor-cache.sh` and `bin/normalize-vendor-cache.sh` in this toolkit help keep a local cache in shape.

### Git LFS

Vendor binaries can be 100MB+. Configure Git LFS to track `build/vendor_cache/**` so large files are stored as LFS pointers and fetched on demand. Until LFS is configured, keep vendor binaries under GitHub's 100MB file size limit.

### What goes where

| Directory | Contents | Committed to git? |
|-----------|----------|--------------------|
| `build/vendor_cache/<Vendor>/` | Vendor-provided DMGs/PKGs/ZIPs — inputs to Pattern 4 recipes | Yes (Git LFS for large files) |
| `build/vendor_cache/AcmeFruitCo/` | In-house inputs — payloads and snapshots for Patterns 6–8 | Yes (Git LFS for large files) |
| `build/output/` | Built packages (`Acme_AppName.pkg`, or `AppName.pkg` for vendor copies) — produced by CI | No (`.gitignore`'d) |

---

## 10. Tools Reference

A recipe repo usually carries a few helpers of its own under `tools/` (for example a plist-to-YAML recipe converter). This toolkit provides the authoring and checking tools referenced throughout this document:

| Tool | Location | Purpose |
|------|----------|---------|
| `recipe-linter.sh` | `bin/` | Lints YAML recipes against the rules in `config/checks.yaml` |
| `checks.yaml` | `config/` | Lint rule definitions; each rule's `prompted_by:` cites a section of this document |
| `org.yaml` | `config/` | Org naming values (§3.3) |
| `autopkg-preflight.py` | `bin/` | Author-side preflight: audit checks plus the linter for one app or a whole repo |
| `scan-placeholders.sh` | `bin/` | Finds unfilled template tokens in recipes (and in `.overrides`, if present) |
| `classify-recipe.sh` | `bin/` | Reports which pattern (number + letter) a recipe directory follows |
| `init-recipe-repo.sh` | `bin/` | Creates the §2 directory shape for a new recipe repo |
| `pkg-reverse.sh` / `blueprint-to-recipe.sh` | `bin/` | Pattern 6: explode an existing package and draft a recipe from it |
| `pkg-compare.sh` | `bin/` | Compares an original package with a rebuilt one |
| `rr-batch.sh` | `bin/` | Run Recipe Robot in bulk and normalize its output (§6.6) |
| Pattern templates | `templates/` | Starting points for Patterns 4–7 |
| Methodology notes | `reference/methodology.md` | The failures behind the vendor-drop rules in §6.2.4 and §6.7 |

---

## 11. Document History

This document is maintained alongside the toolkit; see the repository's git history for changes. Forks should record their own adaptations here.
