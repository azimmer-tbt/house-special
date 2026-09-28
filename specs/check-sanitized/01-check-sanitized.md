# check-sanitized.sh — Leak guard for the toolkit tree

**Status:** Draft
**Date:** 2026-09-27
**Requires:** `specs/toolkit/00-constitution.md`, `specs/toolkit/01-toolkit-common.md`
**Implementation:** `bin/check-sanitized.sh`

---

## Purpose

House Special is an upstream that orgs fork. A fork collects org-specific data:
names, reverse-DNS identifiers, home-directory paths, ticket numbers. This tool
stops that data flowing back upstream, and stops a fork's own private details
landing in a commit.

It scans files for two kinds of leak:

- **Built-in checks** that apply to every fork: home-directory paths, change and
  incident ticket numbers, serial numbers, cloud sync-folder paths, oversized
  files and installer binaries.
- **A private denylist** (`.leak-patterns` at the repo root), one regex per line,
  that each fork writes for its own names. It is gitignored on purpose: a
  committed denylist would leak every name it lists.

It reports findings. It never edits, moves or deletes the files it scans.

It stays in bash (constitution P-7): its safety rests on being simple enough to
read in one sitting.

**Out of scope, on purpose:**

- Secret detection by entropy or key format (API tokens, private keys). Use a
  dedicated secret scanner for that.
- Git history. The tool sees the working tree or the staged set, never past
  commits.
- Fixing anything. The fix is always a content change made by a person (see
  `.devagent/skills/sanitize-check.md`).
- Knowing what is private to a fork. That knowledge lives only in the fork's
  denylist.

### Normative vs. Informative

- **Normative:** which files are scanned and skipped, what each built-in check
  catches, denylist semantics (comments, exemptions, per-file allow), the finding
  line format, exit codes, and the hook's refuse-to-overwrite rule.
- **Informative:** the exact regexes, the placeholder list, the default size
  limit (1024 KB), the label names, the denylist filename, and the temp-file
  mechanics. A conforming implementation MAY tune these; it MAY NOT change what
  the checks are for.

### Classification Key

- **[TESTABLE]** — a command gives a yes/no answer; the mechanism is named.
- **[STRUCTURAL]** — enforced by layout or inspection.
- **[ADVISORY]** — review judgment.

---

## FR-01 — What gets scanned

[TESTABLE]

By default the tool scans every regular file under the toolkit root. The toolkit
root comes from the script's own location (toolkit-common FR-01), so the working
directory does not matter (P-1, P-3).

Inputs:

- `--root <dir>` scans another tree instead. The value is resolved physically. A
  path that is not a directory is a usage error.
- `--path <rel>` limits the scan to a path under the root. It is repeatable, and a
  trailing `/` is dropped. A path that does not exist prints a warning on stderr
  and is skipped.

Always skipped:

