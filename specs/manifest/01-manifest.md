# Manifest Generation and Verification

**Status:** Draft
**Date:** 2026-08-31
**Requires:** `specs/toolkit/00-constitution.md`, `specs/toolkit/01-toolkit-common.md`

---

## Purpose

Governs the pair of frontends that record and verify checksums for a recipe
repo's tracked content. The manifest exists because handoff drift — files that
did not survive a transfer, or arrived stale — was the single largest time sink
in the batch this toolkit was built from. Its job is to make "did everything
actually land?" answerable in one command instead of by spot-checking.

### Normative vs. Informative

- **Normative:** what is covered, the distinction between failure kinds, exit
  semantics, and the requirement of a single implementation.
- **Informative:** the digest algorithm, the manifest filename, and the file
  format.

---

## FR-01 — Single implementation

[STRUCTURAL]

Checksum computation and comparison MUST exist in exactly one place. Two
implementations of the same digest logic drift, and drift in the drift-detector
is a failure with no backstop.

**Acceptance Criteria:**

- AC-01.1: [STRUCTURAL] No second component computes or compares manifest
  digests.
  **Enforced via:** lint rule — grep for digest invocation outside the manifest
  frontends; any hit outside the pair fails. *A duplicate implementation existed
  and was removed; this rule prevents its return.*
- AC-01.2: [STRUCTURAL] Components needing verification invoke the frontend
  rather than reimplementing it.
  **Enforced via:** inspection.

## FR-02 — Coverage

[TESTABLE]

The manifest MUST cover repo content that was authored, and MUST NOT cover
regenerable working scratch. Per the tracking rule: the test is whether losing
the file costs thought or merely a command.

**Acceptance Criteria:**

- AC-02.1: [TESTABLE] Recipe files under the marker directory are covered at any
  depth.
  **Enforced via:** automated test — fixture with nested recipes, assert each
  path appears.
- AC-02.2: [TESTABLE] The vendor cache is excluded.
  **Enforced via:** automated test — place a file in the cache, assert absence
  from the manifest.
- AC-02.3: [TESTABLE] The manifest never lists itself.
  **Enforced via:** automated test — assert its own name absent.
- AC-02.4: [TESTABLE] Platform metadata files are excluded.
  **Enforced via:** automated test — create one, assert absence.
- AC-02.5: [TESTABLE] Ordering is deterministic, so that two runs over unchanged
  content produce byte-identical output.
  **Enforced via:** automated test — generate twice, compare checksums of the
  manifests themselves.

## FR-03 — Verification distinguishes failure kinds

[TESTABLE]

Verification MUST separate *changed* from *absent*, because they mean different
things: a mismatch is an edit, a missing file is an incomplete transfer.

**Acceptance Criteria:**

- AC-03.1: [TESTABLE] An unchanged tree verifies clean and exits zero.
  **Enforced via:** automated test.
- AC-03.2: [TESTABLE] A modified file is reported as mismatched, by path.
  **Enforced via:** automated test — append a byte, assert classification.
- AC-03.3: [TESTABLE] A removed file is reported as missing, by path, and not as
  mismatched.
  **Enforced via:** automated test — delete, assert classification.
- AC-03.4: [TESTABLE] Both kinds present are reported separately with per-kind
  counts.
  **Enforced via:** automated test.
- AC-03.5: [TESTABLE] Any failure yields a non-zero exit.
  **Enforced via:** automated test — assert exit code for each kind.

## FR-04 — Detection of unlisted files

[TESTABLE]

A file present on disk but absent from the manifest is invisible to a
comparison that iterates the manifest. Drift in the "something was added"
direction MUST be detectable.

**Acceptance Criteria:**

- AC-04.1: [TESTABLE] In strict mode, a covered-scope file absent from the
  manifest is reported as unlisted.
  **Enforced via:** automated test — add a recipe without regenerating, assert
  report.
- AC-04.2: [TESTABLE] Outside strict mode, that file produces no finding.
  **Enforced via:** automated test — same fixture, assert clean.
- AC-04.3: [TESTABLE] An unlisted file in strict mode yields a non-zero exit.
  **Enforced via:** automated test.
