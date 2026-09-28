# Agent integration

How coding agents — ZooCode (the community continuation of Roo Code) and Cline —
work in this repository, and how to set one up for recipe work.

The design goal: an agent follows the same method a careful human would. It keeps
the kit org-neutral, runs recipes for real instead of reasoning about YAML, uses
the toolkit's own tools, and stops for operator sign-off between packages.

## How agents load the rules

| Agent | Mechanism | Setup |
|-------|-----------|-------|
| **ZooCode / Roo Code** | Auto-loads every `.md` in `.roo/rules/`, a tracked symlink to `.devagent/rules/` | None — open the repo |
| **Cline** | Reads `.clinerules`, a short pointer that tells it to read `.devagent/rules/` in numeric order | None — open the repo |

Both read the same files; `.devagent/rules/` is the single source of truth. ZooCode's
loading is mechanical, Cline's depends on the agent following the pointer — if a
Cline session ignores repo conventions, check it actually read the rules.

Details and caveats (the symlink on Windows or in CI checkouts, ZooCode rule
precedence): [`.devagent/rules/10-agent-notes.md`](../.devagent/rules/10-agent-notes.md).
Layout of the whole folder: [`.devagent/README.md`](../.devagent/README.md).

Give the agent shell access for this repository. Without it every command needs
manual approval, which defeats the point.

## Rules that shape behaviour

| Rule | Effect |
|------|--------|
| [02 version control](../.devagent/rules/02-version-control.md) | Conventional Commits; commits only when asked; never pushes unprompted |
| [03 pre-action reads](../.devagent/rules/03-pre-action-reads.md) | The skills index — which playbook to read before which task |
| [07 sessions](../.devagent/rules/07-sessions.md) | Keeps a session log in `customer/<name>/sessions/` (gitignored) |
| [09 when in doubt](../.devagent/rules/09-when-in-doubt.md) | Stops and asks rather than guessing |
| [11 per-package sign-off](../.devagent/rules/11-per-package-signoff.md) | Presents findings and waits between research, draft, build and validate |
| [12 sanitization](../.devagent/rules/12-sanitization.md) | Never writes org or personal data; runs the leak check before commits |

## Skills

Skills are Markdown playbooks in `.devagent/skills/`, each with a `name` and a
`description` saying when to use it, then When to use / Inputs / Steps / Outputs /
Verify / Pitfalls. Neither agent loads them automatically: rule 03 lists them, and
the agent reads the matching one before the task.

| Skill | Typical request |
|-------|-----------------|
| [`autopkg-recipe-development`](../.devagent/skills/autopkg-recipe-development.md) | "Write a recipe for …", "why does this recipe fail?" |
| [`analyze-package`](../.devagent/skills/analyze-package.md) | "What is this .pkg?", "vendor or in-house?" |
| [`plan-of-attack`](../.devagent/skills/plan-of-attack.md) | "Plan a batch from this folder of vendor files" |
| [`compare-packages`](../.devagent/skills/compare-packages.md) | "Does my rebuild match the original?" |
| [`postinstall-as-user`](../.devagent/skills/postinstall-as-user.md) | "Set this for every user", "put this on everyone's Desktop" |
| [`new-customer`](../.devagent/skills/new-customer.md) | "Set up a workspace for a new org/customer" |
| [`sanitize-check`](../.devagent/skills/sanitize-check.md) | "Is this safe to commit/share?" |
| [`recipe-linting`](../.devagent/skills/recipe-linting.md) | "Add a lint rule", "why did lint fail?" |
| [`spec-creation`](../.devagent/skills/spec-creation.md) | "Write a spec for …" |
| [`analyze-screenshot`](../.devagent/skills/analyze-screenshot.md) | *(optional, local vision model)* "What does this installer dialog say?" |

## What an agent can do for you

| Ask | What happens |
|-----|--------------|
| "Analyze this package" | Runs `bin/analyze-package.sh --customer <name>`, explains the verdict and the pattern |
| "Plan the Acme batch from `customer/acme/input`" | Runs `bin/analyze-materials.sh`, writes a plan per package in `customer/acme/plans/` |
| "Build the Moonlight recipe" | Lints, runs `autopkg run`, reports the built package — then waits for sign-off |
| "Compare my rebuild with the original" | Runs `bin/pkg-compare.sh` and interprets each section |
| "Why won't this recipe run?" | Reads the real error and cache state, checks `reference/methodology.md` for a known lesson |

## Other agents

Anything that can take a project-instructions file can use this layout: point it at
`.devagent/rules/` (read in order) and tell it rule 03 indexes the skills.
Tool documentation: [ZooCode](https://docs.zoocode.dev), [Cline](https://docs.cline.bot).