- `.git`: the folder, or the one-line file a git worktree has in its place (it
  holds the main repository's path);
- every denylist file: `.leak-patterns` in any folder (the kit's and each
  customer's, FR-09) and whatever file `--patterns` names, when it sits inside
  the root;
- `reference/autopkg-wiki/`, a third-party mirror whose pages contain example
  paths. When anything there was skipped, the tool prints
  `skipped: reference/autopkg-wiki (third-party mirror)` first.

Each file is scanned once, even when two `--path` values overlap.

**Acceptance Criteria:**

- AC-01.1: [TESTABLE] A tree with no leaks exits 0 and prints a line starting
  `clean:`.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "passes a clean tree and
  reports the wiki skip".
- AC-01.2: [TESTABLE] Files under `reference/autopkg-wiki/` are not scanned,
  even when they contain a real home-directory path, and the skip is announced.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "passes a clean tree and
  reports the wiki skip".
- AC-01.3: [TESTABLE] `--path` limits the scan: a leak outside the named path is
  not reported.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "limits the scan with
  --path".
- AC-01.4: [TESTABLE] Files under `.git/` are never scanned.
  **Enforced via:** planned test (planned) — plant a leak inside `.git/`, assert
  a clean result.
- AC-01.5: [TESTABLE] Overlapping `--path` values do not produce duplicate
  findings.
  **Enforced via:** planned test (planned) — `--path docs --path docs/`, assert
  one finding line.
- AC-01.6: [TESTABLE] Run from an unrelated directory with no `--root`, the tool
  scans the toolkit root.
  **Enforced via:** planned test (planned) — invoke from `/`, assert the file
  count matches a run from the toolkit root.
- AC-01.7: [TESTABLE] A run in which no named `--path` exists fails with a usage
  error instead of reporting clean. (Not yet met; see OQ-1.)
  **Enforced via:** planned test (planned) — `--path nope`, assert exit 2.

## FR-02 — Staged mode

[TESTABLE]

`--staged` scans only the files in the git index that are added, copied,
modified or renamed (`git diff --cached --diff-filter=ACMR`). Deleted files are
not scanned. It is what the pre-commit hook runs (FR-07).

If `--root` is not inside a git repository, the tool fails with a usage error.

**Acceptance Criteria:**

- AC-02.1: [TESTABLE] Only staged files are scanned: a leak in an unstaged file
  is not reported.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "scans only staged files
  with --staged".
- AC-02.2: [TESTABLE] `--staged` outside a git repository exits 2 with a message
  naming the root.
  **Enforced via:** planned test (planned).
- AC-02.3: [TESTABLE] A staged deletion is not scanned and does not cause an
  error.
  **Enforced via:** planned test (planned).
- AC-02.4: [TESTABLE] The content scanned is the staged content, not the working
  copy. (Not yet met; see OQ-3.) Today the tool reads the file from the working
  tree, so a leak that is staged and then removed from the working copy (but not
  re-staged) is committed without a finding.
  **Enforced via:** planned test (planned) — stage a leak, clean the working
  copy without staging, assert a finding.

## FR-03 — Built-in content checks

[TESTABLE]

These run on every scan, with or without a denylist. They search text files
only; `grep -I` skips files it detects as binary.

| Label | Catches | Example that is flagged |
|---|---|---|
| `home-path` | `/Users/` followed by a name that is not a placeholder | a path under a real person's home folder |
| `ticket` | `CHG`, `RITM`, `INC` or `CTASK` followed by 6 or more digits, not preceded by a letter or digit | a change number pasted into a note |
| `serial` | "Serial Number" (either capitalisation of each word), then `-`, `:` or spaces, then 6 or more of `A-Z 0-9 -` | a hardware serial copied from System Information |
| `onedrive` | a tenant sync folder written `OneDrive-<Org>` (capital letter after the hyphen) | a path under the CloudStorage folder |

Home-path placeholders are allowed: `/Users/Shared`, `/Users/you`,
`/Users/your-user`, `/Users/YourUser`, `/Users/user`, `/Users/username`,
`/Users/USER`, `/Users/me`, `/Users/example`, `/Users/name`, `/Users/admin` and a
few more, plus any name that starts with a placeholder character such as `<`,
`$`, `{`, `*` or `…`. A placeholder word must be the whole name: `/Users/me` is
allowed, but a home folder named `melissa` or `adminbob` is reported. Trailing sentence
punctuation (`.`, `,`, `;`, `:`, `!`, `?`) is stripped before the check, so
`/Users/you.` at the end of a sentence is still a placeholder. The home-path
finding shows only the matched path (with any trailing punctuation), not the
whole line.

Built-in checks ignore `--allow`, the LICENSE/NOTICE exemption and `!`
exemption lines. Those apply to the denylist only (FR-05).

**Acceptance Criteria:**

- AC-03.1: [TESTABLE] A real home-directory path is reported with label
  `home-path`; `/Users/Shared` and `/Users/you` are not.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "flags a real
  home-directory path but not placeholders".
- AC-03.2: [TESTABLE] A placeholder matches a whole path segment, not a prefix.
  A home folder whose name only starts with a placeholder word (for example
  `adminbob` or `melissa`) is still reported, and a placeholder followed by
  sentence punctuation is still allowed.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "matches placeholder names
  whole, so a real name that starts with one is flagged (KI-25)".
- AC-03.3: [TESTABLE] Ticket numbers, serial numbers and `OneDrive-<Org>` paths
  are reported with labels `ticket`, `serial` and `onedrive`.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "flags ticket numbers,
  serials and OneDrive paths".
- AC-03.4: [TESTABLE] A ticket prefix with fewer than 6 digits, or glued to a
  preceding letter or digit, is not reported.
  **Enforced via:** planned test (planned).
- AC-03.5: [TESTABLE] Built-in checks run when there is no denylist, and the
  tool prints a `note: no denylist at …` line.
  **Enforced via:** planned test (planned) — the existing clean-tree example has
  no denylist but does not assert the note.
- AC-03.6: [TESTABLE] A built-in finding in a file named by `--allow`, or in
  LICENSE, is still reported.
  **Enforced via:** planned test (planned).

## FR-04 — Size and file-type checks

[TESTABLE]

- `large-file`: a file whose size, rounded up to whole KB, is greater than
  `--max-kb` (default 1024). `--max-kb` must be a non-negative integer.
- `binary`: a file ending `.pkg`, `.mpkg`, `.dmg` or `.zip`, unless it is under
  `tests/fixtures/`.

Both are reported with line number `0`, since they are about the whole file.

**Acceptance Criteria:**

- AC-04.1: [TESTABLE] A file over `--max-kb` is reported as `large-file`.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "flags files over
  --max-kb".
- AC-04.2: [TESTABLE] An installer outside `tests/fixtures/` is reported as
  `binary` at line 0; one inside is not.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "flags installers outside
  tests/fixtures only".
- AC-04.3: [TESTABLE] A non-numeric `--max-kb` exits 2.
  **Enforced via:** planned test (planned).
- AC-04.4: [TESTABLE] The extension match ignores case, so `App.DMG` is
  reported. (Not yet met; see OQ-5.)
  **Enforced via:** planned test (planned).

## FR-05 — The denylist

[TESTABLE]

The denylist is `<root>/.leak-patterns` unless `--patterns <file>` names
another. Its format:

- one extended regex (as for `grep -E`) per line, case-sensitive unless the regex
  says otherwise (for example `[Aa]cme`);
- blank lines and lines starting with `#` are ignored;
- a line starting with `!` is an **exemption**: a denylist hit on a line of text
  that also matches the exemption regex is not reported. Exemptions apply to
  every pattern, wherever they appear in the file. The kit's example is a
  maintainer's own `# Author: Pat Example` header line, anchored at both ends;
- a last line without a trailing newline is still read.

Patterns are numbered from 1 in the order they appear, counting only pattern
lines (not comments, blanks or exemptions). A hit is labelled `denylist:N`. The
output never prints the pattern itself, so a report can be shared without
leaking the denylist.

Per-file exemptions: `LICENSE` and `NOTICE` at the root are always exempt (they
name the copyright holder). `--allow <rel>` exempts another file; it is
repeatable and matches the exact root-relative path (a leading `./` is dropped).

**Acceptance Criteria:**

- AC-05.1: [TESTABLE] Each pattern is applied to every scanned file and hits are
  labelled `denylist:N`, with comments and blank lines not counted.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "applies denylist patterns,
  exempting LICENSE and --allow files".
- AC-05.2: [TESTABLE] LICENSE and files named by `--allow` produce no denylist
  findings.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "applies denylist patterns,
  exempting LICENSE and --allow files".
- AC-05.3: [TESTABLE] The denylist file is never scanned.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "applies denylist patterns,
  exempting LICENSE and --allow files" (asserts no `.leak-patterns:` finding).
- AC-05.4: [TESTABLE] A line matching a `!` exemption is not reported; other
  lines in the same file that hit the same pattern are. Exemption lines are not
  counted as patterns.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "exempts lines matching a !
  exemption, but only those lines".
- AC-05.5: [TESTABLE] `--patterns <file>` replaces the default denylist, and that
  file is skipped when it lies inside the root.
  **Enforced via:** planned test (planned).
- AC-05.6: [TESTABLE] A pattern that is not a valid extended regex stops the run
  with exit 2 and names its line. (Not yet met; see OQ-4.) Today grep's error is
  discarded, the pattern silently matches nothing, and it is still counted.
  **Enforced via:** planned test (planned).

## FR-06 — Output and exit codes

[TESTABLE]

Findings go to stdout, one per line:

```text
<file>:<line>: [<label>] <excerpt>
```

`<file>` is relative to the root. The excerpt is the matching line (the matched
path for `home-path`, a short reason for `large-file` and `binary`), cut to 100
characters with a trailing `…`. Findings are sorted by file, then by line
number. After them come a blank line, a count line and a key line:

```text
<n> finding(s) in <f> file(s) (<s> scanned, <p> denylist pattern(s))
denylist:N = line N of the non-comment patterns in .leak-patterns
```

A clean run prints one line:

```text
clean: <s> file(s) scanned, <p> denylist pattern(s)
```

Exit codes: `0` clean, `1` findings, `2` usage error (unknown option, a flag
missing its value, `--root` not a directory, `--staged` or `--install-hook`
outside git, an existing hook). Errors and warnings go to stderr through the
shared library (`tk_die`, `tk_warn`). `-h` or `--help` prints the header and
exits 0.

**Acceptance Criteria:**

- AC-06.1: [TESTABLE] A finding line has the form `<file>:<line>: [<label>]
  <excerpt>`.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "flags a real
  home-directory path but not placeholders".
- AC-06.2: [TESTABLE] Any finding gives exit 1; a clean run gives exit 0.
  **Enforced via:** `tests/check_sanitized_spec.sh` — every example asserts its
  status.
- AC-06.3: [TESTABLE] The summary line reports the denylist pattern count.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "exempts lines matching a !
  exemption, but only those lines".
- AC-06.4: [TESTABLE] An unknown option exits 2 with "Unknown option" on stderr.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "rejects unknown options".
- AC-06.5: [TESTABLE] Findings are sorted by file, then numerically by line.
  **Enforced via:** planned test (planned).
- AC-06.6: [TESTABLE] An excerpt longer than 100 characters is cut with `…`.
  **Enforced via:** planned test (planned).
- AC-06.7: [TESTABLE] A flag missing its value (`--root`, `--path`,
  `--patterns`, `--allow`) exits 2.
  **Enforced via:** planned test (planned).
- AC-06.8: [TESTABLE] `--help` prints usage and exits 0.
  **Enforced via:** planned test (planned).

## FR-07 — Installing the pre-commit hook

[TESTABLE]

`--install-hook` writes a `pre-commit` hook into the root's git hooks directory
(as `git rev-parse --git-path hooks` reports it), marks it executable, prints
`Installed <path>` and exits 0 without scanning. The hook runs
`bin/check-sanitized.sh --staged` from the repository's top level, so a finding
blocks the commit.

If a `pre-commit` hook already exists, the tool MUST NOT touch it. It exits 2
and prints the one line to add to the existing hook instead.

This is the only mode that writes anything.

**Acceptance Criteria:**

- AC-07.1: [TESTABLE] In a git repository with no hook, `--install-hook` creates
  an executable `pre-commit` hook.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "installs a pre-commit hook
  and refuses to overwrite one".
- AC-07.2: [TESTABLE] With a hook already present, it exits 2, says "already
  exists", and leaves the hook unchanged.
  **Enforced via:** `tests/check_sanitized_spec.sh` — "installs a pre-commit hook
  and refuses to overwrite one" (asserts exit and message; a byte-for-byte
  comparison of the old hook is planned (planned)).
- AC-07.3: [TESTABLE] Outside a git repository it exits 2.
  **Enforced via:** planned test (planned).
- AC-07.4: [TESTABLE] The installed hook blocks a commit that stages a leak and
  allows a clean one.
  **Enforced via:** planned test (planned). See OQ-6 for a repo that does not
  contain the script.

## FR-08 — Dialect and side effects

[STRUCTURAL]

The script follows P-7 for bash: bash 3.2, stock macOS tools only (`grep`,
`find`, `xargs`, `sed`, `sort`, `stat -f%z`, `mktemp`, `git`). It prefers
`/usr/bin/grep` so a GNU grep earlier on `PATH` does not change results. It
sources the shared library for the toolkit root and error helpers.

It makes no network calls. Apart from `--install-hook`, its only writes are its
own temp files, which it removes on exit.

**Acceptance Criteria:**

- AC-08.1: [TESTABLE] The script runs under `/bin/bash` 3.2.
  **Enforced via:** `tests/check_sanitized_spec.sh` under ShellSpec, which runs
  with `/bin/bash` (`.shellspec`).
- AC-08.2: [STRUCTURAL] No associative arrays, `mapfile` or case-modification
  expansion.
  **Enforced via:** inspection (constitution AIP-05).
- AC-08.3: [TESTABLE] A scan leaves no temp files behind and changes nothing in
  the scanned tree.
  **Enforced via:** planned test (planned) — compare a listing of the tree and
  the temp directory before and after.

---

## FR-09 — Customers

[TESTABLE]

When the customer registry exists (`config/customers.yaml`, or the file
`$AUTOPKG_TOOLKIT_CUSTOMERS` names; `specs/toolkit/02-customers.md`), each
registered customer's own `.leak-patterns` joins the scan. **A customer's names
may appear only in that customer's own folder.** So:

- every customer's patterns apply to every scanned file **except** those inside
  that customer's folder (when the folder lies under the root; a folder outside
  it is excluded by not being scanned);
