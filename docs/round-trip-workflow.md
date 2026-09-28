# Round-Trip Workflow

The workflow from "here are the files someone built it from" to "it builds and matches
the original". This page is the overview. The detailed steps, research questions and
plan format are in
[`specs/method/00-methodology.md`](../specs/method/00-methodology.md); pattern
classification is in [`docs/patterns.md`](patterns.md).

## The pipeline

```
1.  Compose CSV           ─ inventory of every package, noting what's done
2.  Analyze server pkgs   ─ analyze-package.sh on each on-server package (one pass)
3.  Establish target      ─ step 2 output IS the target
4a. Plan per package      ─ classify easy wins vs custom builds
4b. Create easy wins      ─ Patterns 4/5 from templates
4c. Plan custom builds    ─ mine the upstream material for source files
5.  Build recipe          ─ template, or pkg-reverse.sh → blueprint-to-recipe.sh
6.  Run autopkg           ─ autopkg run
7.  Debug if needed       ─ reference/methodology.md, guardrails
8.  Validate              ─ pkg-compare.sh against the original
```

Do the easy wins first: vendor packages (Pattern 4) and packages with a public URL
(Pattern 5) are the most progress for the least effort. Write down each package's
research and chosen pattern in a plan of attack at `customer/<name>/plans/<App>.md`
(example: [`orchard-analytics.md`](../customer/acme/plans/orchard-analytics.md)).

## Most common commands

```bash
# Analyze a package (step 2)
bin/analyze-package.sh server.pkg --customer acme --output json

# Match vendor material to the catalogue (step 4c)
bin/analyze-materials.sh /path/to/material --customer acme

# Inspect a DMG or app
bin/inspect-dmg.sh file.dmg
bin/inspect-app.sh Some.app --output json

# Reverse-engineer a custom build (step 5, Pattern 6)
sudo bin/pkg-reverse.sh custom.pkg --dest build/vendor_cache/Vendor/
bin/blueprint-to-recipe.sh --blueprint blueprint.conf --out recipes/Vendor/App

# Check, run, validate (steps 5–8)
bin/autopkg-preflight.py --repo <repo> --app <repo>/recipes/Vendor/App
autopkg run -v recipes/Vendor/App/App.pkg.recipe.yaml
bin/pkg-compare.sh --old-pkg server.pkg --new-pkg ~/Library/AutoPkg/Cache/.../Acme_App.pkg
```

`pkg-compare.sh` exits 0 when the rebuild matches the original in file inventory,
permissions and scripts. When a run fails, check
[`reference/methodology.md`](../reference/methodology.md) before guessing: most
failures are already there as a lesson.

## Also see

- [`specs/method/00-methodology.md`](../specs/method/00-methodology.md): the detailed
  8-step workflow and tool-to-step mapping
- [`docs/patterns.md`](patterns.md): pattern definitions and the Quick Reference
- [`docs/usage-guide.md`](usage-guide.md): every tool, by task
- [`reference/methodology.md`](../reference/methodology.md): lessons from real
  recipe runs
- [`guardrails/CHECKLIST.md`](../guardrails/CHECKLIST.md): the pre-flight checklist
