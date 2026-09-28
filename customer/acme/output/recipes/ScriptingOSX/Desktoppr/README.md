# desktoppr

**Pattern 2a — GitHub release, signed vendor `.pkg` copied as-is.** One of the
[tools worth knowing about](../../../../../../docs/community-tools.md).

Sets the desktop picture: `desktoppr "/Library/Desktop Pictures/Acme/kiosk.jpg"`. Must run as the user. By Armin Briegel (Scripting OS X).

| | |
|---|---|
| Source | GitHub releases, [`scriptingosx/desktoppr`](https://github.com/scriptingosx/desktoppr) |
| Signature | Developer ID Installer: Armin Briegel (JME5BW3F3R); notarized. Verified by certificate chain (`expected_authority_names`), copied from `pkgutil --check-signature`. |
| Version | From the release tag |
| Output | `Desktoppr-<version>.pkg`: the vendor's own package, **unchanged** and **without** the org prefix, because we didn't build it |
| Last live run | 0.5 |

This is a sealed vendor package: it's never opened or rebuilt. Anything you configure
with the tool (your Dock layout, your picture, your browser choice) goes in a separate
**config slice** that installs after it. See
[`docs/community-tools.md`](../../../../../../docs/community-tools.md) for the pattern and a
worked kiosk example.
