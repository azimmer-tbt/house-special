# Pearcleaner

**Pattern 2b — GitHub release DMG, rebuilt with PkgCreator.**

| | |
|---|---|
| Source | GitHub releases, `alienator88/Pearcleaner`, asset `Pearcleaner.dmg` |
| License | Apache-2.0 with the Commons Clause ("fair-code": source-available, may not be sold). Fine to download and deploy internally; check your own policy before redistributing. |
| Signature | Developer ID Application: Marius Lupascu (`BK8443AXLU`) |
| Version | Read from the app bundle |
| Output | `Acme_Pearcleaner.pkg`, installs `/Applications/Pearcleaner.app` |
| Last live run | 5.4.3 |

## Why it's in the catalogue

Development is paused at 5.4.3, which makes it a stable, fixed-version target for testing
the kit itself: a run today and a run next month should build the same package.

The release also carries `Pearcleaner.zip` and per-architecture zips; `ASSET_REGEX`
(`^Pearcleaner\.dmg$`) is anchored at both ends so only the DMG matches.
