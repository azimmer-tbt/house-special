# Specs

One folder per script family: a single script, or a few that only make sense
together. Constitutions set the principles; numbered files are the requirements,
with `[TESTABLE]` acceptance criteria.

Two constitutions are shared:
- [`toolkit/00-constitution.md`](toolkit/00-constitution.md) applies to **every**
  tool in the kit.
- [`analysis/00-constitution.md`](analysis/00-constitution.md) applies to the
  analysis families inside `analysis/`.

## Where each script's spec lives

| Script(s) | Spec folder |
|---|---|
| `lib/toolkit-common.sh` | [`toolkit/`](toolkit/) |
| `lib/python/recipekit/` (the shared recipe model) | [`recipekit/`](recipekit/) |
| `lib/python/recipekit/customers.py`, `config/customers.example.yaml` (several customers in one kit) | [`toolkit/02-customers.md`](toolkit/02-customers.md) |
| `bin/recipe-linter.sh` (front end for `recipekit.lint`), `config/checks.yaml` | [`recipe-linter/`](recipe-linter/) |
| `bin/analyze-package.sh` | [`analysis/analyze-package/`](analysis/analyze-package/) |
| `bin/analyze-materials.sh` | [`analysis/analyze-materials/`](analysis/analyze-materials/) |
| `bin/inspect-app.sh`, `inspect-dmg.sh`, `inspect-archive.sh`, `capture-perms.sh` | [`analysis/inspect-tools/`](analysis/inspect-tools/) |
| `bin/classify-recipe.sh` (front end for `recipekit.classify`) | [`analysis/classify-recipe/`](analysis/classify-recipe/) |
| `bin/pkg-reverse.sh`, `blueprint-to-recipe.sh` | [`pkg-reverse/`](pkg-reverse/) |
| `bin/pkg-compare.sh` | [`pkg-compare/`](pkg-compare/) |
| `bin/rr-batch.sh` | [`rr-batch/`](rr-batch/) |
| `bin/normalize-vendor-cache.sh`, `sync-vendor-cache.sh` | [`vendor-cache/`](vendor-cache/) (`03-sync.md` for the sync script) |
| `bin/init-recipe-repo.sh` | [`init-recipe-repo/`](init-recipe-repo/) |
| `bin/generate-manifest.sh`, `verify-manifest.sh` | [`manifest/`](manifest/) |
| `bin/check-sanitized.sh` | [`check-sanitized/`](check-sanitized/) |
| `bin/check-doc-links.sh` | [`check-doc-links/`](check-doc-links/) |
| `bin/make-dist.sh` | [`make-dist/`](make-dist/) |
| `bin/clear-autopkg-cache.sh` | [`clear-autopkg-cache/`](clear-autopkg-cache/) |
| `bin/run-recipes.sh` | [`run-recipes/`](run-recipes/) |
| `bin/scan-placeholders.sh` | [`scan-placeholders/`](scan-placeholders/) |
| `bin/analyze-screenshot.sh` | [`analyze-screenshot/`](analyze-screenshot/) |
| `bin/autopkg-preflight.py`, `guardrails/audit/*.py` | [`guardrail-audits/`](guardrail-audits/) |

The per-package method (how a person or agent works through one app) is not a
script spec. It lives in [`method/00-methodology.md`](method/00-methodology.md).

## Writing one

Start with [`.devagent/skills/spec-creation.md`](../.devagent/skills/spec-creation.md).
A new script gets its own folder, or joins a family folder when it only makes sense
alongside the scripts there. Put a `**Requires:**` line at the top of each spec,
with repo-root paths (`specs/toolkit/00-constitution.md`), so the dependencies read
the same wherever the file is opened.
