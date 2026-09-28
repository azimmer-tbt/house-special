# icongrabber

**Pattern 2a — GitHub release, signed vendor `.pkg` copied as-is.** One of the
[tools worth knowing about](../../../../../../docs/community-tools.md).

Extracts an app's icon, e.g. for a Self Service item.

| | |
|---|---|
| Source | GitHub releases, [`macadmins/icongrabber`](https://github.com/macadmins/icongrabber) |
| Signature | Developer ID Installer: Mac Admins Open Source (T4SK8ZXCXG); notarized. Verified by certificate chain (`expected_authority_names`), copied from `pkgutil --check-signature`. |
| Version | From the release tag |
| Output | `IconGrabber-<version>.pkg`: the vendor's own package, **unchanged** and **without** the org prefix, because we didn't build it |
| Last live run | 1.0.1 |

This is a sealed vendor package: it's never opened or rebuilt. Anything you configure
with the tool (your Dock layout, your picture, your browser choice) goes in a separate
**config slice** that installs after it. See
[`docs/community-tools.md`](../../../../../../docs/community-tools.md) for the pattern and a
worked kiosk example.
