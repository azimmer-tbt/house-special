# Outset

**Pattern 2a — GitHub release, signed vendor `.pkg` copied as-is.** One of the
[tools worth knowing about](../../../../../../docs/community-tools.md).

Runs scripts (and packages) at boot and login, every time or once per user. The standard way to make a setting "stick" at login.

| | |
|---|---|
| Source | GitHub releases, [`macadmins/outset`](https://github.com/macadmins/outset) |
| Signature | Developer ID Installer: Mac Admins Open Source (T4SK8ZXCXG); notarized. Verified by certificate chain (`expected_authority_names`), copied from `pkgutil --check-signature`. |
| Version | From the release tag |
| Output | `Outset-<version>.pkg`: the vendor's own package, **unchanged** and **without** the org prefix, because we didn't build it |
| Last live run | 4.3.0.22031 |

This is a sealed vendor package: it's never opened or rebuilt. Anything you configure
with the tool (your Dock layout, your picture, your browser choice) goes in a separate
**config slice** that installs after it. See
[`docs/community-tools.md`](../../../../../../docs/community-tools.md) for the pattern and a
worked kiosk example.