- a hit is labelled `customer:<name>:N`, N counted as in FR-05; the customer's
  `!` exemptions apply as the kit's do; the count line includes these patterns,
  and a `customer:NAME:N = …` key line follows the `denylist:N` one;
- `--customer <name>` scans that customer's folder (unless `--root` is given) with
  the kit's denylist (`<kit>/.leak-patterns` unless `--patterns`) plus every
  **other** customer's patterns;
- `--all-customers` runs `--customer` for each registered customer in turn,
  printing `=== Customer: <name>` before each, and exits with the worst code;
- an unknown customer name exits 2 and lists the registered names.

No registry means no customer patterns: the tool behaves as FR-01 to FR-08 say.

**Acceptance Criteria:**

- AC-09.1: [TESTABLE] A customer's name is flagged outside its folder and not
  inside it. **Enforced via:** `tests/customers_shell_spec.sh` — "flags a
  customer's name outside its own folder, not inside it".
- AC-09.2: [TESTABLE] A customer whose folder is outside the root still has its
  patterns applied. **Enforced via:** `tests/customers_shell_spec.sh` — "applies
  an outside customer's patterns to the kit".
- AC-09.3: [TESTABLE] No `.leak-patterns` file is ever scanned. **Enforced via:**
  `tests/customers_shell_spec.sh` — "never flags a customer's own .leak-patterns
  file".
