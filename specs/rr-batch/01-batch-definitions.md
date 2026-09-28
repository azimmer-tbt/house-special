# Batch Recipe Creator — Feature Definitions

**Status:** Draft
**Date:** 2026-08-02
**Requires:** `00-constitution.md`

---

## Purpose

Define the command-line interface, recipe generation workflow, output
normalization, directory layout conventions, and relationship to the Recipe
Robot linter for the batch recipe creator (`rr-batch.sh`). This spec provides
enough detail for an implementer to audit the existing `rr-batch.sh` against
these requirements and bring it into conformance.

### Normative vs. Informative Content

- **Normative (MUST/MUST NOT):** CLI flags and their semantics (§1), input file
  format and validation (§2), run lifecycle (§3), output directory layout (§5),
  logging requirements (§6), and all acceptance criteria. These define what a
  conforming implementation does.

- **Informative (reference implementation):** The specific path to Recipe Robot
  (`/Applications/Recipe Robot.app/Contents/Resources/scripts/recipe-robot`),
  default log directory names, the specific example CSV content, and the
  concrete normalization patterns. A conforming implementation may use different
  paths and defaults as long as the normative contracts are satisfied.

### Classification Key

- **[TESTABLE]** — Observable and automatable. Enforcement mechanism stated.
- **[STRUCTURAL]** — Enforced by schema, layout, or data model constraint.
- **[ADVISORY]** — Review judgment. Reserved for genuine non-checkables. A
  hardened spec has very few.

---

## 1. Command-Line Interface

### FR-1 — CLI Argument Parsing

[STRUCTURAL]

The batcher accepts a set of flags and positional-style options for batch
recipe generation. The implementation must parse arguments using portable Bash
parameter expansion (no external argument-parsing libraries).

**Flags:**

| Flag | Long Form | Argument | Required | Description |
|------|-----------|----------|----------|-------------|
| `-i` | `--input` | Path | Yes | Input CSV file with 4 columns: Status, Vendor, AppName, URL |
| `--log-dir` | — | Path | Yes | Directory for run logs (a timestamped subdirectory is created inside) |
| `-o` | `--output-dir` | Path | No | Base output directory for generated recipes; defaults to current working directory |
| `-e` | `--ignore-existing` | None | No | Pass `--ignore-existing` to Recipe Robot to skip community recipe lookups |
| `-l` | `--lint` | None | No | Run the linter (`bin/recipe-linter.sh`) on generated recipes after batch completion |
| `--specs` | — | Path | No | Path to linter checks.yaml; default is `config/checks.yaml`; only meaningful with `--lint` |
| `--vendor` | — | String | No | Vendor name override — if set, overrides the Vendor column from the CSV for all entries; if unset, the Vendor column from the CSV is used |
| `-v` | `--verbose` | None | No | Pass `--verbose` to Recipe Robot |
| `-h` | `--help` | None | No | Print usage and exit |

**Acceptance Criteria:**

- **AC-1.1:** [STRUCTURAL] All flags listed in the table above are recognized.
  Unrecognized flags cause exit code 2 with a usage message. **Enforced via:**
  automated test — invoke with `--bogus-flag`; assert exit 2; assert usage shown.

- **AC-1.2:** [TESTABLE] `-i`/`--input` and `--log-dir` are required. If
  either is missing, the tool exits with code 2 and prints usage. **Enforced
  via:** automated test — invoke with no arguments; assert exit 2 and usage;
  invoke with only `-i file.csv`; assert exit 2; invoke with only `--log-dir /tmp`;
  assert exit 2.

- **AC-1.3:** [TESTABLE] `-o`/`--output-dir` defaults to the current working
  directory when not provided. **Enforced via:** automated test — invoke with
  required args but no `-o`; assert output appears in CWD.

- **AC-1.4:** [TESTABLE] `-h`/`--help` prints usage and exits 0, regardless of
  other flags. **Enforced via:** automated test — invoke `--help`; assert exit 0.

