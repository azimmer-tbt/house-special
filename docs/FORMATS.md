# Formats: data file schemas

This page defines the data files in a customer workspace (`customer/<name>/`),
the customer registry (`config/customers.yaml`) and a recipe repo. [customer-contract.md](customer-contract.md) covers which
files are required, which tool reads each one, and what is tracked in git. The
examples here come from the worked example in
[`customer/acme/`](../customer/acme/README.md).

---

## 1. `customer/<name>/autopkg-recipes.csv`

The progress tracker: one row per app. **No script reads it.** It's for people
(and spreadsheets), so you can add columns at the end without breaking anything.
The columns below are the ones the Acme example uses; keep them in this order.

| CSV header | Type | Description | Example |
|---|---|---|---|
| `active` | `yes` or empty | Being worked on, or has a recipe | `yes` |
| `vendor` | string | Vendor directory name under `recipes/` | `MoonlightGameStreaming` |
| `app name` | string | App directory name (hyphens, no spaces) | `Moonlight` |
| `pattern` | string | Pattern code (see [patterns.md](patterns.md)) | `2b` |
| `source` | string | Where the installer comes from | `GitHub release DMG` |
| `package filename` | string | The package the recipe builds or copies | `Acme_Moonlight.pkg` |
| `built in-house` | `yes` / `no` | The org builds this, not a vendor | `no` |
| `recipe created` | `yes` or empty | A recipe pair exists | `yes` |
| `build tested` | `yes` or empty | An `autopkg run` has built it | `yes` |
| `committed` | `yes` or empty | Committed to the recipe repo | `yes` |
| `notes` | string | Free text | `Canonical drag-to-Applications DMG.` |

```csv
active,vendor,app name,pattern,source,package filename,built in-house,recipe created,build tested,committed,notes
yes,MoonlightGameStreaming,Moonlight,2b,"GitHub release DMG",Acme_Moonlight.pkg,no,yes,yes,yes,"Canonical drag-to-Applications DMG."
,Microsoft,Microsoft-Word,5,"Stable fwlink URL (vendor pkg)",Microsoft-Word.pkg,no,,,,"Use the template example."
```

Packages copied unchanged from the vendor (Patterns 4a, 4b, 5) keep the
vendor's name, so they carry no org prefix.

---

## 2. `customer/<name>/clues.yaml`

These hints help `bin/analyze-package.sh --customer <name>` tell vendor packages
apart from in-house builds. Every pattern is a Python regex, applied with
`re.search`. Every key is optional; anything missing falls back to the built-in
heuristics. A file that isn't valid YAML, isn't a mapping, or holds a bad regex
stops the script (exit 2).

| Key | Type | Used how |
|---|---|---|
| `vendor_identifiers` | list of regex | A package identifier that matches is a **strong vendor** signal. In a distribution package, any component's identifier counts |
| `vendor_team_ids` | list of strings | A signed package whose team ID (the 10 characters in parentheses at the end of the signing authority) is listed is an extra **strong vendor** signal. Exact match |
| `vendor_filename_patterns` | list of `{pattern, vendor}` | A filename (without extension) that matches `pattern` is a **medium vendor** signal. `vendor` is only a label for people |
| `custom_build_signals.filename_contains_org_code` | bool | Turns the filename half of the next check on or off |
| `custom_build_signals.org_codes` | list of regex | Ignoring case: an identifier that matches any entry is a **medium custom** signal, always; a filename that matches is another, when the flag above is on |
| `custom_build_signals.unusual_install_locations` | list of paths | A package whose install location, or any payload path as installed (install location + payload path), is one of these paths or under one is a **medium custom** signal (once) |
| `custom_build_signals.non_reverse_domain_pattern` | regex | An identifier that matches is a **medium custom** signal: the org's legacy in-house identifier pattern. No default: leave it out and there is no check |

The script always adds some signals of its own, whatever `clues.yaml` says:

- An identifier in the org's own namespace (the first two segments of
  `identifier_prefix` in `config/org.yaml`, or the customer's `org.yaml`) is a
  strong custom signal. So an `Acme_*.pkg` rebuild comes out "custom-build".
- Any other reverse-DNS identifier is a strong vendor signal; one that isn't
  reverse-DNS is a strong custom signal.
- A signed package is a strong vendor signal; an unsigned one is a medium
  custom signal.
- A payload with no `.app` bundle counts towards custom.

`bin/analyze-materials.sh` uses the same clues (`--clues`, or the customer's with
`--customer <name>`) to classify every `.pkg` it finds, exactly as
`analyze-package.sh` would.

