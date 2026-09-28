# Execution: How to Run This Kit

## One-time setup

1. Copy this `guardrails/` folder into your AutoPkg recipe repo, alongside
   `recipes/` (not inside them).
2. Make sure your coding agent loads this toolkit's agent rules
   (`.devagent/rules/`, reached through `.roo/rules` for ZooCode/Roo or the
   `.clinerules` pointer for Cline) — this is what makes a local model behave
   consistently across sessions rather than re-learning the same lessons each time.
3. Confirm you're on macOS with `autopkg`, `pkgutil`, and `codesign` all available
   (`which autopkg pkgutil codesign`). None of this kit's audits require them, but
   actually running recipes does.

## Per-recipe workflow

```bash
# 1. Run the audit against the specific app you're working on
bin/autopkg-preflight.py --app recipes/VendorName/AppName

# 2. Fix everything it reports FAIL on — these are must-haves, not suggestions

# 3. Actually run the recipe for real
autopkg run ./recipes/VendorName/AppName/AppName.pkg.recipe.yaml

# 4. If it fails with something the audit didn't catch, that's a genuinely new
#    issue -- diagnose from the real error and the real AutoPkg cache state, not
#    guesswork. Check reference/methodology.md first; it may be a known pattern.

# 5. If a fix doesn't seem to take effect on retry, clear the cache before
#    assuming the fix is wrong:
bin/clear-autopkg-cache.sh com.acmefruit.autopkg.download.AppName com.acmefruit.autopkg.pkg.AppName

# 6. Once genuinely working, update recipes/VendorName/AppName/README.md with
#    what you found -- both the design rationale and any bugs fixed.

# 7. Before considering the batch done, regenerate and verify the manifest:
bin/generate-manifest.sh
bin/verify-manifest.sh
```

## Whole-repo audit (before a batch handoff/commit)

```bash
bin/autopkg-preflight.py --repo .
```

Exits non-zero if anything across the whole `recipes/` tree fails a check —
usable as a pre-commit or CI gate.

## On failure the audit didn't predict

1. Read the actual error message carefully — AutoPkg's errors usually name the
   exact processor and argument that failed.
2. Check `reference/methodology.md` for whether this matches one of the
   cataloged lessons, even if the symptom looks different (several bugs share a root
   cause — e.g. both directory-copy issues are really about the same `Copier`
   behavior).
3. If it's genuinely new: fix it, verify with a real `autopkg run`, then consider
   whether it's common enough to warrant a new `guardrails/audit/check_*.py` script and a new
   entry in `GUARDRAILS.md`'s Must-Haves — this kit should grow, not stay static.

## Cline-specific notes

- Cline reads `.clinerules` automatically as standing project context. In this
  toolkit it is a short pointer to `.devagent/rules/`, so there is no copy to
  keep in sync.
- Give Cline direct bash execution permission for this repo — the entire value of
  running locally is eliminated if it still has to ask you to paste back command
  output.
- If using a different local coding agent (not literally Cline), point it at
  `.devagent/rules/` as its project instructions — the guardrails aren't Cline-specific, just delivered in the
  format Cline expects by default.
