# clear-autopkg-cache.sh — clear AutoPkg's cache for named recipes

**Status:** Draft
**Date:** 2026-09-27
**Requires:** `specs/toolkit/00-constitution.md`
**Implementation:** `bin/clear-autopkg-cache.sh`

---

## Purpose

AutoPkg keeps a cache directory per recipe identifier under
`~/Library/AutoPkg/Cache/`. A stale download or half-built package in there can
make a recipe run use old material. This script deletes those per-recipe
directories, or empties the whole cache, and nothing else.

Its safety argument is its simplicity. It has one hard-coded root, it takes no
path, and a reader can check every deletion in one sitting. That is why it is
bash (P-7), why it does not source `lib/toolkit-common.sh`, and why it has no
repo argument (P-8).

### In scope

- Deleting `~/Library/AutoPkg/Cache/<identifier>` for each identifier given.
- Emptying `~/Library/AutoPkg/Cache/` with `--all`.
- A `--dry-run` preview of either.

### Out of scope

- A recipe repo's `build/`, the vendor cache, or any other path. There is no
  way to point the script at them.
- AutoPkg's own `CACHE_DIR` preference. The script does not read it (OQ-02).
- Finding identifiers for the caller (from a recipe name, a repo or a run log).
- Checking whether `autopkg` is running at the same time.
- Any other user's cache, or the system-wide `/Library/AutoPkg`.

### Normative vs. Informative

- **Normative:** the single fixed root, the absence of any aiming input, the
  identifier guards, what `--all` removes, dry-run making no changes, exit codes.
- **Informative:** message wording and the exact `--help` text.

### Classification Key

- **[TESTABLE]** — can be checked by an automated test; the test is named.
- **[STRUCTURAL]** — checked by reading the code or the layout.
- **[ADVISORY]** — reviewer judgment.

---

## FR-01 — One fixed root, no aim (P-8)

[STRUCTURAL]

The cache root is `${HOME}/Library/AutoPkg/Cache`, set once in the script. The
script MUST NOT accept a flag, positional path or toolkit environment variable
that changes it.

P-8 applies, and the code honours it for everything the script reads on
purpose: there is no `--repo`, `--root` or path argument, no
`AUTOPKG_TOOLKIT_*` variable, and no config file. One input still aims it:
`HOME`. `HOME=/some/dir clear-autopkg-cache.sh --all` empties
`/some/dir/Library/AutoPkg/Cache`. `HOME` is set by the login session, not by
the toolkit, so this is the same trust any per-user tool places in it. The code
comment says so: the root is not a parameter, flag or toolkit variable, and
"HOME decides whose" cache it is.

The root is also resolved physically (`pwd -P`) before use. If
`~/Library/AutoPkg/Cache` is itself a symlink, the script works on the link's
target, and `--all` empties that target (see OQ-01).

**Acceptance Criteria:**

- AC-01.1: [STRUCTURAL] The script has no option other than `--dry-run`,
  `--all`, `-h` and `--help`, and reads no environment variable other than
  `HOME`.
  **Enforced via:** inspection.
- AC-01.2: [TESTABLE] With `HOME` pointed at a temp directory holding
  `Library/AutoPkg/Cache/<id>`, the script deletes that entry and nothing
  outside the temp directory.
  **Enforced via:** `tests/clear_autopkg_cache_spec.sh`, "removes only the
  named identifier" (every example sets `HOME` to a temp directory, so the real
  cache is never touched).
- AC-01.3: [STRUCTURAL] The script does not source `lib/toolkit-common.sh` and
  resolves no recipe repo. Adding a repo argument "for consistency" is
  non-conforming (P-8).
  **Enforced via:** inspection.

## FR-02 — Command line

[TESTABLE]

```
clear-autopkg-cache.sh [--dry-run] <identifier> [<identifier> ...]
clear-autopkg-cache.sh --all [--dry-run]
clear-autopkg-cache.sh -h | --help
```

- Arguments are read left to right. Flags may appear anywhere, before or after
  identifiers.
- Any argument starting with `-` that is not a known flag exits 2 with
  `ERROR: Unknown option: <arg>` on stderr. There is no `--` separator, so an
  identifier can't start with `-`.
- `-h`/`--help` prints the script's header comment (usage and examples) and
  exits 0 at the point it is read. An unknown option before it exits 2 first.
  Help never deletes anything, even after `--all`.
