# AcmeSupport (fictional)

> **EXAMPLE — no real download.** AcmeSupport is Acme Fruit Co.'s fictional help-desk
> helper app. The recipe shows a complete Pattern 6b recipe and passes lint; there is no
> payload to stage, so it can't run.

**Pattern 6b — rebuilt package, payload + scripts.** The original in-house package
survives but its sources don't; `sudo bin/pkg-reverse.sh` extracted the payload and
scripts, and this recipe rebuilds from them.

| | |
|---|---|
| Source | `vendor_cache/AcmeFruitCo/AcmeSupport/payload.zip` + `scripts.zip` |
| Payload | `/Applications/AcmeSupport.app`, `/Library/LaunchAgents/com.acmefruit.support.plist` |
| Scripts | `postinstall` loads the agent for the logged-in user (see `.devagent/skills/postinstall-as-user.md`) |
| Identifier | `com.acmefruit.support` — **kept from the legacy package** so the rebuild upgrades the existing receipt instead of installing beside it |
| Signature | None: the legacy package and app were never signed. `NO_CODE_SIGNATURE_REQUIRED: true`. No team ID. |
| Version | Pinned in the download recipe's `Input` (`3.2.0`) |
| Output | `Acme_AcmeSupport.pkg` |

## Before trusting a rebuild

Diff it against the package it replaces:
`bin/pkg-compare.sh --old-pkg AcmeSupport-legacy.pkg --new-pkg <cache>/Acme_AcmeSupport.pkg`
(methodology lesson 20; `specs/pkg-compare/01-pkg-compare.md`).

<!-- VARIABLES-SPEC-START -->

filename_pattern=`payload.zip`, `scripts.zip`

manufacturer_url=`https://it.acmefruit.example/`

drop_folder=`vendor_cache/AcmeFruitCo/AcmeSupport/`

upload_url=`vendor_cache/AcmeFruitCo/AcmeSupport/payload.zip`

<!-- VARIABLES-SPEC-END -->
