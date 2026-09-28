# House Special

*An AutoPkg recipe toolkit for the recipes nobody else can write for you: your
house's own.*

Tooling and method for turning a pile of Mac software into
[AutoPkg](https://github.com/autopkg/autopkg) recipes that build consistently
named, signature-checked packages — whether the software comes from a GitHub
release, a vendor's download page, a file a vendor emailed you, or an old in-house
package nobody has the sources for.

## Start here

| You are… | Read |
|---|---|
| **Handed a package and asked to "build a recipe"** | **[`docs/build-your-first-recipe.md`](docs/build-your-first-recipe.md)** — a step-by-step walkthrough with decision flowcharts. No prior reading needed. |
| New to the kit and want the tour | [`docs/getting-started.md`](docs/getting-started.md) |
| Setting up a new org or customer | [`docs/customer-contract.md`](docs/customer-contract.md), [`docs/forking.md`](docs/forking.md) |
| Looking up a term or pattern | [`docs/glossary.md`](docs/glossary.md), [`docs/patterns.md`](docs/patterns.md) |
| Asked to set the Dock, desktop picture or default browser | [`docs/community-tools.md`](docs/community-tools.md): trusted tools that do it properly, with recipes |

It gives you:

- **A pattern taxonomy** for every way software arrives, with a template and a worked
  example for each ([`docs/patterns.md`](docs/patterns.md), [`templates/`](templates/)).
- **A config-driven recipe linter**: every rule lives in
  [`config/checks.yaml`](config/checks.yaml), none in code. It runs on AutoPkg's own
  Python, or any Python 3.10+ with PyYAML in CI
  ([`bin/recipe-linter.sh`](bin/recipe-linter.sh)).
- **Analysis tools** that tell a vendor package from an in-house build, match vendor
  material to your catalogue, and reverse-engineer an installed package into a recipe.
- **A method** — a per-package workflow and the lessons behind it
  ([`specs/method/00-methodology.md`](specs/method/00-methodology.md), [`reference/methodology.md`](reference/methodology.md)).
- **A worked example customer**, Acme Fruit Co., whose recipes run end to end
  ([`customer/acme/`](customer/acme/)).
- **Agent rules and skills** so a coding agent (ZooCode/Roo, Cline) follows the same
  method ([`.devagent/`](.devagent/)).

## Quick start

```bash
git clone https://github.com/azimmer-tbt/house-special.git && cd house-special
# Needs AutoPkg; see "Getting ready" below for the full list.

bin/recipe-linter.sh --repo customer/acme/output --pair-check          # lint Acme's recipes
autopkg run -v --search-dir customer/acme/output/recipes \
  customer/acme/output/recipes/MoonlightGameStreaming/Moonlight/Moonlight.pkg.recipe.yaml
```

Then follow the 15-minute tour in [`docs/getting-started.md`](docs/getting-started.md).

## Getting ready

### 1. Install the recommended prerequisites

| App | Why |
|---|---|
| [AutoPkg](https://github.com/autopkg/autopkg/releases) ≥ 2.3 | Runs the recipes. Its bundled Python (with PyYAML) runs the kit's Python tools, so there's nothing else to install. |
| [Recipe Robot](https://github.com/homebysix/recipe-robot) | Drafts a first recipe from a download URL or an app. |
| [Suspicious Package](https://www.mothersruin.com/software/SuspiciousPackage/) | Opens a `.pkg` without installing it: files, scripts, signature, notarization. |
| [Apparency](https://www.mothersruin.com/software/Apparency/) | The same for an `.app`: signature, Team ID, notarization, entitlements. |

Suspicious Package and Apparency (Mothers Ruin Software) are the **second opinion**:
whatever the kit's scripts report about a package or app, check it by eye in one of
them. Task-specific extras (ShellSpec, shellcheck) are listed in
[getting-started](docs/getting-started.md#prerequisites).

### 2. Get the AutoPkg wiki (strongly recommended)

```bash
git clone https://github.com/autopkg/autopkg.wiki.git reference/autopkg-wiki
```

The kit doesn't ship AutoPkg's documentation, but it's built to use a local copy.
With the wiki on disk, you and any coding agent can look up exactly what a processor
does (`Processor-<Name>.md`) instead of guessing. Even the largest language models
misremember processor arguments that one page would settle. Git ignores the folder,
and `git -C reference/autopkg-wiki pull` refreshes it. The content belongs to the AutoPkg project.

### 3. Set your org's naming

Everything org-specific in the kit comes from one file,
[`config/org.yaml`](config/org.yaml):

```yaml
org_name: "Acme Fruit Co."
identifier_prefix: "com.acmefruit.autopkg"   # → com.acmefruit.autopkg.download.<App> / .pkg.<App>
pkgname_prefix: "Acme_"                      # → Acme_<App>.pkg for packages you build
```

The linter's naming rules, the recipe generator and the classifier all read it.
Serving more than one org? A customer can carry its own `org.yaml` with just the keys
that differ; the linter, preflight and `analyze-package.sh --customer` lay it over this one
([FORMATS §11](docs/FORMATS.md#11-per-customer-files-orgyaml-checkslocalyaml-leak-patterns)).

### 4. Create your customer folder

Your own catalogue, vendor hints, plans and recipes go in `customer/<you>/`
(lowercase), next to the worked example in `customer/acme/`. Copy Acme's skeleton,
not its data: [Starting a new customer](docs/customer-contract.md#starting-a-new-customer)
has the commands, and the agent skill
[`new-customer`](.devagent/skills/new-customer.md) does it for you. Then register
it in `config/customers.yaml`, and make it the `default` if it's the one you work on
([FORMATS §10](docs/FORMATS.md#10-configcustomersyaml-the-customer-registry)). The
registry is yours: git ignores it, so it never goes upstream and a new version of the
kit never overwrites it. Start it from the example:

```bash
cp config/customers.example.yaml config/customers.yaml
```

The folder may live outside the kit, in your own private repo. With the example's
`default: acme`, `bin/recipe-linter.sh` with no arguments lints Acme, unless the
current directory is itself a recipe repo.

### 5. Keep it clean

Create a `.leak-patterns` file listing your org's names, and install the pre-commit
guard: `bin/check-sanitized.sh --install-hook`. To run a fork that keeps pulling
from this upstream, see [`docs/forking.md`](docs/forking.md).

## Kit vs customer

| | Kit (repo root) | Customer (`customer/<name>/`) |
|---|---|---|
| What | Tools, rules, templates, method | One org's catalogue, plans, recipe repo |
| Changes when | The toolkit improves | You package software |
| Org-specific? | Never — naming comes from `config/org.yaml` | Yes |

## Optional: `.overrides` for pipeline-supplied values

A recipe folder holds the recipe pair and a `README.md`. Nothing else is required.
Some orgs add an `.overrides` file: `key=value` lines next to the recipe pair.
AutoPkg never reads it. When it exists, `bin/run-recipes.sh` (or your CI job) passes
each line to `autopkg run` as `--key=KEY=VALUE`. The toolkit doesn't require it, the
linter has no rules about it, and Acme and the templates don't ship one.

It helps when a pipeline must supply a value that can't live in git. For example, a
license key: the recipe's script carries a placeholder, the pipeline writes the real
key into `.overrides` just before the run, and the harness slots it in. The key never
touches the recipe or the repo.

- An `.overrides` that holds a secret or a deployment detail (for example, which Jamf
  server to push to) is generated by the pipeline or gitignored. Never commit it, and
  add those values to your fork's `.leak-patterns`.
- A version, or anything AutoPkg must see, belongs in the recipe's `Input`. A bare
  `autopkg run` never reads `.overrides`.

Deployment-pipeline metadata (environments, regions, resource names) is org-specific
too. A fork may keep its own sidecar files for it and add lint rules for them. See
[Standards §3.4–3.5](reference/recipe-standards.md#34-the-overrides-file).

## The frontend contract

> Toolkit assets resolve from the script's own location. Work targets resolve from
> `--repo`. The current working directory is never load-bearing.

Every front end that works on a recipe repo accepts `--repo <recipe-repo>`, falling
back to `$AUTOPKG_TOOLKIT_REPO`, then to the current directory *only if* it contains a
`recipes/` directory. If none of those resolve, it fails loudly rather than guessing.
The linter, preflight and `bin/run-recipes.sh` put one step before the current directory: the selected
customer's recipe repo (`--customer`, `$AUTOPKG_TOOLKIT_CUSTOMER`, or the `default`
in `config/customers.yaml`).
The deliberate exception is `bin/clear-autopkg-cache.sh`, which takes no `--repo`: its
safety rests on the cache root being hard-coded.

Org naming resolves the same way: `--org <file>`, then `$AUTOPKG_TOOLKIT_ORG`, then
`config/org.yaml`.

## Two lanes

- **Lane A — batch generation**, for apps with a real download URL: Recipe Robot
  drafts recipes in bulk, the toolkit normalizes and lints them.
  `bin/rr-batch.sh -i apps.csv --log-dir ./logs -o ./out --lint`
- **Lane B — hands-on**, for vendor drops, rebuilt in-house packages and anything
  unusual: classify ([`docs/patterns.md`](docs/patterns.md)), plan
  ([`specs/method/00-methodology.md`](specs/method/00-methodology.md)), start from a
  template, run `bin/autopkg-preflight.py`, then `autopkg run`.

## Layout

| Path | Purpose |
|------|---------|
| `bin/` | Front ends — every user-facing entry point |
| `lib/` | Shared bash library, sourced by every front end |
| `config/` | `org.yaml` (your naming), `checks.yaml` (lint rules), `customers.example.yaml` (copy it to `customers.yaml`, your customer registry), `paths.yaml` |
| `templates/` | A template per pattern, most with a worked example |
| `guardrails/` | Task framing, checklist, and `audit/` checks run by `bin/autopkg-preflight.py` |
| `docs/` | User documentation — start with [`docs/getting-started.md`](docs/getting-started.md) |
| `reference/` | [`methodology.md`](reference/methodology.md) (lessons), [`recipe-standards.md`](reference/recipe-standards.md) (the standard), `autopkg-wiki/` (your local clone of the AutoPkg wiki; see Getting ready, step 2) |
| `specs/` | Specifications for each tool — read before changing one |
| `tests/` | ShellSpec suite; run `shellspec` (uses `/bin/bash` 3.2) |
| `customer/` | Customer workspaces; `customer/acme/` is the worked example |
| `.devagent/` | Agent rules, skills and standards (loaded via `.roo/rules` and `.clinerules`) |

## Toolchain

- **Shell tools** target stock macOS bash 3.2. **Python tools**, the linter among
  them, run on **AutoPkg's bundled Python** (`/usr/local/autopkg/python`), which
  always has PyYAML, so there is nothing to install. On a CI runner without AutoPkg,
  point `AUTOPKG_TOOLKIT_PYTHON` at any Python 3.10+ with PyYAML
  ([`specs/toolkit/00-constitution.md`](specs/toolkit/00-constitution.md) P-7).
  The `.py` tools use it as their shebang; shell scripts call it through `tk_python`.
  Set `AUTOPKG_TOOLKIT_PYTHON` to use a different interpreter. The tools only make
  sense where AutoPkg is installed, so this adds no dependency.
- **Prerequisites:** see [Getting ready](#getting-ready).
- **Tests:** [ShellSpec](https://github.com/shellspec/shellspec) ≥ 0.28.1 and shellcheck.

## Agents

Rules live in `.devagent/rules/` as numbered files — the single source of truth.
ZooCode/Roo loads them automatically through the `.roo/rules` symlink; Cline reads the
short `.clinerules` pointer. Skills in `.devagent/skills/` are listed, with when to use
each, in `.devagent/rules/03-pre-action-reads.md`. Details:
[`docs/agent-integration.md`](docs/agent-integration.md).

## Distribution

`bin/make-dist.sh` builds a function-only copy — no tests, specs or customer data —
with provenance stamped, a manifest generated, and a smoke test run before the build
is declared good ([`docs/minimal-kit.md`](docs/minimal-kit.md)).

## Status and known issues

Known, verified issues are tracked in [`docs/known-issues.md`](docs/known-issues.md).
Contributions: [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT — see [`LICENSE`](LICENSE). Third-party material is listed in [`NOTICE`](NOTICE).