- AC-09.4: [TESTABLE] `--customer` applies the other customers' patterns and not
  its own. **Enforced via:** `tests/customers_shell_spec.sh` — "--customer scans
  that folder with every other customer's patterns".
- AC-09.5: [TESTABLE] `--all-customers` reports each and exits with the worst
  code; an unknown name exits 2. **Enforced via:** `tests/customers_shell_spec.sh`.

---

## Architecture-Incompatible Patterns

**AIP-07: One customer's names in another's folder.** A customer folder is
shared with that customer only; the other customers' names never belong there.
**Enforced via:** FR-09.

**AIP-01: A committed denylist.** Checking `.leak-patterns` in, or copying its
patterns into a doc, test or finding. It leaks every name it lists. The file is
gitignored and the output shows `denylist:N`, never the pattern.
**Enforced via:** `.gitignore`; reviewer check.

**AIP-02: Fixing a finding by weakening the guard.** Widening the placeholder
list, adding `--allow` for a file with a real leak, or deleting a denylist line
to get a clean run. Fix the content instead. **Enforced via:** reviewer check.

**AIP-03: A guard that edits.** Rewriting, redacting or deleting content during
a scan. A guard that changes files cannot be trusted as a check, and a wrong
redaction is silent. **Enforced via:** AC-08.3.

