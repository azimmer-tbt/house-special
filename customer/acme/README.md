# Acme Fruit Co. — the worked example customer

Acme Fruit Co. is a fictional organization with a managed Mac fleet. This folder is
what the toolkit looks like **in use** for one customer: a catalogue of apps to
package, the hints the analysis tools need, per-package plans, and a real recipe repo
whose recipes run end to end.

Start with [`docs/getting-started.md`](../../docs/getting-started.md) for a 15-minute
tour that uses this folder. For the rules about what goes where, see
[`docs/customer-contract.md`](../../docs/customer-contract.md).

## What's here

| Path | What it is | Read by |
|---|---|---|
| `end_result.yaml` | The target catalogue: every app Acme wants packaged, its pattern and status | `bin/analyze-materials.sh --customer acme` |
| `clues.yaml` | Hints for telling vendor packages from in-house builds | `bin/analyze-package.sh --customer acme` |
| `autopkg-recipes.csv` | Progress tracker (one row per app) | people |
| `paths.yaml` | Where Acme's material lives; paths relative to this folder | `recipe_repo.root`: the linter and preflight; the rest: people, agent skills |
| `plans/` | Per-package plans of attack (`specs/method/00-methodology.md`) | people, agents |
| `input/` | Raw vendor material as received (gitignored) | `bin/analyze-materials.sh` |
| `sessions/` | Working-session logs (gitignored) | people, agents |
| `troubleshooting/` | Logs and screenshots while debugging (gitignored) | people |
| `output/` | **Acme's recipe repo** — `recipes/`, the vendor-drop registry, the vendor-cache manifest | `--customer acme` (the registry default), or `--repo customer/acme/output` |

Org naming (identifier prefix `com.acmefruit.autopkg`, package prefix `Acme_`) comes
from the kit's [`config/org.yaml`](../../config/org.yaml). Acme has no `org.yaml` of its
own; a customer with different naming would add one here
([FORMATS §11](../../docs/FORMATS.md#11-per-customer-files-orgyaml-checkslocalyaml-leak-patterns)).
Acme is registered in the example registry,
[`config/customers.example.yaml`](../../config/customers.example.yaml); copy it to
`config/customers.yaml` to make Acme your default customer.

## The catalogue

| App | Pattern | Kind |
|---|---|---|
| Moonlight | 2b — GitHub release DMG (drag-to-Applications) | **live** |
| Raspberry Pi Imager | 2b — GitHub release DMG | **live** |
| Pearcleaner | 2b — GitHub release DMG | **live** |
| Orange Data Mining | 3c — link scraped from the vendor's page | **live** |
| Fruit screensaver | 2b — GitHub release (`.tar.gz`); installs the screensaver only | **live** |
| Fruit screensaver default | 6b — **config slice**: makes it each user's screensaver, acting as the logged-in user; installed after | **live** |
| Fruta new-hire starter kit | 2d — GitHub source ZIP → tarball on every Desktop | **live** |
| Orchard Analytics | 4c — vendor DMG, app only | example (fictional) |
| Orchard Analytics license | 6c — **slice**: the license file, installed after the app | example (fictional) |
| AcmeSupport | 6b — rebuilt in-house package | example (fictional) |
| dockutil, desktoppr, default-browser, Outset, swiftDialog, Nudge, icongrabber | 2a — signed vendor `.pkg` from GitHub, copied as-is | **live** — [tools worth knowing about](../../docs/community-tools.md) |
| Firefox, Google Chrome | 3b — stable redirect URL | catalogue |
| Microsoft Word | 5 — vendor pkg at a stable URL | catalogue (see the template example) |
| HP printer drivers | 4b — distribution pkg, vendor drop | catalogue |
| Acme Wallpaper | 6c — single file | catalogue (fictional) |
| Acme UninstallAgent | 6d — payloadless | catalogue (fictional) |
| Pomelo Studio | 7 — faux vendor DMG | catalogue (fictional) |

- **live** — real, public software. The recipe downloads, verifies the code signature,
  and builds an `Acme_*.pkg`. Last verified with AutoPkg 2.9 on 2026-09-26.
- **example** — a complete recipe for a fictional app. Passes lint; there is nothing to
  download, so it can't run.
- **catalogue** — listed so the analysis tools and the tracker have realistic data; no
  recipe yet. Where a template has a worked example of the same pattern,
  `end_result.yaml` points at it.

Pattern definitions: [`docs/patterns.md`](../../docs/patterns.md).

## Running the live recipes

```bash
bin/recipe-linter.sh --repo customer/acme/output --pair-check
autopkg run -v --search-dir customer/acme/output/recipes \
  customer/acme/output/recipes/MoonlightGameStreaming/Moonlight/Moonlight.pkg.recipe.yaml
```

The built package lands in `~/Library/AutoPkg/Cache/com.acmefruit.autopkg.pkg.Moonlight/`.

## Licenses

The live examples download public software; this repository doesn't redistribute
any of it. Licenses were checked on 2026-09-26:

| App | License |
|---|---|
| Moonlight | GPL-3.0 |
| Raspberry Pi Imager | Apache-2.0 (main code) |
| Pearcleaner | Apache-2.0 + Commons Clause (source-available; may not be sold) |
| Orange Data Mining | GPL-3.0 |
| Fruit screensaver | MIT |
| Fruta sample | Apple sample code license (MIT terms); image credits in its `ACKNOWLEDGMENTS.txt` |

The Fruta kit is repackaged and copied to users' Desktops inside the org; its
license and acknowledgements travel with it.
