# swiftDialog

**Pattern 2a — GitHub release, signed vendor `.pkg` copied as-is.** One of the
[tools worth knowing about](../../../../../../docs/community-tools.md).

Shows configurable dialogs (progress, prompts, forms) from scripts.

| | |
|---|---|
| Source | GitHub releases, [`swiftDialog/swiftDialog`](https://github.com/swiftDialog/swiftDialog) |
| Signature | Developer ID Installer: Commonwealth Scientific and Industrial Research Organisation (PWA5E9TQ59); notarized. Verified by certificate chain (`expected_authority_names`), copied from `pkgutil --check-signature`. |
| Version | From the release tag |
| Output | `SwiftDialog-<version>.pkg`: the vendor's own package, **unchanged** and **without** the org prefix, because we didn't build it |
| Last live run | 3.1.0 |

This is a sealed vendor package: it's never opened or rebuilt. Anything you configure
with the tool (your Dock layout, your picture, your browser choice) goes in a separate
**config slice** that installs after it. See
[`docs/community-tools.md`](../../../../../../docs/community-tools.md) for the pattern and a
worked kiosk example.
