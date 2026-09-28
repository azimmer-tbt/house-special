# Customers — several orgs from one kit

**Status:** Draft 0.4
**Date:** 2026-09-28
**Requires:** `specs/toolkit/00-constitution.md` (P-1 to P-6), `specs/toolkit/01-toolkit-common.md` (FR-08 org naming), `specs/recipe-linter/01-rule-definitions.md`
**Implementation:** `lib/python/recipekit/customers.py`; `resolve_customer` in `lib/toolkit-common.sh`; front ends `bin/recipe-linter.sh`, `bin/autopkg-preflight.py`, `bin/check-sanitized.sh`, `bin/run-recipes.sh`, `bin/analyze-package.sh`, `bin/analyze-materials.sh`

---

## Purpose

One kit checkout can serve several customers. A **customer is an organisation with its
own naming**: identifier prefix, package prefix, oldest supported macOS, lint
additions and leak denylist. Two customers may be nearly identical (Acme Fruit and
Acme Fruit Europe); they are still two customers.

A customer's folder may live **inside the kit** (`customer/acme/`, the worked
example) **or outside it**, for example in a client's own private repo, so client
material never enters the kit's history.

The design is **one registry plus per-customer files**, not a list inside every
config file: one place says where customers are, and each customer carries its own
flat files. Everything here is optional. A kit with no registry behaves exactly as
before.

The registry is **local to each checkout**. It names the customers someone serves,
so the kit never tracks it: upstream ships `config/customers.example.yaml`, and each
checkout copies it to `config/customers.yaml` and adds its own customers. Taking a
new snapshot of the kit, or merging upstream, therefore never touches a checkout's
registry or its customer folders.

### Normative vs. Informative

- **Normative:** the registry format, selection precedence, how customer files layer
  over the kit's, the required/optional rule contract, the errors.
- **Informative:** module names, the JSON field names of `recipekit.customers show`.

### Classification Key

- **[TESTABLE]** automatable, mechanism named. **[STRUCTURAL]** layout or inspection.

---

## FR-01 — The registry, `config/customers.yaml`

[TESTABLE]

```yaml
default: acme                      # optional
customers:
  acme: customer/acme              # relative to the kit root
  widgets: ~/src/widgets-kit       # absolute or ~, e.g. a client's private repo
```

- `customers` maps a name to the customer's folder. A relative path is relative to
  the kit root; `~` expands to the user's home.
- `default` names the customer used when nothing else selects one. It is optional.
- `$AUTOPKG_TOOLKIT_CUSTOMERS=<file>` replaces `config/customers.yaml` with another
  file. It does not add to it.
- `config/customers.yaml` is listed in `.gitignore`, and the kit's repository never
  contains it. The kit ships `config/customers.example.yaml`, which registers the
  worked example (`acme: customer/acme`, `default: acme`) and says how to start the
  real file from it. No tool reads the example. A private fork may commit its own
  registry with `git add -f`; since upstream never tracks the file, merges don't
  conflict on it.
- With no registry, a customer name still resolves to `customer/<name>/` in the
  kit, so `--customer acme` works in a fresh clone.

**Acceptance criteria:**
- AC-01.1: A name maps to its folder, relative, absolute or `~`.
- AC-01.2: A `default` that isn't in `customers`, or a folder that doesn't exist, is a
  config error naming it (exit 2 in front ends), never a silent fallback (P-5).
- AC-01.3: No registry file means no customers: every tool behaves as before.
- AC-01.4: With no registry, `--customer <name>` resolves `customer/<name>/` in the
  kit; a name with no such folder is an error (`tests/customers_shell_spec.sh`,
  `tests/python/test_customers.py`).
- AC-01.5: [STRUCTURAL] `config/customers.yaml` is gitignored and untracked;
  `config/customers.example.yaml` is tracked and loads as a valid registry
  (`tests/python/test_customers.py`).

## FR-02 — Selecting a customer

[TESTABLE]

Precedence, highest first:
1. `--customer <name>` on the command line;
2. `$AUTOPKG_TOOLKIT_CUSTOMER`;
3. the registry's `default`;
4. the only registered customer, when there is exactly one.

Steps 3 and 4 apply only when a tool **needs** a customer: no `--repo`, `--dir` or
recipe files, no `$AUTOPKG_TOOLKIT_REPO`, and the current directory isn't a recipe
repo. So `cd` into a recipe repo and run the linter still lints that repo. When a
customer is needed and none can be chosen, it is an error listing the registered
customers (P-4). `--all-customers` always uses each customer's own recipe repo.
A selected name that isn't registered is an error (P-5); it never falls back to the
default.

Explicit values still win over the customer's: `--org`, `--repo`, `--config`, and
the `$AUTOPKG_TOOLKIT_ORG` / `$AUTOPKG_TOOLKIT_REPO` variables replace what the
customer would have supplied.

**Acceptance criteria:**
- AC-02.1: Each source works on its own (P-6), and a higher one beats a lower one.
- AC-02.2: An unknown name is an error that lists the registered names.
- AC-02.3: No selection, no default and more than one customer is an error listing
  them; with exactly one registered customer and no default, that one is used.

## FR-03 — Customer files and layering

[TESTABLE]

All optional, all in the customer's folder:

