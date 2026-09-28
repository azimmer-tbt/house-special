---
name: compare-packages
description: Check that a rebuilt package is equivalent to the original it replaces (inventory, permissions, scripts) with bin/pkg-compare.sh. Use when someone says "compare the packages", "does the rebuild match", "diff the old and new pkg", "validate against the original", or after autopkg run builds a Pattern 6 package.
---
# Compare Packages

## When to use

Step 8 of [`specs/method/00-methodology.md`](../../specs/method/00-methodology.md): after
`autopkg run` produces a package that replaces an existing one (Patterns 6, 7, and
any rebuild of an org-built package). The original is the requirements spec
(methodology lesson 20).

## Inputs

- **Original**: the package in use today (from the management server, the customer's
  `input/`, or the durable store in `files_to_copy.yaml`).
- **Rebuilt**: `~/Library/AutoPkg/Cache/<pkg identifier>/<pkgname>.pkg`.
- Both must be flat packages (component, or a distribution with exactly one component).

## Steps

1. Run the comparison (no sudo needed: ownership is read from each BOM):
   ```bash
   bin/pkg-compare.sh --old-pkg /path/to/original.pkg \
     --new-pkg ~/Library/AutoPkg/Cache/com.acmefruit.autopkg.pkg.<App>/Acme_<App>.pkg \
     [--work-dir /tmp/pkg-compare-<App>]
   ```
2. Read the exit code:

   | Code | Meaning | Usual fix |
   |---|---|---|
   | 0 | Equivalent | Go on to the install test |
   | 1 | File inventory mismatch (or symlink target differs) | Missing/extra file, hidden file, wrong `Copier` glob |
   | 2 | Permission mismatch (mode/owner/group from BOM) | Add or correct a `chown` entry (lesson 17) |
   | 3 | Script mismatch (set, bytes or mode) | Dropped or non-executable script |
   | 5 | Expansion failure | Bundle-style pkg, corrupt xar, or a distribution with 0 or >1 components |
   | 4 | Reserved — never emitted | — |

   All sections always run; the exit is the first failing group in order 1, 2, 3.
3. **Metadata is informational only.** Identifier, version, install location and
   signature differences never change the exit code. Expected cases: an identifier
   `PkgCreator` rejects (lesson 18), a pinned version, "unsigned" for a rebuild.
   Record the reason in the app's README.
4. Fix and re-run until 0, then present results and wait for sign-off
   ([rule 11](../rules/11-per-package-signoff.md)).

## Outputs

Per-section PASS/FAIL with the differing paths, and a metadata table that marks
differing fields. A tool-created work dir is removed on success and kept (path printed)
on failure; a `--work-dir` you pass is always kept.

## Verify

Exit 0, and the metadata differences each have a stated reason in the README.
Then a real install test (`sudo installer -pkg … -target /`) on a test Mac.

## Pitfalls

- **KI-4:** the permission diff parses `lsbom` output with default whitespace
  splitting, so **directory entries and paths containing spaces are silently not
  compared** (AC-5.2 not yet met). A permissions PASS does not cover those —
  spot-check them with `lsbom -p MUGf <Bom>` on both packages.
- **KI-5:** `--help` still lists exit 4 "metadata mismatch"; ignore it. Exit 5 for a
  multi-component distribution or an invalid xar checksum gives no hint — try
  `xar -xf` on the original (lesson 21).
- Never read ownership from an unprivileged extraction: it's always you (AIP-1).
- A rebuild that installs to `/Applications` and data-volume paths may be rejected
  by the installer even if it compares clean (lesson 19).

## References

- [`specs/pkg-compare/01-pkg-compare.md`](../../specs/pkg-compare/01-pkg-compare.md)
- [`docs/known-issues.md`](../../docs/known-issues.md) (KI-4, KI-5)
- [`reference/methodology.md`](../../reference/methodology.md) (lessons 17–21)
- [`docs/patterns.md`](../../docs/patterns.md)
