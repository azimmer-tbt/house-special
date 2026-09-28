# Per-Package Workflow — The 8-Step Methodology

**Date:** 2026-09-08  
**Purpose:** This is the canonical per-package recipe authoring workflow. The repo-wide approach is simply "do this, again and again" across every package in the catalogue. Steps 2-3 are done for ALL packages in one pass first, to identify the easy wins.

---

```
    ┌───────────────────────────────────────────────────────────┐
    │  STEPS 2-3: One pass across all packages                 │
    │  (identify easy wins before diving into custom builds)    │
    └───────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌───────────────────────────────────────────────────────────┐
    │  STEPS 4a-4c: Per-package planning                       │
    │  Easy wins first, custom builds last                     │
    └───────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌───────────────────────────────────────────────────────────┐
    │  STEPS 5-8: Per-package build + validate                 │
    │  Build → run → debug → compare                           │
    └───────────────────────────────────────────────────────────┘
```

---

## Pre-Work: Per-Package Research Questionnaire

Before Step 1, answer these questions for each package. Answering them before attempting a recipe speeds things up immensely. Research methods: human investigation, LLM detection, or reverse-engineering from an expanded package.

### The Questions

**Q1 — What is the reference point?**

This should be a bundle (`.app`) or a version cookie text file. The user decides this, though an analysis of the file tree from an expanded package can make a recommendation. The reference point is what we use to determine the version we're building.

*How to find it:* expand the on-server package, look for the "main" application in `/Applications/` (not helper tools), or look for a version file. Use `inspect-app.sh` on candidate bundles.

**Q2 — What version are we seeking to build?**

Determined by:
- **Best:** version number in the reference bundle's `Info.plist` (`CFBundleShortVersionString`), extracted via `inspect-app.sh`.
- **Fallback:** human override — the user provides the version manually.
- **Public download (auto-updating) files:** may not have a tight lock here. If the vendor updates them rapidly, do best effort. Document the heuristic used.

*Note for auto-updating apps:* The version in the recipe may drift from what ships in a week. That's expected. Document the source of the version for future reference.

**Q3 — What pattern is this? (public URL, vendor PKG, flat file, etc.)?**

*A good place to start:* Google. Go to the manufacturer's page, see if a freely-accessible download exists. If yes:
1. Try to download it and put the result in as reference
2. Try to download using `curl`/`wget` to simulate machine download — does the URL work without cookies/session? If yes, it's automatable (Pattern 5). If not, it's probably not a stable URL (Pattern 4 by default).

Deterministic detection via `bin/analyze-package.sh`:
- Vendor-originated + signed → Pattern 4 (ship as-is) or Pattern 5 (if URL found)
- Custom-build → Pattern 6 (reverse-engineer)
- Contradictory signals → manual investigation needed

**Q4 — Does it have scripts to include?**

Run `bin/analyze-package.sh` on the prior/server version of the package. Check for scripts (preinstall/postinstall). If present, the recipe needs a `scripts:` step in both the download and pkg recipes.

*Detection:* `analyze-package.sh` reports script presence in its output. Or expand manually with `pkgutil --expand` and check the `Scripts/` directory.

**Q5 — If vendor provided, what type of file?**

| Type | Detection tool | Key questions |
|------|---------------|---------------|
| ZIP | `inspect-archive.sh` | What top-level paths? Permissions overrides? |
| DMG | `inspect-dmg.sh` | What apps inside? Versions? Signatures? |
| Tarball | `inspect-archive.sh` | Same as ZIP |
| .pkg | `analyze-package.sh` | Already analyzed in step 2 |

For each source file, document:
- What files are included (top-level listing)
- What permissions overrides happened (from `capture-perms.sh` or BOM analysis)
- Whether the source is the same as the vendor's original or was modified

### Answer Format

Capture answers in `customer/<CustomerName>/plans/<AppName>.md`:

```markdown
# Plan: <AppName>

## Research Answers

- **Q1 — Reference point:** <bundle path or version cookie>
- **Q2 — Version:** <version> (source: inspect-app.sh / user override)
- **Q3 — Pattern:** <4|5|6|other> (rationale: <explanation>)
- **Q4 — Scripts:** <yes|no> (if yes: <list of scripts>)
- **Q5 — File type:** <DMG|ZIP|tarball|pkg> (details: <top-level items, permissions>)

## Action Plan

<ordered checklist for building this recipe>
```

---

## Step 1 — Compose the CSV

**What:** The full list of packages in scope, with known attributes.

**Inputs:** Existing partial CSV, upstream repo inventory, server inventory.

**Output:** `customer/<name>/autopkg-recipes.csv` (example: `customer/acme/autopkg-recipes.csv`; schema in `docs/FORMATS.md` §1)

| Column | Example | Notes |
|--------|---------|-------|
| AppName | Kiwi-Capture | Normalized app name |
| Vendor | KiwiSoft | Vendor directory name |
| Pattern | 4 | Initial guess (refined in step 4a) |
| Status | pending | pending / easy-win / custom-build / done |
| ServerPkg | KiwiSoft_Kiwi-Capture_2026.1.2.pkg | Latest on-server package filename |
| Notes | | Anything known upfront |

**Tooling:** Manual editing, CSV tools.

---

## Step 2 — Analyze the Current On-Server Package

**What:** For EVERY package in one pass, grab the most current on-server package. Extract: teamID, filename, receipt IDs. Expand it, find the "important" application (the one in `/Applications`, not a helper tool), note its version.