| File | Layers over | Rule |
|---|---|---|
| `org.yaml` | `config/org.yaml` | Key by key: a key the customer sets wins; a key it leaves out comes from the kit's file. The merged result is validated as FR-08 of toolkit-common describes. |
| `paths.yaml` | built-in defaults | `recipe_repo.root` (default `output`) is load-bearing: it is the customer's recipe repo. Relative paths resolve against the **customer folder**. Other keys stay informational (`docs/FORMATS.md` §5). |
| `checks.local.yaml` | `config/checks.yaml` | Adds rules (same schema) and may `skip:` rules the kit marks optional (FR-04). |
| `.leak-patterns` | the kit's `.leak-patterns` | Applied everywhere **except** that customer's own folder: a customer's names may appear only there (`specs/check-sanitized/01-check-sanitized.md` FR-09). |
| `clues.yaml`, `end_result.yaml` | — | Read by `analyze-package.sh` / `analyze-materials.sh --customer` from the customer's folder, wherever it lives. |

**Acceptance criteria:**
- AC-03.1: A customer `org.yaml` that sets only `identifier_prefix` gets its
  `pkgname_prefix` and the rest from `config/org.yaml`.
- AC-03.2: Without `paths.yaml`, the recipe repo is `<customer>/output`.
- AC-03.3: A customer whose folder is outside the kit works exactly like one inside.

## FR-04 — Required and optional rules

[TESTABLE]

Every rule in `config/checks.yaml` has `required: true` (the default when absent) or
`required: false`. A customer's `checks.local.yaml`:

```yaml
skip: [DIR-001, NAM-003]       # only rules the kit marks required: false
rules:                          # added to the kit's rules, same schema
  - id: "WID-001"
    …
```

- **Adding** is always allowed. A local rule's `id` must not repeat a kit rule's.
- **Skipping** is allowed only for rules marked `required: false`. Skipping a
  required rule, or a rule that doesn't exist, is a config error (exit 2) naming it.
  "Required means required."

**Acceptance criteria:**
- AC-04.1: A local rule runs alongside the kit's.
- AC-04.2: Skipping an optional rule removes it for that customer only.
- AC-04.3: Skipping a required or unknown rule, or reusing a kit rule's `id`, exits 2.
- AC-04.4: `--list-rules` for a customer shows the kit's rules minus the skipped ones
  plus the local ones, with the customer's org values rendered.

## FR-05 — Front ends

[TESTABLE]

- `bin/recipe-linter.sh` and `bin/autopkg-preflight.py` accept `--customer <name>`
  and `--all-customers`.
- With a customer, the linter's org, repo and rules come from FR-03/FR-04 unless an
  explicit value replaces them (FR-02). Preflight uses the customer's repo, and its
  linter pass lints as that customer.
- `--all-customers` runs once per registered customer, in isolation, each with its own
  org and rules, printing a `=== Customer: <name>` header before each. The exit code
  is the worst of the runs.
- `bin/check-sanitized.sh` accepts `--customer <name>` and `--all-customers`
  (check-sanitized FR-09).
- `bin/run-recipes.sh --customer <name>` runs that customer's recipe repo; with no
  repo given it follows FR-02 (the default applies only when no target is given).
- `bin/analyze-package.sh` and `bin/analyze-materials.sh --customer <name>` read
  that customer's files from its folder, inside or outside the kit; analyze-package
  also uses its org naming.
- `tk_python -m recipekit.customers list|show [name]` prints the registry and one
  customer's resolved settings: JSON with `--output json`, shell-quoted assignments
  with `show --output env` (read by `resolve_customer` in `lib/toolkit-common.sh`),
  and `name<TAB>folder<TAB>leak file` rows with `list --output tsv`.

**Acceptance criteria:**
- AC-05.1: Two customers with different prefixes each lint clean as themselves and
  fail IDN-001 / PKG-002 as the other.
- AC-05.2: `--all-customers` reports each customer separately and exits non-zero if
  any fails.
- AC-05.3: The shell tools resolve a customer whose folder is outside the kit
  (`tests/customers_shell_spec.sh`).

---

## Architecture-Incompatible Patterns

- **AIP-01:** A list of customers inside `org.yaml`, `checks.yaml` or `paths.yaml`.
- **AIP-02:** Falling back to the default customer when a named one doesn't resolve.
- **AIP-03:** A customer skipping a rule the kit marks required.
- **AIP-04:** Paths in a customer's files that only work when the folder is inside the
  kit.
- **AIP-05:** Tracking `config/customers.yaml` in the kit's repository. It names
  real customers, and a tracked copy would conflict with every checkout's own.

## Open Questions

- **OQ-01:** *(Resolved 2026-09-27)* Should `bin/check-sanitized.sh` scan each
  customer folder with its own `.leak-patterns`? Resolved the other way round: a
  customer's patterns apply everywhere **but** its own folder, on every run;
  `--customer` scans one folder against the kit's and the other customers'
  patterns (FR-03, FR-05).

## Version History

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09-27 | Initial spec, from the user's decisions: a customer is an org; folders may be outside the kit; add always, skip only optional rules; wait for the Python linter |
| 0.2 | 2026-09-27 | FR-02: standing in a recipe repo counts as choosing one (the default no longer hides it); the single-customer fallback is step 4; `--all-customers` always uses each customer's repo |
| 0.3 | 2026-09-27 | FR-03/FR-05: the shell tools (leak guard, run-recipes, analyze-*) use the registry; OQ-01 resolved |
| 0.4 | 2026-09-28 | FR-01: the registry is local to each checkout (gitignored); the kit ships `config/customers.example.yaml`; AC-01.4, AC-01.5, AIP-05 |
