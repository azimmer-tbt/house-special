# analyze-package.sh — Package Classifier

**Status:** Draft
**Date:** 2026-09-08
**Requires:** `specs/analysis/00-constitution.md`
**Implementation:** `lib/python/recipekit/analyze_package.py` (with `pkg.py`); `bin/analyze-package.sh` is the front end. **Tests:** `tests/python/test_analyze_package.py`, `tests/analyze_package_spec.sh`.

---

## Purpose

Given a `.pkg` file, classify it as vendor-originated or custom-built, identify the recipe pattern it matches, and output structured metadata (text or JSON). This is the entry point for Phase 1 Research.

### Normative vs. Informative

- **Normative (MUST/MUST NOT):** CLI interface, output sections, classification signals, confidence levels, exit codes, and all acceptance criteria.
- **Informative:** specific output formatting details, example values. A conforming implementation may format text output differently as long as the normative contracts are satisfied.

### Classification Key

- **[TESTABLE]** — Observable and automatable. Enforcement mechanism stated.
- **[STRUCTURAL]** — Enforced by schema, layout, or data model constraint.
- **[ADVISORY]** — Review judgment. Reserved for genuine non-checkables.

---

## 1. Command-Line Interface

### FR-1 — Argument Parsing

[STRUCTURAL]

The tool accepts a `.pkg` file path and optional flags:

| Flag | Argument | Required | Description |
|------|----------|----------|-------------|
| `path` (positional) | File path | Yes | Path to the `.pkg` file to analyze |
| `--output` | `text` or `json` | No | Output format; default `text` |
| `--clues` | File path | No | Path to `clues.yaml`; if absent, uses stock defaults only |
| `--customer` | String | No | Customer name, looked up in `config/customers.yaml` (the folder may be inside or outside the kit) — discovers `clues.yaml` in that folder and uses the customer's org naming (its `org.yaml` over `config/org.yaml`). With no registry, `customer/<name>/` in the kit. Unknown name: exit 2, listing the registered names |
| `-h` / `--help` | — | No | Print usage and exit 0 |

**Acceptance Criteria:**

- AC-01.1: [TESTABLE] Running with only a valid `.pkg` path succeeds (text output).
- AC-01.2: [TESTABLE] Running with `--output json` produces valid JSON on stdout.
- AC-01.3: [TESTABLE] Running with `--clues nonexistent.yaml` fails with exit 2.
- AC-01.4: [TESTABLE] Running with `--customer acme` discovers `clues.yaml` in the folder the registry gives for `acme` (`customer/acme/` as shipped).
- AC-01.5: [TESTABLE] Running without a positional path prints usage and exits 2.

---

## 2. Package Metadata Extraction

### FR-2 — Extract Package Metadata

[STRUCTURAL]

From the `.pkg`, extract:

| Field | Source | Notes |
|-------|--------|-------|
| Package kind | `PackageInfo` at the root (component) or `Distribution` with `*.pkg` components | A distribution is read through its components: identifier, version and install location from the first, payload and scripts from all, every identifier kept |
| Package identifier | `pkgutil --expand-full` → `PackageInfo` attribute `identifier` | |
| Version | `PackageInfo` attribute `version` | |
| Install location | `PackageInfo` attribute `install-location` | Defaults to `/` if absent |
| Signature status | `pkgutil --check-signature` | `signed` or `unsigned` |
| Signature authority | `pkgutil --check-signature` output | First authority line (e.g., "Developer ID Installer: Microsoft Corporation (UBF8T346G9)") |
| Team ID | The authority's trailing `(XXXXXXXXXX)` | Empty when unsigned or absent |

**Acceptance Criteria:**

- AC-02.1: [TESTABLE] A signed package reports both status and authority correctly.
- AC-02.2: [TESTABLE] An unsigned package reports `unsigned` with empty authority.
- AC-02.3: [TESTABLE] A package with no explicit install-location defaults to `/`.
- AC-02.4: [TESTABLE] A distribution reports its first component's identifier and lists every component's. **Enforced via:** `test_analyze_package.py` `test_a_distribution_is_read_through_its_component`.
- AC-02.5: [TESTABLE] A missing file, or a file `pkgutil --expand-full` can't expand, exits 2. **Enforced via:** `test_ac_08_3_missing_file_and_non_package_exit_2`.

---

## 3. Payload Analysis

