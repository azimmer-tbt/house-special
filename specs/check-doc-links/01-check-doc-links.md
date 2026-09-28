# check-doc-links.sh — Find doc references to files that don't exist

**Status:** Draft
**Date:** 2026-09-28
**Requires:** `specs/toolkit/00-constitution.md`, `specs/toolkit/01-toolkit-common.md`
**Implementation:** `bin/check-doc-links.sh`

---

## Purpose

The kit's docs, specs and skills point at each other and at scripts. When a file
is renamed or removed, those pointers go stale quietly, and a reader (or an
agent following a skill) is sent to a file that isn't there. This tool finds
those stale pointers in Markdown files, offline, in one command.

It checks two kinds of reference:

- **Relative links**, the target of a Markdown inline link, resolved against
  the directory of the file that contains it.
- **Backticked repo paths**, an inline code span that starts with one of the
  kit's top-level directories (for example the span `bin/check-sanitized.sh`),
  resolved against the toolkit root.

It only reports. It never edits a document or creates a file.

It stays in bash (constitution P-7): it is a thin wrapper around `find` and
`awk`, simple enough to read in one sitting.

**Out of scope, on purpose:**

- Web links. No network access; `http`, `https`, `mailto` and `file` targets are
  skipped, not fetched.
- Anchors. The part after `#` is dropped; the tool does not check that a heading
  exists.
- Reference-style links, HTML `href` attributes and autolinks in angle brackets.
- Bare paths in prose that are not in backticks, and anything inside a fenced
  code block.

### Normative vs. Informative

- **Normative:** which references are checked and how each kind resolves, what is
  skipped, the `(planned` line marker, the output line format and exit codes.
- **Informative:** the list of top-level directories, the placeholder characters,
  the pruned directories in the default file set, and the awk implementation.

### Classification Key

- **[TESTABLE]** — a command gives a yes/no answer; the mechanism is named.
- **[STRUCTURAL]** — enforced by layout or inspection.
- **[ADVISORY]** — review judgment.

---

## FR-01 — Which files are checked

[TESTABLE]

Inputs:

- `--root <dir>`: the tree to check. Default: the toolkit root, from the script's
  own location (toolkit-common FR-01). The value is resolved physically; a path
  that is not a directory is a usage error.
- `FILE.md ...`: check only these files. Each is taken relative to the root, or
  as an absolute path under the root. A name that is not a file prints
  `WARN:  no such file: <name>` on stderr and is skipped.

With no file arguments, every `*.md` file under the root is checked, in sorted
order, except those under:

- `.git`, `dist` (build output);
- `reference/autopkg-wiki/` (a third-party mirror);
- `sessions` and `troubleshooting` inside each customer workspace (raw working
  notes, gitignored).

**Acceptance Criteria:**

- AC-01.1: [TESTABLE] With no file arguments, every Markdown file under the root
  is checked.
  **Enforced via:** `tests/doc_links_spec.sh` — "passes when every reference
  resolves" (two files, three references).
- AC-01.2: [TESTABLE] Pruned directories are not checked: a broken reference in
  `reference/autopkg-wiki/` or a customer `sessions` folder does not fail the run.
  **Enforced via:** planned test (planned).
- AC-01.3: [TESTABLE] With file arguments, only those files are checked.
  **Enforced via:** planned test (planned).
- AC-01.4: [TESTABLE] A file argument that does not exist fails the run with
  exit 2. (Not yet met; see OQ-1.) Today it warns, still counts the file, and
  can print `links ok` with exit 0.
  **Enforced via:** planned test (planned).
- AC-01.5: [TESTABLE] A relative file argument is resolved against the root, not
  the working directory, so the same command gives the same answer from any
  directory (P-3).
  **Enforced via:** planned test (planned). See OQ-2.

## FR-02 — Finding candidate references

[TESTABLE]

Each file is read line by line.

- A line whose first non-blank text is three backticks opens or closes a fenced
  code block. Nothing inside a fence is checked.
- A line that contains `(planned` (any case) is skipped entirely. Specs describe
  files before they exist; the marker lets them name those files.
- On every other line, each inline link target and each backticked span is a
  candidate. A line can yield several.

Line numbers count every line of the file, fences included.

**Acceptance Criteria:**

- AC-02.1: [TESTABLE] A line marked `(planned` may name a path that does not
  exist, without failing the run.
  **Enforced via:** `tests/doc_links_spec.sh` — "lets a line marked (planned)
  name a path that does not exist yet".
- AC-02.2: [TESTABLE] A backticked missing path inside a fenced code block is not
  reported.
  **Enforced via:** planned test (planned). The fixture in
  `tests/doc_links_spec.sh` has a fence, but the path inside it is not
  backticked, so it would be ignored outside a fence too.
