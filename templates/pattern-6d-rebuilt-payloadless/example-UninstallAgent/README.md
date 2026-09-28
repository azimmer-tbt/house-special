# UninstallAgent — Recipe Notes

## Overview

UninstallAgent is an agent for uninstalling Symantec DLP (Data Loss Prevention)
software. Deployed as a script-only package — the postinstall script handles
the binary removal from `/private/tmp/uninstall_agent_15_5`.

## Pattern: Pattern 6d (rebuilt package, script-only)

The upstream file `UninstallAgent_15.5.pkg` is an unsigned distribution package
built by Jamf Composer. The package contains installer scripts but no payload —
the entire function is delivered through the postinstall script.

The recipe extracts the scripts archive and rebuilds with PkgCreator using a
script-only configuration (empty pkgroot).

## DOWNLOAD-SPEC

| Field | Value |
|-------|-------|
| **Vendor** | Acme Fruit Co. (in-house) |
| **Vendor directory** | `AcmeFruitCo/UninstallAgent/` |
| **Upstream file** | `UninstallAgent_15.5.pkg` |
| **Version** | 15.5 |
| **PKG_ID** | `com.acmefruit.uninstallagent` |
| **Pattern** | 6d (rebuilt package, script-only, PkgCreator) |

## Scripts

The `scripts.zip` archive contains:

```
scripts.zip
└── postinstall   — Removes /private/tmp/uninstall_agent_15_5 and cleans up
```

The postinstall script is the sole function of this package. No payload files
are staged or deployed.

## Recipe structure

### Download recipe
- `URLDownloader` stages the scripts archive from the vendor cache
- `Unarchiver` extracts to `%RECIPE_CACHE_DIR%/scripts`
- `NO_CODE_SIGNATURE_REQUIRED: true`

### Pkg recipe
- `PkgCreator` builds `Acme_UninstallAgent.pkg` from scripts only
- No `chown` block — no payload files to set ownership on

## Verification

1. `autopkg run ./UninstallAgent.pkg.recipe.yaml`
2. Verify the built package contains only scripts: `pkgutil --expand Acme_UninstallAgent.pkg /tmp/x`
3. Confirm no Payload file exists in the expanded package
4. Install on a test Mac and verify the postinstall script executes

<!-- VARIABLES-SPEC-START -->

filename_pattern=`UninstallAgent`

manufacturer_url=`https://it.acmefruit.example/`

drop_folder=`vendor_cache/AcmeFruitCo/UninstallAgent/`

upload_url=`vendor_cache/AcmeFruitCo/UninstallAgent/scripts.zip`

<!-- VARIABLES-SPEC-END -->