- **AC-1.5:** [STRUCTURAL] Flag ordering is flexible — long and short forms can
  be mixed. **Enforced via:** automated test — test `-i file.csv --log-dir /tmp`
  and `--log-dir /tmp -i file.csv` produce identical behavior.

- **AC-1.6:** [TESTABLE] `--vendor` overrides the Vendor column from the CSV for
  all entries. When provided, the CSV vendor column is ignored and a warning is
  emitted. **Enforced via:** automated test — invoke with `--vendor MicrosoftCorporation`
  and a 4-column CSV with varying vendor values; assert all recipes placed under
  `MicrosoftCorporation/`.

- **AC-1.7:** [TESTABLE] `--lint` runs the linter on all generated recipe files
  after batch generation completes. If any linter rule fails, the batch is
  reported with exit code 1 and a message indicating lint failure. **Enforced
  via:** automated test — invoke with `--lint` on known input; assert linter is
  invoked; assert batch failure if linter finds errors.

---

## 2. Input File Format and Validation

### FR-2 — Input CSV Structure

[STRUCTURAL]

The input is a CSV file with one app per line. The format is fixed at 4 columns
with the following order:

| Column | Header | Required | Description |
|--------|--------|----------|-------------|
| 1 | Status | Yes | Controls whether the entry is processed (see status semantics below) |
| 2 | Vendor | Yes | Vendor name — maps to directory hierarchy `<output>/recipes/<Vendor>/<AppName>/` |
| 3 | AppName | Yes | Human-readable app name — maps to `Input.NAME` in the recipe |
| 4 | URL | Yes | Download URL or local file path. Passed directly to Recipe Robot's `--url` flag |

**Example CSV:**
```csv
# Status,Vendor,AppName,URL
"TEST","microsoft","Microsoft Teams","https://office.com/download/teams.dmg"
"DONE","microsoft","Microsoft Edge","https://office.com/download/edge.dmg"
"","slack","Slack","https://slack.com/downloads/mac"
"SKIP","adobe","Adobe Reader","https://adobe.com/reader.dmg"
```

### Status Column Semantics

| Status | Meaning | Action |
|--------|---------|--------|
| `TEST` | Recipe exists but not yet approved | Process ONLY if output directory doesn't already exist for this app |
| `DONE` | Already accepted and in-repo | Skip entirely (count as SKIP) |
| `SKIP` | Known to fail (files not available online) | Skip with log note |
| *blank* | New recipe to generate | Always process |
| *other* | Unrecognized status | Skip with warning, count as SKIP |

### Parsing Rules

- Fields are comma-separated with optional surrounding double quotes.
- Leading/trailing whitespace around fields is stripped.
- Blank lines and lines starting with `#` are ignored.
- Smart quotes (Unicode curly quotes `\u201C`, `\u201D`, `\u2018`, `\u2019`)
  are rejected with error.

### Acceptance Criteria

- **AC-2.1:** [STRUCTURAL] The tool parses exactly 4 columns: Status, Vendor,
  AppName, URL. A line with fewer or more than 4 columns is treated as
  malformed. **Enforced via:** automated test — CSV with 4-column entries;
  assert correctly parsed; CSV with a line having 3 or 5 columns; assert
  malformed line detected.

- **AC-2.2:** [TESTABLE] Blank lines and `#` comment lines are correctly
  ignored. **Enforced via:** automated test — CSV with blank lines, comments,
  and data lines; assert only data lines are processed.

- **AC-2.3:** [TESTABLE] Smart quotes anywhere in the input file are detected
  and cause exit code 2 with an error message identifying the issue. **Enforced
  via:** automated test — CSV with smart quotes; assert exit 2; assert error
  message mentions smart quotes.

