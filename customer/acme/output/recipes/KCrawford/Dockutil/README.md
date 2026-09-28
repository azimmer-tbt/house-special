# dockutil

**Pattern 2a — GitHub release, signed vendor `.pkg` copied as-is.** One of the
[tools worth knowing about](../../../../../../docs/community-tools.md).

Adds, removes and reorders Dock items: `dockutil --remove all`, `dockutil --add "/Applications/Google Chrome.app"`, `--allhomes`.

| | |
|---|---|
| Source | GitHub releases, [`kcrawford/dockutil`](https://github.com/kcrawford/dockutil) |
| Signature | Developer ID Installer: Kyle Crawford (Z5J8CJBUWC); notarized. Verified by certificate chain (`expected_authority_names`), copied from `pkgutil --check-signature`. |
| Version | From the release tag |
| Output | `Dockutil-<version>.pkg`: the vendor's own package, **unchanged** and **without** the org prefix, because we didn't build it |
| Last live run | 3.1.3 |

This is a sealed vendor package: it's never opened or rebuilt. Anything you configure
with the tool (your Dock layout, your picture, your browser choice) goes in a separate
**config slice** that installs after it. See
[`docs/community-tools.md`](../../../../../../docs/community-tools.md) for the pattern and a
worked kiosk example.