- Every other argument is an identifier, for example
  `com.acmefruit.autopkg.download.Firefox`.

**Acceptance Criteria:**

- AC-02.1: [TESTABLE] `--help` exits 0 and prints the usage examples.
  **Enforced via:** planned test `tests/clear_autopkg_cache_spec.sh` (planned)
- AC-02.2: [TESTABLE] `--all --help` exits 0 and removes nothing.
  **Enforced via:** planned test `tests/clear_autopkg_cache_spec.sh` (planned)
- AC-02.3: [TESTABLE] `--bogus` exits 2 with `Unknown option` on stderr and
  removes nothing, even with identifiers given.
  **Enforced via:** planned test `tests/clear_autopkg_cache_spec.sh` (planned)

## FR-03 — Order of checks

[TESTABLE]

After parsing, the script runs these steps in order:

1. If the cache root is not a directory, print `Cache root does not exist:
   <root> — nothing to clear.` on stdout and exit 0.
2. Resolve the root's physical path.
3. With `--all`, clear the root (FR-05) and exit 0. Identifiers given alongside
   `--all` are ignored.
4. With no identifiers, print a usage message on stderr and exit 1.
5. Otherwise, clear each identifier in turn (FR-04).

Because step 1 comes first, running with no arguments on a machine with no
cache exits 0, not 1 (see OQ-04).

**Acceptance Criteria:**

- AC-03.1: [TESTABLE] With no cache root, any identifier or `--all` exits 0 with
  the "does not exist" message and creates nothing.
  **Enforced via:** planned test `tests/clear_autopkg_cache_spec.sh` (planned)
- AC-03.2: [TESTABLE] With a cache root and no arguments, the script exits 1 and
  prints usage on stderr.
  **Enforced via:** planned test `tests/clear_autopkg_cache_spec.sh` (planned)
- AC-03.3: [TESTABLE] `--all com.acmefruit.autopkg.pkg.Firefox` empties the
  whole root, not just that entry.
  **Enforced via:** planned test `tests/clear_autopkg_cache_spec.sh` (planned)

## FR-04 — Clearing by identifier

[TESTABLE]

For each identifier:

1. **Identifier guard.** If it is empty, is `.`, or contains `/` or `..`, print
   `REFUSED: '<id>' is empty, '.', or contains a path separator or '..' …` on
   stderr, mark the run failed and skip it. The script goes on to the next
   identifier.
2. Print `Clearing cache for: <id>` on stdout.
3. **Existence check.** The target is `<root>/<id>`. If nothing exists there
   (`! -e`), print `  (nothing to clear: <target>)` and move on. A dangling
   symlink counts as nothing, so it is left in place.
4. **Containment guard.** Resolve the target's parent physically and append the
   target's name. The result must be strictly inside the physical root. The root
   itself is refused, and so are `<root>/.` and `<root>/..` (`REFUSED: … is not
   an entry inside <root>`). Anything else outside the root prints `REFUSED: …
   outside <root>`. Both go to stderr, mark the run failed and skip the
   identifier.
5. With `--dry-run`, print `  [DRY RUN] would remove: <path>`. Otherwise run
   `rm -rf <path>`. If it succeeds, print `  removed: <path>`. If it fails,
   print `  FAILED to remove: <path>` on stderr and mark the run failed.

What this removes and what it does not:

- It removes the directory `<root>/<id>` and everything in it.
- If `<root>/<id>` is a symlink, it removes the link only. `rm -rf` does not
  follow a symlink given as its argument, so the link's target is untouched,
  even when it is outside the root.
- It never removes the root itself or anything outside it. With empty, `.`,
  `/` and `..` rejected, the target is always a single name directly inside the
  root, so the containment guard in step 4 cannot fail for an identifier that
  got past step 1. It is a second line of defence, not the one that does the
  work. Emptying the root is `--all`'s job only.
- A caller that runs `clear-autopkg-cache.sh "${ID}"` with `ID` unset gets a
  refusal and exit 1, not a deleted cache.

**Acceptance Criteria:**

- AC-04.1: [TESTABLE] Given two identifiers with cache entries and a third
  without, the first two directories are gone, the third prints `nothing to
  clear`, and sibling entries remain.
  **Enforced via:** `tests/clear_autopkg_cache_spec.sh`, "removes only the named
  identifier" and "reports an identifier with nothing cached" (one identifier
  per run; the mixed three-identifier run is planned)
