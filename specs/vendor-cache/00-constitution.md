# Vendor Drop Norms — Constitution

**Spec suite:** `specs/vendor-cache/`
**Status:** Draft
**Last updated:** 2026-09-12

---

## 0. Purpose

This constitution defines the contract between an upstream CI/CD pipeline
that receives files from a vendor's application owner ("Bob drops a file")
and the AutoPkg recipes that consume them via `URLDownloader` with `file://`
URIs.

The core problem: vendor-provided installer files arrive with arbitrary,
potentially-versioned, and frequently-changing filenames. These filenames
often contain spaces, `@` signs, parentheses, or other characters that break
curl's `file://` URL parsing. The recipes cannot hardcode exact filenames
because the filenames change with every vendor release.

IT IS AN INVOLABLE PRINCIPLE THAT:
- No `.download.recipe.yaml` or `.pkg.recipe.yaml` may contain an exact
  vendor filename in `DOWNLOAD_URL` or any other Input field.
- No runtime config file may contain an exact vendor filename.
- Vendor filenames are normalized before any AutoPkg recipe runs, by a
  dedicated pre-processing script driven by its own config.

---

## 1. Terminology

| Term | Definition |
|------|------------|
| **Vendor cache** | The directory tree at `VENDOR_CACHE_ROOT` (e.g., `/tmp/autopkg/vendor_cache/`) where vendor-provided installer files land before any AutoPkg step runs. |
| **Vendor-drop recipe** | An AutoPkg recipe (download + pkg) that uses `URLDownloader` with a `file://` URI to consume a locally-staged file. |
| **Canonical filename** | The single safe name that a recipe expects to find inside a given Vendor/App directory. Must contain only `[A-Za-z0-9._-]`. |
| **Pre-scan script** | A tool that enumerates every file under `VENDOR_CACHE_ROOT`, compares each against a config file, renames any file that does not match its canonical name, and reports what it did. |
| **Vendor-drop registry** | A YAML config file that maps each Vendor/App directory to its canonical filename. |

---

## 2. The Pre-Scan Script Contract

The pre-scan script (`bin/normalize-vendor-cache.sh`) SHALL:

1. Accept `--repo <recipe-repo>` (the registry is `<repo>/vendor-drop-registry.yaml`)
   and `--vendor-cache <path>`; optionally `--dry-run` and `--relocate-dir <dir>`.
2. Read the vendor-drop registry from that file.
3. For each Vendor/App entry in the registry:
   a. Consider the regular, non-dot files in `VENDOR_CACHE_ROOT/<Vendor>/<App>/`.
      Only files of the canonical name's **type** (its extension, compared
      case-insensitively, `.tar.gz`/`.tar.bz2` whole) are versions of it; any
      other file is left in place and reported.
   b. Files named in `protected_files` are never renamed, moved or deleted.
   c. If a file matches the canonical name exactly and is the newest of its type
      (it wins ties), stale files of the same type are moved aside.
      If a newer same-type file sits beside it (a vendor update), the old
      canonical file is moved aside and the newest renamed into place.
   d. If none matches, rename the most recently modified same-type file to the
      canonical name and warn about any others.
   e. If there is no file to use, report it but do not fail.
   f. If the renamed file had unsafe characters (spaces, `@`, parentheses,
      etc.), flag it in the output.
4. Exit 0 on success, exit 1 on any error that prevents normalization.
5. Write structured output, one line per action:
   `ACTION<TAB>Vendor/App<TAB>old_name<TAB>new_name<TAB>message`.
6. NOT modify recipe files, config files, or any tracked git content.
7. NEVER delete or overwrite a file: stale files are moved aside to the same
   `<Vendor>/<App>/` path under a relocate folder (`<vendor-cache>/relocated/`
   by default), and `--dry-run`
   changes nothing at all.

IT IS AN INVOLABLE PRINCIPLE THAT:
- No `.download.recipe.yaml` or `.pkg.recipe.yaml` may contain an exact
  vendor filename in `DOWNLOAD_URL` or any other Input field.
- No runtime config file may contain an exact vendor filename.
- Vendor filenames are normalized before any AutoPkg recipe runs, by a
  dedicated pre-processing script driven by its own config.

---

## 1. Terminology

| Term | Definition |
|------|------------|
| **Vendor cache** | The directory tree at `VENDOR_CACHE_ROOT` (e.g., `/tmp/autopkg/vendor_cache/`) where vendor-provided installer files land before any AutoPkg step runs. |
| **Vendor-drop recipe** | An AutoPkg recipe (download + pkg) that uses `URLDownloader` with a `file://` URI to consume a locally-staged file. |
| **Canonical filename** | The single safe name that a recipe expects to find inside a given Vendor/App directory. Must contain only `[A-Za-z0-9._-]`. |
| **Pre-scan script** | A tool that enumerates every file under `VENDOR_CACHE_ROOT`, compares each against a config file, renames any file that does not match its canonical name, and reports what it did. |
| **Vendor-drop registry** | A YAML config file that maps each Vendor/App directory to its canonical filename. |

