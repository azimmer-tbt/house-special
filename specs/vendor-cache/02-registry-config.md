# Vendor-Drop Registry Config Reference

**Spec ref:** `specs/vendor-cache/00-constitution.md` §3
**File:** `<recipe-repo>/vendor-drop-registry.yaml` (example: `customer/acme/output/vendor-drop-registry.yaml`)
**Status:** Draft
**Last updated:** 2026-09-12

---

## 1. Purpose

`vendor-drop-registry.yaml`, at the root of the recipe repo, is the single point of configuration for
vendor cache filename normalization. It maps each `Vendor/App` directory to
the canonical filename that the AutoPkg recipes expect.

The pre-scan script (`bin/normalize-vendor-cache.sh`) reads this file at
runtime and renames whatever files it finds in the vendor cache to match
the canonical names.

## 2. File Location

```
vendor-drop-registry.yaml
```

This file lives at the **root of the recipe repo**, not in the toolkit repo.
For the Acme example, that means:
`customer/acme/output/vendor-drop-registry.yaml`

Different customers/CI runners have their own copy in their own recipe repo.
The pre-scan script accepts `--repo <path>` to locate it.

## 3. Format

```yaml
canonical_filenames:
  VendorName/AppName: "Canonical_Filename.pkg"
  VendorName/AnotherApp: "Another_App.dmg"
```

### Rules for canonical filenames

- **Character set:** Only `[A-Za-z0-9._-]` — no spaces, no `@`, no
  parentheses, no commas, no `&`, no `+`.
- **Extension:** Match the actual file type (`.pkg`, `.dmg`, `.zip`, etc.).
- **Uniqueness:** One canonical name per directory. If a directory naturally
  holds more files of the same type (e.g., `payload.zip` + `scripts.zip`),
  list the others in `protected_files` so they are never renamed or pruned.
- **Other keys:** `ignored_subdirs` (subfolders to skip, reported as `IGNORE`)
  and `protected_files` (file names never touched, in any folder).

### Rules for adding entries

1. Determine the Vendor/App directory structure — must match how the recipe
   references it.
2. Choose a canonical name that is descriptive and safe:
   - Use underscores for spaces in the original vendor name.
   - Preserve recognizable parts of the vendor's naming convention if safe.
   - Drop version numbers — recipes must not depend on them.
3. Add the entry to the YAML file.
4. Update the recipe's `DOWNLOAD_URL` to reference the canonical name.
5. Update the pre-scan script tests if the behavior changes.

### Example

```yaml
canonical_filenames:
  # Pattern 4b (distribution vendor pkg, copied as-is):
  Adobe/Adobe-Creative-Cloud: "Adobe_Creative_Cloud.pkg"
  AnthropicPBC/Claude: "Claude.pkg"

  # Pattern 4c (vendor DMG, Copier extracts .app):
  OrchardLabs/Orchard-Analytics: "Orchard-Analytics.dmg"

  # Pattern 7 (faux vendor DMG):
  PomeloSoftware/Pomelo-Studio: "Pomelo-Studio.dmg"
```

## 4. CI/CD Usage

The registry file is checked into the recipe repo. A CI runner that needs a
different set of mappings points `--repo` at a checkout holding its own copy.

## 5. One-Time Initialization

When adding the pre-scan script to an existing vendor cache for the first
time, the operator MUST:

1. Ensure every Vendor/App directory has exactly one file per canonical name.
2. For directories that currently contain files with problematic names, the
   operator may manually rename them to match the canonical names, or rely on
   the pre-scan script to do it on first run.