**AIP-04: Overwriting someone's hook.** Replacing an existing `pre-commit` hook
throws away whatever it did. **Enforced via:** AC-07.2.

**AIP-05: A source file that trips its own check.** A literal leak string in the
script or a test makes a whole-tree scan fail. Split such strings so the source
line does not match (the script writes `'One''Drive-'`; the test builds planted
leaks from pieces). **Enforced via:** running the tool on the kit (CONTRIBUTING
"Before you commit").

**AIP-06: Silent success on bad input.** Reporting `clean` when the scan could
not do its job: no files found, a pattern that failed to compile, a path that
did not exist. A leak guard's worst failure is a false "clean". **Enforced via:**
AC-01.7, AC-05.6 (both not yet met).

---

## Open Questions

**OQ-1: A missing `--path` reports clean.** A mistyped path prints a warning and
then `clean: 0 file(s) scanned` with exit 0. Options: (a) exit 2 when any named
path is missing; (b) exit 2 only when nothing at all was scanned. Leaning: (a),
since a typo in a pre-commit or CI line should never look like a pass.

**OQ-2: Placeholder names match as prefixes.** **(Resolved 2026-09-27)** Fixed:
the placeholder word must be the whole name, and trailing sentence punctuation
is stripped before matching. Original question: the placeholder regex was anchored
at the start but not at the end of the name, so any home folder whose name
began with `me`, `user`, `name`, `admin`, `you` or `example` was treated as a
placeholder and not reported. Fix: require the placeholder to be followed by `/`,
a quote, whitespace or end of match. Leaning: fix, and add the AC-03.2 test.

