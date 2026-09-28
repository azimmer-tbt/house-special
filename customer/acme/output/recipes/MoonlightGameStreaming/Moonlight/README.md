# Moonlight

**Pattern 2b — GitHub release DMG, rebuilt with PkgCreator.** The reference example
for the most common vendor shape there is: a DMG you open and drag the app to
Applications.

| | |
|---|---|
| Source | GitHub releases, `moonlight-stream/moonlight-qt`, asset `Moonlight-<version>.dmg` |
| License | GPL-3.0 (we download and repackage the vendor's signed app; we don't redistribute outside the org) |
| Signature | Developer ID Application: Cameron Gutman (`45U78722YL`) — verified on the `.app` inside the DMG |
| Version | Read from the app bundle (`Versioner`) |
| Output | `Acme_Moonlight.pkg`, installs `/Applications/Moonlight.app` |
| Last live run | 6.1.0 |

## How it works

1. `GitHubReleasesInfoProvider` finds the newest non-prerelease and the asset matching
   `ASSET_REGEX`. The `$` anchor matters: without it, a `.dmg.sha256` would match too.
2. `URLDownloader` fetches it; `EndOfCheckPhase` lets `autopkg run --check` stop here.
3. `CodeSignatureVerifier` checks the app *inside* the DMG (AutoPkg mounts it) against the
   designated requirement copied verbatim from `codesign -dr - Moonlight.app`.
4. The pkg recipe's `Copier` mounts the DMG, copies the app into a pkgroot, and unmounts.
5. `PkgCreator` builds `Acme_Moonlight.pkg`. `AppPkgCreator` would be one step shorter
   but can't apply the org prefix, so the standards ban it (Standards §6.7 item 3).

## Updating

Nothing to do: each run picks up the newest release. If the vendor renames the asset,
fix `ASSET_REGEX` (Standards §6.2.2.2, "Writing the asset_regex").
