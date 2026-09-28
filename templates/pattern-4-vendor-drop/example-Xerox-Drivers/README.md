# Xerox Drivers — Recipe Notes

## Why this driver package, not the one currently on Jamf

We don't have an easy way to query which specific Xerox printer models are actually
deployed across the fleet, so "check every model we own against both driver packages"
wasn't available as a decision method. Instead we compared the **model coverage of the
two driver packages directly**:

- Newer package (`new-drivers.txt`): 178 supported models
- Package currently on Jamf (`old-drivers.txt`): 164 supported models
- Diff: the newer package is a **strict superset** — every model Jamf supports, the
  newer package also supports. Zero models lost. 14 models gained.

The 14 gained models are:

- **C-series refresh:** C240, C245, C255a, C300, C303a, C305ae, C2432, XC2432, ZC364 —
  launched June 23, 2026 as the first hardware under Xerox's unified brand following
  its Lexmark integration. ~2 months old as of this writing.
- **EC81xx line:** EC8131, EC8136, EC8146, EC8156, EC8171 — documentation dates to
  August 2025, so roughly a year old.

## Decision (superseded — see update below)

Since switching to the newer package can only add printer-model coverage and cannot
remove support for anything currently working, the initial lean was to pull the newer
package rather than re-wrap what's already on Jamf. Given the C-series line shipped only
~2 months ago, it's a live possibility (not a remote edge case) that some of the 14
newly-covered models are already deployed somewhere in the fleet — this isn't purely a
hedge against a hypothetical.

**Update:** pinning to 5.16 for now instead. Approval status of the newer package in
the org's software-approval process is unknown, and that trumps the model-coverage analysis above — a wider driver
package that hasn't cleared approval isn't actually deployable regardless of how good
its coverage looks on paper. The superset/subset analysis above stands as reference for
whenever the newer package's approval status is confirmed; it just isn't the deciding
factor today.

**Heuristic used:** superset/subset comparison of model coverage, in the absence of
fleet inventory visibility. If fleet inventory data becomes available later, this
decision is worth revisiting — not because the superset logic was wrong, but because a
confirmed inventory match would be stronger evidence than a heuristic.

## Known gap

No stable, model-agnostic direct download URL exists for Xerox print drivers — every
path is gated behind Xerox's model-search + platform-filter + EULA click-through flow
on `support.xerox.com`. This recipe is therefore **Pattern 4 (vendor-drop)**, not a
public-URL pattern, despite the driver technically being "freely available" — the
gating makes it functionally equivalent to a vendor-drop for automation purposes.

## Status: confirmed working, real signature verified

The pkg is genuinely signed — confirmed via a full real run:

```
Status: signed by a developer certificate issued by Apple for distribution
Notarization: trusted by the Apple notary service
Certificate Chain:
 1. Developer ID Installer: Xerox Corporation (G59Y3XFNFR)
 2. Developer ID Certification Authority
 3. Apple Root CA
Signature is valid
Authority name chain is valid
```

The `teamid` (`G59Y3XFNFR`) and `authority_name` (`Xerox Corporation`) Inputs were copied from
`pkgutil --check-signature` output, not typed from memory.

## Bug found here: missing certificate chain

The original `expected_authority_names` only had the vendor's own leaf certificate
line — missing the two standard Apple entries (`Developer ID Certification Authority`,
`Apple Root CA`) that `CodeSignatureVerifier` also checks. This produced "Mismatch in
authority names" on the very first genuinely-signed pkg tested in the batch (every
other Variant A app turned out unsigned, so none of them had exercised this code path
before). Fixed by adding the two standard entries — they're constant across every
Apple Developer ID Installer cert, not vendor-specific. Full detail in
`autopkg-recipe-methodology.md` item #6.

## Shared fixes applied (found on the first recipe of this shape)

- Removed `PathDeleter` (errors on a fresh cache)
- Fixed `vendor_cache` path depth (`../../..`, not `../..`)
- `PkgCopier`'s `source_pkg` references the literal known path, not `%pathname%`
