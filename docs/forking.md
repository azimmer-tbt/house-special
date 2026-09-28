# Forking the kit

This repository is a clean, public **upstream**. An org uses it by keeping a
**fork**:

- the fork carries the org's naming and its customer workspace;
- it pulls in upstream improvements;
- now and then, it sends generic fixes back.

This page covers that loop. It assumes you've done the
[getting-started](getting-started.md) tour.

## 1. Fork and clone

Fork on your git host (or push a clone to an internal remote), then clone the
fork and point `upstream` at this repository:

```bash
git clone <your-fork-url> house-special
cd house-special
git remote add upstream <upstream-url>
git fetch upstream
```

## 2. Make it your org's: `config/org.yaml`

Everything org-specific in the kit comes from one file,
[`config/org.yaml`](../config/org.yaml). It uses flat `key: value` lines only,
because the shell tools parse it in bash as well as the Python ones.

| Key | Acme default | What it drives |
|---|---|---|
| `org_name` | `Acme Fruit Co.` | Generated recipe `Description`s, lint messages |
| `identifier_prefix` | `com.acmefruit.autopkg` | Recipe identifiers `<prefix>.download.<App>` / `<prefix>.pkg.<App>` (lint rules IDN-001, IDN-002) |
| `pkgname_prefix` | `Acme_` | The prefix on every package the org builds (lint rule PKG-002) |
| `internal_domain` | `acmefruit.example` | Examples and in-house package identifiers |
| `vendor_dir` | `AcmeFruitCo` | The vendor folder for in-house packages |

These tools read it:

- **`bin/recipe-linter.sh`**: `config/checks.yaml` is written with tokens
  (`{{IDENTIFIER_PREFIX}}`, `{{PKGNAME_PREFIX}}`, `{{ORG_NAME}}` …), which the
  linter fills in from `org.yaml` at load time. Never write a literal prefix
  into `checks.yaml`; that keeps it identical to upstream and merges clean.
- **`bin/blueprint-to-recipe.sh`**: generated identifiers, `ParentRecipe`, and
  `pkgname`.
- **`bin/rr-batch.sh`**: sets each generated recipe's Identifier, ParentRecipe
  and NAME from your prefix and the CSV's app name (whatever Recipe Robot wrote),
  and passes `--org` on to the linter. Configure Recipe Robot with the same
  prefix and YAML output; the batcher warns when it isn't.
- **`bin/classify-recipe.sh`**: which output prefix to expect.

Each run looks for the file in this order:

