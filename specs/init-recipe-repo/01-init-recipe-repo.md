# Repo Initialization

**Status:** Draft
**Date:** 2026-08-31
**Requires:** `specs/toolkit/00-constitution.md`, `specs/toolkit/01-toolkit-common.md`

---

## Purpose

Governs the frontend that creates the directory shape a recipe repo must have
for the toolkit to operate on it. Without it, a new repo has to be assembled by
hand from prose, and the resolution routine rejects anything missing the marker
directory.

### Normative vs. Informative

- **Normative:** the created shape, the sibling invariant, exclusion of the
  vendor cache from version control, idempotency, post-creation verification.
- **Informative:** the specific directory names, the generated README's wording,
  and the default vendor-cache value.

---

## FR-01 — Created shape

[TESTABLE]

The tool MUST create a recipe directory and a vendor-cache directory such that
the vendor cache is reachable from a recipe at `<marker>/<Vendor>/<App>/` by
ascending exactly three levels.

**Acceptance Criteria:**

- AC-01.1: [TESTABLE] After a run, the target is identified as a recipe repo by
  the shared routine.
  **Enforced via:** automated test — run, then assert the identification routine
  succeeds. *The tool already performs this check itself; the test asserts it is
  not vacuous.*
- AC-01.2: [TESTABLE] The path formed by `<target>/<marker>/V/A/../../../<cache>`
  normalizes to `<target>/<cache>` and that directory exists.
  **Enforced via:** automated test — compute with a path-normalization utility,
  assert existence. *Do not verify by reading the string; the defect class here
  is miscounted levels.*
- AC-01.3: [TESTABLE] The shape is created correctly at any prefix depth.
  **Enforced via:** automated test — at least three targets of differing depth,
  including one nested five or more levels.

## FR-02 — Vendor cache placement is a parameter

[TESTABLE]

The vendor-cache path MUST be settable relative to the repo root, because more
than one layout is in use and a recipe's path is literal.

**Acceptance Criteria:**

- AC-02.1: [TESTABLE] Absent the parameter, the default nested layout is created.
  **Enforced via:** automated test.
- AC-02.2: [TESTABLE] With a flat value supplied, the cache is a direct sibling
  of the marker directory.
  **Enforced via:** automated test.
- AC-02.3: [TESTABLE] An absolute value is rejected with a non-zero exit.
  **Enforced via:** automated test. *An absolute cache path breaks the relative
  arithmetic every recipe depends on.*
- AC-02.4: [TESTABLE] The exclusion entry matches the first path segment of the
  supplied value.
  **Enforced via:** automated test — assert the ignore file contains the leading
  segment for both a nested and a flat value.
- AC-02.5: [TESTABLE] The generated README states which layout the repo uses.
  **Enforced via:** automated test — assert the value appears in the README.

## FR-03 — Vendor cache is excluded from version control

[TESTABLE]

The vendor cache holds installers and extracted payloads: re-sourced and
re-extracted by command, never authored. Per the repository tracking rule, it
MUST be excluded.

**Acceptance Criteria:**

- AC-03.1: [TESTABLE] A fresh run produces an ignore file excluding the cache.
  **Enforced via:** automated test — create a file under the cache, assert it
  does not appear as a candidate for tracking.
- AC-03.2: [TESTABLE] An existing ignore file already excluding the cache is left
  byte-identical.
  **Enforced via:** automated test — checksum before and after.
- AC-03.3: [TESTABLE] An existing ignore file not excluding the cache is appended
  to, preserving all prior content.
  **Enforced via:** automated test — assert prior lines present and the new entry
  added.

## FR-04 — Idempotency

[TESTABLE]

Re-running MUST be safe. The tool creates what is missing and reports what
exists; it MUST NOT overwrite user content.

**Acceptance Criteria:**

- AC-04.1: [TESTABLE] A second run exits zero and creates nothing new.
  **Enforced via:** automated test — snapshot the tree, re-run, compare.
- AC-04.2: [TESTABLE] An edited README survives a re-run unchanged.
  **Enforced via:** automated test — modify, re-run, checksum.
- AC-04.3: [TESTABLE] Output distinguishes created from pre-existing items.
  **Enforced via:** automated test — assert distinct markers.

## FR-05 — Optional version control initialization

[TESTABLE]

Where the tool offers to initialize version control, failures MUST be reported,
not swallowed. A repository left without an initial commit and without
explanation is worse than none.

**Acceptance Criteria:**

- AC-05.1: [TESTABLE] With identity configured, a repo and an initial commit are
  produced.
  **Enforced via:** automated test — assert one commit exists.
- AC-05.2: [TESTABLE] With identity absent, the tool exits zero but emits a
  warning naming the likely cause and the commands to finish by hand.
  **Enforced via:** automated test — run with an empty config environment,
  assert warning text.
- AC-05.3: [TESTABLE] The default branch name is normalized rather than
  inherited from the VCS version.
  **Enforced via:** automated test — assert the branch name.
- AC-05.4: [TESTABLE] An already-initialized target is detected and left alone.
  **Enforced via:** automated test — pre-initialize, run, assert commit count
  unchanged.
- AC-05.5: [TESTABLE] Absence of the VCS binary is reported as a skipped step,
  not a hard failure — the directory shape is still valid without it.
  **Enforced via:** automated test — invoke with an empty `PATH` for that binary.

## FR-06 — Post-creation verification

[STRUCTURAL]

The tool MUST verify its own output using the same routine the rest of the
toolkit uses, and MUST NOT report success if that check fails.

**Acceptance Criteria:**

- AC-06.1: [STRUCTURAL] The verification calls the shared identification routine
  rather than re-implementing the check.
  **Enforced via:** inspection.
- AC-06.2: [TESTABLE] If creation is sabotaged, the tool exits non-zero rather
  than reporting success.
  **Enforced via:** automated test — make the target read-only mid-run.

---

## Architecture-Incompatible Patterns

**AIP-01: Creating recipe content.** Seeding example recipes into the new repo.
The tool creates shape, not content; a stub recipe would be linted, fail, and
confuse. **Enforced via:** automated test — assert no recipe files created.

**AIP-02: Assuming the repo root is a VCS root.** Requiring or implying that the
repo root coincides with a version-control root. Nothing in resolution depends
on it. **Enforced via:** automated test — initialize inside an existing checkout
without the VCS option; assert success.

**AIP-03: Hardcoding the vendor cache.** Violates FR-02 and silently produces
recipes pointing at a path the target repo does not use. **Enforced via:**
AC-02.2.

**AIP-04: Tracking the vendor cache.** Violates FR-03 and the tracking rule.
**Enforced via:** AC-03.1.

---

## Open Questions

**OQ-1:** Should the tool offer to create a first recipe from a template? It
would shorten the path from empty repo to working recipe, but it conflicts with
AIP-01 and puts template selection in a tool whose job is directory shape.
Leaning: no — the completion message already names the copy command.

**OQ-2:** Should it record the chosen vendor-cache layout somewhere machine-
readable, so recipe-generating tools could read it instead of being told again?
It would remove a class of mismatch where a repo uses one layout and a generated
recipe another. Cost is a new config file and a new source of drift. Leaning:
yes, worth a follow-on spec.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-08-31 | Initial release. FR-05 written against defects where VCS failures were swallowed and the branch name inherited. |
