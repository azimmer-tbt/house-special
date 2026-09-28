# Repo Identity

This is **House Special** (repo and dist name `house-special`), an AutoPkg recipe
toolkit: tooling and method for turning Mac software into AutoPkg recipes that
build consistently named, signature-checked packages.
It covers authoring (templates, generators), linting (`bin/recipe-linter.sh` +
`config/checks.yaml`), analysis (`bin/analyze-*.sh`, `bin/inspect-*.sh`,
`bin/pkg-reverse.sh`), and running/validating recipes.

Two things live here, and they must not mix:

- **The kit** (repo root) — org-neutral. All org naming comes from
  `config/org.yaml` (identifier prefix, package-name prefix, org name).
- **Customers** (`customer/<name>/`) — one org's catalogue, plans and recipe repo.
  `customer/acme/` (Acme Fruit Co., fictional) is the worked example.

This repository is a public upstream; organizations fork it. Nothing
org-confidential may be written into it (rule 12).
