---
name: postinstall-as-user
description: The "runs as root, acts as the logged-in user" pattern for package scripts that must set per-user preferences or deliver files into every user's home, with a per-user LaunchAgent for users not logged in or created later. Use when someone says "set this for every user", "per-user preference from a postinstall", "put a file on each user's Desktop", "run as the console user", or "launchctl asuser".
---
# Postinstall as the User

## When to use

A package (usually Pattern 2c/4d/6b with `scripts:`) must change something that
belongs to a user — a `defaults` preference, a file in `~` — while the installer
runs as root. Writing into a home as root leaves root-owned files there, and
per-user/per-host prefs need the user's GUI context.

Worked examples (read both before writing a new one):
- **Preference in GUI context:** [Fruit screensaver default slice](../../customer/acme/output/recipes/Corkscrews/Fruit-Screensaver-Default/README.md) —
  [`postinstall`](../../customer/acme/output/recipes/Corkscrews/Fruit-Screensaver-Default/scripts/postinstall)
  (a config slice: the screensaver itself is a separate package)
- **File delivery to every account:** [Fruta starter kit](../../customer/acme/output/recipes/AcmeFruitCo/Fruta-Starter-Kit/README.md) —
  [`postinstall`](../../customer/acme/output/recipes/AcmeFruitCo/Fruta-Starter-Kit/scripts/postinstall)

## Inputs

- The per-user action, as a **helper script** installed in the payload under
  `/Library/Application Support/<Org>/<App>/`.
- A **LaunchAgent** plist in the payload at `/Library/LaunchAgents/<reverse-dns>.plist`.
- The package's `scripts/postinstall`.

## Steps

1. **Helper (runs as the user, never root):** refuse `id -u` = 0; exit 0 early if a
   marker exists at `~/Library/Application Support/<Org>/.<thing>-applied`; do the
   work; `mkdir -p` the marker dir and `touch` the marker only on success. The marker
   makes it idempotent and respects a user who later changes the setting.
2. **LaunchAgent:** `ProgramArguments` = the helper, `RunAtLoad` true,
   `LimitLoadToSessionType` `Aqua`. It covers users who weren't logged in and
   accounts created later, at their next login.
3. **postinstall (root):**
   - act only on the running system: `[[ "${3:-/}" == "/" ]] || exit 0`;
   - **GUI-context preference** — console user only:
     `user=$(/usr/bin/stat -f%Su /dev/console)`; skip `""`, `root`, `loginwindow`,
     `_mbsetupuser` (the agent handles them later); then
     `/bin/launchctl asuser "$(id -u "$user")" /usr/bin/sudo -u "$user" "$HELPER"`;
   - **file delivery to every account** — loop `dscl . -list /Users UniqueID`,
     keep UID ≥ 501 with a real `NFSHomeDirectory` that exists, and run
     `/usr/bin/sudo -H -u "$user" "$HELPER"` (`-H` so `$HOME` is theirs);
   - **never fail the install over a preference**: log and `exit 0`; the agent retries.
4. **Recipe:** `PkgCreator` with `scripts: "%RECIPE_DIR%/scripts"`, the payload copied
   into the pkgroot, and `chown` entries: an **owner-only** `root:wheel` entry on
   `Library` (so the building user isn't recorded as owner), then leaf entries for your
   own dirs/files. **No `mode:` on directories** — it applies to every descendant
   (lesson 17); a file mode like `0644` on the plist leaf is fine.
5. **Lint the scripts:** `shellcheck -S warning scripts/postinstall payload/**/*.sh`
   and keep them bash 3.2 (`/bin/bash`, no associative arrays, absolute tool paths).
   Scripts must be executable (lesson 18); `plutil -lint` the plist.

## Outputs

`scripts/postinstall`, `payload/Library/Application Support/<Org>/<App>/<helper>.sh`,
`payload/Library/LaunchAgents/<label>.plist`, `chown` entries, and a README section
"Runs as root, acts as the user" plus an install-test checklist.

## Verify

Install-test on a test Mac, per supported macOS release:
1. With a user logged in: applied immediately; files in `~` owned by that user (`ls -l`).
2. At the login window: nothing happens at install; applied at next login.
3. A second existing account and a newly created account both get it at login.
4. Reinstall: no re-apply (marker respected); user's own later change survives.
5. Helper run as root refuses; `sudo installer -pkg … -target /` exits 0 even if the
   helper fails.
6. `pkgutil --payload-files` / `lsbom` shows `root:wheel` on your paths, no stray modes.

## Pitfalls

- **A self-deleting run-once agent doesn't work**: agents run as the user, and only
  root can delete from `/Library/LaunchAgents`. Use the marker instead.
- Writing prefs as root (`defaults write` under `sudo` without `-u`) leaves root-owned
  files in the home. `-currentHost` prefs need the user's GUI session (`launchctl asuser`).
- `$3` is not `/` when installing to another volume — do nothing then.
- Lesson 19 warns about `chown` entries on shared parents like `Library`; the examples
  use an owner-only entry there on purpose. Install-test on every supported release.
- Some preferences move between macOS releases (screensaver settings moved under
  Wallpaper in 14); a configuration profile may be the managed alternative.

## References

- [`reference/methodology.md`](../../reference/methodology.md) (lessons 17, 18, 19)
- [`docs/patterns.md`](../../docs/patterns.md) (2c, 2d, 4d, 6b)
- [`.devagent/standards/bash-code-standards.md`](../standards/bash-code-standards.md)
- [autopkg-recipe-development.md](autopkg-recipe-development.md)