- AC-02.3: [TESTABLE] Every reference on a line is checked, not just the first.
  **Enforced via:** `tests/doc_links_spec.sh` — "passes when every reference
  resolves" (one line holds three).
- AC-02.4: [TESTABLE] A fence written with tildes (`~~~`) is also treated as a
  fence. (Not yet met; see OQ-3.)
  **Enforced via:** planned test (planned).

## FR-03 — What is skipped

[TESTABLE]

Before a candidate is resolved:

1. A link title (a space then a double quote, and everything after) is dropped.
2. An anchor (`#` and everything after) is dropped. A candidate that is now empty
   (a same-page anchor) is skipped.
3. Web targets are skipped: `http://`, `https://`, `mailto:`, `file://`.
4. Placeholders are skipped: anything containing `<`, `>`, `*`, `%`, `{`, `$`,
   `…`, `...` or a space. This covers `<name>`, globs, `%VAR%`, `{{TOKEN}}`,
   shell variables and elided paths.
5. Backticked mentions of **local-only paths** are skipped: paths each checkout
   makes for itself and the kit never ships. Today those are `config/customers.yaml`
   (`specs/toolkit/02-customers.md` FR-01) and anything under
   `reference/autopkg-wiki/` (the user's clone of the AutoPkg wiki). A *link* to one is still checked and
   reported, since it would be a dead link wherever the file doesn't exist.

**Acceptance Criteria:**

- AC-03.1: [TESTABLE] Web links and placeholders are not counted as references.
  **Enforced via:** `tests/doc_links_spec.sh` — "passes when every reference
  resolves" (the fixture holds an `https` link and a `<tool>` placeholder; the
  count is exactly 3).
- AC-03.2: [TESTABLE] A link with an anchor resolves on its file part; a
  same-page anchor is skipped.
  **Enforced via:** planned test (planned).
- AC-03.3: [TESTABLE] A link with a title resolves on its target.
  **Enforced via:** planned test (planned).
- AC-03.4: [TESTABLE] Other URL schemes (for example `ftp:` or `tel:`) are
  skipped, not reported as missing files. (Not yet met; see OQ-4.)
  **Enforced via:** planned test (planned).
- AC-03.5: [TESTABLE] A backticked local-only file is not reported; a link to it
  is.
  **Enforced via:** `tests/doc_links_spec.sh` — "skips a backticked local-only
  file but reports a link to it".

## FR-04 — How references resolve

[TESTABLE]

- **Link:** `<directory of this file>/<target>`.
- **Backticked span:** checked only if it starts with a top-level directory
  followed by `/`. The list is `bin`, `lib`, `config`, `docs`, `specs`,
  `templates`, `tests`, `guardrails`, `reference`, `customer`, `.devagent` and
  `.roo`. A span that also contains whitespace, `=`, `|` or `;` is a command
  line, not a path, and is skipped. The rest resolves to `<root>/<span>`, with a
  trailing `/` dropped.

A reference is good if the target exists, as a file or a directory.

**Acceptance Criteria:**

- AC-04.1: [TESTABLE] A relative link resolves from the linking file's
  directory, including `../` targets.
  **Enforced via:** `tests/doc_links_spec.sh` — "passes when every reference
  resolves".
- AC-04.2: [TESTABLE] A broken relative link is reported.
  **Enforced via:** `tests/doc_links_spec.sh` — "reports a broken relative link
  with file and line".
- AC-04.3: [TESTABLE] A backticked repo path resolves from the root, and a
  missing one is reported.
  **Enforced via:** `tests/doc_links_spec.sh` — "reports a broken backticked repo
  path".
- AC-04.4: [TESTABLE] A backticked span that does not start with a top-level
  directory is not checked.
  **Enforced via:** planned test (planned).
- AC-04.5: [TESTABLE] A directory target counts as existing.
  **Enforced via:** planned test (planned).
- AC-04.6: [TESTABLE] A root-absolute link (a target starting with `/`) resolves
  against the root, not the file's directory. (Not yet met; see OQ-5.)
  **Enforced via:** planned test (planned).

## FR-05 — Output and exit codes

[TESTABLE]

Each broken reference is one line on stdout, in file order then line order:

```text
docs/page.md:7: missing missing.md
```

That is `<file relative to root>:<line>: missing <reference as written>`. After
the broken lines come a blank line and:

```text
<b> broken reference(s) (<c> checked in <f> file(s))
```

A clean run prints one line:

```text
links ok: <c> reference(s) in <f> file(s)
```

Exit codes: `0` every reference resolves, `1` at least one is broken, `2` usage
error (unknown option, `--root` without a value or not a directory). Usage
errors go to stderr through the shared library (`tk_die`). `-h` or `--help`
prints the header and exits 0.

**Acceptance Criteria:**

- AC-05.1: [TESTABLE] A clean run exits 0 and prints `links ok:` with the
  reference count.
  **Enforced via:** `tests/doc_links_spec.sh` — "passes when every reference
  resolves".
