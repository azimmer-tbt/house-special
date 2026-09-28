---
name: autopkg-recipe-development
description: The core workflow for writing, fixing or debugging an AutoPkg recipe pair in this kit, from pattern choice through preflight, a real autopkg run and the sidecar README. Use when someone says "write a recipe for X", "fix this recipe", "autopkg run fails", "why doesn't this recipe build", or "package this app".
---
# AutoPkg Recipe Development

## When to use

Before any recipe work: drafting a new download/pkg pair, fixing a failing one, or
reviewing one. Loaded by `.devagent/rules/03-pre-action-reads.md` for every agent.

## Inputs

- A recipe repo: `customer/<name>/output` (it has `recipes/`) or any path passed as
  `--repo`. Toolkit assets resolve from the script's location, work targets from
  `--repo`; the current directory is never load-bearing. If a front end can't
  resolve the repo it fails loudly. Don't "fix" that by `cd`-ing and re-running.
- Org naming from [`config/org.yaml`](../../config/org.yaml): identifiers
  `<identifier_prefix>.download.<App>` / `.pkg.<App>`, package name
  `<pkgname_prefix>%NAME%` (only when `PkgCreator` builds it). Never hard-code them.
- For Lane B: a plan in `customer/<name>/plans/<App>.md` (see
  [plan-of-attack.md](plan-of-attack.md)) and operator sign-off per
  [rule 11](../rules/11-per-package-signoff.md).

## Steps

1. **Read [`reference/methodology.md`](../../reference/methodology.md)** — 27 lessons,
   each found by actually running recipes that had passed review. YAML that looks
   right is not evidence: what sets `%pathname%`, whether `%RECIPE_CACHE_DIR%` is
   shared across a parent→child chain, what `PkgCreator` rejects, only show at run time.
2. **Pick the pattern** from [`docs/patterns.md`](../../docs/patterns.md): numbers 1–8
   are the source, letters the variant (`2b`, `4d`, `6c` …). Derive it from the
   processors, not a README or filename (lesson 26). A "known-working" example is a
   valid reference only if it's the same shape (lesson 9).
3. **Slice what the org adds.** License files, config files, LaunchAgents and setup
   scripts go in their **own** recipe (usually 6c, or 6b/6d), installed after the app.
   This is **required** when the vendor ships a sealed `.pkg` we copy as-is (never open
   it), and **preferred** when we rebuild an app-only DMG/ZIP. A same-package ridealong
   (2c, 4d) is the exception; propose it for review, don't default to it. A slice
   installs **after** the package that creates its target folder (record
   "Install after:" in its README); one that writes inside an app bundle must re-run
   after every app update.
   Walkthrough: [`docs/build-your-first-recipe.md`](../../docs/build-your-first-recipe.md)
   step 3; standard: `reference/recipe-standards.md` §6.10.1.
4. **Start from a template** under [`templates/`](../../templates/README.md), or for
   Pattern 6 from `sudo bin/pkg-reverse.sh <pkg> --dest <dir>` then
   `bin/blueprint-to-recipe.sh`. Find leftovers with
   `bin/scan-placeholders.sh --repo <repo> <App>`.
5. **Follow the conventions the linter enforces:**
   - download recipe verifies signatures (`CodeSignatureVerifier`) — or declares
     `Input.NO_CODE_SIGNATURE_REQUIRED: true` with a comment and README reason (CSV-001);
   - publisher pinned (`subject.OU` / `expected_authority_names`) or recorded as
     absent with `teamid: "UNSIGNED_NO_TEAMID"` plus a comment in the download
     recipe's `Input` (CSV-005); the README records the Team ID for humans;
   - version extracted by a processor, or pinned in `Input.version` (VER-001).
     AutoPkg never reads `.overrides`, so nothing the recipe needs goes there;
   - a sidecar `README.md`: pattern, design decisions, signature status, known gaps
     (Standards §6.7 item 8). Pattern 8 also names an approver.
6. **Lint and preflight:**
   ```bash
   bin/recipe-linter.sh --repo <repo> --pair-check
   bin/autopkg-preflight.py --repo <repo> --app <repo>/recipes/<Vendor>/<App>
   ```
   Fix every failure; they are must-haves.