```yaml
vendor_identifiers:
  - "^com\\.microsoft\\."
  - "^com\\.moonlight-stream\\."

vendor_team_ids:                 # from "Developer ID Installer: … (UBF8T346G9)"
  - "UBF8T346G9"   # Microsoft
  - "45U78722YL"   # Moonlight (Cameron Gutman)

vendor_filename_patterns:
  - pattern: "^Microsoft_.*_Installer"
    vendor: "Microsoft"            # a label for people

custom_build_signals:
  filename_contains_org_code: true   # filename check only; the identifier check always runs
  org_codes:
    - "Acme"
    - "acmefruit"
  unusual_install_locations:       # install location and installed payload paths
    - "/Users/Shared"
    - "/Library/Application Support/AcmeFruit"
  non_reverse_domain_pattern: "^[a-z]+[a-z0-9]*$"   # legacy in-house identifiers
```

---

## 3. `customer/<name>/end_result.yaml`

The target catalogue: every app the customer wants packaged. It's a list under
`recipes:`.

| Field | Type | Required | Description |
|---|---|---|---|
| `app_name` | string | yes | App directory name, e.g. `Orchard-Analytics` |
| `vendor` | string | yes | Vendor directory name, e.g. `OrchardLabs` |
| `pattern` | string | yes | Pattern code, **quoted**: `"2b"`, `"4d"`, `"5"` |
| `source` | string | yes | Where the installer comes from |
| `kind` | `live` \| `example` \| `catalogue` | yes | `live`: real recipe that runs end to end; `example`: recipe for a fictional app (lints, can't run); `catalogue`: listed, no recipe yet |
| `status` | string | yes | `planned`, `drafted` or `done` in the Acme data |
| `built_in_house` | bool | yes | The org builds this package |
| `recipe_drafted` | bool | yes | A recipe pair exists |
| `build_tested` | bool | yes | `autopkg run` has built it |
| `template_example` | path | no | A template directory whose worked example shows this pattern |
| `notes` | string | no | Free text |

**What the tools use:** `bin/analyze-materials.sh` reads `app_name` and `vendor`
to match received files to targets. It compares them after lowercasing and
stripping everything that isn't a letter or digit, so `Orchard-Analytics`
matches `Orchard Analytics 7.2.dmg`. It copies `pattern` into its report
unchanged. People and agents use the other fields.

```yaml
recipes:
- app_name: Orchard-Analytics
  vendor: OrchardLabs
  pattern: "4c"
  source: "Vendor drop (DMG, app only)"
  kind: example
  status: drafted
  built_in_house: false
  recipe_drafted: true
  build_tested: false
  notes: "Fictional vendor. Plan: plans/orchard-analytics.md."
- app_name: Microsoft-Word
  vendor: Microsoft
  pattern: "5"
  source: "Stable fwlink URL (vendor pkg)"
  kind: catalogue
  status: planned
  built_in_house: false
  recipe_drafted: false
  build_tested: false
  template_example: templates/pattern-5-vendor-pkg-url/example-Microsoft-Word
  notes: "Use the template example."
```

---

## 4. Customer workspace layout

```text
customer/<name>/
├── README.md                    # what this customer is; start here
├── autopkg-recipes.csv          # progress tracker (§1)
├── clues.yaml                   # analyze-package hints (§2)
├── end_result.yaml              # target catalogue (§3)
├── paths.yaml                   # where material lives; recipe_repo.root is read (§5)
├── org.yaml                     # optional: naming that differs from config/org.yaml (§11)
├── checks.local.yaml            # optional: extra lint rules, skipped optional ones (§11)
├── .leak-patterns               # optional: this customer's leak denylist (§11)
├── plans/
│   └── <app>.md                 # plan of attack per Lane B package (§6)
├── input/                       # raw vendor material as received  (gitignored but README)
├── sessions/                    # working-session logs              (gitignored but README)
├── troubleshooting/             # debugging evidence                (gitignored but README)
└── output/                      # the recipe repo (recipe_repo.root, default output)
    ├── README.md
    ├── recipes/<Vendor>/<App>/  # download + pkg recipe pair, README.md
    ├── vendor-drop-registry.yaml   # §8
    ├── files_to_copy.yaml          # §9
    ├── build/                   # local build output (gitignored)
    └── vendor_cache/            # local vendor-drop files (gitignored)
```

A recipe folder may also hold an optional, org-defined `.overrides` file:
`KEY=VALUE` lines, `#` comments and blank lines ignored. AutoPkg never reads it;
`bin/run-recipes.sh` passes each line to `autopkg run` as `--key=KEY=VALUE`. One that
holds a secret or deployment detail is generated at run time or gitignored, never
committed. See [Standards §3.4](../reference/recipe-standards.md#34-the-overrides-file).

---

## 5. `customer/<name>/paths.yaml`

Where the customer's material lives. It is optional.

**One key is read by the tools: `recipe_repo.root`.** It is the customer's recipe
repo. When the file or the key is missing, the repo is `output`. The linter and
preflight use it when they run for a customer (§10). The other keys are for people
and agent skills; no script reads them.

**Relative paths are relative to the customer folder**, not the kit root. So the
same file works whether the folder is `customer/acme/` inside the kit or a client's
own repo somewhere else. `~` and absolute paths work too.

| Key | Description |
|---|---|
| `customer_name` | The customer's name in `config/customers.yaml` |
| `recipe_repo.root` | The recipe repo (read by the tools; default `output`) |
| `recipe_repo.recipes` / `.build` / `.vendor_cache` | Its subfolders (informational) |
| `input` | Raw vendor material |
| `plans` | Plan-of-attack documents |
| `sessions`, `troubleshooting` | Drop points (gitignored) |
| `vendor_cache_root` | Where AutoPkg stages vendor-drop files at run time (`-k VENDOR_CACHE_ROOT=…`) |

```yaml
customer_name: "acme"

recipe_repo:
  root: output                  # customer/acme/output
  recipes: output/recipes
  build: output/build
  vendor_cache: output/vendor_cache

input: input
plans: plans
sessions: sessions
troubleshooting: troubleshooting

vendor_cache_root: /tmp/autopkg/vendor_cache
```

The kit-level [`config/paths.yaml`](../config/paths.yaml) is informational and
records machine-wide locations. No script reads it.

---

## 6. `customer/<name>/plans/<AppName>.md`: plan of attack

These are per-package research notes (step 3 of
[`specs/method/00-methodology.md`](../specs/method/00-methodology.md)), with YAML
front matter that machines can read.

### Front matter

| Field | Type | Description | Example |
|---|---|---|---|
| `ready_draft` | bool | Ready to write the recipe | `true` |
| `ready_test` | bool | Ready to test-run in AutoPkg | `false` |
| `ready_compare` | bool | Compared the new build with the original package (stays `false` when there is no original) | `false` |
| `ref_file` | string | Reference file or, ideally, bundle | `Orchard Analytics.app` |
| `ref_version` | string | Reference version | `7.2` |
| `team_id` | string | Signing team ID, if any | `ORCHARD000` |
| `public_download` | bool | A public download URL exists | `false` |
| `download_url` | string | That URL | `""` |
| `vendor_name` | string | Vendor directory name | `OrchardLabs` |
| `app_name` | string | App directory name | `Orchard-Analytics` |
| `pattern` | string | Pattern code, quoted like in §3 | `"4d"` |

### Example

This is the front matter and the start of
[`customer/acme/plans/orchard-analytics.md`](../customer/acme/plans/orchard-analytics.md):

```markdown
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

## Research Notes
## Source Location
## Actions
- [x] Classify: app 4c (vendor DMG, app only) + license slice 6c
- [ ] Install on a test Mac; confirm the app starts licensed …
```

---

## 7. `specs/method/00-methodology.md`

The per-package workflow and the research questionnaire are defined in
[that file](../specs/method/00-methodology.md). The lessons behind it are in
[`reference/methodology.md`](../reference/methodology.md).

---

## 8. `<recipe-repo>/vendor-drop-registry.yaml`

This file maps each `Vendor/App` directory in the vendor cache to the file name
its recipe expects. `bin/normalize-vendor-cache.sh --repo <recipe-repo>
--vendor-cache <dir>` reads it from the recipe repo's root and renames whatever
was dropped to that name. Only files of the canonical name's type (its extension,
`.tar.gz`/`.tar.bz2` whole, case-insensitive) are renamed; other files are left in
place and reported as `KEEP`. Stale extras of that type are moved aside to
`<vendor-cache>/relocated/<Vendor>/<App>/`, never deleted; `--dry-run` changes nothing. The full rules are in
[`specs/vendor-cache/02-registry-config.md`](../specs/vendor-cache/02-registry-config.md)
and [normalize-vendor-cache.md](normalize-vendor-cache.md).

| Key | Type | Description |
|---|---|---|
| `canonical_filenames` | map `Vendor/App` → filename | The name the recipe expects. `[A-Za-z0-9._-]` only: no spaces, no version numbers. A key that isn't `Vendor/App`, or a name with a `/`, is an error (exit 1) |
| `ignored_subdirs` | list | Subfolder names the script never touches (e.g. `scripts`, `payload`) |
| `protected_files` | list | File names never renamed or moved (e.g. `scripts.zip`, `payload.zip`) |

```yaml
ignored_subdirs:
  - "scripts"
  - "payload"

protected_files:
  - "scripts.zip"
  - "payload.zip"

canonical_filenames:
  HP/HP-Printer-Drivers: "HP-Printer-Drivers.pkg"
  OrchardLabs/Orchard-Analytics: "Orchard-Analytics.dmg"
  OrchardLabs/Orchard-Analytics-License: "payload.zip"
  AcmeFruitCo/AcmeSupport: "payload.zip"
```

---

## 9. `<recipe-repo>/files_to_copy.yaml`

The vendor-cache manifest: every file the vendor-drop recipes need. Paths are
relative to the vendor cache root, and directories are copied recursively.
`bin/sync-vendor-cache.sh [--dry-run] <this file> <durable-source> <VENDOR_CACHE_ROOT>`
copies only what is listed, keeping timestamps, so a file already copied is skipped
next time. An entry that is absolute or contains `..` is refused. Spec:
[`specs/vendor-cache/03-sync.md`](../specs/vendor-cache/03-sync.md). Keep the
originals somewhere durable: the default `/tmp/autopkg/vendor_cache` is cleared at
reboot.

```yaml
files:
  - "HP/HP-Printer-Drivers/HP-Printer-Drivers.pkg"
  - "OrchardLabs/Orchard-Analytics/Orchard-Analytics.dmg"
  - "OrchardLabs/Orchard-Analytics-License/payload.zip"
  - "AcmeFruitCo/AcmeSupport/payload.zip"
  - "AcmeFruitCo/AcmeSupport/scripts.zip"
```

---

## 10. `config/customers.yaml`: the customer registry

One kit can serve several customers. A customer is an org with its own naming. The
registry says where each customer's folder is. Spec:
[`specs/toolkit/02-customers.md`](../specs/toolkit/02-customers.md).

```yaml
default: acme                      # optional
customers:
  acme: customer/acme              # relative to the kit root
  widgets: ~/src/widgets-kit       # absolute or ~, e.g. a client's private repo
```

| Key | Description |
|---|---|
| `customers` | Maps a name to the customer's folder. Relative paths are relative to the kit root; absolute paths and `~` work. |
| `default` | Optional. The customer used when a tool needs one and nothing else picks one. It must be a name in `customers`. |

The registry is **yours**: git ignores `config/customers.yaml`, since it names your
customers, and the kit ships
[`config/customers.example.yaml`](../config/customers.example.yaml) (Acme, as the
default) to start from:

```bash
cp config/customers.example.yaml config/customers.yaml
```

A new version of the kit never overwrites your registry. A private fork that wants it
in its history adds it with `git add -f config/customers.yaml`.

`$AUTOPKG_TOOLKIT_CUSTOMERS=<file>` points the tools at another registry file instead.
**No registry file means no customers**, and every tool works as it did before;
`--customer <name>` then still finds `customer/<name>/` in the kit.

A tool picks a customer in this order:

1. `--customer <name>`;
2. `$AUTOPKG_TOOLKIT_CUSTOMER`;
3. the registry's `default`;
4. the only registered customer, if there is just one.

An unknown name exits 2 and lists the registered names. It never falls back to the
default. Several customers, no default and no selection also exits 2.

The default (steps 3 and 4) applies only when the tool needs a customer: no
`--repo`, `$AUTOPKG_TOOLKIT_REPO`, `--dir` or recipe files were given. A customer
named with `--customer` or `$AUTOPKG_TOOLKIT_CUSTOMER` always applies.
`--org` and `$AUTOPKG_TOOLKIT_ORG` beat the customer's org. `--config` replaces the
rule file and drops the customer's local rules.

With the shipped registry (`default: acme`), `bin/recipe-linter.sh` and
`bin/autopkg-preflight.py` with no arguments check Acme's recipe repo. The one
exception is standing in a recipe repo: the current directory then counts as the
target, exactly as before, and the default stays out of the way.

A bad `default`, a folder that doesn't exist, or a file that isn't valid YAML is a
config error (exit 2) that names the problem.

`recipekit.customers` prints what the tools will use. From the kit root:

```bash
PYTHONPATH=lib/python /usr/local/autopkg/python -m recipekit.customers list
PYTHONPATH=lib/python /usr/local/autopkg/python -m recipekit.customers show acme
```

`list` prints the registry. `show [<name>]` prints one customer's resolved settings:
folder, recipe repo, merged org values and which optional files exist. Add
`--output json` for scripts. Kit shell scripts call it as
`tk_python -m recipekit.customers …`.

---

## 11. Per-customer files: `org.yaml`, `checks.local.yaml`, `.leak-patterns`

All optional, all in the customer's folder.

### `org.yaml`

The same flat `key: value` format as [`config/org.yaml`](../config/org.yaml). It is
layered **key by key** over the kit's file: a key the customer sets wins; a key it
leaves out comes from `config/org.yaml`. The merged values are then checked as
usual. For example, a Widgets Inc. customer can set only these:

```yaml
org_name: "Widgets Inc."
identifier_prefix: com.example.widgets
pkgname_prefix: "Wid_"
```

and get `fleet_min_macos` and the rest from the kit. `--org` and
`$AUTOPKG_TOOLKIT_ORG` replace the merged result.

### `checks.local.yaml`

Lint rules for this customer, on top of [`config/checks.yaml`](../config/checks.yaml).

```yaml
skip: [DIR-001, NAM-003]       # only rules the kit marks required: false
rules:                          # added to the kit's rules, same schema as checks.yaml
  - id: "WID-001"
    severity: "error"
    description: "Widgets recipes carry a Description"
    recipe_type: "both"
    check_target:
      key: "Description"
      source: "self"
    allowed_values:
      type: "regex"
      pattern: "^.+$"
    pass_message: "Description present"
    fail_message: "Description is missing"
```

| Key | Description |
|---|---|
| `skip` | Kit rule ids to leave out for this customer. Only rules marked `required: false` in `checks.yaml` can be skipped. Skipping a required rule, or one that doesn't exist, exits 2. |
| `rules` | Rules added for this customer. The schema is `checks.yaml`'s ([rule definitions](../specs/recipe-linter/01-rule-definitions.md)), `{{TOKENS}}` included. An `id` must not repeat a kit rule's id (exit 2). |

The rules a kit marks optional today: SRC-002, SRC-003, NAM-002, NAM-003, DIR-001,
MIN-001, CMT-001, CMT-002, CMT-003, CMT-004. Every other rule is required.

`bin/recipe-linter.sh --customer <name> --list-rules` shows the result: the kit's
rules minus the skipped ones plus the local ones. `--config <file>` replaces the
rule file and ignores `checks.local.yaml`.

### `.leak-patterns`

The customer's own leak denylist, in the kit's `.leak-patterns` format
(`recipekit.customers show` lists it). When a registry exists,
`bin/check-sanitized.sh` applies every customer's file to the whole scan except that
customer's own folder, so a customer's names may appear only there. Hits are
labelled `customer:<name>:N` (line N of the non-comment patterns); `!` exemption
lines work as in the kit's file. `--customer <name>` scans that customer's folder
with the kit's `.leak-patterns` plus every other customer's; `--all-customers` does
each in turn. The scan always skips every `.leak-patterns` file.

---

## Version history

| Version | Date | Change |
|---|---|---|
| 1.7 | 2026-09-27 | §8: stale files are relocated to `relocated/<Vendor>/<App>/` at the top of the vendor cache (was a hidden, timestamped quarantine). |
| 1.6 | 2026-09-27 | §8, §9: the vendor-cache scripts run on AutoPkg's Python; no `yq` (KI-21 fixed). §8: only files of the canonical name's type are renamed; stale extras are quarantined, not deleted; `--dry-run` (KI-7 fixed). §9: timestamps kept, unsafe entries refused, `--dry-run`. |
| 1.5 | 2026-09-27 | §2: `analyze-materials.sh` classifies each `.pkg` with the clues. |
| 1.4 | 2026-09-27 | §2: every `clues.yaml` key is used (KI-15 fixed): `vendor_team_ids`, `org_codes` in the identifier, `unusual_install_locations` on payload paths, `non_reverse_domain_pattern` (no default). The org's own namespace counts as custom. An invalid file exits 2. |
| 1.3 | 2026-09-27 | §11: `bin/check-sanitized.sh` applies each customer's `.leak-patterns` outside that customer's folder. |
| 1.2 | 2026-09-27 | §5: `recipe_repo.root` is read by the tools, and paths are relative to the customer folder. New §10 (`config/customers.yaml`) and §11 (per-customer `org.yaml`, `checks.local.yaml`, `.leak-patterns`). |
| 1.1 | 2026-09-27 | §4: `.overrides` described as optional and org-defined; no `.autopkg_config` in upstream. |
| 1.0 | 2026-09-26 | Schemas for the customer workspace, the progress tracker, `clues.yaml`, `end_result.yaml`, `paths.yaml`, plan-of-attack front matter, the vendor-drop registry and the vendor-cache manifest. |
