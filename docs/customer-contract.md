# The customer contract

The kit is split in two:

- **The kit**: `bin/`, `lib/`, `config/`, `templates/`, `specs/`, `reference/`,
  `docs/`. It is generic and shared by every org that forks it.
- **A customer workspace**: `customer/<name>/`. It holds one customer's data:
  what to package, hints for the analysis tools, plans, and the recipe repo
  itself.

The tools never hard-code customer data. They find it in one of two ways:

- the customer registry, `config/customers.yaml` (yours, gitignored; start it from
  [`config/customers.example.yaml`](../config/customers.example.yaml)), via
  `--customer <name>` (or, for the linter, preflight and `bin/run-recipes.sh`, the
  registry's `default`);
- `--repo <path>`, for everything that works on recipes.

A customer is an org with its own naming. One kit can serve several; see
[Several customers in one kit](#several-customers-in-one-kit).

[`customer/acme/`](../customer/acme/README.md) is the worked example. Copy its
shape, not its data.

## What lives in `customer/<name>/`

"Tracked" means committed in a work fork. Upstream only ever carries
`customer/acme/`; see [forking.md](forking.md).

| Path | Required? | Read by | Schema | In git? |
|---|---|---|---|---|
| `README.md` | recommended | people | — | tracked |
| `end_result.yaml` | for `analyze-materials` matching | `bin/analyze-materials.sh --customer` (the `recipes[].app_name`, `vendor` and `pattern` fields) | [FORMATS §3](FORMATS.md#3-customernameend_resultyaml) | tracked |
| `clues.yaml` | optional (the tools fall back to their built-in heuristics) | `bin/analyze-package.sh --customer`; `bin/analyze-materials.sh --customer` (classifies each `.pkg` it finds) | [FORMATS §2](FORMATS.md#2-customernamecluesyaml) | tracked |
| `autopkg-recipes.csv` | optional | people only | [FORMATS §1](FORMATS.md#1-customernameautopkg-recipescsv) | tracked |
| `paths.yaml` | optional | `recipe_repo.root` (default `output`) is read by the linter, preflight and `bin/run-recipes.sh --customer`; the other keys by people and agents | [FORMATS §5](FORMATS.md#5-customernamepathsyaml) | tracked |
| `org.yaml` | optional | the linter, preflight and `bin/analyze-package.sh --customer`, layered key by key over `config/org.yaml` | [FORMATS §11](FORMATS.md#11-per-customer-files-orgyaml-checkslocalyaml-leak-patterns) | tracked |
| `checks.local.yaml` | optional | the linter: extra rules, and skips of optional kit rules | [FORMATS §11](FORMATS.md#11-per-customer-files-orgyaml-checkslocalyaml-leak-patterns) | tracked |
| `.leak-patterns` | optional | `bin/check-sanitized.sh`: applied everywhere except this customer's own folder | [FORMATS §11](FORMATS.md#11-per-customer-files-orgyaml-checkslocalyaml-leak-patterns) | tracked in a private repo only |
| `plans/<App>.md` | one per Lane B package | people and agents | [FORMATS §6](FORMATS.md#6-customernameplansappnamemd-plan-of-attack) | tracked |
| `input/` | optional | `bin/analyze-materials.sh <dir>` (you pass the path) | — | gitignored except `README.md`, `.gitkeep` |
| `sessions/` | optional | people and agents | `.devagent/rules/07-sessions.md` | gitignored except `README.md`, `.gitkeep` |
| `troubleshooting/` | optional | people | — | gitignored except `README.md`, `.gitkeep` |
| `output/` | **required**: the recipe repo (another folder if `paths.yaml` says so) | every `--repo` front end; the linter, preflight and `bin/run-recipes.sh` for a customer | [FORMATS §4](FORMATS.md#4-customer-workspace-layout) | tracked |
| `output/recipes/<Vendor>/<App>/` | one per app | `bin/recipe-linter.sh`, `bin/classify-recipe.sh`, `bin/scan-placeholders.sh`, `autopkg` | [`reference/recipe-standards.md`](../reference/recipe-standards.md) | tracked (`autopkg-run-*.log` ignored) |
| `output/vendor-drop-registry.yaml` | if you have vendor drops | `bin/normalize-vendor-cache.sh --repo` | [FORMATS §8](FORMATS.md#8-recipe-repovendor-drop-registryyaml) | tracked |
| `output/files_to_copy.yaml` | if you have vendor drops | `bin/sync-vendor-cache.sh` (you pass the path) | [FORMATS §9](FORMATS.md#9-recipe-repofiles_to_copyyaml) | tracked |
| `output/build/` | created by builds | local build output | — | gitignored |
| `output/vendor_cache/` | local only | vendor-drop recipes, via `VENDOR_CACHE_ROOT`; `bin/normalize-vendor-cache.sh` moves stale files aside to its `relocated/` | — | gitignored |

The `.gitignore` rules behind the last column:

- `customer/*/input/*`, `customer/*/sessions/*`, `customer/*/troubleshooting/*`,
  each with its `README.md` and `.gitkeep` re-included;
- `customer/**/build/`, `customer/**/vendor_cache/`,
  `customer/**/reverse_engineer/`, `customer/**/prod_content/`;
- all `*.pkg`, `*.mpkg`, `*.dmg`, `*.pkg.zip` and `*.tar.gz` files, anywhere.

## How `--customer <name>` resolves

Every tool that takes `--customer` looks the name up in `config/customers.yaml`
([FORMATS §10](FORMATS.md#10-configcustomersyaml-the-customer-registry)), so the
folder can be anywhere, inside the kit or not. The name is matched
**case-sensitively**; use lowercase names. An unknown name exits 2 and lists the
registered ones. With no registry at all, a name still means `customer/<name>/` in
the kit, if that folder exists.

### The linter, preflight and `run-recipes.sh`

`bin/recipe-linter.sh`, `bin/autopkg-preflight.py` and `bin/run-recipes.sh` pick a
customer in this order: `--customer`, then `$AUTOPKG_TOOLKIT_CUSTOMER`, then the
registry's `default`. They work on that customer's recipe repo.

The default applies only when you gave no target (`--repo`,
`$AUTOPKG_TOOLKIT_REPO`, `--dir`, recipe files, or a current directory that is a
recipe repo). With the shipped registry (`default: acme`), `bin/recipe-linter.sh`
with no arguments, run from anywhere but a recipe repo, lints Acme.
`--repo` and `$AUTOPKG_TOOLKIT_REPO` beat a named customer's repo.

```bash
bin/recipe-linter.sh --customer acme --pair-check
bin/recipe-linter.sh --all-customers          # each customer in turn, worst exit wins
bin/autopkg-preflight.py --customer acme
bin/run-recipes.sh --customer acme Orchard    # real runs of Acme's recipes
PYTHONPATH=lib/python /usr/local/autopkg/python -m recipekit.customers show acme   # what the tools will use
```

### The analysis tools

`bin/analyze-package.sh` and `bin/analyze-materials.sh` take `--customer <name>`
only (not the environment or the default), and read from that customer's folder:

```text
<customer folder>/clues.yaml        # analyze-package, analyze-materials
<customer folder>/end_result.yaml   # analyze-materials
```

- `analyze-package.sh` also uses the customer's org naming (its `org.yaml` laid
  over `config/org.yaml`) for the in-house check.
- An explicit `--clues <file>` or `--targets <file>` overrides the customer
  path.
- If `clues.yaml` is missing, `analyze-package.sh` warns and continues with its
  default heuristics; if it is invalid (bad YAML or regex), it exits 2. If `end_result.yaml` is missing, `analyze-materials.sh`
  skips matching.

## `output/` is a recipe repo

`customer/<name>/output/` is laid out exactly like a stand-alone recipe repo:
it contains `recipes/`, and the vendor-drop files sit at its root. So:

```bash
bin/recipe-linter.sh --repo customer/acme/output --pair-check
bin/scan-placeholders.sh --repo customer/acme/output Orchard
bin/normalize-vendor-cache.sh --repo customer/acme/output --vendor-cache /tmp/autopkg/vendor_cache
```

Repo resolution follows the frontend contract in the [README](../README.md):

1. `--repo`;
2. then `$AUTOPKG_TOOLKIT_REPO`;
3. then, for the linter, preflight and `bin/run-recipes.sh`, the selected customer's recipe repo
   (`recipe_repo.root` in its `paths.yaml`, default `output`);
4. then the current directory, but only if it contains `recipes/`.

Step 4 is reached only when no customer is selected: no `--customer`, no
`$AUTOPKG_TOOLKIT_CUSTOMER`, and no `default` in the registry.

If your real recipe repo lives elsewhere (a separate git repo, say), point
`--repo` at it. The `output/` folder is simply the default place for one.

Each recipe folder holds the recipe pair and a `README.md`. An `.overrides` file
is optional and org-defined: `bin/run-recipes.sh` passes its lines to
`autopkg run` as `--key` values. One that holds a secret or a deployment detail is
generated by your pipeline or gitignored, never committed. Deployment-pipeline
metadata is org-specific too; your fork may keep its own sidecar files for it and
lint them with its own rules ([forking.md](forking.md#pipeline-files-next-to-your-recipes)).

## Org naming: the kit's, with per-customer changes

`config/org.yaml` holds the naming conventions:

- `org_name`;
- `identifier_prefix`;
- `pkgname_prefix`;
- `internal_domain`;
- `vendor_dir`;
- `fleet_min_macos`.

A customer whose naming differs adds its own `org.yaml` with just the keys that
change. The linter, preflight and `bin/analyze-package.sh` lay it over
`config/org.yaml` key by key when they run for that customer. The other tools read
`config/org.yaml` only.

To lint with different naming for a single run, pass `--org <file>`
(`--org=<file>` for `bin/classify-recipe.sh`) or set `$AUTOPKG_TOOLKIT_ORG`. Either
one beats the customer's `org.yaml`. See [forking.md](forking.md).

## Several customers in one kit

Register each customer in `config/customers.yaml`. Git ignores that file, so each
checkout keeps its own; start it with
`cp config/customers.example.yaml config/customers.yaml`:

```yaml
default: acme
customers:
  acme: customer/acme
  widgets: ~/src/widgets-kit       # Widgets Inc., kept in its own private repo
```

A customer folder may live **outside the kit**, for example in a client's own
private repo. Its `paths.yaml` paths are relative to that folder, so it works the
same anywhere, and the client's data never enters the kit's history.

Each customer can change the kit's lint rules in a `checks.local.yaml`: add rules,
and skip the ones `config/checks.yaml` marks `required: false`
([FORMATS §11](FORMATS.md#11-per-customer-files-orgyaml-checkslocalyaml-leak-patterns)).

Some customer data does repeat the org's name, and that is expected:

- `clues.yaml` `org_codes`: how the org's own packages are recognised.
- vendor folders named after `vendor_dir`: where the org's in-house packages
  live.

## Starting a new customer

1. Copy the skeleton, not Acme's data:

   ```bash
   new=widgets    # lowercase
   mkdir -p customer/$new/{input,sessions,troubleshooting,plans,output/recipes}
   for d in input sessions troubleshooting; do
     cp customer/acme/$d/README.md customer/$new/$d/
     touch customer/$new/$d/.gitkeep
   done
   ```

   Then edit the three copied READMEs: they name `acme` in their example
   commands.

2. Create empty data files, with the headers from [FORMATS.md](FORMATS.md):

   ```bash
   head -1 customer/acme/autopkg-recipes.csv > customer/$new/autopkg-recipes.csv
   printf 'recipes: []\n'              > customer/$new/end_result.yaml
   printf 'vendor_identifiers: []\n'   > customer/$new/clues.yaml
   printf 'canonical_filenames: {}\n'  > customer/$new/output/vendor-drop-registry.yaml
   printf 'files: []\n'                > customer/$new/output/files_to_copy.yaml
   ```

   Add a `paths.yaml` and a top-level `README.md` if they help your team.
   In `paths.yaml`, write paths relative to the customer folder (`output`, not
   `customer/<name>/output`).

3. Register it in `config/customers.yaml` (if you don't have one yet:
   `cp config/customers.example.yaml config/customers.yaml`):

   ```yaml
   customers:
     acme: customer/acme
     widgets: customer/widgets
   ```

   The folder may also live outside the kit (an absolute path or `~/...`). Every
   `--customer` tool finds it through this line.

4. Naming. If this customer's naming matches `config/org.yaml`, do nothing. If it
   differs, add `customer/$new/org.yaml` with just the keys that change (see
   [forking.md](forking.md) for the keys). Add `checks.local.yaml` only if the
   customer needs extra lint rules or skips optional ones.

5. Check what the tools will use, add the first recipe from a template
   (`templates/pattern-*/`), then lint:

   ```bash
   PYTHONPATH=lib/python /usr/local/autopkg/python -m recipekit.customers show $new
   bin/recipe-linter.sh --customer $new --pair-check
   ```

## What must never be committed

- **Vendor binaries**: installers, DMGs, archives. `.gitignore` excludes them,
  and they belong in a durable store listed in `output/files_to_copy.yaml`.
- **Session logs** (`sessions/`): they routinely contain hostnames, user names
  and ticket numbers.
- **Troubleshooting evidence** (`troubleshooting/`): install logs,
  `autopkg -vvv` output, screenshots.
- **An `.overrides` holding a secret or deployment detail**: license keys, which
  MDM server to push to. The pipeline generates it at run time, or it is
  gitignored.

`bin/check-sanitized.sh` guards against leaks. Out of the box it looks for:

- home-directory paths;
- ticket numbers;
- serial numbers;
- tenant sync-folder paths;
- oversized files;
- installer binaries.

It also matches your fork's own denylist in `.leak-patterns` at the kit root, and
every registered customer's `.leak-patterns` everywhere except in that customer's
own folder: a customer's names may appear only there. Those hits are labelled
`customer:<name>:N`. Run it before you share anything:

```bash
bin/check-sanitized.sh                          # the kit, with every customer's denylist
bin/check-sanitized.sh --customer <name>        # that customer's folder, wherever it lives
bin/check-sanitized.sh --all-customers          # each customer folder in turn, worst exit wins
bin/check-sanitized.sh --staged                 # just what you're about to commit
```

`--customer` scans the customer's folder with the kit's `.leak-patterns` plus every
*other* customer's.

[forking.md](forking.md#5-contributing-back-upstream) covers the denylist and the
pre-commit hook.
