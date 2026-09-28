---
name: recipe-linting
description: Run, interpret and extend the config-driven recipe linter (bin/recipe-linter.sh + config/checks.yaml). Use when someone says "lint the recipes", "why does IDN-001 fail", "add a lint rule", "change a rule's severity", "the linter is wrong about this recipe", or before touching the linter code.
---
# Recipe Linting

## When to use

- Linting a recipe, an app directory or a whole recipe repo.
- Explaining a failing rule, or deciding a rule is a false positive.
- Adding or changing a rule, or changing the linter engine.

## Inputs

- Targets: recipe files, `--dir <app-or-vendor-dir>`, `--repo <recipe-repo>`
  (a folder with `recipes/`, e.g. `customer/acme/output`), or a customer:
  `--customer <name>` / `$AUTOPKG_TOOLKIT_CUSTOMER`, registered in
  `config/customers.yaml` (gitignored; started from
  [`config/customers.example.yaml`](../../config/customers.example.yaml)). With no
  target at all the registry's `default` is used — with the example registry, plain
  `bin/recipe-linter.sh` lints Acme, unless you're standing in a recipe repo, which
  then counts as the target.
- Rules: [`config/checks.yaml`](../../config/checks.yaml), plus the customer's
  `checks.local.yaml` if it has one. `--config <path>` replaces the rule file and
  drops the local rules.
- Org naming: [`config/org.yaml`](../../config/org.yaml) with the customer's
  `org.yaml` laid over it key by key; `--org <file>` or `$AUTOPKG_TOOLKIT_ORG` beat both.

## Steps

1. Lint:
   ```bash
   bin/recipe-linter.sh --repo customer/<name>/output --pair-check   # whole repo + pairs
   bin/recipe-linter.sh --dir <repo>/recipes/<Vendor>/<App> --pair-check
   bin/recipe-linter.sh <App>.download.recipe.yaml <App>.pkg.recipe.yaml
   bin/recipe-linter.sh --org /path/to/other-org.yaml --repo <repo>  # other naming, one run
   bin/recipe-linter.sh --customer <name> --pair-check               # a customer: its repo, org, rules
   bin/recipe-linter.sh --all-customers                              # each registered customer in turn
   bin/recipe-linter.sh --list-rules                                 # rendered rules by severity
   bin/recipe-linter.sh --customer <name> --list-rules               # kit rules - skipped + local
   ```
   `--pair-check` requires every download recipe to have its pkg recipe and vice versa.
   `--all-customers` can't be combined with `--customer`, `--dir`, `--repo` or files;
   it prints `=== Customer: <name>` before each run and exits with the worst code.
   An unknown customer, or several with no default and none selected, exits 2 and
   lists the registered names.
2. Read results: `[FAIL]` (error severity) fails the run (non-zero exit); `[WARN]` and `[INFO]`
   never do. Each line carries a rule ID; look it up in `checks.yaml` (`prompted_by:`
   cites the Standards section).
3. Before calling a failure a false positive, check
   [`docs/known-issues.md`](../../docs/known-issues.md) (KI-2, KI-3, KI-13) and the
   escape hatches below.
4. **Change a rule** in `config/checks.yaml`, never in the script. Use tokens, never
   literal org values: `{{IDENTIFIER_PREFIX}}`, `{{IDENTIFIER_PREFIX_RE_YAML}}` (regex-escaped),
   `{{PKGNAME_PREFIX}}`, `{{ORG_NAME}}` — filled from `org.yaml` at load time.
   Comparison types: `regex`, `exact`, `list`, `exists`, `not_exists`, `absent`,
   and `exists_any` (pass if any condition matches; conditions can read `self` keys
   or a `related-file` via `related_key`: the `pkg_recipe`, or in a fork, its own
   `.overrides` / `.autopkg_config` sidecars), and `classification` (the `Comment:`
   pattern must match what the classifier concludes; CMT-004).
   **Required or optional.** A rule is required unless it has `required: false`.
   A customer's `checks.local.yaml` may `skip:` optional rules and add its own
   (`rules:`, same schema, ids that don't repeat a kit id); skipping a required or
   unknown rule exits 2. Mark a rule optional only when an org could reasonably
   disagree with it (style, layout), never for naming, signatures or safety.
   Optional today: SRC-002, SRC-003, NAM-002, NAM-003, DIR-001, MIN-001,
   CMT-001–CMT-004. Schema: [FORMATS §11](../../docs/FORMATS.md#11-per-customer-files-orgyaml-checkslocalyaml-leak-patterns).
5. **Add a test** for the rule in `tests/python/test_lint.py` with a passing and a
   failing fixture, and update
   [`specs/recipe-linter/01-rule-definitions.md`](../../specs/recipe-linter/01-rule-definitions.md)
   if you add a type or field.
6. Run the suite and the examples:
   ```bash
   shellspec                      # runs the Python tests too (tests/python_unittest_spec.sh)
   bin/recipe-linter.sh --repo customer/acme/output --pair-check
   ```

## Outputs

A header (rules file, org file, `customer: <name> (<folder>)` when linting as a
customer, rule count), a pair-check section, then per recipe
its findings and an `N errors, N warnings, N info` line; finally
`All N recipe(s) passed lint checks` or a failure summary. Exit 0 clean, 1 errors,
2 usage error.

## Verify

- `tests/examples_lint_spec.sh` passes: every template example and
  `customer/acme/output` must lint clean. A rule change that breaks an example
  fails there first — fix the rule or the example, never skip the test.
- `--list-rules` shows your new rule with the org values rendered.

## Pitfalls

- Signature/version escape hatches (all `exists_any`, KI-2): VER-001 accepts a pinned
  `Input.version` (never `.overrides`: AutoPkg doesn't read it); CSV-001 accepts
  `Input.NO_CODE_SIGNATURE_REQUIRED: true`; CSV-005 accepts `subject.OU`,
  `expected_authority_names`, `Input.teamid: UNSIGNED_NO_TEAMID`, or the same
  `NO_CODE_SIGNATURE_REQUIRED`. Upstream has no rules about `.overrides`.
- KI-3: `related-file` conditions read `related_key`, not `key`.
- `DIR-001` prints INFO on every recipe; ignore it, or `skip:` it in a customer's
  `checks.local.yaml`.
- **Python on AutoPkg's interpreter** (`lib/python/recipekit/lint.py`), standard
  library and PyYAML only; follow `.devagent/standards/python-code-standards.md`.
  Rule values are read from recipe text as the old bash engine read them; a rule that
  needs real structure should ask the recipe model instead.
  `tests/kit_hygiene_spec.sh` fails on org literals in script logic.

## References

- [`specs/recipe-linter/00-constitution.md`](../../specs/recipe-linter/00-constitution.md) and the
  numbered specs beside it; fixtures in `specs/recipe-linter/artifacts/`
- [`reference/recipe-standards.md`](../../reference/recipe-standards.md) §6.7
- [spec-creation.md](spec-creation.md) — before adding or hardening a linter spec
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md)