- AC-04.2: [TESTABLE] `../x`, `a/b` and `..` are each refused on stderr and
  nothing is removed for them; a valid identifier after them is still cleared.
  **Enforced via:** `tests/clear_autopkg_cache_spec.sh`, `refuses "." and
  paths` covers `../x` and `a/b` (bare `..` and a valid identifier after them
  are planned)
- AC-04.3: [TESTABLE] A cache entry that is a symlink to a directory outside the
  root is removed as a link, and the outside directory and its files remain.
  **Enforced via:** planned test `tests/clear_autopkg_cache_spec.sh` (planned)
- AC-04.4: [TESTABLE] An empty identifier is refused and the cache root remains.
  **Enforced via:** `tests/clear_autopkg_cache_spec.sh`, "refuses an empty
  identifier and leaves the cache intact (KI-24)".
- AC-04.5: [TESTABLE] `.` is refused as not an identifier.
  **Enforced via:** `tests/clear_autopkg_cache_spec.sh`, `refuses "." and
  paths`.
- AC-04.6: [TESTABLE] `removed:` is printed only when `rm` succeeded; a failed
  `rm` prints `FAILED to remove:` on stderr.
  **Enforced via:** planned example in `tests/clear_autopkg_cache_spec.sh`
  (planned; needs an entry `rm` cannot delete)

## FR-05 — Clearing everything (`--all`)

[TESTABLE]

`--all` prints `Clearing entire cache root: <root>` and removes every entry
directly inside the physical root, with
`find <root> -mindepth 1 -maxdepth 1 -exec rm -rf {} +`, then prints `Cache
root emptied.`

- The root directory itself stays.
- Hidden entries (names starting with `.`) are removed too.
- A symlink directly inside the root is removed as a link; its target is
  untouched. `find` does not follow symlinks by default.
- Entries are not checked against the identifier rules, and the containment
  guard is not used. Everything found is directly inside the root by
  construction.

**Acceptance Criteria:**

- AC-05.1: [TESTABLE] After `--all`, the root exists and is empty, including of
  hidden entries.
  **Enforced via:** `tests/clear_autopkg_cache_spec.sh`, "empties the cache
  root, but keeps the root, with --all" (a hidden entry in the fixture is
  planned)
- AC-05.2: [TESTABLE] A symlink inside the root pointing outside it is removed,
  and its target remains.
  **Enforced via:** planned test `tests/clear_autopkg_cache_spec.sh` (planned)

## FR-06 — Dry run

[TESTABLE]

`--dry-run` makes no change to the file system. By identifier, it prints
`  [DRY RUN] would remove: <path>` for each entry that would go. With `--all`,
it prints `[DRY RUN] would remove contents of: <root>` followed by one line per
top-level entry (the raw `find` output).

**Acceptance Criteria:**

- AC-06.1: [TESTABLE] A tree listing of a fixture root is identical before and
  after `--dry-run` with identifiers, and after `--all --dry-run`.
  **Enforced via:** `tests/clear_autopkg_cache_spec.sh`, "removes nothing with
  --dry-run" covers identifiers (`--all --dry-run` is planned)
- AC-06.2: [TESTABLE] `--all --dry-run` lists every top-level entry of the root.
  **Enforced via:** planned test `tests/clear_autopkg_cache_spec.sh` (planned)
- AC-06.3: [TESTABLE] `--dry-run` works in either position
  (`--dry-run <id>` and `<id> --dry-run`).
  **Enforced via:** planned test `tests/clear_autopkg_cache_spec.sh` (planned)

## FR-07 — Output and exit codes

[TESTABLE]

Progress lines go to stdout. `REFUSED`, `ERROR` and usage lines go to stderr.
Paths printed after `removed:` and `would remove:` are physical paths.

| Exit | When |
|---|---|
| 0 | Help; no cache root; `--all` (whether or not `rm` succeeded); identifier mode when every identifier was removed, previewed, or had nothing to clear |
| 1 | Cache root exists but no identifier and no `--all` given; identifier mode when any identifier was refused or failed to remove |
| 2 | Unknown option |

In identifier mode the script clears every identifier it can, then exits 1 if
any one was refused or failed, else 0. The header comment documents these
codes. `--all` still exits 0 even if `rm` fails on an entry.

**Acceptance Criteria:**

- AC-07.1: [TESTABLE] Each exit code in the table is produced by the case it
  names.
  **Enforced via:** planned test `tests/clear_autopkg_cache_spec.sh` (planned)
