# Audit Control Expiry — Recipe Notes

**Pattern 6c example.** Modelled on a real in-house package; the identifiers,
paths and vendor directory are the fictional Acme Fruit Co.'s.

## Overview

Audit Control Expiry provides an `audit_control` configuration file for the
macOS audit system (`/private/etc/security/audit_control`). Deployed as a
security configuration baseline.

## Pattern: Pattern 6c (rebuilt, single file)

The upstream file `Acme_Audit_Control_Expiry_20190422.pkg` is an unsigned
distribution package built by Jamf Composer. The recipe extracts the payload
and rebuilds with PkgCreator.

## DOWNLOAD-SPEC

| Field | Value |
|-------|-------|
| **Vendor** | Acme Fruit Co. (in-house) |
| **Vendor directory** | `AcmeFruitCo/Audit-Control-Expiry/` |
| **Upstream file** | `Acme_Audit_Control_Expiry_20190422.pkg` |
| **Version** | 1 |
| **PKG_ID** | `com.acmefruit.auditcontrol` |
| **Pattern** | 6c (rebuilt single file, PkgCreator) |

## Payload

Single file deployed to `/private/etc/security/audit_control`:
- Mode: `0400` (owner read-only)
- Owner: `root:wheel`
- Size: 364 bytes

No postinstall or preinstall scripts exist in the original package.

## Recipe structure

### Download recipe
- `URLDownloader` fetches `payload.zip` from vendor cache
- `Unarchiver` extracts to `%RECIPE_CACHE_DIR%/payload`
- No `CodeSignatureVerifier` — rebuilt package (unsigned by construction)
- `NO_CODE_SIGNATURE_REQUIRED: true`

### Pkg recipe
- `PkgCreator` builds `Acme_Audit-Control-Expiry.pkg` from the payload
- Uses `chown` block with mode `0400` to restore file permissions from the BOM
- `options: purge_dest` ensures clean deployment on each install

## About the upstream package

The upstream is built by **Jamf Composer** (authoringTool="com.jamfsoftware.Composer").
It was not code-signed. The rebuild from extracted payload preserves the single
`audit_control` file with its original permissions.

<!-- VARIABLES-SPEC-START -->

filename_pattern=`Audit-Control-Expiry`

manufacturer_url=`https://it.acmefruit.example/`

drop_folder=`vendor_cache/AcmeFruitCo/Audit-Control-Expiry/`

upload_url=`vendor_cache/AcmeFruitCo/Audit-Control-Expiry/payload.zip`

<!-- VARIABLES-SPEC-END -->