- **AC-2.4:** [TESTABLE] A line with other than 4 fields (e.g., 1, 2, 3, or 5+
  columns) is reported as a malformed line and skipped. The malformed line is
  counted in the total and recorded as a failure. **Enforced via:** automated
  test — CSV with one malformed line among valid entries; assert malformed line
  is failed; assert valid entries are processed.

- **AC-2.5:** [TESTABLE] Empty fields (e.g., `,"MyApp",` or `"URL",,"App"`) are
  detected and treated as malformed (empty Status, Vendor, AppName, or URL
  fields all count as malformed). **Enforced via:** automated test — CSV with
  empty URL; assert fail; CSV with empty AppName; assert fail; CSV with empty
  Status; assert fail.

- **AC-2.6:** [TESTABLE] The input file is validated before any recipe
  generation begins — if the file does not exist, the tool exits with code 2
  before running Recipe Robot. **Enforced via:** automated test — specify
  non-existent input file; assert exit 2; assert no Recipe Robot invocation.

- **AC-2.7:** [TESTABLE] URL validation: the URL field accepts any value valid
  for Recipe Robot's `--url` flag. The tool passes the URL field directly
  without validation. Acceptable values include:
  - `http://` and `https://` URLs (remote downloads)
  - Absolute file paths starting with `/` (local recipes)
  - Relative file paths starting with `../` or `./` (local recipes)
  Recipe Robot itself handles URL validation. **Enforced via:** automated test —
  CSV with HTTP URL, absolute path, and relative path; assert all are passed
  through to Recipe Robot without validation error.

- **AC-2.8:** [TESTABLE] Status column semantics are correctly applied:
  - `TEST` status: process if output directory does not exist for this app;
    skip if it does
  - `DONE` status: skip with log note indicating `DONE`
  - `SKIP` status: skip with log note indicating `SKIP`
  - blank status: always process
  - unrecognized status: skip with warning, counted as SKIP
  **Enforced via:** automated test — CSV with each status variant; assert
  correct processing/skip behavior for each.

---

## 3. Run Lifecycle

### FR-3 — Batch Run Phases

[STRUCTURAL]

A batch run proceeds through these phases in order:

```
  1. Pre-flight validation
     ├── Validate CLI arguments (FR-1)
     ├── Validate input file exists and is readable (FR-2)
     ├── Validate Recipe Robot binary is executable at expected path
     ├── Create log directory structure
     └── Create output directory structure

  2. Processing loop
     ├── For each entry in the input CSV:
     │   ├── Evaluate Status column
     │   │   ├── DONE/SKIP/unrecognized → skip entry, log reason
     │   │   ├── TEST → check if output dir exists for this app;
     │   │   │           if yes, skip; if no, proceed
     │   │   └── blank → always process
     │   ├── Create per-app log directory
     │   ├── Invoke Recipe Robot with appropriate arguments
     │   ├── Capture exit code and output
     │   ├── If success: normalize output files (FR-5)
     │   └── Record PASS/FAIL/SKIP in combined log
     └── [All entries processed]

  3. Post-processing
     ├── Optionally run linter on generated recipes (if --lint)
     ├── Print summary (pass/fail/total/skip counts, failed apps list)
     └── Exit with appropriate code
```

**Acceptance Criteria:**

- **AC-3.1:** [TESTABLE] Pre-flight failure (invalid args, missing input, or
  missing Recipe Robot binary) exits before any recipe generation. **Enforced
  via:** automated test — each pre-flight condition tested independently; assert
  no Recipe Robot invocation.

- **AC-3.2:** [TESTABLE] The processing loop continues after an individual
  failure. A single failing entry does not abort the batch. **Enforced via:**
  automated test — CSV with 3 entries where the middle one fails; assert all 3
  are attempted; assert PASS count >= 2.

- **AC-3.3:** [TESTABLE] The summary is printed to stdout and also recorded in
  the combined log file. **Enforced via:** automated test — capture stdout and
  read log file; assert both contain pass/fail/total counts.