- AC-07.2: [TESTABLE] Refusal messages appear on stderr only; `removed:` lines
  appear on stdout only.
  **Enforced via:** planned test `tests/clear_autopkg_cache_spec.sh` (planned)
- AC-07.3: [TESTABLE] A refused identifier makes the run exit non-zero.
  **Enforced via:** `tests/clear_autopkg_cache_spec.sh`, "refuses an empty
  identifier and leaves the cache intact (KI-24)" and `refuses "." and paths`.

## FR-08 — Dialect and size

[ADVISORY]

The script stays in bash (P-7): its safety rests on being short enough to read
in one sitting. Its shebang is `#!/bin/bash`, and it runs under `/bin/bash` 3.2 with `set -uo pipefail` and uses
only `sed`, `find`, `rm`, `dirname`, `basename` and shell built-ins. It needs no
AutoPkg, no Python and no elevated privileges, and works on the invoking user's
cache only.

**Acceptance Criteria:**

- AC-08.1: [STRUCTURAL] No associative arrays, `mapfile` or case-modification
  expansion.
  **Enforced via:** inspection.
- AC-08.2: [ADVISORY] A change that adds a path argument, a config file, or a
  second root is rejected in review (P-8). A change that grows the script past
  what one reader can check in one sitting needs a stated reason.
  **Enforced via:** reviewer check.

---

## Architecture-Incompatible Patterns

**AIP-01: An aiming input.** A `--root`, `--repo`, path argument, config key or
toolkit environment variable that moves the deletion root. It removes the
property the script's safety rests on (P-8). **Enforced via:** AC-01.1.

**AIP-02: Deleting through a symlink.** Resolving an entry's symlink and
deleting its target, or using `find -L`. **Enforced via:** AC-04.3, AC-05.2.

**AIP-03: Globbing identifiers.** Accepting `com.acmefruit.*` and expanding it
against the cache. A pattern that matches more than intended deletes more than
intended; the caller can list entries and pass them explicitly.
**Enforced via:** reviewer check.

**AIP-04: Sourcing the shared library.** Pulling in `lib/toolkit-common.sh`
adds code the reader must also check, for no gain: the script resolves no repo
and reads no toolkit asset. **Enforced via:** AC-01.3.

---

## Open Questions

**OQ-01:** `HOME` aims the script (`bin/clear-autopkg-cache.sh` line 28), and a
symlinked cache root is followed (`bin/clear-autopkg-cache.sh` line 51), so `--all`
empties whatever the link points at. Should the script refuse when the root is a
symlink, and refuse when `HOME` is not the invoking user's home directory from
the directory service? **(HOME part resolved 2026-09-27:** `HOME` is accepted as
the same trust every per-user tool places in it, and the code comment now says
so.) The symlinked root is still followed; leaning: refuse it.

**OQ-02:** AutoPkg honours a `CACHE_DIR` preference. When it is set, this script
clears the default location, which AutoPkg is not using. Should the script read
`CACHE_DIR` and refuse (not follow) when it differs from the default? Following
it would be an aiming input (P-8).

**OQ-03:** **(Resolved 2026-09-27)** Empty and `.` identifiers are refused, and
the containment guard accepts only paths strictly inside the root. Original
question: the empty identifier deleted the whole cache root directory
(`bin/clear-autopkg-cache.sh` line 65 accepted the root itself as a target), and `.`
reached `rm`. Fix: reject empty identifiers and `.` in the separator guard, and
drop the `"${CACHE_ROOT_REAL}"` (root-equals) branch from the containment check,
since `--all` does not use it.

**OQ-04:** With no cache root and no arguments, the script exits 0 instead of
1. Should argument validation come before the root check?

**OQ-05:** **(Resolved 2026-09-27)** Yes: identifier mode exits 1 if any
identifier was refused or failed, and `removed:` prints only when `rm`
succeeded. `--all` is unchanged. Original question: refused identifiers and `rm` failures don't affect the exit code, and
`removed:` was printed even when `rm` failed. Should the script exit 1 if any identifier was refused or any removal
failed?

**OQ-06:** `--all` with identifiers silently ignores the identifiers. Should the
combination be a usage error (exit 2)?

**OQ-07:** Should the script refuse to run while an `autopkg` process is
running, since clearing a cache mid-run can break that run?

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-09-27 | Initial spec, written from the existing implementation. |
| 0.2 | 2026-09-27 | Updated for the fixes to KI-24. |
