# Agent-Specific Notes

Rules 01–09, 11 and 12 apply to every coding agent. This file covers the mechanics
that differ between agents.

## How each agent loads these rules

| Agent | Mechanism | Guarantee |
|-------|-----------|-----------|
| ZooCode / Roo Code | Auto-loads every `.md` in `.roo/rules/` (a symlink → `.devagent/rules/`), alphabetically | Mechanical — the rules are in context whether or not the agent reads them |
| Cline | Reads `.clinerules`, a short pointer telling it to read `.devagent/rules/` in order | Behavioral — depends on the agent following the pointer |

The `NN-` filename prefixes are load order. Keep them, and number new files.
Nothing but rules belongs in `.devagent/rules/` — ZooCode would load a README
there as if it were a rule, which is why the directory's README lives one level up.

ZooCode's precedence, later overriding earlier: `~/.roo/rules-{mode}/`,
`~/.roo/rules/`, `.roo/rules-{mode}/`, `.roo/rules/`, then the legacy
`.roorules*` and `.clinerules*` fallbacks.

## Skills

Neither agent auto-loads skills. Rule 03 is the index; read the skill file before
the task it covers.

## Tools and modes

Most tool names match between Cline and ZooCode; ZooCode's primary edit tool is
`apply_diff`. Architect-style modes may only edit Markdown in either agent.

Give the agent shell access for this repo. The toolkit exists so an agent can run
`autopkg`, the linter and the analysis tools itself instead of asking the operator
to paste output.

## The symlink

`.roo/rules` is the repo's only tracked symlink (target `../.devagent/rules`, so it
resolves wherever the repo is cloned). Some CI checkouts dereference symlinks, and a
Windows checkout without developer mode turns it into a text file containing the
path. If ZooCode seems not to see the rules, check the link survived the checkout.
`bin/make-dist.sh --with-devagent` copies it dereferenced.
