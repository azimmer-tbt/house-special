# Fruta new-hire developer starter kit

**Pattern 2d — GitHub source ZIP, reassembled, with scripts.** Every developer account
gets a tarball of Apple's *Fruta* SwiftUI sample project on its Desktop.

| | |
|---|---|
| Source | `https://github.com/apple-sample-code/FrutaBuildingAFeatureRichAppWithSwiftUI/archive/refs/heads/main.zip` (GitHub's source archive; the repo has no releases) |
| License | Apple sample code license (MIT terms), © 2022 Apple Inc.; image assets credited in the project's `LICENSE/ACKNOWLEDGMENTS.txt` (Unsplash). The license and acknowledgements travel inside the tarball. |
| Signature | None — source code only. `NO_CODE_SIGNATURE_REQUIRED: true`. No team ID. |
| Version | Pinned (`version` in the download recipe's `Input`), because the source has none. Bump it when the kit changes. |
| Output | `Acme_Fruta-Starter-Kit.pkg` |
| Last live run | 1.0.0 |

## What the package installs

| Path | Purpose |
|---|---|
| `/Library/Application Support/AcmeFruit/StarterKit/Fruta/` | The project source (~700 files) |
| `/Library/Application Support/AcmeFruit/StarterKit/deliver-starter-kit.sh` | Per-user delivery: copies the tarball to `~/Desktop`, once |
| `/Library/LaunchAgents/com.acmefruit.starter-kit.plist` | Runs delivery at login, for accounts created after install |
| `postinstall` | Builds `Fruta-StarterKit.tar.gz`, then delivers it to every existing account |

## Design notes

- **Tarball built at install time.** Core AutoPkg has no processor that creates an
  archive, and shipping the source unpacked keeps the payload inspectable with
  `pkgutil --payload-files`. The postinstall writes the tarball atomically (temp file,
  then `mv`), so no one ever receives a half-written file.
- **Delivery runs as each user** (`sudo -H -u <user>`), so the copy on their Desktop is
  theirs, not root's. Only accounts with UID ≥ 501 and a real home directory qualify.
- **Once per user.** A marker in `~/Library/Application Support/AcmeFruit/` prevents
  re-delivery; someone who deletes the tarball doesn't get it back at every login.
- **New accounts** are handled by the LaunchAgent rather than the new-user template,
  which recent macOS protects.

## Install testing

Built, not installed, by this kit's automation. Test on a Mac with two local accounts:
both Desktops get the tarball; create a third account and log in as it; it gets the
tarball once.
