# Justification: Why a Vendor Cache Normalization Script

---

## The Problem

AutoPkg recipes for vendor-drop packages (Patterns 2, 4, 5, 6 — any recipe
that uses `URLDownloader` with a `file://` URI) hardcode exact filenames in
their `DOWNLOAD_URL` Input field:

```yaml
DOWNLOAD_URL: "file://%VENDOR_CACHE_ROOT%/OrchardLabs/Orchard-Analytics/Orchard Analytics 3.1 Installer.dmg"
```

This works exactly once — until the next release changes the filename.

### Why URLDownloader?

`URLDownloader` is the right processor for vendor-drop recipes because it
handles both `file://` URIs for local files and `https://` URIs for
internet-hosted files through the same interface. It is the "universal
download mechanism" the methodology settled on. Using a separate processor
for each URI scheme would duplicate logic and break the recipe pattern
consistency.

### What URLDownloader cannot do

`URLDownloader` delegates to `curl` for the actual transfer. `curl` expects
URI-encoded paths in `file://` URIs. Characters like `@`, spaces, and
parentheses must be percent-encoded (`%40`, `%20`, `%28`/`%29`). When a
vendor drops a file named `AcmeSelfService_v2.3_08_20_2026 1.pkg`, the resulting
`file://` URI breaks because `curl` has no way to tell whether the `@` is a
URI delimiter or part of the path.

### Why explicit renaming is not a solution

Product Owners ("Bob drops whatever Adobe gives him") cannot be expected to
manually rename files before placing them in the upload point. The CI/CD
pipeline must handle this automatically. Hardcoding exact names into recipes,
even if the current names are safe, creates a maintenance trap: the recipe
breaks silently the next time the vendor changes anything.

### The alternative considered — glob patterns in recipes

AutoPkg's `DOWNLOAD_URL` does not support glob or wildcard patterns. The
processor constructs an exact `file://` URI from the input string and passes
it directly to `curl`. There is no intermediate "find the file" step.

### Why a pre-scan normalization script is the right solution

1. **Separation of concerns.** The recipe knows what the canonical name
   *should be*. The pre-scan script ensures the file on disk *has* that name.
   Neither needs to know about the other's internals.

2. **Config-driven, not code-driven.** Adding a new vendor-drop app means
   adding one line to `vendor-drop-registry.yaml`. The script itself never
   changes. No shell script expertise required to onboard a new app.

3. **Cache directory is outside the git repo.** `/tmp/autopkg/vendor_cache/`
   is a CI artifact, not tracked content. Renaming files there does not
   pollute git history or trigger unnecessary CI runs. The config file is
   tracked, but it only changes when a genuinely new app is added — not on
   every vendor release.

4. **Idempotent.** Running the script against an already-normalized cache is
   a no-op. Running it again after a vendor updates the file works the same
   way. The script is safe to run on every CI invocation.

5. **Auditable.** The script produces structured output showing exactly what
   it renamed. This feeds into CI logs and can be monitored for unexpected
   changes in vendor filenames.

---

## Conclusion

| Approach | Brittle? | Auto-fixes? | Config-driven? |
|----------|----------|-------------|----------------|
| Exact filename in recipe | Yes | No | N/A |
| Glob/wildcard in recipe | Not supported | N/A | N/A |
| Manual rename by PO | Yes | No | No |
| Pre-scan normalization script | No | Yes | Yes |
