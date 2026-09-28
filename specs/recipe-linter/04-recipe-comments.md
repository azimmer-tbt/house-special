# Recipe Comments Standard

**Status:** Draft
**Date:** 2026-09-12
**Requires:** `00-constitution.md`, `01-rule-definitions.md`

---

## Purpose

Define the standard for the `Comment:` YAML field in recipe files and the inline `#` comment convention for `Process:` blocks. Every recipe in a recipe repo the kit lints must conform to this standard.

### Classification Key

- **[TESTABLE]** — Observable and automatable. Enforcement mechanism stated.
- **[STRUCTURAL]** — Enforced by schema, layout, or data model constraint.
- **[ADVISORY]** — Review judgment. Reserved for genuine non-checkables.

---

## 1. The `Comment:` Field

### 1.1 Purpose

[STRUCTURAL] The `Comment:` field is the first thing an operator or agent sees when reading a recipe. It must answer: "what pattern is this, and why?"

Every recipe file (download and pkg) MUST have a `Comment:` that includes:

1. **Pattern number** (e.g. 2, 4, 4a, 4b, 4c, 4d, 5, 6, 6a, 6b, 6c, 6d, 7, 8)
2. **Why this pattern was chosen** — one sentence describing the data flow
3. **Any choice that would be breakable if changed** — e.g. "distribution package, not component — Copier instead of FlatPkgUnpacker"

### 1.2 Format

[STRUCTURAL]

```
Comment: Pattern <N> (<brief reason>). <Key constraint>.
```

**AC-1.2.1:** [TESTABLE] The Comment value starts with the literal word `Pattern`, followed by a space, then a positive integer, optionally followed by a lowercase letter. **Enforced via:** lint rule CMT-003.

**AC-1.2.2:** [STRUCTURAL] Comment ends with a period, or a parenthetical period if the constraint is parenthetical. No trailing punctuation rule is enforced — the period is a convention, not a checkable requirement.

### 1.3 Per-Pattern Comment Templates

#### Pattern 4a — Vendor-Drop PKG (Copier, distribution package)

Download recipe:
```yaml
Comment: Pattern 4 vendor-drop pkg. URLDownloader with file:// URI for vendor_cache staging.
```

Pkg recipe:
```yaml
Comment: Pattern 4 vendor-drop pkg. Copier bit-for-bit copy (distribution package — PkgCopier cannot handle).
```

#### Pattern 4a — Vendor-Drop PKG (Copier, simple flat pkg)

When the pkg is a simple component pkg (not a distribution):

```yaml
Comment: Pattern 4 vendor-drop pkg. Copier bit-for-bit copy.
```

#### Pattern 4b — Vendor-Drop DMG (Copier + PkgCreator)

Download recipe:
```yaml
Comment: Pattern 4 (DMG source). URLDownloader stages DMG from vendor_cache, Copier mounts DMG natively for app extraction.
```

Pkg recipe:
```yaml
Comment: Pattern 4 (DMG source). PkgCreator with chown block.
```

#### Pattern 4c — Vendor-Drop DMG with Ridealong Scripts

Download recipe:
```yaml
Comment: Pattern 4 (DMG source). URLDownloader stages DMG + scripts + payload from vendor_cache.
```

Pkg recipe:
```yaml
Comment: Pattern 4 (DMG source). PkgCreator with scripts + payload injection.
```

#### Pattern 5 — Distribution Package (Copier)

Download recipe:
```yaml
Comment: Pattern 5 distribution package. URLDownloader with file:// URI for vendor_cache staging.
```

Pkg recipe:
```yaml
Comment: Pattern 5 distribution package. Copier bit-for-bit copy (FlatPkgUnpacker cannot handle distribution packages).
```

#### Pattern 6a — Rebuilt, Flat Payload

Download recipe:
```yaml
Comment: Pattern 6a rebuilt package — payload extracted from existing installer. URLDownloader + Unarchiver for payload archive.
```

Pkg recipe:
```yaml
Comment: Pattern 6a rebuilt package. PkgCreator with chown block (payload extracted without root).
```

#### Pattern 6b — Rebuilt, Payload + Scripts

Download recipe:
```yaml
Comment: Pattern 6b rebuilt package — payload+scripts extracted from existing installer. URLDownloader + Unarchiver for payload and scripts archives.
```

Pkg recipe:
```yaml
Comment: Pattern 6b rebuilt package. PkgCreator with scripts + postinstall.
```

#### Pattern 6c — Rebuilt, Single File with Specific Mode

Pkg recipe:
```yaml
Comment: Pattern 6c rebuilt package. PkgCreator restoring 0400 ownership on single file.
```

#### Pattern 6d — Rebuilt, Payloadless (Script-Only)

Pkg recipe:
```yaml
Comment: Pattern 6d rebuilt package. PkgCreator with scripts only (no payload).
```

#### Pattern 7 — Faux Vendor DMG

Download recipe:
```yaml
Comment: Pattern 7 faux vendor DMG — app extracted from in-house Composer snapshot. URLDownloader stages DMG from vendor_cache.
```

Pkg recipe:
```yaml
Comment: Pattern 7 faux vendor DMG. PkgCreator with DMG-extracted .app.
```

### 1.4 The claim must match the recipe

[TESTABLE] The pattern in the `Comment:` must be the one the recipe's processors
actually implement. Labels drift: a template example labelled 6a (flat payload)
shipped install scripts, which makes it 6b, and nothing caught it until the
classifier was rebuilt (methodology lesson 26).

**AC-1.4.1:** [TESTABLE] A `Comment:` whose pattern differs from the classifier's
verdict (or its alternatives, when uncertain) raises a warning naming both.
**Enforced via:** lint rule CMT-004 (type `classification`, rule-definitions §2.8).

---

## 2. Inline `#` Comments

### 2.1 Purpose

[ADVISORY] Every processor step SHOULD have a `#` comment above it explaining:
- WHY this processor is needed (not what it does — that is the processor name)
- WHAT could go wrong if this step is removed or reordered

### 2.2 Format

[ADVISORY]

```yaml
  # <reason this processor is needed>
  # <what could break if removed>
  - Processor: <ProcessorName>
    Arguments:
```

Each comment block covers one processor step. Multi-line comments are acceptable if the rationale needs more space.

### 2.3 Examples

Good — PkgCreator with chown:
```yaml
  # Build the org-prefixed package with restored ownership from BOM
  - Processor: PkgCreator
```

Good — Copier on distribution package:
```yaml
  # Copier instead of PkgCopier: distribution package, PkgCopier cannot handle.
  # URLDownloader saves to downloads/ subdirectory.
  - Processor: Copier
```

---

## 3. Lint Rule Mappings

The following rules in `config/checks.yaml` enforce the requirements in this spec:

| Rule ID | Target | Type | Severity | Applies To |
|---------|--------|------|----------|------------|
| CMT-001 | `Comment` key exists | `exists` | `warning` | Download recipes |
| CMT-002 | `Comment` key exists | `exists` | `warning` | Pkg recipes |
| CMT-003 | Comment starts with `Pattern <N>` | `regex` | `warning` | Both recipe types |
| CMT-004 | Comment's pattern matches the classification | `classification` | `warning` | Both recipe types |

---

## 4. Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-09-12 | Initial release — Comment field standard, inline comment convention, pattern templates, lint rule mappings |
| 1.1 | 2026-09-27 | §1.4 and CMT-004: the claimed pattern must match what the processors do |
