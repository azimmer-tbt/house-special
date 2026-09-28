# Microsoft Word — Pattern 5 example

**Pattern 5:** a signed vendor `.pkg` at a stable redirect URL, copied as-is, with the
version read from inside the package.

| | |
|---|---|
| Source | `https://go.microsoft.com/fwlink/?linkid=525134`, a Microsoft fwlink that always redirects to the current installer |
| Artifact | A signed flat `.pkg` (`Microsoft-Word.pkg` in the cache) |
| Signature | `expected_authority_names`: Microsoft Corporation's Developer ID Installer certificate (Team ID `UBF8T346G9`) plus Apple's chain |
| Version | Read from the app inside the package: `FlatPkgUnpacker` → `PkgPayloadUnpacker` → `Versioner` on `Microsoft Word.app` |
| Output | `PkgCopier`: the vendor's package, signature intact |
| Clean-up | A final `PathDeleter` removes the unpacked copies. It runs after they were created, so it can't fail on a fresh cache (methodology lesson 2) |

## Why the version comes from inside

The fwlink URL has no version in it, and the package file name doesn't either. The
only reliable version is the app's `CFBundleShortVersionString`, so the pkg recipe
unpacks the payload just far enough to read it, then copies the untouched vendor
package.

## Things to check when you adapt it

- The inner package name (`Microsoft_Word.pkg`) in `pkg_payload_path` is Microsoft's
  and can change between releases. If `PkgPayloadUnpacker` fails, expand the download
  with `pkgutil --expand` and look.
- Keep the `Developer ID Installer` leaf exactly as `pkgutil --check-signature` prints
  it.
