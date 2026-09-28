---
name: new-customer
description: Scaffold a new customer workspace customer/<name>/ with the Acme shape but none of Acme's data, register it in config/customers.yaml, set its org naming, and get a first clean lint. Use when someone says "set up a new customer", "start a workspace for <org>", "make the kit ours", "new customer folder", or is starting work in a fresh fork.
---
# New Customer Workspace

## When to use

First time an org (or a second customer in a fork) uses the kit. The workspace
holds that customer's catalogue, hints, plans and recipe repo; the kit stays generic.

## Inputs

- A lowercase name (`--customer` matching is case-sensitive), e.g. `widgets`.
- Where the folder lives: `customer/<name>/` in the kit, or outside it (a client's
  own private repo) so client data never enters the kit's history.
- The org's `org_name`, `identifier_prefix`, `pkgname_prefix`, `internal_domain`,
  `vendor_dir`, `fleet_min_macos`, if they differ from
  [`config/org.yaml`](../../config/org.yaml).
- **Upstream never receives a real customer folder** — only `customer/acme/`.

## Steps

1. Directories and drop-point READMEs (copy the shape, not the data):
   ```bash
   new=widgets
   mkdir -p customer/$new/{input,sessions,troubleshooting,plans,output/recipes}
   for d in input sessions troubleshooting; do
     cp customer/acme/$d/README.md customer/$new/$d/
     touch customer/$new/$d/.gitkeep
   done
   touch customer/$new/plans/.gitkeep customer/$new/output/recipes/.gitkeep
   sed -i '' "s#customer/acme#customer/$new#g; s#--customer acme#--customer $new#g" \
     customer/$new/{input,sessions,troubleshooting}/README.md
   ```
2. Empty-but-valid data files ([FORMATS](../../docs/FORMATS.md) §1–3, §8–9):
   ```bash
   head -1 customer/acme/autopkg-recipes.csv > customer/$new/autopkg-recipes.csv
   printf 'recipes: []\n'            > customer/$new/end_result.yaml
   printf 'vendor_identifiers: []\nvendor_filename_patterns: []\ncustom_build_signals:\n  filename_contains_org_code: true\n  org_codes: []\n  unusual_install_locations: []\n' \
                                     > customer/$new/clues.yaml
   printf 'ignored_subdirs:\n  - "scripts"\n  - "payload"\nprotected_files:\n  - "scripts.zip"\n  - "payload.zip"\ncanonical_filenames: {}\n' \
                                     > customer/$new/output/vendor-drop-registry.yaml
   printf 'files: []\n'              > customer/$new/output/files_to_copy.yaml
   ```
   The CSV header is `active,vendor,app name,pattern,source,package filename,built in-house,recipe created,build tested,committed,notes`.