1. `--org <file>` (`--org=<file>` for `classify-recipe.sh`);
2. then `$AUTOPKG_TOOLKIT_ORG`;
3. then `config/org.yaml`, with the selected customer's `org.yaml` laid over it
   (linter, preflight and `analyze-package.sh --customer` only; see
   [Serving several orgs](#serving-several-orgs)).

Existing recipes are data. Changing `org.yaml` doesn't rewrite them. After you
change the prefixes, the Acme example recipes will fail IDN-001, IDN-002 and
PKG-002 under your naming. That is the linter doing its job, not a bug.

## 3. Add your customer workspace

Create `customer/<you>/` (lowercase) as described in
[customer-contract.md](customer-contract.md#starting-a-new-customer).

- In the **fork**, commit it: recipes, plans, the catalogue, `clues.yaml`. The kit's `.gitignore` already keeps binaries, `input/`,
  `sessions/`, `troubleshooting/`, `build/` and `vendor_cache/` out.
- **Upstream must never receive it.** Your customer folder names your org, your
  in-house apps and your vendors.

Register it in `config/customers.yaml` and make it the `default`, so the linter,
preflight and `run-recipes.sh` use it when you give no `--repo`. Start the file from
[`config/customers.example.yaml`](../config/customers.example.yaml). Git ignores
`config/customers.yaml`, because it names your customers: upstream never ships one,
so merging upstream or dropping in a new snapshot of the kit never touches yours. To
keep it in a private fork's history, add it with `git add -f config/customers.yaml`.

You can keep `customer/acme/` as a reference, or delete it in the fork. If you
delete it, expect a merge conflict whenever upstream changes it; resolve by
keeping it deleted (`git rm`). Remove its line from your `config/customers.yaml` too.

### Serving several orgs

A consultant or a shared team may package for more than one org, say Acme Fruit Co.
and Widgets Inc. Don't edit `config/org.yaml` each time you switch. Register each
org as a customer instead
([FORMATS §10](FORMATS.md#10-configcustomersyaml-the-customer-registry)):

```yaml
default: acme
customers:
  acme: customer/acme
  widgets: ~/src/widgets-kit       # outside the kit: Widgets' own private repo
```

- Give each customer an `org.yaml` with the keys that differ from
  `config/org.yaml`. They are laid over it key by key.
- Pick one per run with `--customer <name>` or `$AUTOPKG_TOOLKIT_CUSTOMER`, or check
  them all with `bin/recipe-linter.sh --all-customers` and
  `bin/check-sanitized.sh --all-customers`.
- Keep a client's folder **outside the kit**, in the client's own repo. Its paths in
  `paths.yaml` are relative to that folder, so it works anywhere, and client data
  never enters the kit's history. Only the registry line names it.

`bin/run-recipes.sh --customer <name>` runs that customer's recipes. The analysis
tools (`analyze-package.sh`, `analyze-materials.sh`) find a `--customer` folder
through the registry too, wherever it lives.

Give each customer a `.leak-patterns` of its own. `bin/check-sanitized.sh` applies
it everywhere except that customer's folder, so one client's names can't turn up
in the kit or in another client's folder.

## 4. Stay in sync with upstream

```bash
git fetch upstream
git merge upstream/main          # on your fork's main
bin/recipe-linter.sh --customer <you> --pair-check
```

Merges stay clean when each side owns separate files:

| Yours (the fork edits these) | Upstream's (don't edit in the fork) |
|---|---|
| `config/org.yaml`, `config/customers.yaml` (gitignored upstream; `git add -f` to keep it) | everything else: `bin/`, `lib/`, `config/checks.yaml`, `templates/`, `specs/`, `reference/`, `docs/`, `tests/` |
| `customer/<you>/` | `customer/acme/` |
| `.leak-patterns` (gitignored, never committed) | |

`config/paths.yaml` is informational and holds placeholders. If you record
machine paths in it, expect to resolve a small conflict now and then.

If you need to change an upstream file, make the change generic and send it
upstream (below) rather than carrying a local patch.

### Pipeline files next to your recipes

Upstream requires only the recipe pair and a `README.md` in each recipe folder.
Anything your deployment pipeline needs is yours to define:

- **`.overrides`** (optional): `key=value` lines that `bin/run-recipes.sh` or your
  CI job passes to `autopkg run` as `--key=KEY=VALUE`. Use it for values the
  pipeline supplies at run time, such as a license key. If it holds a secret or a
  deployment detail (for example, which Jamf server to push to), generate it in
  the pipeline or gitignore it, never commit it, and add those values to
  `.leak-patterns`. A version or anything AutoPkg must see goes in the recipe's
  `Input`, because a bare `autopkg run` never reads `.overrides`.
- **Deployment-pipeline metadata** (environments, regions, resource names): keep
  your own sidecar files for it in `customer/<you>/`. To lint them, the linter
  engine supports `related_type: "overrides"` and `related_type: "autopkg_config"`
  checks (reading `.overrides` and `.autopkg_config` next to the recipe). Keep your
  rules in a fork-owned copy of `config/checks.yaml` and run it with
  `bin/recipe-linter.sh --config <file>`, so upstream's file still merges clean.

See [Standards §3.4–3.5](../reference/recipe-standards.md#34-the-overrides-file).

## 5. Contributing back upstream

Anything generic is welcome upstream: a linter fix, a template correction, a
new lesson in the methodology. A contribution must carry **nothing** from your
org.

1. Branch from `upstream/main`, not from your fork's `main`, so none of your
   org's history comes along:

   ```bash
   git fetch upstream
   git switch -c fix/linter-dir-rule upstream/main
   ```

2. Make the change using Acme names in any example. **Never touch
   `customer/`** except `customer/acme/`.
3. Stage it, then scan what's staged:

   ```bash
   git add -p
   bin/check-sanitized.sh --staged
   ```

4. Push the branch and open the pull request against upstream.

### The denylist: `.leak-patterns`

`bin/check-sanitized.sh` has built-in checks that always run:

- home-directory paths other than placeholders like `/Users/you`;
- ticket numbers;
- serial numbers;
- tenant sync-folder paths;
- files over 1 MB;
- installer binaries.

On top of these, it reads your fork's own denylist from `.leak-patterns` at the
repo root, and each registered customer's `.leak-patterns`
([Serving several orgs](#serving-several-orgs)). A customer's patterns apply
everywhere except in its own folder; their hits are labelled `customer:<name>:N`.
Every `.leak-patterns` file is skipped by the scan.

- **Format:** one extended regex (ERE, as for `grep -E`) per line. Blank lines
  and `#` comments are ignored.
- **Exemptions:** a line starting with `!` is a regex for lines that are allowed
  even though they match the denylist, e.g. a maintainer's own
  `!^# Author: Pat Example <pat@example\.com>$` in script headers. Keep them narrow:
  a whole line, anchored at both ends.
- **Gitignored on purpose:** a committed denylist would itself leak every name
  it lists. Each fork keeps its own, and each person keeps a copy locally.

What to list:

```text
# org names and codes, in every spelling
Your Org Name
yourorg
YOURORG_
# the reverse-DNS prefix and internal domains
com\.yourorg\.
yourorg\.internal
corp\.yourorg\.com
# internal hostnames
jss[0-9]*\.yourorg
# employee / user-ID formats
\b[A-Z][0-9]{6}\b
# in-house app and team names
YourOrgSupportTool
```

Test a new pattern before you rely on it. Look for false positives across the
upstream tree, then check that it catches your own workspace:

```bash
bin/check-sanitized.sh                          # whole tree: should stay clean
bin/check-sanitized.sh --path customer/<you>    # should light up
bin/check-sanitized.sh --customer <you>         # a customer folder, inside the kit or not
```

### The pre-commit hook

```bash
bin/check-sanitized.sh --install-hook
```

This writes `.git/hooks/pre-commit`, which runs `check-sanitized.sh --staged`
on every commit. If a hook already exists, the script prints the one line to
add to it.

In a **work fork**, commits to `customer/<you>/` legitimately contain names from
your denylist, so the hook would block them. Choose one of two setups:

- Install the hook only in a **separate clone used for upstream
  contributions**.
- In the fork, run `bin/check-sanitized.sh --staged` by hand on contribution
  branches.

In either setup, the hook only guards what you commit. Look at the diff before
you push.
