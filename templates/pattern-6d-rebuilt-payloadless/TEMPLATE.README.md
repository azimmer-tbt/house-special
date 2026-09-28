# Pattern 6d — Rebuilt, Payloadless (Script-Only)

**Defined in `reference/recipe-standards.md` §6.2.6 (Pattern 6 variants).**
Pattern 6d is a variant of Pattern 6 for script-only packages with no payload
files — uninstallers, launchagent/daemon deployments, trigger packages, and
any package whose function is delivered entirely through preinstall/postinstall
scripts.

## When

You have a built package that contains installer scripts (preinstall and/or
postinstall) but **no payload files** — the pkgroot is empty or absent. The
source archive (`scripts.zip`) is stored in the vendor cache.

The recipe chain is: `URLDownloader` + `Unarchiver` (scripts only) → `PkgCreator`
with scripts, no pkgroot.

## Why not Pattern 4, 6, or 6c

| Pattern | Why not for script-only |
|---------|------------------------|
| **Pattern 4 (Variant A — PkgCopier)** | Ships the vendor package as-is. Script-only packages rarely come from an external vendor; they are almost always in-house built. |
| **Pattern 4 (Variant B — FileCopy)** | Stages files to a flat package. Overkill when there are no files to stage. |
| **Pattern 6 (multi-file)** | Designed for multi-file payload trees with scripts as a secondary concern. Scripts are the entire concern here. |
| **Pattern 6c (single file)** | Designed for a single payload file with explicit mode. Not applicable when there is no payload. |
| **Pattern 6d** | The right fit: script-only, no payload, no chown block. |

## Key differences from Pattern 6

| Aspect | Pattern 6 | Pattern 6d |
|--------|-----------|------------|
| Staging | Two `Copier` steps (payload + scripts) | `URLDownloader` + `Unarchiver` (scripts archive only) |
| pkgroot | Required (payload tree) | Empty or absent (no payload) |
| Scripts | Optional addition to payload | The entire package |
| chown | When extracted without sudo | Never needed (no payload files) |

## Usage

1. Place `scripts.zip` in the vendor cache under `Vendor/AppName/`.
2. Replace all `REPLACE_*` tokens in the recipe files.
3. Set `PKG_ID` to match the original package's identifier.
4. Set `version` to the pinned version.
5. Ensure `preinstall` and/or `postinstall` scripts have the executable bit set.
6. Run `autopkg run ./<App>.pkg.recipe.yaml`.

## Scripts archive contents

The `scripts.zip` archive should contain only the installer scripts that the
original package carried. Typically:

```
scripts.zip
├── preinstall    (optional — runs before payload installation)
└── postinstall   (optional — runs after payload installation)
```

Both must have the executable bit set (`chmod +x`). PkgCreator rejects the
build if they exist but are not executable.

## Verification

1. `pkgutil --expand <original>.pkg /tmp/x` — confirm only Scripts directory
   exists (no Payload)
2. `cat /tmp/x/PackageInfo` — confirm `<installer-scripts />` is present
3. Verify script contents reference correct paths and versions
4. `autopkg run ./<App>.pkg.recipe.yaml`
5. Install on a test Mac and verify the script executes correctly

## Expected lint findings

None once the recipe is filled in. `NO_CODE_SIGNATURE_REQUIRED` satisfies `CSV-001`
and `CSV-005`, and the pinned `version` Input in the download recipe satisfies
`VER-001`. See KI-2 in `docs/known-issues.md` for the rule history.

Do not edit a recipe to silence a finding.