- **AC-3.4:** [TESTABLE] All per-app log files are written to the timestamped
  run directory under `--log-dir`. **Enforced via:** automated test — check per-app
  log files exist at expected paths.

- **AC-3.5:** [TESTABLE] The status column filter is correctly applied during
  the processing loop:
  - `DONE` entries are skipped without invoking Recipe Robot
  - `SKIP` entries are skipped without invoking Recipe Robot
  - unrecognized status entries are skipped with a warning
  - `TEST` entries are skipped if the output directory already exists
  - `TEST` entries proceed if the output directory does not exist
  - blank status entries always proceed
  **Enforced via:** automated test — CSV with mixed statuses; assert Recipe Robot
  is invoked only for entries that pass the status filter.

---

### FR-4 — Recipe Robot Invocation

[STRUCTURAL]

The batcher invokes Recipe Robot as a subprocess for each entry. The exact
command must be:

```bash
"$RR_BIN" [global_flags] "$URL"
```

Where:
- `$RR_BIN` is the path to the Recipe Robot CLI script
  (`/Applications/Recipe Robot.app/Contents/Resources/scripts/recipe-robot`)
- `global_flags` are pass-through flags from the batcher's own CLI:  
  `--ignore-existing` (if `-e` set), `--verbose` (if `-v` set)
- `$URL` is the URL field from the CSV entry

The batcher does not modify Recipe Robot's arguments based on per-app
configuration — all flags are batch-wide.

**Acceptance Criteria:**

- **AC-4.1:** [TESTABLE] Recipe Robot is invoked with the correct URL and
  pass-through flags. **Enforced via:** automated test that wraps `recipe-robot`
  with a spy script; invoke batcher; assert spy received expected args.

- **AC-4.2:** [TESTABLE] Recipe Robot's stdout and stderr are captured to the
  per-app log file, not printed to the batcher's stdout. **Enforced via:**
  automated test — capture batcher stdout and check log file; assert stdout has
  no raw Recipe Robot output; assert log file contains it.

- **AC-4.3:** [TESTABLE] When Recipe Robot is not found or not executable, the
  batcher exits at pre-flight with code 2 and a clear error message. **Enforced
  via:** automated test — remove execute permission or point at non-existent
  path; assert exit 2.

---

## 4. Output Normalization

### FR-5 — Post-Generation Recipe Renaming and Relocation

[STRUCTURAL]

Recipe Robot (2.5.0, read from its code and checked live) writes each recipe as
`<RecipeCreateLocation>/<Developer>/<BundleName>.<type>.recipe`, plus `.yaml` when
its `RecipeFormat` is `yaml`. `RecipeCreateLocation` defaults to
`~/Library/AutoPkg/Recipe Robot Output`; the folder is the app's developer (or the
app name when unknown). It prints every path it writes on a line of its own after
`Generating <type> recipe...`. The batcher must:

1. **Discover** the recipes a run wrote by reading those paths from its output
   (ANSI colour codes stripped), so any output location and folder works.

2. **Keep** only `download` and `pkg` recipes in YAML. A plist recipe is reported
   with a pointer to `recipe-robot --config`; other types are reported and skipped.

3. **Relocate and rename** each to
   `<output-dir>/recipes/<VendorName>/<AppName>/<AppName>.<type>.recipe.yaml`,
   `VendorName` from the CSV (or `--vendor`) and `AppName` from the CSV.

4. **Rename inside** (replacing `rr-rename-postprocess.sh`, OQ-5): set
   - `Identifier` to `<identifier_prefix>.<type>.<AppName>` (org config), which
     also fixes Recipe Robot's `.pkg.download.` / `.pkg.pkg.` forms;
   - `ParentRecipe` (pkg) to `<identifier_prefix>.download.<AppName>`;
   - `Input` → `NAME` to `<AppName>`.
   Nothing else in the recipe changes.

**Acceptance Criteria:**

