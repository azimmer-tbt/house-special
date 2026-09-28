---
name: spec-creation
description: The methodology for writing and hardening tool specs in specs/<family>/ — constitution plus numbered feature specs with classified, enforceable acceptance criteria. Use when someone says "write a spec", "spec this tool first", "harden this spec", "add acceptance criteria", or before building or changing a tool's behaviour.
---
# Spec Creation

## When to use

- A new tool or behaviour (CONTRIBUTING rule 3: spec first).
- Adding a numbered spec to an existing `specs/<family>/` directory.
- Hardening a spec: classifying ACs, naming enforcement, adding AIPs.
- Reviewing a spec for completeness before implementation.

## Inputs

- The tool's purpose and the behaviour to pin down.
- Existing specs for the tool: `specs/<family>/00-constitution.md` and `NN-*.md`.
- For linter work, the runtime rules in [`config/checks.yaml`](../../config/checks.yaml)
  (config lives in `config/`, never in `specs/`).

## Steps

1. **Constitution (`00-constitution.md`)** — answers "what kind of tool is this?",
   not "what features does it have?". It holds numbered, standalone, inviolable
   principles; an **enforcement line** wherever a principle could be violated by an
   implementer who believes they complied (name the lint rule, test or reviewer
   check); and a dated amendment history with rationale. It does *not* hold
   features, schemas, code, or tool/file names in binding requirements.
2. **Feature specs (`NN-name.md`, 01+)** — detailed enough that a modest model can
   implement without fundamental errors. Use this skeleton:
   ```markdown
   # <Tool> — <Title>
   **Status:** Draft | Hardened | Amended   **Date:** YYYY-MM-DD
   **Requires:** `00-constitution.md` [, `NN-other.md`]
   ## Purpose            (one paragraph; Normative vs Informative; classification key)
   ### FR-NN — <title>   [STRUCTURAL] | [TESTABLE] | [ADVISORY]
   **Acceptance Criteria:**
   - AC-NN.1: [TESTABLE] <observable behaviour>. **Enforced via:** <mechanism>
   ## Architecture-Incompatible Patterns   (AIP-01: <name>. why; what it violates; enforcement)
   ## Open Questions     (OQ-1: options and leaning)
   ## Version History    (| Version | Date | Change |)
   ```
3. **Partition normative from informative.** MUST/MUST NOT covers behaviours,
   invariants, data contracts and wire formats. Tool choices, thresholds and file
   layouts are informative: a conforming implementation may replace them.
   *Behaviour is normative; tools are informative* — the one exception is an interop
   format a third party must match.
4. **Write the ACs** by these rules:
   1. Every AC carries exactly one tag: `[TESTABLE]`, `[STRUCTURAL]`, `[ADVISORY]`.
   2. `[TESTABLE]` = a command gives a deterministic yes/no, and the AC names its
      mechanism (input → expected observable). Can't name one? It's probably ADVISORY.
   3. `[STRUCTURAL]` = enforced by schema, layout or lifecycle; checked by inspection.
      Schema/front-matter requirements are STRUCTURAL.
   4. `[ADVISORY]` = genuine review judgment. A hardened spec has very few.
   5. Observable behaviour, not design assertion ("shows conflicts", not "is intuitive").
5. **Write AIPs** — the negative space: memorable name, why it's incompatible, the
   principle/FR it violates, enforcement if any. The mistakes a careful-but-new
   implementer would make.
6. **Wire enforcement**: each `[TESTABLE]` AC gets a ShellSpec example in
   `tests/<tool>_spec.sh` (runs under `/bin/bash` 3.2); cite the AC ID in the example
   name. Known gaps go in [`docs/known-issues.md`](../../docs/known-issues.md) and the
   AC says "(Not yet met; see KI-N)".

## Outputs

```
specs/<family>/
  00-constitution.md     # principles (Level 1)
  NN-name.md             # feature/subsystem specs (Level 2)
  artifacts/             # example and malformed inputs for tests (optional)
tests/<tool>_spec.sh     # ShellSpec examples enforcing the TESTABLE ACs
config/<tool>.yaml       # runtime config, if the tool has any (e.g. config/checks.yaml)
```

## Verify

- `grep -c 'AC-' specs/<family>/NN-*.md` matches the tagged count; no untagged ACs.
- Every `[TESTABLE]` AC has a matching test, and `shellspec` passes.
- `bin/check-doc-links.sh specs/<family>/*.md` exits 0.

## Pitfalls

- Features creeping into the constitution; tool names in binding requirements.
- ACs that restate design intent instead of an observable.
- Test IDs that collide with section numbers (see KI-3(c)).
- A spec that drifts from the code: when behaviour changes, amend the spec and its
  version history in the same change.

## References

- Existing examples: [`specs/recipe-linter/`](../../specs/recipe-linter/00-constitution.md),
  [`specs/pkg-compare/01-pkg-compare.md`](../../specs/pkg-compare/01-pkg-compare.md),
  [`specs/analysis/analyze-package/01-analyze-package.md`](../../specs/analysis/analyze-package/01-analyze-package.md)
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md), [`.devagent/standards/shellspec.md`](../standards/shellspec.md)