### FR-3 — Analyze Payload Contents

[TESTABLE]

Extract the payload and report:

| Field | Detection |
|-------|-----------|
| File count | Regular files, every depth |
| Directory count | Directories, the payload root included, not following symlinks |
| Symlink count | Symlinks (to files or directories) |
| `.app` bundles found | Directories named `*.app`, up to 10 levels deep |
| Payload size | `du -sh` / `du -sm` of the expanded payload |

**Acceptance Criteria:**

- AC-03.1: [TESTABLE] An empty package reports 0 files, 0 dirs, 0 symlinks, 0 apps.
- AC-03.2: [TESTABLE] A package with an .app bundle lists its name.
- AC-03.3: [TESTABLE] Symlinks in the payload are counted separately.

---

## 4. Classification Heuristics

### FR-4 — Classify Origin

[TESTABLE]

Classify as `vendor-originated` or `custom-build` using signals from `clues.yaml` and the extracted metadata.

#### Vendor-Originated Signals

| Signal | Weight | Detection |
|--------|--------|-----------|
| Identifier is reverse-domain: `^[a-z]{2,}(\.[A-Za-z0-9_-]+){2,}$`, and not in the org's own namespace | Strong | PackageInfo identifier |
| Any component's identifier matches `clues.yaml` → `vendor_identifiers` | Strong | `re.search` |
| Package is signed | Strong | `pkgutil --check-signature` |
| Signing team ID is in `clues.yaml` → `vendor_team_ids` | Strong | Team ID from the authority (KI-15) |
| Filename (without `.pkg`) matches `clues.yaml` → `vendor_filename_patterns[].pattern` | Medium | `re.search` |
| Payload contains `.app` bundles | Medium | Payload walk |

#### Custom-Build Signals

