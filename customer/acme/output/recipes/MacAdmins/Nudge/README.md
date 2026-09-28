# Nudge

**Pattern 2a — GitHub release, signed vendor `.pkg` copied as-is.** One of the
[tools worth knowing about](../../../../../../docs/community-tools.md).

Reminds users to install macOS updates, with deadlines. This recipe takes **`Nudge_Essentials`** (app + LaunchAgent + logger); the release also offers each part separately (`Nudge`, `Nudge_LaunchAgent`, `Nudge_Logger`), which is the vendor slicing its own product. Nudge's settings (deadlines, minimum OS) are policy: deliver them separately, as a configuration profile or a slice. The output file is named `Nudge-<version>.pkg`.

| | |
|---|---|
| Source | GitHub releases, [`macadmins/nudge`](https://github.com/macadmins/nudge) |
| Signature | Developer ID Installer: Mac Admins Open Source (T4SK8ZXCXG); notarized. Verified by certificate chain (`expected_authority_names`), copied from `pkgutil --check-signature`. |
| Version | From the release tag |
| Output | `Nudge-<version>.pkg`: the vendor's own package, **unchanged** and **without** the org prefix, because we didn't build it |
| Last live run | 2.1.3.81860 |

This is a sealed vendor package: it's never opened or rebuilt. Anything you configure
with the tool (your Dock layout, your picture, your browser choice) goes in a separate
**config slice** that installs after it. See
[`docs/community-tools.md`](../../../../../../docs/community-tools.md) for the pattern and a
worked kiosk example.