7. **Run it for real** (preflight catches known patterns, not every runtime failure):
   ```bash
   autopkg run -v --search-dir <repo>/recipes <repo>/recipes/<Vendor>/<App>/<App>.pkg.recipe.yaml
   # vendor drops (Pattern 4) also need: -k VENDOR_CACHE_ROOT=/tmp/autopkg/vendor_cache
   ```
8. **Debug from evidence**: the actual error and `~/Library/AutoPkg/Cache/<identifier>/`.
   If a fix doesn't seem to take, clear stale cache first:
   `bin/clear-autopkg-cache.sh --dry-run <identifier>`, then without `--dry-run`.
9. **Compare** a rebuild against the package it replaces
   ([compare-packages.md](compare-packages.md), lesson 20), then write what you found
   into the app's `README.md`.

## Outputs

`recipes/<Vendor>/<App>/` with `<App>.download.recipe.yaml`, `<App>.pkg.recipe.yaml`,
`README.md` (plus `scripts/` / `payload/` if ridealong). No `.overrides` unless the
org's pipeline uses one (Standards §3.4); if it holds a secret, it is generated or
gitignored, never committed.

## Verify

- Linter ends `All N recipe(s) passed lint checks`, exit 0; preflight exits 0.
- `autopkg run` prints "The following packages were built" and the `.pkg` is in the cache.
- `bin/generate-manifest.sh --repo <repo>` run before handing off a batch;
  `manifest.sha256` travels with it (silent handoff drift was the batch's biggest time sink).

## Pitfalls

- **Never silently drop `CodeSignatureVerifier`.** Check a `.pkg` with
  `pkgutil --check-signature`, never `codesign` (lesson 5); check `.app`s inside
  unsigned wrappers anyway (lesson 16). Unsigned → declare it, don't delete the step.
- **Vendor binaries are never committed.** They live in `customer/<name>/output/vendor_cache`
  or `/tmp/autopkg/vendor_cache` (both outside git), listed in `files_to_copy.yaml`.
  `/tmp` is purged at reboot (lesson 24). No real license keys in ridealong files:
  use a marked placeholder and flag it in the README.
- `chown` `mode:` on a directory hits every descendant (lesson 17); `PkgCreator`
  validates id/pkgname/version and needs an existing pkgroot (lesson 18).
- Several lessons look different but share a root cause — re-read before calling a
  failure new. Known tool bugs: [`docs/known-issues.md`](../../docs/known-issues.md).
- **You have a shell — use it.** Run commands yourself; don't ask the operator to
  paste output back.
- **Wiki lookup: one page for one question.** If `reference/autopkg-wiki/` exists,
  read `reference/autopkg-wiki/Processor-<ExactName>.md` (small pages). Skip the big
  concept pages; `reference/methodology.md` and `guardrails/GUARDRAILS.md` are the
  orientation. Two pages without an answer means it isn't in the wiki. The kit
  doesn't ship the wiki: if it's absent, don't answer a processor question from
  memory. Suggest `git clone https://github.com/autopkg/autopkg.wiki.git reference/autopkg-wiki`, or check the processor's source in AutoPkg.
- **Toolchain:** `bin/recipe-linter.sh` is a front end for `recipekit.lint` (AutoPkg's
  Python). Rules live in `config/checks.yaml`, never in code. A check the rule engine
  can't express is either a new engine feature (spec first) or a guardrail audit in
  `lib/python/recipekit/audits.py`
  ([`specs/recipe-linter/00-constitution.md`](../../specs/recipe-linter/00-constitution.md)).

## References

- [`docs/patterns.md`](../../docs/patterns.md), [`docs/glossary.md`](../../docs/glossary.md)
- [`reference/recipe-standards.md`](../../reference/recipe-standards.md) (§6.7 Review Checklist)
- [`specs/method/00-methodology.md`](../../specs/method/00-methodology.md) — the per-package workflow
- [`docs/getting-started.md`](../../docs/getting-started.md), [`customer/acme/README.md`](../../customer/acme/README.md)
- Related skills: [recipe-linting.md](recipe-linting.md), [postinstall-as-user.md](postinstall-as-user.md),
  [compare-packages.md](compare-packages.md)