- **AC-5.1:** [TESTABLE] A reported `<Bundle>.download.recipe.yaml` becomes
  `<AppName>.download.recipe.yaml`; the same for `pkg` (AC-5.2).
- **AC-5.3:** [TESTABLE] Files are placed in `<output-dir>/recipes/<VendorName>/<AppName>/`,
  with `--vendor` overriding the CSV column.
- **AC-5.4 / AC-5.5:** [TESTABLE] Identifier, ParentRecipe and NAME are set from the
  org prefix and the CSV AppName, whatever Recipe Robot wrote.
- **AC-5.6:** [TESTABLE] Discovery works for any Recipe Robot output location.
- **AC-5.7:** [STRUCTURAL] Recipe Robot's own output is copied, never moved or deleted.
- **AC-5.8:** [TESTABLE] An existing target is not overwritten without `--force` (OQ-4).

**Enforced via:** `tests/python/test_rr_batch.py`; `tests/batch_spec.sh` (a fake
`recipe-robot` that writes and prints like 2.5.0); a live run on 2026-09-27 against
Recipe Robot 2.5.0 (Pearcleaner, Raspberry Pi Imager).

*(Before 2026-09-27 the batcher looked for `AppName_download.recipe` under
`~/Library/AutoPkg/RecipeRobotOutput/<AppName>/`, which Recipe Robot never writes,
so no recipe was ever filed; and under bash 3.2 it stopped at the first app when
neither `-e` nor `-v` was given.)*

---

## 5. Output Directory Layout

### FR-6 — Generated Recipe Directory Structure

[STRUCTURAL]

The batcher's output follows the upstream spec (§3.1) directory layout:

```
<output-dir>/
└── recipes/
    └── <VendorName>/
        └── <AppName>/
            ├── <AppName>.download.recipe.yaml
            └── <AppName>.pkg.recipe.yaml
```

Where:
- `<output-dir>` is the base output directory (`-o` flag or CWD)
- `<VendorName>` is PascalCase, no spaces (e.g., `MicrosoftCorporation`, `SmartsheetInc`)
- `<AppName>` is hyphenated if multi-word (e.g., `Microsoft-Teams`, `Microsoft-Edge-Browser`)
- No `.overrides` or other sidecar file is generated. `.overrides` is an optional,
  org-defined file (Standards §3.4), and upstream has no pipeline-metadata file
  (Standards §3.5). The app's `README.md` is written by hand afterwards.

**Acceptance Criteria:**

- **AC-6.1:** [TESTABLE] The directory structure matches the layout above.
  **Enforced via:** automated test — run batcher with known input; assert
  directory tree equals expected.

- **AC-6.2:** [TESTABLE] No `.overrides` file is created. The app folder exists
  even when normalization writes no recipe. **Enforced via:** automated test —
  run the batcher; assert the app folder exists and holds no `.overrides`.

- **AC-6.3:** Retired (2026-09-27). It required a generated `.autopkg_config`;
  upstream no longer defines that file.

- **AC-6.4:** [ADVISORY] A `scripts/` directory may be created alongside the
  recipe files if the download pattern requires postinstall scripts (Pattern 5
  vendor PKG or payloadless packages). This is at the operator's discretion.

- **AC-6.5:** [TESTABLE] The output directory tree is created before any recipe
  generation begins — not lazily per app. **Enforced via:** automated test —
  inspect file system after pre-flight but before processing.

---

## 6. Logging and Reporting

### FR-7 — Audit Trail

[STRUCTURAL]

The batcher produces a structured set of logs:

```
<log-dir>/<timestamp>/
├── rr-batch_<timestamp>.log          # Combined run log
├── <AppName>/
│   └── <AppName>_<timestamp>.log     # Per-app Recipe Robot output
└── ... (one per app)
```

