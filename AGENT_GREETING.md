# Welcome to House Special

Hello! I'm the startup guide for this toolkit. Tell me what you're here to do and
I'll point you at the right place.

---

## What are you here to do?

**A — I'm new. Show me around.**
  → [`README.md`](README.md), then the 15-minute tour in
  [`docs/getting-started.md`](docs/getting-started.md). It uses the worked example,
  Acme Fruit Co. ([`customer/acme/`](customer/acme/)).

**B — I have one package to turn into a recipe.**
  → Follow [`docs/build-your-first-recipe.md`](docs/build-your-first-recipe.md): four
  questions (where from? what file? do we add anything? scripts?) with three small flowcharts, then
  template → lint → run → README. Or ask to be walked through it: the
  [`first-recipe-interview`](.devagent/skills/first-recipe-interview.md) skill runs it
  as an interview. The short version:
  - A `.pkg` you were given: `bin/analyze-package.sh <file.pkg> --customer <name>`
    tells you vendor-built vs in-house.
  - An in-house package with no sources: `sudo bin/pkg-reverse.sh <file.pkg> --dest <cache-dir>`,
    then `bin/blueprint-to-recipe.sh` drafts the recipe (Pattern 6).
  - Then copy the matching template from [`templates/`](templates/) and read
    [`reference/methodology.md`](reference/methodology.md) before the first run.

**C — I have a pile of vendor material and need a plan.**
  → [`specs/method/00-methodology.md`](specs/method/00-methodology.md) is the per-package
  workflow. Scan the pile against your catalogue with
  `bin/analyze-materials.sh <dir> --customer <name>`, then write a plan per package
  (example: [`customer/acme/plans/orchard-analytics.md`](customer/acme/plans/orchard-analytics.md)).

**D — I'm setting up a new organization or customer.**
  → Set your naming in [`config/org.yaml`](config/org.yaml), then follow
  [`docs/customer-contract.md`](docs/customer-contract.md). Running a fork of this
  repo? [`docs/forking.md`](docs/forking.md).

**E — I'm an AI agent (ZooCode/Roo, Cline).**
  → Your rules are in [`.devagent/rules/`](.devagent/rules/) — read them in numeric
  order. [`.devagent/rules/03-pre-action-reads.md`](.devagent/rules/03-pre-action-reads.md)
  lists the skills and when to use each. Then the methodology above is your task
  template; per-package plans live in `customer/<name>/plans/`.

---

## Where to go next

| If you want to… | Read |
|---|---|
| Understand the layout and the frontend contract | [`README.md`](README.md) |
| Look up a term | [`docs/glossary.md`](docs/glossary.md) |
| See the full pipeline end to end | [`docs/round-trip-workflow.md`](docs/round-trip-workflow.md) |
| Classify a package (vendor or custom?) | [`docs/package-analysis.md`](docs/package-analysis.md) |
| Scan vendor materials | [`docs/material-analysis.md`](docs/material-analysis.md) |
| Update an existing recipe for a new version | [`docs/updating-existing-recipes.md`](docs/updating-existing-recipes.md) |
| See a customer's progress | `customer/<name>/autopkg-recipes.csv` (e.g. [`customer/acme/autopkg-recipes.csv`](customer/acme/autopkg-recipes.csv)) |
| Know what's broken | [`docs/known-issues.md`](docs/known-issues.md) |

## One-command samples (using Acme)

```bash
bin/recipe-linter.sh --repo customer/acme/output --pair-check
bin/classify-recipe.sh customer/acme/output/recipes/MoonlightGameStreaming/Moonlight
bin/analyze-package.sh ~/Downloads/some.pkg --customer acme
bin/analyze-materials.sh customer/acme/input --customer acme
bin/inspect-dmg.sh ~/Downloads/some.dmg
bin/inspect-app.sh /Applications/Some.app --output yaml
```

---

**So — what would you like to work on?**