3. `customer/$new/paths.yaml` (optional, [FORMATS §5](../../docs/FORMATS.md#5-customernamepathsyaml)):
   copy `customer/acme/paths.yaml` and change `customer_name`. Paths are relative to
   the customer folder (`output`, not `customer/$new/output`). `recipe_repo.root` is
   read by the linter, preflight and `run-recipes.sh --customer` (default `output`);
   the rest is informational.
   Keep machine paths generic (`/tmp/autopkg/vendor_cache`, `/Users/you/...`).
4. `customer/$new/README.md` and `output/README.md`: what this customer is, where to
   start. Write them fresh; don't copy Acme's catalogue text.
5. Register it in `config/customers.yaml`, which is gitignored (if it doesn't exist:
   `cp config/customers.example.yaml config/customers.yaml`)
   ([FORMATS §10](../../docs/FORMATS.md#10-configcustomersyaml-the-customer-registry)):
   add `$new: customer/$new` (or an absolute / `~` path for a folder outside the kit)
   under `customers:`. Set `default: $new` if it's the one people work on.
6. Naming ([FORMATS §11](../../docs/FORMATS.md#11-per-customer-files-orgyaml-checkslocalyaml-leak-patterns)):
   - Same naming as `config/org.yaml`: nothing to do.
   - Different naming: `customer/$new/org.yaml` with only the keys that change
     (flat `key: value` lines). It's laid over `config/org.yaml` key by key.
   - A single-org fork may instead edit `config/org.yaml` itself. The Acme examples
     will then fail IDN-001/IDN-002/PKG-002 under your naming — expected.
   - Only if needed: `customer/$new/checks.local.yaml` to add rules or `skip:`
     rules the kit marks `required: false`.
   Add the org's names to the local, gitignored `.leak-patterns`, or to
   `<folder>/.leak-patterns` for a folder kept in the client's private repo:
   `check-sanitized.sh` applies a customer's file everywhere except that customer's
   folder ([sanitize-check.md](sanitize-check.md)).
7. Check, then lint (an empty repo reports "No .recipe.yaml files found" and exits 0):
   ```bash
   PYTHONPATH=lib/python /usr/local/autopkg/python -m recipekit.customers show $new
   bin/recipe-linter.sh --customer $new --pair-check
   bin/analyze-materials.sh customer/$new/input --customer $new
   ```
   `show` prints the folder, recipe repo, merged org values and which optional files
   it found. The linter header prints `customer: $new (<folder>)`.
8. Add the first recipe from `templates/pattern-*/` following
   [autopkg-recipe-development.md](autopkg-recipe-development.md) and lint again.

## Outputs

```
customer/<name>/  README.md  autopkg-recipes.csv  clues.yaml  end_result.yaml  paths.yaml
                  [org.yaml  checks.local.yaml  .leak-patterns]   (optional)
                  plans/  input/  sessions/  troubleshooting/   (README + .gitkeep)
                  output/  README.md  recipes/  vendor-drop-registry.yaml  files_to_copy.yaml
config/customers.yaml    one new line under customers: (local, gitignored)
```

## Verify

- `recipekit.customers show <name>` exits 0 and shows the expected prefixes.
- `recipe-linter.sh --customer <name>` exits 0; `analyze-materials.sh --customer <name>`
  finds `end_result.yaml`.
- `/usr/local/autopkg/python -c 'import yaml,sys;[yaml.safe_load(open(f)) for f in sys.argv[1:]]' customer/$new/*.yaml customer/$new/output/*.yaml` succeeds.
- `git status --short customer/$new` shows only READMEs, `.gitkeep`s and data files —
  nothing under `input/`, `sessions/`, `troubleshooting/` besides those.
- `bin/check-sanitized.sh --customer $new` behaves as expected (in a fork it
  *should* light up on the kit's denylisted names; upstream it must be clean), and
  plain `bin/check-sanitized.sh` stays clean: the customer's own names only in its
  folder.

## Pitfalls

- Copying `customer/acme/` wholesale drags in Acme's catalogue, plans and recipes.
- Capitalised folder names break `--customer` on case-sensitive volumes.
- A customer `org.yaml` changes naming for the linter, preflight and
  `analyze-package.sh` / `analyze-materials.sh --customer` only; the generator and
  the classifier still read `config/org.yaml`.
  `--org <file>` or `$AUTOPKG_TOOLKIT_ORG` beats the customer's file.
- Registered but not `default`: plain `bin/recipe-linter.sh` still lints the default
  customer. Pass `--customer <name>`.
- `paths.yaml` paths written as `customer/<name>/...` break: they're relative to the
  customer folder now.
- `skip:` of a required rule exits 2. Only the rules marked `required: false` in
  `config/checks.yaml` can be skipped.
- Vendor binaries, sessions and troubleshooting evidence are never committed; the
  vendor cache (`output/vendor_cache`, `/tmp/autopkg/vendor_cache`) is not a backup
  (methodology lesson 24) — list durable sources in `files_to_copy.yaml`.

## References

- [`docs/customer-contract.md`](../../docs/customer-contract.md) — what lives where, what's tracked
- [`docs/FORMATS.md`](../../docs/FORMATS.md) — every schema
- [`docs/forking.md`](../../docs/forking.md) — org.yaml, several orgs, syncing, contributing back
- [`specs/toolkit/02-customers.md`](../../specs/toolkit/02-customers.md) — the customer registry spec
- [`customer/acme/README.md`](../../customer/acme/README.md) — the worked example
