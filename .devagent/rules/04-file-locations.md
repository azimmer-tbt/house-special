# File Locations

| Path | Purpose |
|------|---------|
| `.devagent/rules/` | These rules, numbered — the single source of truth |
| `.devagent/skills/` | Task skills; indexed in rule 03 |
| `.devagent/standards/` | Adopted standards (bash, shellspec, commits) |
| `.roo/rules` | Symlink → `.devagent/rules/` (ZooCode/Roo auto-load) |
| `.clinerules` | Pointer file for Cline — contains no rules itself |
| `bin/` | Front ends — every user-facing entry point |
| `lib/toolkit-common.sh` | Shared bash library — sourced, never executed |
| `config/org.yaml` | **Org naming** (identifier prefix, package-name prefix) — the only org-specific kit file |
| `config/customers.yaml` | Customer registry: name → folder, and the `default` customer (`specs/toolkit/02-customers.md`). Local to each checkout and gitignored, because it names real customers; never commit it upstream |
| `config/customers.example.yaml` | The tracked example registry (Acme); copy it to `config/customers.yaml` |
| `config/checks.yaml` | Lint rules; org values appear only as `{{TOKENS}}`; `required: false` marks the ones a customer may skip |
| `config/paths.yaml` | Informational: where external material lives |
| `templates/` | One template per pattern, most with a worked example |
| `guardrails/` | Lane B task framing, checklist, `audit/` checks |
| `docs/` | User documentation (`patterns.md`, `getting-started.md`, `customer-contract.md`, `known-issues.md`, …) |
| `reference/methodology.md` | Lessons from real recipe runs |
| `reference/recipe-standards.md` | The standard; cited as "Standards §x" |
| `reference/autopkg-wiki/` | The user's local clone of the AutoPkg wiki (gitignored; not shipped). If it's absent, suggest `git clone https://github.com/autopkg/autopkg.wiki.git reference/autopkg-wiki` |
| `specs/<family>/` | Specifications, one folder per script family; index in `specs/README.md`. No runtime config lives here |
| `tests/` | ShellSpec suite (`shellspec`, runs under `/bin/bash` 3.2) |
| `customer/<name>/` | One customer's workspace; `customer/acme/` is the example |
| `customer/<name>/output/` | That customer's recipe repo (`--customer <name>`, or `--repo customer/<name>/output`) |
| `customer/<name>/org.yaml`, `checks.local.yaml`, `.leak-patterns` | Optional per-customer naming, lint additions/skips, denylist (`docs/FORMATS.md` §11). A customer folder may also live outside the kit |
| `customer/<name>/sessions/`, `troubleshooting/`, `input/` | Session logs, evidence, raw vendor files — gitignored |
| `BUGFIX.md`, `PROGRESS.md` | Kit development logs (rules 05, 06) |

**The frontend contract:** toolkit assets resolve from the script's own location
(`TOOLKIT_ROOT`); work targets resolve from `--repo` (`REPO_ROOT`), then
`$AUTOPKG_TOOLKIT_REPO`, then (linter and preflight) the selected customer's repo,
then the CWD only if it contains `recipes/`. The current working directory is never
load-bearing. Org naming resolves from `--org`, then `$AUTOPKG_TOOLKIT_ORG`, then
`config/org.yaml` with the customer's `org.yaml` laid over it.
