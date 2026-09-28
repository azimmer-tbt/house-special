# Raspberry Pi Imager

**Pattern 2b — GitHub release DMG, rebuilt with PkgCreator.** The easy GitHub case,
with one quirk worth knowing.

| | |
|---|---|
| Source | GitHub releases, `raspberrypi/rpi-imager`, asset `rpi-imager-v<version>.dmg` |
| License | Apache-2.0 (main code); third-party components listed in the project's `license.txt` |
| Signature | Developer ID Application: RASPBERRY PI LTD (`8RDZTRXE62`) |
| Version | From the release tag — **not** from the bundle (see below) |
| Output | `Acme_Raspberry-Pi-Imager.pkg`, installs `/Applications/Raspberry Pi Imager.app` |
| Last live run | 2.0.11.1 |

## The quirk: a "v" in the bundle version

The app's `CFBundleShortVersionString` is `v2.0.11.1`. A `Versioner` step would stamp
that onto the package. `GitHubReleasesInfoProvider` already strips a leading `v` from
the tag and sets `%version%`, so this recipe deliberately has no `Versioner`. Check
what a vendor actually puts in `Info.plist` before assuming it's clean.

## Updating

Nothing to do: each run picks up the newest release.
