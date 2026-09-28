# Pattern 6c — Rebuilt, Single File (reverse-engineered)

**Defined in `reference/recipe-standards.md` §6.2.6 (Pattern 6 variants).**
Pattern 6c is a variant of Pattern 6 for single-file payloads deployed with
specific ownership/mode.

## When

You have a built package that contains a single configuration file deployed to
a system path — typically a security baseline file like `audit_control` (mode
0400), a sudoers drop-in (mode 0440), or a plist configuration (mode 0644).
The source archive (`payload.zip`) is stored in the vendor cache.

The recipe chain is: `URLDownloader` + `Unarchiver` → `PkgCreator` with chown
block.

## Why not Pattern 4 or Pattern 6

| Pattern | Why not for a single-file deployment |
|---------|--------------------------------------|
| **Pattern 4 (Variant A — PkgCopier)** | Ships the vendor package as-is. You could use this if the vendor signs their package, but most single-file configuration packages come from in-house tools (Jamf Composer, etc.) and are unsigned. |
| **Pattern 4 (Variant B — FileCopy)** | Stages a single file but produces a flat package with no chown control. Use only when the file lands in a user-writable path. |
| **Pattern 6 (multi-file)** | Designed for multi-file payload trees. The `Copier`-based staging is overkill for a single archive, and scripts are almost never present. |
| **Pattern 6c** | The right fit: archive-based staging, explicit mode in chown, no scripts. |

## Key differences from Pattern 6

| Aspect | Pattern 6 | Pattern 6c |
|--------|-----------|------------|
| Staging | Two `Copier` steps (payload + scripts) | `URLDownloader` + `Unarchiver` (single archive) |
| Scripts | Often present | Never present (single file) |
| chown | Only when extracted without sudo | Always needed (archive extracted at run time) |
| Mode | Usually 0755/0644 (git-compatible) | Usually restrictive (0400, 0600, 0640) |

## Usage

1. Place `payload.zip` in the vendor cache under `Vendor/AppName/`.
2. Replace all `REPLACE_*` tokens in the recipe files.
3. Set `PKG_ID` to match the original package's identifier.
4. Set the chown mode from the original BOM.
5. Run `autopkg run ./<App>.pkg.recipe.yaml`.

## Verification

1. `pkgutil --files <identifier>` on the original, against the files in the archive
2. Verify mode matches: `lsbom -p MUGsf /tmp/x/Bom`
3. `autopkg run ./<App>.pkg.recipe.yaml`
4. Install on a test Mac and verify the deployed file's mode and ownership

## Expected lint findings

None once the recipe is filled in. `NO_CODE_SIGNATURE_REQUIRED` satisfies `CSV-001`
and `CSV-005`, and the pinned `version` Input in the download recipe satisfies
`VER-001`. See KI-2 in `docs/known-issues.md` for the rule history.

Do not edit a recipe to silence a finding.