**Inputs:** Server package path, or `sources.upstream_packages` from paths.yaml.

**Command (proposed):**
```bash
bin/analyze-package.sh /path/to/on-server-package.pkg --clues customer/acme/clues.yaml --output json
```

**Output per package (captured in CSV):**
- Filename
- Team ID / signature authority
- Receipt IDs (package identifier)
- Version of the main application
- Whether it's vendor-originated or custom-build

**This is the "target"** — it's what we need to find the upstream source of.

**Tooling:** `analyze-package.sh` (A3), plus `inspect-app.sh` (A4c) for version extraction from the expanded payload.

---

## Step 3 — Establish the Target

**What:** The output of Step 2 IS the target — the known-working state we need to reproduce. This step is implicit: the analysis data becomes the benchmark.

**Tooling:** CSV from step 1 + analysis from step 2 = complete target specification.

---

## Step 4a — Plan Per Package (Easy Wins)

**What:** For each package, note in the plan-of-attack doc: if it's likely vendor-provided, and ESPECIALLY if it has a publicly-visible download URL.

**Easy win signals:**
- Vendor package (sealed, their team ID, not ours)
- Has a public download URL → Pattern 5
- No public URL but clearly a vendor package → Pattern 4 (use PkgCopier)

**Output:** `customer/acme/plans/<AppName>.md` — one per package, with pattern recommendation.

**Tooling:** `analyze-package.sh` output + manual/LLM review.

---

## Step 4b — Create the Easy-Win Packages

**What:** Implement recipes for all easy wins first. Most progress, least effort.

- Public URL packages → Pattern 5 template
- Vendor-provided sealed packages → Pattern 4 template (PkgCopier)

**These are fast.** Template copy + placeholder fill + `autopkg run` + `pkg-compare`.

**Tooling:** Templates from `templates/pattern-4-vendor-drop/` and `templates/pattern-5-vendor-pkg-url/`, `scan-placeholders.sh`, `autopkg-preflight.py`.

---

## Step 4c — Plan the Custom Builds

**What:** For the remaining packages (truly custom builds), plan the time-consuming part: mining the upstream recipe repo for original source materials (_Vendor/ dirs, txt/rtf/PDF docs, companion files).

**Inputs:** The upstream recipe repo (_Vendor/ dirs, documentation files).

**Tooling:** `analyze-materials.sh` (A4a) to match source candidates, micro-tools (A4b-A4e) for inspection, LLM for interpreting messy notes.

**Output:** Detailed plan-of-attack per package for Step 5.

---

## Step 5 — Build a Recipe

**What:** From the plan-of-attack, generate the actual recipe pair.

- Pattern 4/5: Copy template, fill placeholders
- Pattern 6: Use `pkg-reverse.sh` → `blueprint-to-recipe.sh`

**Tooling:** `blueprint-to-recipe.sh`, templates, `pkg-reverse.sh`.

**Output:** `AppName.download.recipe.yaml` + `AppName.pkg.recipe.yaml` + `README.md`. No `.overrides` unless the org's pipeline uses one (Standards §3.4).

---

## Step 6 — Run in AutoPkg

**What:** `autopkg run` to verify the recipe builds successfully.

```bash
autopkg run ./recipes/Vendor/App/App.pkg.recipe.yaml
```

**Tooling:** `autopkg run`, `clear-autopkg-cache.sh` if needed.

---

## Step 7 — Debug If Needed

**What:** If the recipe fails at runtime, debug using `reference/methodology.md` (lessons from real runs), methodology-linting results, and actual error output.

**Tooling:** `reference/methodology.md`, `guardrails/`, methodology-linting output.

---

## Step 8 — Validate Against Original

**What:** If the recipe produces correct output on the first try (or after debugging), point `pkg-compare.sh` at the rebuilt package and the original from the server.

```bash
bin/pkg-compare.sh --old-pkg /path/to/on-server/original.pkg --new-pkg ~/Library/AutoPkg/Cache/.../Acme_App.pkg
```

**Tooling:** `pkg-compare.sh`.

**Exit:** 0 = pass. Non-zero = investigate mismatch.

---

## Tool-to-Step Mapping

| Step | Primary Tool(s) | Dependencies |
|------|----------------|--------------|
| 1 — Compose CSV | Manual + CSV tools | Nothing |
| 2 — Analyze server pkg | `analyze-package.sh` (A3), `inspect-app.sh` (A4c) | A3, A4c |
| 3 — Establish target | (implicit — output of step 2) | Step 2 |
| 4a — Plan per package | `analyze-package.sh` output + manual/LLM | A3 |
| 4b — Create easy wins | Templates, `scan-placeholders.sh`, `autopkg-preflight.py` | Templates exist |
| 4c — Plan custom builds | `analyze-materials.sh` (A4a), micro-tools (A4b-A4e), LLM | A4a, A4b, A4c, A4d, A4e |
| 5 — Build recipe | `pkg-reverse.sh`, `blueprint-to-recipe.sh` | Existing tools |
| 6 — Run autopkg | `autopkg run`, `clear-autopkg-cache.sh` | autopkg |
| 7 — Debug | `reference/methodology.md`, `guardrails/` | Existing docs |
| 8 — Validate | `pkg-compare.sh` | Existing tool |

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.2 | 2026-09-27 | .overrides optional; .autopkg_config removed from upstream. Step 5 output is the recipe pair and README. |