The combined log records:
- Run header: invocation, input file, output dir, flags
- Per-entry: `[timestamp] RESULT:TYPE [AppName] URL [exit code] [status]`
  Where `RESULT` is PASS/FAIL/SKIP, `TYPE` describes the status filter reason
  (e.g., `DONE`, `TEST-existing`, `SKIP-status`, `unrecognized`), and `status`
  is the original value from the CSV Status column (or blank if empty).
- Run footer: total/pass/fail/skip counts, list of failed apps, combined log path

**Acceptance Criteria:**

- **AC-7.1:** [TESTABLE] The combined log contains all run header fields:
  invocation arguments, input file path, output directory, flags, timestamp.
  **Enforced via:** automated test — run batcher; parse log file; assert header
  fields present.

- **AC-7.2:** [TESTABLE] Each entry in the processing loop produces a START
  line and a result (PASS/FAIL/SKIP) line in the combined log, including the
  Status column value. **Enforced via:** automated test — CSV with 3 entries;
  assert 3 START lines; assert 3 result lines; assert each result line includes
  the original Status column value.

- **AC-7.3:** [TESTABLE] The run footer contains total/pass/fail/skip counts
  and, if any failures, a list of failed app names. **Enforced via:** automated
  test — CSV with mixed results including SKIP entries; assert footer has correct
  total/pass/fail/skip counts; assert failed names listed.

- **AC-7.4:** [TESTABLE] The summary printed to stdout matches the log footer.
  **Enforced via:** automated test — capture stdout and log footer; assert
  identical counts.

---

## 7. Relationship to the Linter

### FR-8 — Optional Post-Generation Linting

[STRUCTURAL]

When `--lint` is specified, the batcher runs the linter on each generated
recipe file after normalization is complete. This provides immediate feedback
if normalization did not produce linter-compliant output.

**Behavior:**

1. After all entries are processed and normalized, locate every generated
   `.recipe.yaml` file in the output directory.
2. Invoke `bin/recipe-linter.sh` (or the path specified via `--specs`) on
   the set of generated recipe files.
3. Capture the linter's exit code and output.
4. If the linter exit code is non-zero (1), report "LINT FAILURE" in the batch
   summary and set overall batch exit code to 1.
5. If the linter exit code is 2 (usage error), report "LINTER ERROR — invalid
   config?" and exit 2.

**Acceptance Criteria:**

- **AC-8.1:** [TESTABLE] Without `--lint`, the batcher completes without
  invoking the linter. **Enforced via:** automated test — spy on linter path;
  assert not invoked.

- **AC-8.2:** [TESTABLE] With `--lint` and all generated recipes passing the
  linter, the batch completes with exit 0 and no lint-related failure message.
  **Enforced via:** automated test — run with `--lint` on clean input; assert
  exit 0.

- **AC-8.3:** [TESTABLE] With `--lint` and at least one generated recipe
  failing the linter, the batch exits 1 and reports lint failure. **Enforced
  via:** automated test — mock linter to return 1; assert exit 1; assert "LINT
  FAILURE" in output.

- **AC-8.4:** [TESTABLE] With `--lint` and the linter itself failing (exit 2),
  the batch exits 2 with a "LINTER ERROR" message. **Enforced via:** automated
  test — mock linter to return 2; assert exit 2.

- **AC-8.5:** [TESTABLE] `--specs <path>` changes the linter config file
  passed to `recipe-linter.sh --specs <path>`. **Enforced via:** automated test —
  run with `--lint --specs /tmp/custom.yaml`; assert linter invoked with correct
  `--specs` argument.

---

## 8. Architecture-Incompatible Patterns

**AIP-01: Ad-hoc single-app mode.** Adding a mode that accepts a single URL
directly (without a CSV file) violates Constitution §1 (Batch Input, Not Ad-Hoc
Execution). Recipe Robot itself handles single-app generation; the batcher's
purpose is batch processing.

**AIP-02: Stateful operation.** Storing state between runs (e.g., a database or
status file that influences subsequent runs) violates Constitution §2
(Deterministic, Idempotent Operation). Each run is independent.

