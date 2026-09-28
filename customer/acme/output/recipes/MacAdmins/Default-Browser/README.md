# default-browser

**Pattern 2a — GitHub release, signed vendor `.pkg` copied as-is.** One of the
[tools worth knowing about](../../../../../../docs/community-tools.md).

Sets the default web browser for the current user: `/opt/macadmins/bin/default-browser --identifier com.google.chrome`.

| | |
|---|---|
| Source | GitHub releases, [`macadmins/default-browser`](https://github.com/macadmins/default-browser) |
| Signature | Developer ID Installer: Mac Admins Open Source (T4SK8ZXCXG); notarized. Verified by certificate chain (`expected_authority_names`), copied from `pkgutil --check-signature`. |
| Version | From the release tag |
| Output | `Default-Browser-<version>.pkg`: the vendor's own package, **unchanged** and **without** the org prefix, because we didn't build it |
| Last live run | 1.1.19 |

This is a sealed vendor package: it's never opened or rebuilt. Anything you configure
with the tool (your Dock layout, your picture, your browser choice) goes in a separate
**config slice** that installs after it. See
[`docs/community-tools.md`](../../../../../../docs/community-tools.md) for the pattern and a
worked kiosk example.
