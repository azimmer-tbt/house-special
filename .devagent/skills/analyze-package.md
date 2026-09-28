---
name: analyze-package
description: Classify a .pkg as vendor-originated or in-house built and get a recommended recipe pattern with bin/analyze-package.sh. Use when someone says "what is this package", "who built this pkg", "analyze this installer", "which pattern is this .pkg", or hands over an inherited package.
---
# Analyze Package

## When to use

A `.pkg` arrives (inherited from a management server, emailed, found in `input/`)
and you need its origin, metadata, payload summary and a starting pattern — step 2
of [`specs/method/00-methodology.md`](../../specs/method/00-methodology.md).

## Inputs

- A path to a `.pkg`. If you only have a name, look in the customer's
  `input` / `recipe_repo.vendor_cache` from `customer/<name>/paths.yaml`
  (informational; schema [FORMATS §5](../../docs/FORMATS.md#5-customernamepathsyaml)),
  or `~/Library/AutoPkg/Cache/<identifier>/`.
- Optional customer context: `--customer <name>`, the **lowercase** folder under
  `customer/` (case-sensitive match), which loads `customer/<name>/clues.yaml`.
  `--clues <file>` overrides it.
- AutoPkg installed — the script runs AutoPkg's bundled Python (PyYAML included); override with `AUTOPKG_TOOLKIT_PYTHON`.

## Steps

1. Run the classifier:
   ```bash
   bin/analyze-package.sh /path/to/Package.pkg --customer <name>
   bin/analyze-package.sh /path/to/Package.pkg --customer <name> --output json
   ```
   Without customer context, drop `--customer`; the generic heuristics still run.
2. Read the **rationale lines**, not just the verdict. Signals:
   - strong vendor: reverse-DNS identifier (outside the org's namespace), a
     `vendor_identifiers` match, a signature, a listed `vendor_team_ids` team;
   - strong in-house: the org's own identifier namespace (`identifier_prefix` from
     `config/org.yaml` or the customer's `org.yaml`), a non-reverse-DNS identifier;
   - medium in-house: `org_codes` in the identifier or filename, the
     `non_reverse_domain_pattern` match, an unusual install location or payload
     path, no `.app` in the payload, unsigned.
   A distribution package is read through its components (`Kind:` line).
3. If confidence is `low` (exit 1), inspect by hand:
   ```bash
   pkgutil --check-signature /path/to/Package.pkg
   pkgutil --expand-full /path/to/Package.pkg /tmp/analyze-x
   find /tmp/analyze-x -name '*.app' -type d -prune
   bin/inspect-app.sh "/tmp/analyze-x/<component>/Payload/Applications/<App>.app" --output json
   ```
4. Map to a pattern with [`docs/patterns.md`](../../docs/patterns.md): the tool says
   only `4`, `5`, `6` or `other`; you choose the letter.
5. For Pattern 6, extract with ownership intact: `sudo bin/pkg-reverse.sh <pkg> --dest <dir>`.
6. Report:

   | Field | Value |
   |---|---|
   | File / size | path, MB |
   | Identifier / version | from PackageInfo |
   | Signature | `pkgutil --check-signature` result |
   | Origin / confidence | vendor-originated or custom-build; high/medium/low |
   | Pattern | number + your chosen letter |
   | Key signals | the rationale lines that decided it |

## Outputs

Text (or JSON) sections: metadata (with `Kind:`; JSON adds `team_id`, `kind`,
`identifiers`), classification + rationale, payload summary, heuristic notes
(which `clues.yaml` was used). Exit 0 = classified (high/medium), 1 = low
confidence, 2 = usage error, missing file, not a flat package, invalid
`clues.yaml` (bad YAML, not a mapping, bad regex) or extraction failure.

## Verify

- "Heuristic notes" names the `clues.yaml` you expected (a customer with no file
  warns and falls back to defaults; an invalid one exits 2).
- The payload summary lists files and `.app`s — an empty payload on a real app
  package means something is wrong.

## Pitfalls

- **KI-15 (fixed):** every `clues.yaml` key is used now, and `com.acmefruit.*`-style
  identifiers count as in-house. Rerun any old result.
- **KI-16 (fixed):** older runs never analysed the payload and rejected uppercase
  reverse-DNS identifiers; rerun any old result.
- The verdict is a heuristic built for *inherited* packages. The operator decides.
- Signatures: `pkgutil`, never `codesign`, for a `.pkg` (methodology lesson 5).
  An unsigned wrapper can still hold a signed `.app` (lesson 16).
- Org wrapper packages mixing several products: split by origin (lesson 21).

## References

- [`specs/analysis/analyze-package/01-analyze-package.md`](../../specs/analysis/analyze-package/01-analyze-package.md)
- [`docs/package-analysis.md`](../../docs/package-analysis.md), [FORMATS §2 `clues.yaml`](../../docs/FORMATS.md#2-customernamecluesyaml)
- [`docs/known-issues.md`](../../docs/known-issues.md) (KI-10, KI-15, KI-16)
- [`reference/methodology.md`](../../reference/methodology.md) (lessons 5, 16, 21)