**AIP-03: Silent failure.** Failing to generate a recipe and not recording it
in the log violates Constitution §3 (Transparent Audit Trail). Every failure
must be logged with the app name and error detail.

**AIP-04: Skipping linter on generated output.** Producing recipes that do not
pass the linter, without warning, violates Constitution §4 (Generated Output
Must Be Linter-Valid). If `--lint` is not used, the operator bears
responsibility, but the tool must never claim compliance without verification.

**AIP-05: One failure aborts the batch.** Aborting the entire batch when a
single app fails violates Constitution §7 (Graceful Degradation on Recipe Robot
Failure). The loop continues; failures are reported in the summary.

**AIP-06: GNU-only flag dependency.** Using `grep -P`, `sed -r`, `sort -V`, or
other GNU-only flags without a fallback violates Constitution §5 (Stock macOS
Toolchain Constraint). All processing must work on a standard macOS system.

**AIP-07: Leaving Recipe Robot output in place without normalization.**
Treating Recipe Robot's raw output (with wrong filenames, wrong Identifiers,
wrong directory structure) as the final artifact violates Constitution §6
(Post-Generation Recipe Normalization). Normalization is mandatory.

**AIP-08: Overwriting without warning.** Silently overwriting existing recipe
files in the output directory without any `--force` confirmation violates the
principle of safe operation. If an output file already exists, the batcher
should either skip, warn, or require an explicit `--force` flag.

---

## 9. Smart Quote Detection

### FR-9 — Input File Sanitization Check

[TESTABLE]

Smart/curly quotes (`\u201C` `\u201D` `\u2018` `\u2019`) are a common
copy-paste trap when copying CSV data from web pages, spreadsheets, or
documents. The batcher must detect any occurrence of these characters in the
input file and exit before processing.

**Acceptance Criteria:**

- **AC-9.1:** [TESTABLE] A CSV file containing any smart quote character causes
  exit code 2 with an error message identifying the issue. **Enforced via:**
  automated test — create CSV with each smart quote variant; assert exit 2.

- **AC-9.2:** [TESTABLE] The detection logic works on macOS via `grep` with
  Unicode character matching. If `grep -P` is unavailable (BSD grep), an
  alternative detection method using `tr` or hex byte matching must be used.
  **Enforced via:** Shellcheck + CI on macOS runner.

- **AC-9.3:** [TESTABLE] `TEST` status with an existing output directory for the
  same Vendor/AppName causes the entry to be skipped. Recipe Robot is not
  invoked. **Enforced via:** automated test — create output directory before
  running batcher with a `TEST` entry; assert entry is SKIP-logged; assert no
  Recipe Robot invocation.

- **AC-9.4:** [TESTABLE] `TEST` status without an existing output directory
  causes the entry to be processed normally. Recipe Robot is invoked. **Enforced
  via:** automated test — run batcher with a `TEST` entry where no output
  directory exists; assert Recipe Robot is invoked.

- **AC-9.5:** [TESTABLE] `DONE` status causes the entry to be skipped regardless
  of whether the output directory exists. A log entry records the skip with the
  `DONE` reason. **Enforced via:** automated test — CSV with `DONE` entry;
  assert skip logged; assert no Recipe Robot invocation.

- **AC-9.6:** [TESTABLE] An unrecognized status value (e.g., `"PENDING"`,
  `"FOO"`) causes the entry to be skipped with a warning message. The entry is
  counted as SKIP, and Recipe Robot is not invoked. **Enforced via:** automated
  test — CSV with unrecognized status; assert warning printed; assert skip
  logged; assert no Recipe Robot invocation.

---

## 10. Recipe Robot Preferences Warning

### FR-10 — Pre-Flight Configuration Check

[ADVISORY]

