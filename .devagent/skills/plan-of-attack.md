---
name: plan-of-attack
description: Scan a folder of received vendor material against the customer's catalogue and write a per-package plan of attack before any recipe is drafted. Use when someone says "analyze materials", "plan a batch", "what did the vendor send", "which of these are easy wins", or drops a directory of installers.
---
# Plan of Attack

## When to use

Lane B, before drafting: steps 2–4 of
[`specs/method/00-methodology.md`](../../specs/method/00-methodology.md). One pass across
all packages first to find easy wins, then one plan file per package.

## Inputs

- A source directory — usually `customer/<name>/input/` (gitignored drop point).
- The customer's catalogue `customer/<name>/end_result.yaml`
  ([FORMATS §3](../../docs/FORMATS.md#3-customernameend_resultyaml)) — reached via
  `--customer <name>` (lowercase folder name) or an explicit `--targets <file>`.
- AutoPkg installed — the scripts run AutoPkg's bundled Python (PyYAML included).

## Steps

1. Match material to targets:
   ```bash
   bin/analyze-materials.sh customer/<name>/input --customer <name>
   bin/analyze-materials.sh <dir> --targets customer/<name>/end_result.yaml --output json
   ```
   Matching lowercases and strips non-alphanumerics, so `Orchard-Analytics` matches
   `Orchard Analytics 7.2.dmg`. A target with `(0 candidates)` just means nothing matched.
2. Inspect each candidate (all take `--output json`):
   - `.pkg` → `bin/analyze-package.sh <file> --customer <name>` ([analyze-package.md](analyze-package.md))
   - `.dmg` → `bin/inspect-dmg.sh <file>`
   - `.app` → `bin/inspect-app.sh <path>` (version, signature, architectures)
   - archives → `bin/inspect-archive.sh <file>`
   - a staged tree's modes → `bin/capture-perms.sh <dir>`
3. Answer the research questionnaire (Q1 reference point, Q2 version, Q3 pattern,
   Q4 scripts, Q5 file type) and choose the pattern and letter from
   [`docs/patterns.md`](../../docs/patterns.md). Check for a public download first —
   a stable URL beats a vendor drop.
4. Write `customer/<name>/plans/<app>.md` with the front matter from
   [FORMATS §6](../../docs/FORMATS.md#6-customernameplansappnamemd-plan-of-attack)
   (`ready_draft`, `ready_test`, `ready_compare`, `ref_file`, `ref_version`, `team_id`,
   `public_download`, `download_url`, `vendor_name`, `app_name`, `pattern` quoted),
   then Research Notes, Source Location, and an Actions checklist. Model it on
   [`customer/acme/plans/orchard-analytics.md`](../../customer/acme/plans/orchard-analytics.md).
5. Order the work: easy wins (4a/4b/4c/5, public-URL 3b) first, rebuilds (6x) last.
   - Easy win: template → `bin/scan-placeholders.sh --repo <repo> <App>` →
     preflight → `autopkg run`.
   - Rebuild: `sudo bin/pkg-reverse.sh <pkg> --dest <dir>` → review `blueprint.conf` →
     `bin/blueprint-to-recipe.sh` → same chain → `bin/pkg-compare.sh`.
6. **Stop for sign-off** ([rule 11](../rules/11-per-package-signoff.md)): present the
   research and plan and wait for the operator before drafting.

## Outputs

- A per-package summary table: package, version, pattern, confidence, complexity,
  source candidate, action items.
- One plan file per Lane B package in `customer/<name>/plans/`.

## Verify

- Every catalogue target is either matched to material or listed as missing.
- Each plan's front matter parses as YAML and `pattern` matches a label in
  `docs/patterns.md`; `ref_version` comes from the payload, not a filename (lesson 22).

## Pitfalls

- `analyze-materials.sh` is a deterministic matcher, not an interpreter: reading
  vendor notes, PDFs and emails is your job.
- Versions and names come from the payload (methodology lesson 22); the vendor
  cache is not a backup (lesson 24) — record the durable source in the plan.
- Corporate networks may block a public URL; tune `curl` or fall back to a vendor
  drop and write down why (lesson 25).
- Keep hostnames, user names and ticket numbers out of plans (they're tracked);
  put raw evidence in `troubleshooting/` or `sessions/`.

## References

- [`specs/analysis/analyze-materials/01-analyze-materials.md`](../../specs/analysis/analyze-materials/01-analyze-materials.md)
- [`docs/material-analysis.md`](../../docs/material-analysis.md), [`docs/FORMATS.md`](../../docs/FORMATS.md)
- [`docs/patterns.md`](../../docs/patterns.md), [`docs/glossary.md`](../../docs/glossary.md)
- [`reference/methodology.md`](../../reference/methodology.md)
