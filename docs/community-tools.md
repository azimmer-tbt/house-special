# Tools worth knowing about

The same few requests arrive at every Mac admin sooner or later:

- *"Put these apps in the Dock, and nothing else."*
- *"Make the desktop the school's sports team."*
- *"Make Chrome the default browser."*
- *"…and make it stay that way."*

Desktop picture, Dock items, and default browser can be maddening to script by hand. Each has a small, free, community-trusted tool that does it properly. If you didn't know they existed, now you do. The kit ships a recipe for every tool below, so you can package them like anything else.

| Tool | Solves | By | Recipe |
|---|---|---|---|
| [**dockutil**](https://github.com/kcrawford/dockutil) | Add, remove and reorder Dock items (`--remove all`, `--add …`, `--allhomes`) | Kyle Crawford | [`KCrawford/Dockutil`](../customer/acme/output/recipes/KCrawford/Dockutil/README.md) |
| [**desktoppr**](https://github.com/scriptingosx/desktoppr) | Set the desktop picture (per screen, scale, solid colour) | Armin Briegel, Scripting OS X | [`ScriptingOSX/Desktoppr`](../customer/acme/output/recipes/ScriptingOSX/Desktoppr/README.md) |
| [**default-browser**](https://github.com/macadmins/default-browser) | Set the default web browser | MacAdmins | [`MacAdmins/Default-Browser`](../customer/acme/output/recipes/MacAdmins/Default-Browser/README.md) |
| [**Outset**](https://github.com/macadmins/outset) | Run scripts at boot or login: every time, or once per user | MacAdmins | [`MacAdmins/Outset`](../customer/acme/output/recipes/MacAdmins/Outset/README.md) |
| [**swiftDialog**](https://github.com/swiftDialog/swiftDialog) | Show users a configurable dialog from a script | swiftDialog project | [`SwiftDialog/SwiftDialog`](../customer/acme/output/recipes/SwiftDialog/SwiftDialog/README.md) |
| [**Nudge**](https://github.com/macadmins/nudge) | Remind users to install macOS updates, with deadlines | MacAdmins | [`MacAdmins/Nudge`](../customer/acme/output/recipes/MacAdmins/Nudge/README.md) |
| [**icongrabber**](https://github.com/macadmins/icongrabber) | Extract an app's icon, e.g. for a Self Service item | MacAdmins | [`MacAdmins/IconGrabber`](../customer/acme/output/recipes/MacAdmins/IconGrabber/README.md) |

**Why these and not a random GitHub project:** the
[MacAdmins](https://github.com/macadmins) organisation and the authors above are long-standing,
well-known members of the Mac admin community. Every package above is also **signed with a
Developer ID and notarized by Apple** (checked with `pkgutil --check-signature` and
`spctl -a -vv -t install`, 2026-09-27).

Treat *signed + notarized* as **the floor, not a guarantee**. Notarization means Apple's
automated scan found nothing malicious **when the build was submitted**. It isn't a code
review, and it says nothing about what the software does with the permissions you give it.
The floor does carry forward, though: Apple can revoke a developer's certificate or a
notarization ticket if something turns out to be bad, and macOS keeps checking at launch
(Gatekeeper, and XProtect's regularly updated signatures). Reputation
of the maintainers, an open codebase and a long track record are what lift these above
the floor. Check both for any tool you add, and re-check signatures on every new version
(the recipes do this on every run).

All seven are Pattern **2a**: a signed vendor `.pkg` from a GitHub release, copied as-is
and never opened ([patterns](patterns.md)).

---

## How to use them: tool package + config slice

Installing the tool changes nothing a user can see. The *configuration*, meaning which
apps go in the Dock and which picture goes on the desktop, is a separate **slice**
([build-your-first-recipe.md](build-your-first-recipe.md) step 3). So a request becomes
two things:

1. the **tool's** package (from the recipe here), and
2. your **config slice**: a small package whose script runs the tool with *your*
   choices.

Two ways to run the config:

| When | How | Good for |
|---|---|---|
| **Once**, at install | The config slice's `postinstall` runs the tool **as the logged-in user** (see [postinstall-as-user](../.devagent/skills/postinstall-as-user.md)). The tool can even ride along in the slice itself, installed to a temporary folder like `/private/tmp/…`, and be deleted when the script finishes. Nothing stays behind and nothing user-visible changes except the setting. | A one-time setup: "new machines start with this Dock" |
| **At every login** | Install the tool normally, plus **Outset**, and have the slice drop a script into Outset's *login-every* folder. Outset runs it as each user at every login. | "Make it stay that way": labs, libraries, kiosks |

Things to know:
- **Dock, desktop picture and default browser are per-user settings.** The tools must run
  as the user, not as root: via Outset, a LaunchAgent, or `launchctl asuser`. dockutil
  can also edit other users' Docks directly (`--allhomes`, or a home-folder path).
- **default-browser** installs to `/opt/macadmins/bin/default-browser` and takes
  `--identifier` (`com.google.chrome`, `com.apple.safari`, `org.mozilla.firefox`,
  `com.microsoft.edgemac`). Its README notes that System Settings may need a restart
  afterwards.
- **desktoppr** can manage the picture continuously from a LaunchAgent (`desktoppr
  manage`). On macOS 13 and later, LaunchAgent tools need approval in Login Items, which
  an MDM profile can pre-approve.
- If you have an MDM, check what it can do natively first; some of this is a checkbox
  there. Not every AutoPkg user has an MDM, though, and no MDM does all of it.

---

## Worked example: a kiosk

> *"Add Chrome, make it the default browser, and put it in the Dock as the only entry
> besides System Settings."*

A perfectly reasonable request, and miserable without these tools. With them:

| Package | Pattern | Where it comes from |
|---|---|---|
| Google Chrome | 3b (or a community recipe) | AutoPkg recipe |
| dockutil, default-browser, desktoppr | 2a | recipes above |
| Outset | 2a | recipe above |
| **Kiosk config slice** | 6b (payload + scripts) | yours: one login-every script |

The slice's login script (runs as the user, at every login, via Outset):

```bash
#!/bin/bash
# Kiosk: Chrome is the default browser and the Dock holds only Chrome and Settings.
/opt/macadmins/bin/default-browser --identifier com.google.chrome
dockutil --remove all --no-restart
dockutil --add "/Applications/Google Chrome.app" --no-restart
dockutil --add "/System/Applications/System Settings.app"
desktoppr "/Library/Desktop Pictures/Acme/kiosk.jpg"     # optional
```

(Check the tools' install paths on your Macs; dockutil and desktoppr normally land in
`/usr/local/bin`.)

## Worked example: no MDM, or an MDM that barely configures anything

Not ideal, but real: a school library with a dozen Macs and either no MDM at all, or a
limited one that does little beyond the basics. Some places go no further than "make sure
auto-enrollment and Find My are on, for anti-theft". With AutoPkg you can still produce
today's signed packages of Chrome, Outset, dockutil, default-browser and desktoppr, plus
the kiosk config slice above. Then either push them through whatever the MDM can deploy,
or put them on a flash drive and have someone install them on each Mac once. Every login
from then on:

- Chrome is the default browser;
- the Dock holds Chrome and System Settings;
- the desktop is the library's picture.

It's "enforced" only in the sense that any drift is undone at the next login. With the
flash drive there's no reporting and no remote updates: next term's Chrome means another
round with the drive. If the MDM can at least deploy packages, it covers the updates. When
a fuller MDM arrives, the same packages and the same slice deploy through it unchanged.