---

## 2. The Pre-Scan Script Contract

The pre-scan script (`bin/normalize-vendor-cache.sh`) SHALL:

1. Accept `--config <path>` and `--vendor-cache <path>` arguments.
2. Read the vendor-drop registry from the config file.
3. For each Vendor/App entry in the registry:
   a. List all files in `VENDOR_CACHE_ROOT/<Vendor>/<App>/`.
   b. If a file exists whose name matches the canonical name exactly, do nothing.
   c. If a file exists whose name differs from the canonical name, rename it
      to the canonical name.
   d. If multiple files exist and none match the canonical name exactly,
      rename the single most-recently-modified file to the canonical name
      and report a warning about the others.
   e. If no files exist at all, emit a warning but do not fail.
   f. If a file exists but has unsafe characters (spaces, `@`, parentheses,
      etc.), log this as a HIGH-severity warning in addition to renaming.
4. Exit 0 on success, exit 1 on any error that prevents normalization.
5. Write structured output to stdout — one line per action taken, in the
   format: `ACTION|Vendor/App|old_name|new_name|message`
6. NOT modify recipe files, config files, or any tracked git content.

IT IS AN INVOLABLE PRINCIPLE THAT:
- The pre-scan script is configuration-driven. Adding a new vendor/app means
  adding one entry to the config file, not modifying the script.
- The pre-scan script never modifies the recipe repo. It only touches files
  under `VENDOR_CACHE_ROOT` (which is outside the git repo by definition).
- The pre-scan script runs before `autopkg run` in any CI/CD pipeline.

---

## 3. Config File Format

The vendor-drop registry SHALL be at `vendor-drop-registry.yaml` in the root
of the recipe repo (e.g., `customer/acme/output/vendor-drop-registry.yaml`)
with the following structure:

```yaml
# Vendor Drop Registry
# Maps each Vendor/App directory to the canonical filename the recipes expect.
# The pre-scan script renames whatever it finds to these names.
#
# To add a new vendor-drop app: add one entry here. No script changes needed.

canonical_filenames:
  # ── Household names ───────────────────────────────────────────────────────
  Adobe/Adobe-Creative-Cloud: "Adobe_Creative_Cloud.pkg"
  AnthropicPBC/Claude: "Claude.pkg"
  CitrixSystems/Citrix-Workspace: "Citrix-Workspace.pkg"
  Sophos/Sophos-Endpoint: "Sophos_Endpoint.payload.zip"
  XeroxCorporation/Xerox-Drivers: "Xerox_Drivers.pkg"
  # ── Acme Fruit Co. (fictional; customer/acme/output/vendor-drop-registry.yaml)
  HP/HP-Printer-Drivers: "HP-Printer-Drivers.pkg"
  OrchardLabs/Orchard-Analytics: "Orchard-Analytics.dmg"
  OrchardLabs/Orchard-Analytics-License: "payload.zip"
  AcmeFruitCo/AcmeSupport: "payload.zip"
  AcmeFruitCo/Acme-Wallpaper: "payload.zip"
  AcmeFruitCo/Acme-UninstallAgent: "scripts.zip"
  PomeloSoftware/Pomelo-Studio: "Pomelo-Studio.dmg"
```

Canonical filenames MUST:
- Contain only `[A-Za-z0-9._-]` — no spaces, no `@`, no parentheses, no commas.
- Be unique within a single Vendor/App directory.
- Use an extension that reflects the actual file type (`.pkg`, `.dmg`, `.zip`).

---

## 4. Recipe Contract

Every vendor-drop download recipe SHALL:

1. Set `DOWNLOAD_URL` to the canonical form:
   ```
   file://%VENDOR_CACHE_ROOT%/Vendor/App/canonical_name.ext
   ```
2. NOT hardcode any version number in `DOWNLOAD_URL`.
3. Use `%VENDOR_CACHE_ROOT%` as the base, defined in Input, to keep the
   root path configurable.

---

## 5. CI/CD Integration

The CI/CD pipeline SHALL run `bin/normalize-vendor-cache.sh` immediately
before `autopkg run` in any workflow that consumes vendor-drop recipes. The
normalization step SHALL use the same `VENDOR_CACHE_ROOT` that the recipes
reference.

---

## 6. Spec Documents

- `00-constitution.md` — This file. Inviolable principles.
- `01-pre-scan-script.md` — Detailed design of `bin/normalize-vendor-cache.sh`
- `02-registry-config.md` — `vendor-drop-registry.yaml` reference (lives at the recipe repo root)
- `03-sync.md` — `bin/sync-vendor-cache.sh`, copying a manifest's files from a durable source

---

## Amendments

- 2026-09-27: §2.7: stale files are relocated to a mirrored `relocated/` tree, not a hidden timestamped quarantine.
- 2026-09-27: §2 rewritten to the real interface (`--repo`, tab-separated output) and hardened (KI-7): type-matched candidates, protected files never touched, quarantine instead of delete, `--dry-run`. Implementation moved to Python (toolkit P-7/P-10); no `yq` (KI-21).