**OQ-3: Staged mode reads the working copy.** `--staged` picks file names from
the index but reads content from disk. Options: (a) read each file with
`git show :<path>`; (b) refuse when a staged file also has unstaged changes.
Leaning: (a).

**OQ-4: Invalid denylist patterns are silent.** grep's error output is discarded,
so a broken regex matches nothing but is still counted as a pattern. Leaning:
compile-check each pattern first (`grep -E -e <pat> /dev/null`, exit 2 means
invalid) and fail with the line number.

**OQ-5: Narrow built-in matches.** Several forms slip through: installer
extensions in capitals (`.DMG`); the spaced sync-folder form (the
`OneDrive - <Org>` folder name); serial values with lowercase letters. Leaning:
case-insensitive extensions and serial values; add the spaced sync-folder form.

**OQ-6: The hook assumes the script lives in the target repo.** The hook runs
`bin/check-sanitized.sh` from the repo's top level. `--install-hook --root` on a
repo that does not contain the kit writes a hook that fails every commit. Also,
when `--root` is a subdirectory of a larger repository, `--staged` gets paths
relative to the top level, which do not resolve under the root and are silently
dropped. Leaning: refuse to install when the script is missing from the target,
and pass `--relative` to `git diff` (or resolve from the top level).

**OQ-7: `--path` is ignored with `--staged`.** Combining them scans every staged
file. Options: intersect the two, or reject the combination. Leaning: intersect.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-09-27 | Initial spec, written from the existing implementation. |
| 0.2 | 2026-09-27 | Updated for the fixes to KI-25. |
| 0.3 | 2026-09-27 | FR-09: customers' `.leak-patterns`, `--customer`, `--all-customers`; every `.leak-patterns` file is skipped. |
| 0.4 | 2026-09-27 | FR-01: a worktree's `.git` file is skipped like the `.git/` folder. |
