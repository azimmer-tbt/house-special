# Fruit screensaver — make it the default

**Pattern 6b — configuration slice, payload + scripts.** Makes Fruit each user's
screensaver, once. The screensaver itself is installed by
[`Fruit-Screensaver`](../Fruit-Screensaver/README.md): this package only sets a
preference, and a user who later picks something else keeps their choice.

| | |
|---|---|
| Source | Nothing is downloaded: `payload/` and `scripts/` are small, org-authored files committed next to this recipe |
| Signature | None: org-authored scripts and a plist. `NO_CODE_SIGNATURE_REQUIRED: true`. No team ID. |
| Version | Pinned (`version` in the download recipe's `Input`); bump it when `payload/` or `scripts/` change |
| Output | `Acme_Fruit-Screensaver-Default.pkg` |

## Install order

**Install after:** `Acme_Fruit-Screensaver.pkg`. The helper checks that
`/Library/Screen Savers/Fruit.saver` exists. If it doesn't yet, the helper leaves no
marker, so the LaunchAgent simply tries again at the user's next login.

## What the package installs

| Path | Purpose |
|---|---|
| `/Library/Application Support/AcmeFruit/FruitScreensaver/apply-screensaver.sh` | Per-user helper: selects Fruit as that user's screensaver, once. |
| `/Library/LaunchAgents/com.acmefruit.fruit-screensaver.plist` | Runs the helper at every user's login. |
| `postinstall` | Runs the helper right away for whoever is logged in. |

## Runs as root, acts as the user

Choosing a screensaver is a per-user, per-host preference
(`defaults -currentHost write com.apple.screensaver moduleDict`). An installer runs as
root, and writing a user's preferences as root leaves root-owned files in their home.
So:

- the **postinstall** finds the console user (`stat -f%Su /dev/console`), skips the
  login window and setup assistant, and runs the helper *as that user* with
  `launchctl asuser <uid> sudo -u <user> …`;
- the **LaunchAgent** covers everyone else — users who weren't logged in, and accounts
  created later — at their next login;
- the **helper** refuses to run as root and writes a marker in the user's Library after
  it succeeds, so it applies once. A user who later picks a different screensaver keeps
  their choice.

A "run-once agent that deletes itself" doesn't work here: agents run as the user, and
only root can remove a file from `/Library/LaunchAgents`.

See `.devagent/skills/postinstall-as-user.md` for the general pattern.

## Install testing

Built, not installed, by this kit's automation. Before deploying, with
`Acme_Fruit-Screensaver.pkg` already installed:

1. Install on a test Mac with a user logged in; confirm Fruit is selected.
2. Install at the login window; log in; confirm the agent selects it.
3. On macOS 14 and later, Apple moved screensaver settings under Wallpaper. Confirm the
   `moduleDict` preference is still honoured on each release you support; if not, a
   configuration profile (`com.apple.screensaver` payload, `modulePath`) is the managed
   alternative.
4. Install this slice **without** the screensaver package: the helper must exit quietly
   and apply at a later login once `Fruit.saver` exists.
5. Confirm the shared folders (`/Library`, `/Library/Application Support`,
   `/Library/LaunchAgents`) keep their stock owners and modes after install. The package
   declares the stock values ([`docs/package-ownership.md`](../../../../../../docs/package-ownership.md)).