Before processing any entries, the batcher checks whether Recipe Robot's
preferences indicate YAML output format and a known recipe prefix. This is an
informational check — the batcher cannot enforce Recipe Robot's configuration,
but should warn the operator if it cannot confirm settings.

**Acceptance Criteria:**

- **AC-10.1:** [ADVISORY] If Recipe Robot preferences are not found or do not
  mention YAML, a warning is printed and the operator is prompted to continue.
  This is a soft check that does not block execution.

- **AC-10.2:** [TESTABLE] The warning includes actionable instructions (e.g.,
  "Run 'recipe-robot --config' to verify format and recipe prefix"). **Enforced
  via:** reviewer inspection.

- **AC-10.3:** [TESTABLE] The check never causes a crash if the preferences
  file is missing or unreadable. **Enforced via:** automated test — run with no
  preferences file; assert warning printed; assert execution continues.

---

## 11. Open Questions

**OQ-1: Output directory default when `-o` is not specified.**
- Option A: Current working directory (matches current `rr-batch.sh` behavior)
- Option B: `~/Desktop/RecipeRobotOutput/` (parallel to Recipe Robot's default)
- **Leaning:** Option A — simpler, more predictable, and matches existing behavior.

**OQ-2 (resolved 2026-09-27): Should the batcher create `.overrides` and
`.autopkg_config`?** No. Only the recipe files are created. `.overrides` is
optional and org-defined, and pipeline metadata is org-specific (Standards
§3.4–3.5). A fork that wants sidecar stubs generates them in its own tooling.

**OQ-3: Should the batcher support MUNKI recipe generation?**
- Option A: No — only download + pkg recipes are supported
- Option B: Yes — but via a separate `--type` flag
- **Leaning:** Option A — the upstream spec only defines download and pkg
  recipe types. MUNKI is out of scope for this tool.

**OQ-4 (resolved): Should `--force` be required to overwrite existing output files?** Yes (AC-5.8).
- Option A: Yes — require `--force` to overwrite; without it, skip existing
- Option B: No — always overwrite (current behavior)
- **Leaning:** Option A — safer default; prevents accidental loss of manual
  changes. Current `rr-batch.sh` has no `--force` flag, so this would be new.

**OQ-5 (resolved 2026-09-27, Option A): Integration with `rr-rename-postprocess.sh` (removed).**
Folded into the batcher (FR-5 step 4); the script is removed. It read a different,
two-column CSV and only knew `com.github.*` identifiers.
- Option A: Fold rename post-processing into the batcher itself
- Option B: Keep as a separate standalone tool
- **Leaning:** Option A — the `rr-rename-postprocess.sh` script performs
  the exact normalization described in FR-5. Integrating it would consolidate
  the workflow. However, this spec treats normalization as a normative behavior;
  whether it uses the existing script or reimplements the logic is an
  implementation detail.

---

## 12. Version History

| Version | Date | Change |
|---------|------|--------|
| 3.0 | 2026-09-27 | Ported to Python (`recipekit.rr_batch`). FR-5 rewritten to Recipe Robot's real output (checked live on 2.5.0): discovery from its printed paths, rename folded in (OQ-5; `rr-rename-postprocess.sh` removed), `--force` (OQ-4). FR-10 reads the plist. |
| 2.1 | 2026-09-27 | .overrides optional; .autopkg_config removed from upstream. FR-6 no longer generates companion files; AC-6.2 inverted, AC-6.3 retired, OQ-2 resolved |
| 2.0 | 2026-08-02 | Added Status column — replaced 2-col/3-col auto-detect with fixed 4-column format (Status, Vendor, AppName, URL); broadened URL validation to accept Recipe Robot-compatible values (HTTP(S), absolute/relative paths); added status filter logic (TEST/DONE/SKIP/blank/unrecognized) to processing loop; added SKIP logging and counts; added AC-2.8, AC-3.5, AC-9.3 through AC-9.6 for status semantics |
| 1.0 | 2026-08-02 | Initial release |
