# Version Control

- Commit messages follow **Conventional Commits**: `type(scope): summary`.
  Summary and this repo's types/scopes: `.devagent/standards/conv_commits.md`.
- **Commit only when the operator asks** (or has said to commit as you go for
  the current task). **Never push** unless the operator explicitly asks.
- One logical change per commit. Tests (`shellspec`) should be green before a
  commit; if you must commit red, say so in the subject (`WIP:`) and tell the
  operator.
- Never rewrite published history. If something sensitive was committed, stop
  and ask the operator (`.devagent/skills/sanitize-check.md`).

## Examples

```
feat(linter): add exists_any condition for pinned versions
fix(analysis): expand payload with pkgutil --expand-full
docs(acme): add Orchard Analytics plan of attack
chore(devagent): refresh skills index
```