- AC-04.4: [TESTABLE] Files outside covered scope are never reported as unlisted,
  in either mode.
  **Enforced via:** automated test — place a file in the vendor cache, assert no
  finding under strict.
- AC-04.5: [TESTABLE] The unlisted report names the remedy — regeneration.
  **Enforced via:** automated test — assert remedy text present.

## FR-05 — Missing manifest

[TESTABLE]

Verification against a repo with no manifest MUST be distinguishable from
verification that passed.

**Acceptance Criteria:**

- AC-05.1: [TESTABLE] Absent manifest → non-zero exit and a message naming the
  expected location.
  **Enforced via:** automated test.
- AC-05.2: [TESTABLE] Verification never creates a manifest as a side effect.
  **Enforced via:** automated test — assert absence after a failed run.

## FR-06 — Round-trip

[TESTABLE]

The two frontends MUST agree: anything one records, the other verifies.

**Acceptance Criteria:**

- AC-06.1: [TESTABLE] Generate then verify on an unchanged tree passes,
  including under strict mode.
  **Enforced via:** automated test.
- AC-06.2: [TESTABLE] Round-trip holds for paths containing spaces and non-ASCII
  characters.
  **Enforced via:** automated test — fixture with such names. *Both sides split
  on a fixed separator; this is the boundary where that assumption fails.*
- AC-06.3: [TESTABLE] Round-trip holds at every depth the marker directory
  permits.
  **Enforced via:** automated test — nested fixture.

## FR-07 — Repo resolution

[STRUCTURAL]

Both frontends resolve their target per `01-toolkit-common.md` FR-03 and MUST
NOT assume a fixed position relative to the toolkit.

**Acceptance Criteria:**

- AC-07.1: [STRUCTURAL] Neither derives the repo root from its own location.
  **Enforced via:** inspection. *Both previously assumed they lived inside the
  repo they operated on, which is false for a standalone toolkit.*
- AC-07.2: [TESTABLE] Both operate correctly when invoked from an unrelated
  working directory.
  **Enforced via:** automated test — invoke from `/`, assert the manifest lands
  in the repo.

---

## Architecture-Incompatible Patterns

**AIP-01: A second digest implementation.** See FR-01. **Enforced via:** AC-01.1.

**AIP-02: Loading whole files into memory to digest them.** Fine for text,
unbounded if coverage ever includes binaries. Stream instead. **Enforced via:**
reviewer check.

**AIP-03: Auto-regenerating on verification failure.** Makes the check
unfalsifiable. Verification reports; it does not repair. **Enforced via:**
AC-05.2.

**AIP-04: Covering the vendor cache.** Digesting large binaries the tracking
rule excludes, coupling the manifest to content that is not version-controlled.
**Enforced via:** AC-02.2.

**AIP-05: Treating missing as mismatched.** Collapses FR-03's distinction and
misdirects the reader toward "who edited this" when the answer is "it never
arrived." **Enforced via:** AC-03.3.

---

## Open Questions

**OQ-1:** Should coverage be configurable? Currently fixed. Configurability
would let a repo cover documentation directories, but a manifest whose scope
varies per repo is harder to reason about across a handoff. Leaning: keep fixed
until a second repo layout needs it.

**OQ-2:** Should strict mode be the default? It catches a real drift direction
the default misses. Against: it fails on legitimately-in-progress work, which
would train people to skip verification. Leaning: keep opt-in, but have the
non-strict summary state that unlisted files were not checked.

**OQ-4:** How should the distribution builder obtain a manifest without
violating FR-01? Its coverage differs from a recipe repo's, so it cannot call
the generator unchanged. Options: (a) parameterize the generator's coverage and
have the builder call it; (b) extract the digest step into the shared library and
have both call that; (c) accept the duplication and narrow FR-01 to the recipe-
repo pair. Leaning: (b) — the shared library already exists and the duplicated
logic is three lines.

**OQ-3:** Should generation refuse to overwrite a manifest whose verification is
currently failing? That would prevent papering over drift by regenerating. It
would also block the legitimate case of recording deliberate changes. Leaning:
warn rather than refuse.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-08-31 | Initial release. FR-01 records the removal of a duplicate implementation; FR-04 records the blind spot both implementations shared. |