| Signal | Weight | Detection |
|--------|--------|-----------|
| Identifier is in the org's own namespace (first two segments of `identifier_prefix`, `config/org.yaml` or the customer's) | Strong | Prefix match |
| Identifier is NOT reverse-domain | Strong | Regex negative match |
| Identifier contains an org code (`custom_build_signals.org_codes`) | Medium | `re.search`, ignoring case |
| Identifier matches `custom_build_signals.non_reverse_domain_pattern` (the org's legacy shape) | Medium | `re.search`; only when set |
| Package is unsigned | Medium | `pkgutil --check-signature` |
| Filename contains an org code (when `filename_contains_org_code: true`) | Medium | `re.search`, ignoring case |
| Install location, or any payload path as installed, is at or under `custom_build_signals.unusual_install_locations` | Medium | PackageInfo and payload walk (KI-15) |
| No `.app` bundles in payload | Medium | Payload walk |
| Has scripts (preinstall/postinstall) | Low | Reported only; not scored |

#### Confidence Levels

Score each side: strong = 2, medium = 1.

| Result | Conditions |
|-------|-----------|
| **vendor-originated, high / medium** | Vendor score higher, with 2+ / 1 strong vendor signals |
| **custom-build, high / medium** | Custom score higher, with 2+ / 1 strong custom signals |
| **unknown, low** | No strong signal either way, or a winner without a strong signal |
| **contradictory, low** | Strong signals on both sides and no winner by score |

**Acceptance Criteria:**

- AC-04.1: [TESTABLE] A signed package with `com.microsoft.*` identifier classifies as `vendor-originated` with `high` confidence.
- AC-04.2: [TESTABLE] An unsigned package with a non-reverse-domain identifier containing an org code from clues.yaml (e.g. "Acme") classifies as `custom-build` (one strong signal, so `medium`).
- AC-04.3: [TESTABLE] A package with mixed signals (vendor-like identifier but unsigned, no .app) rates `low` confidence.
- AC-04.5: [TESTABLE] Each clues key changes the result as the tables say (KI-15). **Enforced via:** `test_analyze_package.py` `ClassifyTest` (AC-04.1 to AC-04.5).
- AC-04.4: [TESTABLE] Classification without `--clues` uses no customer-specific heuristics but still applies the generic reverse-domain check.

---

## 5. Pattern Recommendation

### FR-5 — Recommend Recipe Pattern

[TESTABLE]

Based on the classification, recommend:

| Classification | Pattern | Rationale |
|----------------|---------|-----------|
| Vendor-originated, ships as-is | **4** (vendor-drop) | Use PkgCopier on the vendor file — do not rebuild |
| Vendor-originated, has download URL | **5** (stable-URL) | Use URLDownloader + PkgCopier |
| Custom-build, no source files | **6** (rebuilt) | Use pkg-reverse.sh + blueprint-to-recipe.sh |
| Cannot determine | **other** | Requires human investigation |

**Acceptance Criteria:**

- AC-05.1: [TESTABLE] `vendor-originated` + signed → pattern 4.
- AC-05.2: [TESTABLE] `custom-build` → pattern 6.
- AC-05.3: [TESTABLE] `low` confidence → pattern `other` with message indicating manual review needed.
- AC-05.4: [ADVISORY] The pattern recommendation is informational — the human operator makes the final decision.

---

## 6. Output Structure

### FR-6 — Text Output Format

[STRUCTURAL]

```
=== analyze-package.sh ===
  File:         /path/to/package.pkg
  Size:         <bytes> bytes (<human>)

=== Package metadata ===
  Identifier:   <identifier>
  Version:      <version>
  Install loc:  <install-location>
  Kind:         <component|distribution (N component(s): id, …)>
  Signature:    <signed|unsigned>
  Authority:    <authority>

=== Classification ===
  Origin:       <vendor-originated|custom-build>
  Confidence:   <high|medium|low>
  Pattern:      <4|5|6|other>
  Rationale:
    - <signal description>

=== Payload summary ===
  Files:        <count>
  Dirs:         <count>
  Symlinks:     <count>
  Apps found:   <list>
  Estimated:    <size>

=== Heuristic notes ===
  - <note>
```

### FR-7 — JSON Output Format

[STRUCTURAL]

```json
{
  "file": "/path/to/package.pkg",
  "size_bytes": 14308840,
  "metadata": {
    "identifier": "com.vendor.app",
    "version": "1.0",
    "install_location": "/Applications",
    "signature": "signed",
    "authority": "Developer ID Installer: Vendor Inc. (ABCDE12345)",
    "team_id": "ABCDE12345",
    "kind": "component",
    "identifiers": ["com.vendor.app"]
  },
  "classification": {
    "origin": "vendor-originated",
    "confidence": "high",
    "pattern": 4,
    "rationale": [
      "Identifier matches reverse-domain pattern",
      "Signed by recognized vendor authority",
      "Payload contains .app at /Applications/"
    ]
  },
  "payload": {
    "files": 1456,
    "dirs": 234,
    "symlinks": 3,
    "apps_found": ["Example.app"],
    "size_mb": 143
  }
}
```

---

## 7. Exit Codes

### FR-8 — Exit Code Contract

[STRUCTURAL]

| Code | Meaning |
|------|---------|
| 0 | Analysis completed, classification determined |
| 1 | Analysis completed, but confidence is `low` or found concerning signals |
| 2 | Usage error, missing file, invalid config (a clues.yaml that isn't a YAML mapping, or holds a bad regex), unknown customer, or extraction failure |

**Acceptance Criteria:**

- AC-08.1: [TESTABLE] A clearly classified package exits 0.
- AC-08.2: [TESTABLE] An ambiguous package exits 1.
- AC-08.3: [TESTABLE] A non-existent file exits 2. *(The bash version exited 0 and classified it; fixed in the port.)*

---

## 8. Test inputs

Packages are built during the tests with `pkgbuild` and `productbuild`
(`tests/python/test_analyze_package.py`, `tests/analyze_package_spec.sh`); the
classifier is also tested on hand-made facts. The port was checked side by side
with the bash version on 28 real packages: results matched except where the bash
version was wrong (distributions read as empty, the KI-15 clues).

---

## 9. Version History

| Version | Date | Change |
|---------|------|--------|
| 1.2 | 2026-09-27 | Ported to Python (`recipekit.analyze_package`). Every clues key is used (KI-15): team IDs, org codes in the identifier, the legacy identifier pattern, unusual locations in the payload. Distributions are read through their components; `Kind:`, `team_id`, `kind`, `identifiers` added. Missing or non-package input and invalid clues exit 2. Confidence rules written as implemented. |
| 1.1 | 2026-09-27 | `--customer` resolves through the customer registry and brings the customer's org naming; AC-01.4 reworded. |
| 1.0 | 2026-09-08 | Initial release. Derived from architecture spec Spec B and the Master Enhancement Plan. |
