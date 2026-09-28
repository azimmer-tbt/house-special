# `.devagent/` — rules, skills and standards for coding agents

Everything a coding agent needs to work in this repository the way a careful
human would: follow the frontend contract, keep the kit org-neutral, run recipes
for real instead of guessing, and stop for sign-off between packages.

| Folder | What | Loaded how |
|--------|------|------------|
| `rules/` | Numbered operating rules — the single source of truth | ZooCode/Roo: automatically, via the `.roo/rules` symlink. Cline: `.clinerules` tells it to read them in order. |
| `skills/` | Task playbooks (frontmatter `name` + `description`, then When to use / Inputs / Steps / Outputs / Verify / Pitfalls) | On demand. `rules/03-pre-action-reads.md` is the index. |
| `standards/` | Adopted standards: bash, ShellSpec, commit messages | Read when writing code, tests or commits. |

Only rule files belong in `rules/`: ZooCode loads **every** `.md` there, which is
why this README lives here and not inside it.

## Rules at a glance

| File | Rule |
|------|------|
| `01-repo-identity.md` | What this repo is; kit vs customer |
| `02-version-control.md` | Conventional Commits; commit when asked, never push unprompted |
| `03-pre-action-reads.md` | Skills index and what to read before each kind of task |
| `04-file-locations.md` | Where everything lives; the frontend contract |
| `05-bugfix-tracking.md` | `BUGFIX.md` for kit bugs |
| `06-progress-tracking.md` | `PROGRESS.md` for kit work |
| `06b-context-boundaries.md` | What not to read |
| `07-sessions.md` | Per-customer session logs |
| `08-references.md` | Where to find things |
| `09-when-in-doubt.md` | Stop and ask |
| `10-agent-notes.md` | ZooCode vs Cline mechanics |
| `11-per-package-signoff.md` | Operator sign-off between per-package steps |
| `12-sanitization.md` | Nothing org-confidential, ever; run the leak check |

## Setting up

Nothing to install. `.roo/rules` is tracked in git; if it is missing, recreate it:

```bash
ln -s ../.devagent/rules .roo/rules
```

Give the agent shell access to this repository. See
[`docs/agent-integration.md`](../docs/agent-integration.md) for a walkthrough.
