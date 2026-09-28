# Fruit screensaver

**Pattern 2b — GitHub release, rebuilt.** Installs the Fruit screensaver for all users.
That's all: it does **not** make Fruit anyone's screensaver. That's a configuration
choice, shipped separately as the
[`Fruit-Screensaver-Default`](../Fruit-Screensaver-Default/README.md) slice.

| | |
|---|---|
| Source | GitHub releases, `Corkscrews/fruit`, asset `Fruit.saver.tar.gz` |
| License | MIT |
| Signature | **Ad-hoc only** — no Developer ID, no team ID (see "Signature status") |
| Architecture | Apple silicon only (`arm64` binary) |
| Version | Read from the bundle |
| Output | `Acme_Fruit-Screensaver.pkg`, installs `/Library/Screen Savers/Fruit.saver` |
| Slices | `Fruit-Screensaver-Default` (optional) — install **after** this package |
| Last live run | 1.3.3 |

## Why "install" and "make it the default" are separate packages

Installing the screensaver makes it *available* in System Settings; it's a tool. Making it
everyone's screensaver is a *policy*. Keeping them apart lets an org offer Fruit without
imposing it, apply the default to only some Macs, and change or roll back the policy
without touching the screensaver itself.

`/Library/Screen Savers/` is the all-users location. Installing there skips the "this
user or all users?" prompt a double-clicked `.saver` shows.

## Signature status

`codesign -dvv` reports `Signature=adhoc`, `TeamIdentifier=not set`. The recipe keeps a
`CodeSignatureVerifier` with an **identifier-only** requirement
(`identifier "io.corkscrews.Fruit"`). That proves the bundle is intact and is the bundle
we expect. It does **not** prove who published it — anyone can ad-hoc sign a bundle with
that identifier. The recipe's `Input` records `teamid: UNSIGNED_NO_TEAMID` so the lint rule
that wants a pinned publisher (CSV-005) knows this is deliberate.

**Open question for the org:** the standards reserve Pattern 8 (Experimental, with a
named approver) for unsigned apps. Whether an ad-hoc-signed public app belongs there is
a policy decision, not a technical one.

## Install testing

Built, not installed, by this kit's automation. Install on a test Mac and confirm Fruit
appears in **System Settings → Screen Saver** for every user, and that nobody's current
screensaver changed.
