# Known Issues

Toolkit bugs and gaps that are known but not yet fixed. Each was reproduced or
verified against the current tree unless marked *(reported)*. Numbering is stable
(KI-1 was fixed and is kept only as a reference); specs cite these IDs.

- **KI-1 (fixed): bash 4 syntax in scripts that must run on stock macOS bash 3.2.**
  `recipe-linter.sh --pair-check`, `scan-placeholders.sh` and
  `rr-rename-postprocess.sh` (since folded into `rr-batch.sh`) used associative arrays. They now use parallel
  indexed arrays, and the test suite runs under `/bin/bash` 3.2.
- **KI-2 (partly fixed): `config/checks.yaml` false positives on vendor-drop, rebuilt and faux-DMG recipes.**
  - Fixed: VER-001, CSV-001 and CSV-005 are now `exists_any` rules. They accept a
    pinned `Input.version`, a declared `Input.NO_CODE_SIGNATURE_REQUIRED: true`, and
    `Input.teamid: UNSIGNED_NO_TEAMID` / `expected_authority_names` respectively
    (`tests/python/test_lint.py`). Since 2026-09-27 a version
    pinned only in `.overrides` no longer counts, because AutoPkg never reads that
    file, and the ad-hoc exemption moved from `.overrides` to `Input`.
  - Fixed: SRC-002 matched any `x.y.z` in `Process`, including the certificate OIDs
    in every requirement string; it now inspects `url:` lines only.
  - Open: SRC-003's message tells you to `curl -LI` a URL that doesn't exist for
    vendor-drop recipes; give it a `Copier|file://` alternative.
  - Open: a conditional primitive (`requires_when`: "if vendor-drop then
    `Input.version` required") is still undesigned (see also KI-13).
- **KI-3 (partly fixed 2026-09-27): `exists_any` edge cases.**
  - (a) For `source: "related-file"` conditions the engine reads `related_key`, not `key`. A condition written the way the design doc and the EXA-001 fixture write it (`key: "Process"`) silently never matches. The test passes only because condition A short-circuits first.
  - (b) *(fixed)* The bash engine joined conditions with `;`, so a `pattern` containing `;` broke parsing. The Python linter reads conditions as a YAML list.
  - (c) *(obsolete)* The colliding `AC-2.6.x` IDs were in the bash tests, now replaced by `tests/python/test_lint.py`.
  - (a) is kept deliberately while the linter matches the bash engine's behaviour; fixing it changes what existing rules mean, so it needs its own change.
- **KI-4 (fixed 2026-09-27): `lsbom -p MUGsf` output was parsed as if it were numeric
  and whitespace-delimited.** The real output is tab-separated, with a symbolic mode
  and owner *names*, so the "all-self" check could never be true, directory rows and
  spaced paths fell out of the chown rollup and the permission diff, and the fixtures
  used an invented format. Both tools are now Python (`recipekit.pkg`), read
  `lsbom -p mugsfl` (numeric, tab-separated), compare directories and spaced paths,
  and write a parent-first rollup with numeric `uid:gid`; tests build real packages
  with `pkgbuild` (`tests/python/test_pkg.py`).
- **KI-5: `pkg-compare.sh` exit codes and messages.** (Header now documents exit 4 as reserved.)
  - The header and the process doc list exit 4 "metadata mismatch", which is never emitted (metadata is informational).
  - Multi-component distributions and packages with invalid xar checksums both exit 5 with no hint to try `xar -xf` (see methodology lesson 21).
- **KI-6 (fixed 2026-09-27): `classify-recipe.sh` defects.** It died silently under
  `set -e` (a), read `url:` literally instead of resolving `%DOWNLOAD_URL%` (b),
  checked ridealong before payloadless (c), and matched processors anywhere in the
  file, comments included (d). It matched 11 of 26 examples' claims. It is now a
  front end for `recipekit.classify`, built on the recipe model, and matches 26 of 26
  (`tests/python/test_classify.py`).
- **KI-7 (fixed 2026-09-27): `normalize-vendor-cache.sh` was destructive and didn't
  check types.** It renamed the newest file whatever its type (a text sidecar
  became `payload.zip`), could rename a protected `scripts.zip` into place, and
  `rm -f`'d every other file once the canonical one existed. The Python port
  (`recipekit.vendor_cache`) renames and prunes only files of the canonical
  name's type, never touches protected files, moves stale files aside to a
  `relocated/` folder instead of deleting them, and has `--dry-run`
  (`specs/vendor-cache/01-pre-scan-script.md`, `tests/python/test_vendor_cache.py`).
- **KI-8 (partly fixed 2026-09-27): Guardrail audit gaps.**
  - (a) *(fixed 2026-09-27)* `check_vendor_cache_path.py` only inspected `LOCAL_*_PATH`, so recipes on `DOWNLOAD_URL: file://%VENDOR_CACHE_ROOT%/…` passed without being checked. It now resolves `file://` values in `Input` and in `URLDownloader`'s `url` through the recipe model, and reports SKIP when the vendor cache isn't on the machine.
  - (b) Still open: `check_cert_chain_complete.py` hardcodes `Developer ID Certification Authority` and false-fails valid Mac App Store–style chains (methodology lesson 6).
  - (c) *(fixed 2026-09-27)* `check_variables_declared.py`'s Input-block regex stopped at the first blank line, so later keys were reported undeclared. It now parses the YAML (KI-30).
- **KI-9: Documentation and templates teach behavior that is wrong.**
  - (a) "Distribution packages crash `PkgCopier`; use `Copier`" appears in `templates/README.md`, `docs/updating-existing-recipes.md` (including its "list index out of range" troubleshooting entry), `docs/usage-guide.md` and `specs/recipe-linter/04-recipe-comments.md` (the Pattern 4a comment templates). `templates/pattern-4b-distribution-package/` rests on the same claim, and its own example uses `PkgCopier`. See methodology lesson 14.
  - (c) The Pattern 6 and 7 template READMEs say "unsigned by construction" (methodology lesson 16). Add a `codesign` step to `specs/method/00-methodology.md` Step 2.
  - (d) The 6d template example points `pkgroot` at a directory that nothing creates (methodology lesson 18).
  - (e) `config/paths.yaml` says `vendor_cache: build/vendor_cache/`, but recipes and specs use `/tmp/autopkg/vendor_cache`.
  - (f) `docs/updating-existing-recipes.md` teaches manual `pkgutil | gzip | cpio` pipelines instead of `sudo bin/pkg-reverse.sh`.
- **KI-10 (fixed): Undeclared PyYAML dependency.** Tools called whatever `python3`
  was first on PATH; Apple's `/usr/bin/python3` has no PyYAML, so running a `.py`
  directly failed. Python tools now run AutoPkg's bundled interpreter
  (`/usr/local/autopkg/python`, which always has PyYAML): `.py` shebangs point at it,
  shell scripts call it via `tk_python`, and `AUTOPKG_TOOLKIT_PYTHON` overrides it
  (`tests/toolkit_python_spec.sh`, `tests/kit_hygiene_spec.sh`).
- **KI-11: Test coverage gaps.**
  - No signed flat-pkg fixture yet (formerly SIGNED-001), so AC-06.1 and AC-06.2 are untested. Plan: download a small, version-pinned signed `.pkg` from an open-source release in `BeforeAll`, and skip when offline. Confirm the candidate really is a signed flat package before pinning it.
  - `normalize-vendor-cache.sh` and `sync-vendor-cache.sh` are covered by `tests/python/test_vendor_cache.py` (since 2026-09-27), `pkg-compare.sh` by `tests/pkg_compare_spec.sh`. (The guardrail audits and `bin/autopkg-preflight.py` now have tests: `tests/python/test_audits.py`, `tests/python/test_repo.py` and `tests/guardrail_audits_spec.sh` give every audit a failing and a passing fixture.)
- **KI-12 (fixed 2026-09-27): Unspecified shipped components.** `bin/sync-vendor-cache.sh`
  had no spec; it now has `specs/vendor-cache/03-sync.md`.
- **KI-13 (fixed): PKG-002 ignored the packaging processor.** It demanded the org
  prefix in every pkg recipe, so vendor copies (PkgCopier/Copier — Patterns 4a, 4b,
  5) failed, and the 4b example "passed" only by wrongly prefixing a vendor package.
  PKG-002 is now an `exists_any` rule: the pkgname carries the prefix, *or* the recipe
  has no PkgCreator. `exists_any` conditions gained `!` negation for this
  (`specs/recipe-linter/01-rule-definitions.md` §2.7).
- **KI-14 (fixed 2026-09-27): Two pattern-letter schemes.** The classifier's generic
  output letters didn't match `docs/patterns.md`. It now reports the per-pattern
  labels.
- **KI-15 (fixed 2026-09-27): `clues.yaml` keys that `analyze-package.sh` ignored.**
  `vendor_team_ids`, `non_reverse_domain_pattern` and the identifier half of
  `org_codes` weren't used, and `unusual_install_locations` was compared with the
  install location only. The Python port (`recipekit.analyze_package`) uses them
  all: a listed signing team ID is a strong vendor signal, an org code in the
  identifier and the legacy identifier pattern are medium custom signals, and
  unusual locations match payload paths too. The org's own identifier namespace
  counts as in-house. The port also reads distribution packages through their
  components (the bash version saw an empty identifier and called every signed
  vendor distribution a custom build) and exits 2 on a missing or non-package file
  (`tests/python/test_analyze_package.py`).
- **KI-16 (fixed): `analyze-package.sh` never analysed the payload.** It expanded
  with `pkgutil --expand`, which leaves `Payload` as a cpio archive, so file counts
  and `.app` detection were always empty. Its reverse-domain check also accepted
  only lowercase `com`/`org`/`net` identifiers, so `com.acmefruit.pkg.Moonlight` or
  `io.corkscrews.Fruit` counted as "custom builds". Now `--expand-full` and a
  case-tolerant check (`tests/analyze_package_spec.sh`).
- **KI-17 (fixed): `analyze-materials.sh` matching noise.** A version number alone
  made every versioned file a candidate for every target; hyphenated recipe names
  didn't match spaced filenames; symlinked material was skipped. Fixed
  (`tests/analyze_materials_spec.sh`).
- **KI-18 (fixed): five front ends were not executable** (`analyze-materials.sh`,
  `analyze-package.sh`, `capture-perms.sh`, `classify-recipe.sh`,
  `inspect-archive.sh`), so `bin/<tool>` failed with "Permission denied".
  `tests/kit_hygiene_spec.sh` now guards the exec bit.
- **KI-19 (fixed): inspection tool output bugs.** `capture-perms.sh` assigned to
  bash's read-only `UID`, so it aborted before listing files; `inspect-app.sh` and
  `inspect-dmg.sh` repeated architectures (`x86_64,x86_64,arm64,…`) and printed
  literal quotes in `'(not set)'`; `analyze-materials.sh --output json` mixed status
  lines into stdout. Sample outputs in `specs/analysis/*/artifacts/` were regenerated
  from real runs.
- **KI-20 (fixed): manifests silently empty.** `generate-manifest.sh` and
  `make-dist.sh` piped filenames through plain `xargs`, which aborts on a quote
  ("unterminated quote") and left an empty `manifest.sha256`. Both now use
  NUL-delimited pipelines; `make-dist.sh` fails if the manifest doesn't cover
  every shipped file, and no longer `chmod +x`es the dist (which had hidden KI-18).
- **KI-21 (fixed 2026-09-27): `yq` was a hidden dependency.** `normalize-vendor-cache.sh`,
  `sync-vendor-cache.sh` and `analyze-screenshot.sh` needed `yq` v4. All three now
  read YAML with AutoPkg's Python and PyYAML.
- **KI-22 (fixed): `classify-recipe.sh` took `--org=<file>` only.** It now also
  accepts `--org <file>`, like every other front end.

- **KI-23 (fixed): lint rules matched text inside YAML comments.** `Process` was
  read as raw text, so a comment saying "never use AppPkgCreator" failed PKG-001 /
  PRO-001, and a commented-out processor could satisfy a rule. Whole-line comments
  are now dropped before rules are applied.

Found while writing the specs for tools that had none (2026-09-27). Each spec lists
the details as "Not yet met" acceptance criteria and open questions.

- **KI-24 (fixed 2026-09-27): `clear-autopkg-cache.sh` could empty the whole cache without `--all`.** An
  empty identifier (`""`, e.g. an unset variable) resolves to the cache root, which
  the safety check allows, so `rm -rf` deletes all of it. `.` passes the checks too.
  Refused identifiers and failed deletions still exit 0. Fixed: empty and `.`
  identifiers are refused, only entries strictly inside the root can be removed, and
  any refusal or failed removal exits 1 (`tests/clear_autopkg_cache_spec.sh`). Still
  open: `HOME` aims the script, and a symlinked cache root is followed. Spec:
  [`specs/clear-autopkg-cache/`](../specs/clear-autopkg-cache/01-clear-autopkg-cache.md).
- **KI-25 (partly fixed 2026-09-27): `check-sanitized.sh` gaps.** Fixed: placeholder home names matched as prefixes, so
  a real `/Users/<name>` that starts with `me`, `user`, `admin`, `you`, `name` or
  `example` was not reported; names now match whole. Still open: a missing `--path`
  scans nothing and passes. An invalid
  denylist regex is silently ignored. `--staged` reads the working copy, not the
  staged content. Serial, sync-folder and installer-extension checks are narrower
  than intended. Spec: [`specs/check-sanitized/`](../specs/check-sanitized/01-check-sanitized.md).
- **KI-26: `check-doc-links.sh` gaps.** A missing file argument passes; `~~~` fences,
  non-http URL schemes and root-relative (`/…`) links aren't handled. Spec:
  [`specs/check-doc-links/`](../specs/check-doc-links/01-check-doc-links.md).
- **KI-27 (partly fixed 2026-09-27): `run-recipes.sh` stopped at the first app without `.overrides`.** Under
  `set -u`, bash 3.2 treats an empty `"${array[@]}"` as unbound, so the run dies with
  no summary, and the last `.overrides` line was dropped without a trailing newline.
  Both fixed (`tests/run_recipes_spec.sh`). Still open: a missing `autopkg` exits 1
  like an app failure; unknown options become the filter. Spec:
  [`specs/run-recipes/`](../specs/run-recipes/01-run-recipes.md).
- **KI-28 (partly fixed 2026-09-27): `scan-placeholders.sh` false positives.** Fixed:
  `UNSIGNED_NO_TEAMID` counted as a placeholder, so a repo with any ad-hoc-signed app
  never scanned clean; and the certificate-chain check flagged recipes that verify with
  `requirement:` (the stronger form). The chain check now applies only to
  `expected_authority_names` lists (`tests/scan_placeholders_spec.sh`). Still open:
  text in YAML comments counts; only the last chain problem per app is reported;
  unknown options become the filter. Spec:
  [`specs/scan-placeholders/`](../specs/scan-placeholders/01-scan-placeholders.md).
- **KI-29: `analyze-screenshot.sh` trusts its config.** The local-only rule is
  documented, not enforced: it sends to any configured endpoint. The API key is on
  `curl`'s command line, there is no timeout, screenshots over about 750 KB exceed
  the argument limit, and prompt text with quotes breaks the request. Spec:
  [`specs/analyze-screenshot/`](../specs/analyze-screenshot/01-analyze-screenshot.md).
- **KI-30 (fixed 2026-09-27): guardrail audits failed correct recipes.** Beyond KI-8: the cert-chain audit
  fails every `requirement:`-based verifier (6 Acme apps), the unsigned audit needs
  one literal phrase, the variables audit flags processor-set variables such as
  `url` from `URLTextSearcher`. So `bin/autopkg-preflight.py --repo customer/acme/output`
  failed on recipes that build. Fixed: those three audits now parse the YAML and
  know which processors set which variables; preflight passes on Acme, and
  `tests/guardrail_audits_spec.sh` covers it. The fix also exposed two Acme recipes
  that set `version` only in `.overrides` (now declared in `Input`). The rest is
  fixed too: every audit now reads recipes through the recipe model, and
  preflight uses the shared repo resolution (`lib/python/recipekit/repo.py`) and
  the model's pairs instead of pairing by sort order. Specs:
  [`specs/guardrail-audits/`](../specs/guardrail-audits/00-constitution.md).
- **KI-31: `make-dist.sh` hides failures.** Copy and `tar` failures don't fail the
  build; untracked files inside shipped folders ship; the tarball is always
  `house-special.tar.gz`; a failed build leaves a partial output folder; it computes
  checksums itself instead of using `generate-manifest.sh`. Spec:
  [`specs/make-dist/`](../specs/make-dist/01-make-dist.md).
- **KI-32 (fixed 2026-09-27): `rr-batch.sh` never filed a recipe.** It looked for
  `AppName_download.recipe` under `~/Library/AutoPkg/RecipeRobotOutput/<AppName>/`;
  Recipe Robot writes `<Bundle>.<type>.recipe.yaml` under
  `~/Library/AutoPkg/Recipe Robot Output/<Developer>/` (or its configured folder).
  Under bash 3.2 it also stopped at the first app unless `-e` or `-v` was given
  (an empty array under `set -u`), which is why `tests/batch_spec.sh` always
  warned. The Python port reads the paths Recipe Robot prints and files the
  recipes under `<Vendor>/<AppName>/` with names and identifiers from the CSV,
  absorbing `rr-rename-postprocess.sh` (which read a different CSV). Checked live
  against Recipe Robot 2.5.0 ([`specs/rr-batch/`](../specs/rr-batch/01-batch-definitions.md)).
- **KI-33 (fixed 2026-09-27): the inspect tools' JSON and parsing.** `inspect-app.sh
  --output json` crashed on every signed app; `inspect-dmg.sh` split app names at
  spaces, turned each app's fields into separate "apps" in JSON, and failed silently
  on some DMGs (Moonlight); `inspect-archive.sh`'s JSON crashed, zip names with
  spaces broke its listing, and it always printed "truncated". All three now run on
  Python (`recipekit.inspect_tools`; [`specs/analysis/inspect-tools/`](../specs/analysis/inspect-tools/01-inspect-tools.md)).
