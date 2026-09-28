# pkg-compare: Original vs Rebuilt Package Equivalence

**Status:** Draft · **Requires:** `00-methodology.md` (Step 8) · **Implementation:** `lib/python/recipekit/pkg_compare.py` and `pkg.py`; `bin/pkg-compare.sh` is the front end · **Tests:** `tests/pkg_compare_spec.sh`, `tests/python/test_pkg.py`

## Purpose
Confirm that a package rebuilt by `PkgCreator` deploys the same content as the
package it replaces: the same paths, ownership, modes and scripts. This is the cheap,
repeatable check before an install test. It does not replace installing the package.

## FR-1: Interface
`pkg-compare.sh --old-pkg <original.pkg> --new-pkg <rebuilt.pkg> [--work-dir <dir>]`, plus `-h|--help`.
- AC-1.1 [TESTABLE] Missing `--old-pkg` or `--new-pkg`, or a flag without its value, gives a non-zero exit and an error.
- AC-1.2 [STRUCTURAL] No root is needed. Ownership comes from each package's BOM, not from extracted files.
- AC-1.3 [STRUCTURAL] Standalone. It needs no recipe repo, vendor cache or toolkit config, beyond sourcing `lib/toolkit-common.sh`.

## FR-2: Expansion
Each package is expanded with `pkgutil --expand-full`. Component kind: `PackageInfo`
at the root. Distribution kind: exactly one `*.pkg` component directory.
- AC-2.1 [TESTABLE] A distribution with 0 or more than 1 component exits 5 and lists the components.
- AC-2.2 [TESTABLE] An expansion failure (bundle-style package, corrupt xar or invalid checksum) exits 5.

## FR-3: Metadata (informational)
Reports identifier, version, install-location (default `/`) and signature status
(`pkgutil --check-signature`) for both packages, and marks each field that differs.
- AC-3.1 [TESTABLE] Metadata differences never change the exit code.
- Guidance: an identifier difference is expected when a legacy identifier isn't valid for `PkgCreator` (see methodology lesson 18). A version difference is expected when the recipe pins it. "Unsigned" is expected for rebuilt packages.

## FR-4: File inventory
Compares relative files, directories and symlinks (with their targets) between the two payload trees.
- AC-4.1 [TESTABLE] Any path present in only one package, or a symlink whose target differs, is an inventory mismatch.

## FR-5: Permissions
For every path in both BOMs (files, directories, symlinks and the payload root), compares
mode, uid and gid, read with `lsbom -p mugsfl` (numeric, tab-separated). A symlink's own
mode is ignored (macOS doesn't use it); its owner is compared. A difference prints as
`<path>` then `old: <mode>:<uid>:<gid>  new: …`, the mode symbolic (`-rw-r--r--:0:0`).
A package without a readable Bom prints `[SKIP] permissions` and doesn't fail.
- AC-5.1 [TESTABLE] Any difference is a permission mismatch. **Enforced via:** `test_pkg.py` `test_compare_exit_codes`.
- AC-5.2 [TESTABLE] Paths containing spaces, and directory entries, are compared (KI-4, fixed 2026-09-27). **Enforced via:** `tests/pkg_compare_spec.sh` "AC-5.2"; `test_pkg.py` `CompareLogicTest`.

## FR-6: Scripts
Compares the script file sets. For matching names it compares bytes (`diff -q`) and mode.
- AC-6.1 [TESTABLE] Scripts present on one side only, different content, or a different mode is a script mismatch. An empty `Scripts/` counts as "no scripts".

## FR-7: Exit codes and cleanup
All sections always run. Exit status: `0` if equivalent. Otherwise the first failing
group in this order: `1` inventory, `2` permissions, `3` scripts. Expansion failure
gives `5`. Code `4` is reserved and not emitted.
- AC-7.1 [TESTABLE] A work dir created by the tool is removed on success and kept (and its path printed) on failure. A user-supplied `--work-dir` is always kept.

## Interpretation
- **All PASS:** content-equivalent. Go on to the install test.
- **Only metadata differs:** acceptable. Record the reason in the app README.
- **Inventory, permission or script FAIL:** the rebuild is wrong. Fix the recipe (usually a `chown` entry, a dropped script or a hidden file) and re-run.

## Architecture-Incompatible Patterns
- AIP-1: Reading ownership from an unprivileged extraction. It is always the invoking user.
- AIP-2: Making metadata affect the exit code.

## Version History
| Version | Date | Change |
|---|---|---|
| 1.1 | 2026-09-27 | Ported to Python (`recipekit.pkg_compare`), same command, flags, exit codes and output (checked side by side on five real package pairs). KI-4 fixed: BOM read numerically and tab-separated, so directories and spaced paths are compared; the pass line reads "all shared paths match". Scripts compared byte for byte. |
