# Pattern 6b — Rebuilt Package (Payload + Scripts)

**Defined in `reference/recipe-standards.md` §6.2.6.** Pattern 6 is this kit's
addition to the common AutoPkg shapes — say "Pattern 6 (rebuilt package)" the
first time you use the term outside this repo.

## When

An installed package exists; its source files do not. A legacy in-house package
with no build recipe, no pkgroot, and nobody left who has them. You extract the
built package and rebuild from what comes out.

Pattern 6b is the variant where both the **payload** and the **installer scripts**
were extracted as separate archives (`payload.zip` + `scripts.zip`). This is
typical of packages extracted via `pkgutil --expand` that have both a Payload
and Scripts file inside.

**Not for vendor packages you could ship as-is.** Rebuilding discards the
original signature. If the input is signed by someone else, Pattern 4 Variant A
(`PkgCopier`) preserves it and is the right answer.

## Recipe chain

```
URLDownloader (payload.zip) → Unarchiver → payload/
URLDownloader (scripts.zip) → Unarchiver → scripts/
                                    ↓
                              PkgCreator
                          (payload + scripts + chown)
```

The download recipe has **two** URLDownloader + Unarchiver pairs — one for the
payload archive and one for the scripts archive.

The pkg recipe uses `PkgCreator` with a `scripts:` argument pointing at the
extracted scripts directory. A `chown:` block is included when ownership must
be restored (i.e., the payload was extracted without `sudo`).

## Why not Pattern 4

Pattern 4 stages a file someone handed you and ships it. Pattern 6 dismantles a
built artifact and reconstructs it. The acquisition looks similar; the work does
not. Four decisions have no Pattern 4 equivalent, and three fail silently:

| Decision | Failure mode if wrong |
|----------|----------------------|
| Package identifier | Installs *alongside* the original instead of upgrading it. Two receipts claim the same files. Nothing errors. |
| Install location | `PkgCreator` has no such argument — the payload tree's shape *is* the install location. Wrong shape, wrong destination, no error. |
| Installer scripts | Build fails outright if `preinstall`/`postinstall` are present but not executable. The loud one. |
| File ownership | Extracted without root, everything is owned by whoever ran the extractor and installs that way. |

## The normal path

Generate rather than hand-write:

```bash
sudo <toolkit>/bin/pkg-reverse.sh /path/to/Legacy.pkg \
  --dest <repo>/<vendor-cache>/<Vendor>

<toolkit>/bin/blueprint-to-recipe.sh \
  --blueprint <repo>/<vendor-cache>/<Vendor>/<App>/blueprint.conf \
  --out <repo>/recipes/<Vendor>/<App> \
  --vendor <Vendor> --vendor-cache <vendor-cache>
```

`sudo` is not advisory. `pkgutil` extracts as the invoking user, so without it
ownership is lost and the rebuilt package installs files owned by you. The tool
refuses rather than producing a quietly-broken package; `--allow-unprivileged`
proceeds and reconstructs ownership from the BOM into a `chown` block instead,
which is strictly worse.

Use these templates directly only when adapting an existing extraction by hand.

## Before trusting the result

1. `pkgutil --files <identifier>` on the original, against `find payload -type f`
2. Read any extracted scripts — they often reference paths, receipts, or versions
    that no longer hold
3. `<toolkit>/bin/autopkg-preflight.py --app <recipe dir>`
4. `autopkg run ./<App>.pkg.recipe.yaml`
5. **Run `pkg-compare.sh` validation:**
   ```bash
   ./bin/pkg-compare.sh \
     --old-pkg /path/to/original.pkg \
     --new-pkg /path/to/rebuilt.pkg \
     --work-dir /tmp/pkg-compare-<app>
   ```
   This compares file inventory, permissions (from BOM), scripts, and metadata.
   Exit code 0 = all checks pass. See [`specs/pkg-compare/01-pkg-compare.md`](../../specs/pkg-compare/01-pkg-compare.md) (Interpretation) for details.
6. Install on a test Mac and compare receipts against the original

## Expected lint findings

None once the recipe is filled in. `NO_CODE_SIGNATURE_REQUIRED` satisfies `CSV-001`
and `CSV-005`, and the pinned `version` Input in the download recipe satisfies
`VER-001`. See KI-2 in `docs/known-issues.md` for the rule history.

Do not edit a recipe to silence a finding.

## Known gaps

- **Multi-component distribution packages are not supported.** `pkg-reverse.sh`
  detects and refuses them. Their `Distribution` XML carries install choices,
  requirements, and often JavaScript that `PkgCreator` cannot reproduce, so a
  generated recipe would silently drop them.
- **The output is unsigned** regardless of the input.
- **Version is pinned.** Nothing detects a new one.
- **The template and `blueprint-to-recipe.sh` describe the same structure in two
  places.** The generator emits its recipes from inline heredocs rather than
  filling this template, so the two can drift. Unresolved; see the note in
  `../README.md`.
