# Package Analysis

How to classify a `.pkg` file as vendor-originated or custom-built, identify the recipe pattern it matches, and extract metadata.

## Quick Reference

### At a Glance

| Signal | Vendor | Custom |
|--------|--------|--------|
| Identifier | `com.vendor.app` (reverse-domain) | The org's own namespace, or a non-standard string |
| Signature | Signed, ideally by a known vendor team ID | Unsigned |
| Payload | `.app` in `/Applications/` | Scripts, configs, no app bundle |
| Filename | `Vendor-App-Version.pkg` | `ORG-App-Description.pkg` |
| Install location | `/Applications/` | `/Users/Shared/`, `/Library/`, `/tmp/` |

### One Command

```bash
bin/analyze-package.sh package.pkg
bin/analyze-package.sh package.pkg --output json          # machine-readable
bin/analyze-package.sh package.pkg --customer acme       # with customer heuristics
bin/analyze-package.sh package.pkg --clues clues.yaml     # explicit heuristics file
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Classification determined (high/medium confidence) |
| 1 | Low confidence — manual review needed |
| 2 | Usage error, missing file, not a flat package, invalid `clues.yaml`, or extraction failure |

---

## Walkthrough

### Step 1 — Quick check by metadata only

Metadata extraction (identifier, version, signature, install location) is fast and doesn't need root:

```bash
bin/analyze-package.sh ~/Downloads/SomeApp-2.1.pkg
```

The output tells you right away if this looks like a vendor package (`com.microsoft.*`, signed) or a custom build (`acmeinternalapp`, unsigned).

### Step 2 — Understand the signals

The tool scores signals in three weight classes:

- **Strong** — identifier reverse-domain match (or the org's own namespace, which counts as custom), signature, known vendor prefix, known vendor team ID
- **Medium** — filename pattern, org code in the identifier or filename, the org's legacy identifier pattern, app bundles in payload, unusual install location or payload path
- **Low** — presence of installer scripts

Two or more strong signals agreeing = high confidence. Mixed strong signals = low confidence.

### Step 3 — Add customer context

For better results, provide a `clues.yaml` with known vendor identifiers, team IDs, filename patterns and the org's own signals ([FORMATS §2](FORMATS.md#2-customernamecluesyaml)):

```bash
bin/analyze-package.sh package.pkg --customer acme
```

This reads `customer/acme/clues.yaml` automatically. Without it, only the generic heuristics apply (reverse-domain, the org's namespace, signature, payload). A distribution package is read through its components.

### Step 4 — Use JSON output for automation

```bash
bin/analyze-package.sh package.pkg --output json | jq '.classification'
```

Tool-friendly JSON is designed for LLM consumption and scripting — one valid JSON object per invocation.

### Step 5 — Classify the result

The tool recommends a recipe pattern:

| Classification | Pattern | Approach |
|----------------|---------|----------|
| Vendor-originated | 4 | Ship as-is with PkgCopier |
| Vendor-originated (has URL) | 5 | URLDownloader + PkgCopier |
| Custom build | 6 | Reverse-engineer with `pkg-reverse.sh` |
| Unknown / contradictory | — | Manual investigation required |

The recommendation is informational — you make the final call.

### If the tool recommends Pattern 6 (rebuilt)

```bash
sudo bin/pkg-reverse.sh package.pkg --dest build/vendor_cache/Vendor/
bin/blueprint-to-recipe.sh --blueprint build/.../blueprint.conf --out recipes/Vendor/App
```

---

## Also See

- [`specs/analysis/analyze-package/01-analyze-package.md`](../specs/analysis/analyze-package/01-analyze-package.md) — full feature specification
- [`bin/analyze-package.sh`](../bin/analyze-package.sh) — the tool itself
- [`specs/method/00-methodology.md`](../specs/method/00-methodology.md) — the 8-step per-package workflow