- AC-05.2: [TESTABLE] A broken reference exits 1 and prints
  `<file>:<line>: missing <ref>`.
  **Enforced via:** `tests/doc_links_spec.sh` — "reports a broken relative link
  with file and line".
- AC-05.3: [TESTABLE] The failure summary gives the broken and checked counts.
  **Enforced via:** planned test (planned).
- AC-05.4: [TESTABLE] An unknown option, or `--root` with no directory, exits 2.
  **Enforced via:** planned test (planned).
- AC-05.5: [TESTABLE] `--help` prints usage and exits 0.
  **Enforced via:** planned test (planned).

## FR-06 — The kit's own docs pass

[TESTABLE]

The kit runs this tool on itself before every commit (CONTRIBUTING, "Before you
commit"). The default run over the toolkit root MUST exit 0.

**Acceptance Criteria:**

- AC-06.1: [TESTABLE] `bin/check-doc-links.sh` with no arguments exits 0 on the
  kit.
  **Enforced via:** planned test (planned). The header comment of
  `tests/doc_links_spec.sh` says the kit's docs must pass, but no example runs
  the tool on the real tree yet.

## FR-07 — Dialect and side effects

[STRUCTURAL]

Bash 3.2 and stock macOS tools only (`find`, `awk`, `sed`, `sort`), per P-7. It
sources the shared library for the toolkit root and error helpers. It makes no
network calls and writes nothing.

**Acceptance Criteria:**

- AC-07.1: [TESTABLE] The script runs under `/bin/bash` 3.2.
  **Enforced via:** `tests/doc_links_spec.sh` under ShellSpec, which runs with
  `/bin/bash` (`.shellspec`).
- AC-07.2: [STRUCTURAL] No associative arrays, `mapfile` or case-modification
  expansion.
  **Enforced via:** inspection (constitution AIP-05).
- AC-07.3: [STRUCTURAL] No network access and no writes.
  **Enforced via:** inspection.

---

## Architecture-Incompatible Patterns

**AIP-01: Fetching web links.** Checking `https` targets over the network makes
the result depend on the network and on third-party sites, and makes a
pre-commit check slow and flaky. **Enforced via:** FR-03; reviewer check.

**AIP-02: Treating every backticked word as a path.** Specs are full of code
spans that are commands, keys or values. Checking all of them buries real
breaks in noise. Only spans that start with a top-level directory are paths.
**Enforced via:** AC-04.4.

**AIP-03: A file-wide or directory-wide opt-out.** The `(planned` marker works
per line so that one planned file cannot hide a broken link elsewhere in the
same document. A marker that exempts a whole file or folder would. **Enforced
via:** AC-02.1; reviewer check.

**AIP-04: A checker that repairs.** Rewriting links or creating stub files to
make a run pass hides the rename that broke them. **Enforced via:** AC-07.3.

**AIP-05: Silent success on bad input.** Printing `links ok` when a named file
was not found. **Enforced via:** AC-01.4 (not yet met).

---

## Open Questions

**OQ-1: A missing file argument still passes.** A typo'd file name prints a
warning, is counted in the file total, and the run can report `links ok` with
exit 0. Leaning: exit 2 when any named file is missing.

**OQ-2: File arguments ignore the working directory.** Arguments resolve against
the root, which keeps P-3. But shell globs expand from the working directory, so
running the tool from `docs/` with a glob gives "no such file" warnings (and,
per OQ-1, a pass). Options: (a) resolve relative arguments against the working
directory when they exist there, else against the root; (b) keep root-relative
and fail on missing files (OQ-1). Leaning: (b), which is simpler and still
catches the mistake.

**OQ-3: Only backtick fences are recognised.** A tilde fence is read as prose,
so paths in it are checked. The kit uses only backtick fences today. Leaning:
add tilde fences when a doc first needs one.

**OQ-4: Unknown URL schemes are treated as files.** Only four schemes are
skipped, so an `ftp:`, `tel:` or `x-man-page:` link is reported missing.
Leaning: skip any target that starts with a scheme (letters, then `:`).

**OQ-5: Root-absolute links resolve wrongly.** A target that starts with `/` is
joined to the file's directory. Options: resolve against the root, or report it
as a style error. Leaning: resolve against the root.

**OQ-6: Parser edge cases.** Link targets that contain `)` are cut short; a link
written inside an inline code span is still checked as a link; a code span
written with double backticks is not recognised; a span with a line suffix
(a path followed by a colon and a line number) is checked as a path and reported
missing. None occur in the kit today. Leaning: leave them until one does, and
add a test when fixing.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-09-27 | Initial spec, written from the existing implementation. |
| 0.2 | 2026-09-28 | FR-03 step 5: backticked local-only paths (`config/customers.yaml`, `reference/autopkg-wiki/`) are skipped; AC-03.5. |
