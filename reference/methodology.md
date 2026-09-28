# AutoPkg Vendor-Drop Recipe Methodology

**Why this exists:** batch-1 needed roughly a dozen live-fire debugging rounds to get
a single recipe fully working, despite passing manual review and a
(partially broken) linter beforehand. Every failure was a genuine AutoPkg runtime
behavior that only surfaces when you actually execute a recipe — none of them were
visible from reading the YAML. This doc turns those into a pre-flight checklist so the
next batch doesn't have to rediscover the same six bugs one at a time.

## The core lesson

**Manual review and linting can only catch what they know to look for. Runtime
behavior of specific AutoPkg processors — what sets `%pathname%`, whether `PathDeleter`
tolerates a missing file, whether `%RECIPE_CACHE_DIR%` is shared across a chain — isn't
visible in the YAML at all.** A recipe that looks structurally identical to a working
public example (see: the Microsoft Word mixup) can still fail for reasons specific to
*why* it's shaped that way. Pattern 4 (vendor-drop, local file) is a much less-trodden
path than Pattern 5 (stable URL) in the wider AutoPkg ecosystem — most public recipes,
including Recipe Robot's own defaults, are Pattern 1–3/5 shaped, so their processors
(`URLDownloader`, etc.) have had thousands of real runs to shake bugs out. `Copier`-based
vendor-drop recipes have not.

**The fix isn't "review harder." It's: run every new recipe shape once, for real,
against the cheapest/simplest app available, before assuming the pattern works.**

## Pre-flight checklist for any new vendor-drop recipe

Before considering a Pattern 4 (or similar non-standard) recipe done, walk through
these explicitly — each one is a real bug found in batch-1, not a hypothetical:

### 1. Path arithmetic — count the levels, don't eyeball it
`recipes/VendorName/AppName/recipe.yaml` is **3 levels** below repo root. Escaping
back to repo root needs `../../../`, not `../..`. Two `..` lands you *inside*
`recipes/`, not next to it. **Verify with code, not by reading:**
```python
from pathlib import Path
print(Path('/repo/recipes/Vendor/App/../../../build/vendor_cache/x.pkg').resolve())
# should print /repo/build/vendor_cache/x.pkg
```
If the directory depth of your layout ever changes, every recipe's relative path needs
re-counting — don't assume yesterday's math still applies.

**Mostly superseded:** recipes now declare an absolute, overridable
`VENDOR_CACHE_ROOT` Input (`autopkg run -k VENDOR_CACHE_ROOT=/path …`) instead of
`%RECIPE_DIR%/../../../`. Keep the depth-counting advice for `%RECIPE_DIR%`-relative
sidecars (e.g. a `scripts/` directory committed next to the recipe); see #24 for where
the cache should live.

### 2. Never open a download recipe with `PathDeleter`
`PathDeleter` **errors if its target doesn't exist** — it's for cleaning up a *previous*
run's leftovers, not for guaranteeing a clean slate on a fresh cache. On a first-ever
run there's nothing to delete, so it fails immediately. `Copier` already overwrites its
destination on every run — you don't need `PathDeleter` before it. If you're tempted to
add a "just in case" cleanup step at the top of a recipe, don't; verify whether the
next processor already handles overwriting before adding anything defensive.

### 3. `%pathname%` is not universal — know which processors actually set it
`URLDownloader` sets `%pathname%` as part of its normal behavior. **`Copier` does not.**
If a pkg recipe's `PkgCopier`/similar step needs to reference "the file the download
recipe just placed," and the download recipe used `Copier`, don't rely on `%pathname%`
— reference the literal, known path directly: `%RECIPE_CACHE_DIR%/AppName.pkg` (see #4
for why this works reliably across the parent/child boundary). Don't try to "fix" this
by embedding `%RECIPE_CACHE_DIR%` inside an `Input:` default value — `Input:` defaults
resolve *before* `RECIPE_CACHE_DIR` is seeded into the environment, so that specific
trick doesn't work (a real dead-end hit in this batch, documented so it isn't retried;
`autopkglib` substitutes Input values before it sets `RECIPE_CACHE_DIR`). Once the
parent uses `URLDownloader` instead of `Copier`, `%pathname%` *is* available to the
child pkg recipe — see #14.

### 4. `%RECIPE_CACHE_DIR%` IS shared across a parent→child recipe chain
Confirmed by cross-checking against a known-working public recipe (Microsoft Word):
its `PkgCopier` step references `%RECIPE_CACHE_DIR%/%NAME%.pkg` reliably across the
download→pkg boundary. Don't assume each recipe in a chain gets an isolated cache dir
based on its own identifier — it doesn't, in practice. This means a literal
`%RECIPE_CACHE_DIR%/AppName.pkg` reference in a child recipe correctly points at the
same file the parent's `Copier` step wrote.

The mechanism: `RECIPE_CACHE_DIR` is `<CACHE_DIR>/<identifier of the recipe you
invoked>`, and the whole parent→child chain runs in one environment. Consequence:
running the download recipe on its own fills a *different* cache directory than
running the pkg recipe, so cache clearing (#11, the guardrails footgun list) has to
target the identifier you actually invoke.

### 5. Use `pkgutil`, not `codesign`, to check a `.pkg`'s signature
`codesign` is built for Mach-O binaries and `.app` bundles — flat `.pkg` installers use
a different signing mechanism (`productsign`/CMS) that `codesign` doesn't understand.
It will report **"not signed at all" even on a genuinely signed pkg** — a real false
negative hit in this batch, on two pkgs later confirmed signed by the correct tool.
```bash
pkgutil --check-signature build/vendor_cache/AppName.pkg
```
is the authoritative check. If `codesign` and `pkgutil` disagree, trust `pkgutil` for
anything ending in `.pkg`.

### 6. `expected_authority_names` needs the FULL certificate chain, not just the vendor's cert
`CodeSignatureVerifier` checks the entire chain, not just the leaf certificate. A
correct entry has (at minimum) three lines:
```yaml
expected_authority_names:
  - "Developer ID Installer: Vendor Name (TEAMID)"
  - Developer ID Certification Authority
  - Apple Root CA
```
Copy **all three lines verbatim** from `pkgutil --check-signature` output — don't
assume the last two. Most vendors sign with a Developer ID Installer cert that chains
through `Developer ID Certification Authority`, but a vendor signing with a Mac App
Store–style `3rd Party Mac Developer Installer` cert chains through `Apple Worldwide
Developer Relations Certification Authority` instead. Don't normalize the vendor's
punctuation or case either (a lowercase `inc` in a vendor CN is correct). Missing lines produces "Mismatch in
authority names" that only surfaces once a *genuinely signed* pkg is tested — recipes
for confirmed-unsigned pkgs never exercise this path at all, so this bug can hide
behind other apps' unsigned status for a long time before it's caught.

### 7. Confirm signed-vs-unsigned explicitly, and don't be surprised when it's "unsigned"
Run `pkgutil --check-signature` on every real vendor pkg before assuming
`CodeSignatureVerifier` applies. In batch-1, **4 of 9 apps turned out to be genuinely
unsigned** — this is the expected, common case when your MDM's deployment channel is the
actual trust boundary, not an edge case to be surprised by each time. Package-level
unsigned is not the same as bundle-level unsigned — see #16. Use an explicit
`Input.NO_CODE_SIGNATURE_REQUIRED: true` + a comment explaining *why* (unsigned vendor
artifact vs. no signable content at all — these are two different reasons for the same
escape hatch) rather than silently omitting the verifier.

### 8. Test outside cloud-sync folders (OneDrive/iCloud Drive) as a default, not a fallback
A repo living inside a OneDrive-synced folder can produce file-visibility failures
that are genuinely confusing to debug (a file that's fully downloaded and visible to
`ls`/plain `python3 glob.glob()` can still be invisible to a different process's TCC/
Full-Disk-Access grant, or to whatever Python interpreter AutoPkg bundles internally).
This cost real debugging time in batch-1 before being ruled out. Default to a native
local path for any AutoPkg working repo; treat cloud-sync folders as something to rule
out early if a `Copier`/glob-related failure looks inexplicable, not late.

### 9. A "known-working" example recipe is only a valid reference if it's the *same shape*
Superficial resemblance (same processor names, same general layout) isn't enough —
verify the *mechanism*, not just the appearance. The Microsoft Word recipe looks
structurally similar to ours but is Pattern 5 (URL-based), not Pattern 4 (vendor-drop)
— it never needed to solve the `%pathname%`-from-`Copier` problem because it uses
`URLDownloader`, which doesn't have that problem in the first place. Before treating any
external recipe as a template, confirm which pattern in `docs/patterns.md` it's actually an instance of.

### 10. Once a new recipe *shape* is validated once, trust it — don't re-litigate per app
The first fully-clean recipe validated the entire Variant A (PKG-sourced, unsigned)
shape at once — the next two recipes of that shape then passed on the
first try with the identical fix set applied. Pick the cheapest/simplest app sharing a
new shape as the first real test, fix forward from there, then apply the same fix to
every other app sharing that shape *before* re-testing each one individually — this
batch's actual sequence (fix once, apply to all affected recipes, test the group) is
the right order, not fixing-and-testing one app at a time in isolation.

### 11. `Copier` directory-to-directory copies need `overwrite: true` for repeat runs
The single-directory-copy fix (item #13 below) works cleanly on a *fresh* cache, but
AutoPkg's cache persists across separate invocations at
`~/Library/AutoPkg/Cache/<identifier>/`. A second run against a destination that
already exists from a prior attempt fails with `[Errno 17] File exists` — directory
copies, unlike single-file copies, don't overwrite by default. Add `overwrite: true`
to the `Copier` arguments whenever the source is a directory, not just a file.
(Single-file copies always overwrite. The equivalent switch on `Unarchiver` is
`purge_destination: true`.)

### 12. Every `%variable%` referenced in `Process` needs a real `Input` declaration somewhere in the chain
`%version%`, `%teamid%`, `%authority_name%` — none of these work just because an
optional `.overrides` file has a value for them. `.overrides` is an org-defined
harness convention: `bin/run-recipes.sh` or a CI job passes its lines as `--key`, but
AutoPkg never reads it, so a bare `autopkg run` never sees those values. A recipe using `%version%` in
`PkgCreator`'s `pkg_request` needs `Input: version: "..."` declared explicitly
somewhere in the chain, the same way `teamid`/`authority_name` need to be. This is
easy to miss because Variant A recipes (`PkgCopier`) never reference `%version%` at
all — the gap only surfaces on Variant C (`PkgCreator`) recipes, and only at runtime,
since there's no static check for "this substitution token has no source."

### 13. Multi-file Variant C payloads: copy the whole staged directory, not each file individually
`Copier` doesn't create missing parent directories when copying a single file into a
nested destination that doesn't exist yet (`payload/Shared/Example/settings.cfg` fails if
`payload/Shared/Example/` isn't already there). It *does* create the full destination tree
automatically when copying an entire directory. For any Variant C app with more than
one file, stage `vendor_cache` to already mirror the exact final structure needed, and
use a single directory-level `Copier` call rather than one call per file — combined
with item #11's `overwrite: true` for repeat runs.

### 14. `PkgCopier: list index out of range` means the source path matched nothing. It does not mean the package format is wrong.
> **Under review:** this lesson contradicts the rationale for Pattern 4b
> (`templates/pattern-4b-distribution-package/`, "distribution packages crash
> `PkgCopier`"). It was verified against the AutoPkg 2.9 source; the 4b template and
> docs have not yet been reconciled with it.

**Rule: when `PkgCopier` fails with `list index out of range` (or `Copier` fails with
`Error processing path '…' with glob`), fix the path. Don't swap the processor.**

`PkgCopier` runs `glob.glob(source_pkg)[0]` without checking for an empty result, so a
source path that doesn't exist raises a bare `IndexError`. It never parses the package.
It only requires the matched name to end in `.pkg` or `.mpkg`, and it copies flat,
component and distribution packages the same way. The history misread this error as
"PkgCopier can't handle distribution packages". The recipes switched to `Copier`, the
docs explained it, and a whole template variant was built on the idea. The real cause
came in the same change: the download recipes had moved from `Copier`, which writes
to the cache root, to `URLDownloader`, which writes to
`%RECIPE_CACHE_DIR%/downloads/<filename>`. The child recipes still pointed at the old
literal `%RECIPE_CACHE_DIR%/download_%NAME%.pkg`. Using `Copier` in the pkg recipe
works, but it hides the path bug instead of fixing it.

**How to check:**
```bash
autopkg run -vvv App.pkg.recipe.yaml 2>&1 | grep -iE 'source_pkg|source_path|pathname'
find ~/Library/AutoPkg/Cache/com.acmefruit.autopkg.pkg.App -name '*.pkg' -maxdepth 3
```
When the parent recipe uses `URLDownloader`, point the child at
`source_pkg: "%pathname%"`. `%pathname%` is in the shared chain environment, as
lesson 4 describes. After any change from `Copier` to `URLDownloader`, grep every child
recipe for literal `download_%NAME%` paths. Any doc that tells readers to "use
`Copier` because distribution packages crash `PkgCopier`" should be corrected.

### 15. `Copier` mounts a DMG for its own step only, and only when the path contains `.dmg/`. Build the glob against the real mounted layout.
**Rule: write DMG `source_path` globs against the volume you actually mounted. Use a
trailing `X.dmg/` when you need the whole volume.**

`Copier` and `PkgCopier` both subclass `DmgMounter`. When the path contains `.dmg/` (or
`.iso/`), they mount the image, glob inside it, copy, and unmount in a `finally`
block. Nothing stays mounted for the next step, whatever an older note says. Three
failures came from this:
- A glob of `Applications/Orchard Analytics*/Orchard Analytics*.app` expected a version-named
  folder that the DMG didn't have. `*` never matches across `/`. Use `**` if you need
  recursion, because `Copier` globs with `recursive=True`.
- A recipe copied only `Pomelo Studio 4.app` out of a DMG whose volume root also held a
  hidden `.license.dat`, and the product came out unlicensed. `X.dmg/` with nothing
  after the slash copies the entire volume root, dotfiles included.
- When a glob matches more than one path, the processor uses `matches[0]` in
  filesystem order and only prints a warning. A DMG that holds two versions picks one
  of them arbitrarily.

A version-numbered folder inside the DMG (for example `App 7.80rev7/App 7.80rev7.app`)
forces version-specific destination and `Versioner` paths. Glob the source, and copy
to a destination path with no version in it.

**How to check:**
```bash
hdiutil attach -nobrowse -readonly Vendor.dmg        # note the /Volumes/<name> it prints
ls -la "/Volumes/<name>"                              # -a: hidden files matter
python3 -c 'import glob,sys; print(glob.glob(sys.argv[1], recursive=True))' "/Volumes/<name>/<your pattern>"
hdiutil detach "/Volumes/<name>"
```
The Python line should print exactly one path.

### 16. An unsigned wrapper doesn't make its contents unsigned. Verify every `.app` inside a rebuilt or faux-DMG payload.
**Rule: `NO_CODE_SIGNATURE_REQUIRED` is only correct when nothing in the payload
carries a signature. If a vendor `.app` inside an in-house wrapper is signed, verify
that `.app`.**

The Pattern 6 and Pattern 7 docs said a rebuilt package is "unsigned by construction".
That is true of the outer `.pkg` or `.dmg`. But several payloads
repackaged in-house each contained a Developer ID–signed `.app`.
Declaring the whole recipe unsigned discarded the only integrity check that was
available, and the README recorded no Team ID when a real one existed.
Lesson 5 covers the package level; this lesson covers the bundle level.

**How to check:**
```bash
find payload -name '*.app' -maxdepth 4 -type d -exec codesign --verify --deep --strict -vv {} \;
codesign --display --requirements - "payload/Applications/App.app"   # copy this requirement string verbatim
```
If the `.app` is signed, add a `CodeSignatureVerifier` step with `input_path` set to
the staged `.app` and the extracted `requirement`, and record the Team ID in the README.
Use `NO_CODE_SIGNATURE_REQUIRED` only when `codesign` reports "code object is not
signed at all" for everything that could be signed. Record which case applies in the
README.

### 17. With `PkgCreator`, a `chown` `mode` on a directory applies to every descendant. Take owner, group and mode from the original BOM.
**Rule: put `mode:` on single files or on subtrees whose contents are uniform. Copy
the owner, group and mode from the package you're replacing, not from memory.**

`autopkgserver/packager.py` handles a directory `chown` entry with `os.walk`. It
`lchown`s everything, and when `mode` is set it `lchmod`s every child file and
subdirectory to that one mode. The directory itself gets no chmod. So `0644` on a
directory makes its subdirectories untraversable, and `0755` makes every file
executable. With no `chown` entry at all, `pkgbuild --ownership preserve` records
whoever ran AutoPkg as the owner of the payload.

Two history notes about the same 29-byte license-key file under `/Users/Shared`
disagreed: one said `root:admin 0777`, the other `root:wheel 0754`. The app refused
to launch until the mode matched what the vendor's app expected. The original BOM had
the right answer all along.

**How to check:**
```bash
pkgutil --expand original.pkg /tmp/orig && lsbom -p MUGf /tmp/orig/Bom | grep -F 'LicenseKey'
# (for a distribution package the Bom is under /tmp/orig/<Component>.pkg/Bom)
```
Give every file whose mode or group differs from its siblings its own `chown` entry
with `path`, `user`, `group` and `mode`. Then run `pkg-compare.sh` against the original
(lesson 20). Its permissions section reads both BOMs.

### 18. `PkgCreator` checks the request before it builds anything. A payloadless package still needs an existing pkgroot, and names must pass its regexes.
**Rule: create an empty pkgroot explicitly. Keep scripts executable. Run `id`,
`pkgname` and `version` through the packager's own rules before the first run.**

These checks come from `autopkgserver/packager.py`:
- `pkgroot` and `pkgdir` must already exist and be owned by the building user. A
  script-only (6d) recipe whose download step stages only `scripts/` fails because
  `%RECIPE_CACHE_DIR%/payload` never gets created. Create it with the core processor
  `PkgRootCreator` (`pkgroot: "%RECIPE_CACHE_DIR%/payload"`, `pkgdirs: {}`). There is
  no core `PathCreator`, even though some docs suggest one.
- The volume that holds pkgroot must have ownership enabled. An external drive with
  "Ignore ownership on this volume" set is rejected.
- Each `preinstall` and `postinstall` must be executable. A `scripts.zip` built by a
  tool that drops mode bits fails here.
- `pkgname`: `[A-Za-z0-9][A-Za-z0-9 ._-]*`, at most 80 characters, and no `.pkg`
  suffix. An app name with `@` in it can't be a pkgname.
- `id`: at least two dot-separated components, each alphanumeric, space or hyphen, and
  **no underscores**. Legacy repackaged identifiers such as a single token
  (`acmefruitbanner20191121`) or `acme_foo.pkg` are rejected.
- `version`: every dot-separated component must contain a digit.

Replacing a legacy package ID changes the installed receipt. Anything that detects the
app by `pkgutil --pkgs` (smart groups, installs checks) has to move to the new
`com.acmefruit.pkg.<App>` ID. `pkg-compare.sh` reports the ID change only as
information, which is expected.

A related naming point: dots in an app name (for example `Setup.Manager`) become extra
identifier segments. Use hyphens in directory names, `NAME` and identifiers.

**How to check:** run `ls -ld` on the pkgroot inside the recipe cache after the
download step, run `zipinfo scripts.zip` and look for `-rwx` on the scripts, and test
the proposed `PKG_ID` with
`python3 -c 'import re,sys; print(all(re.fullmatch(r"[a-z0-9]([a-z0-9 \-]*[a-z0-9])?", c, re.I) for c in sys.argv[1].split(".")))' com.acmefruit.pkg.App`.

### 19. If a rebuilt package that writes to both `/Applications` and data-volume paths is rejected by the installer, split it into two packages.
**Rule: when the macOS installer rejects a `PkgCreator` package with "The package is
trying to install content to the system volume", split it into an app package that
touches only `/Applications` and a sibling (`App-License`, `App-Config`) that touches
only `/Users/Shared` or `/Library/…`. Test the install on each supported OS release
before shipping.**

This happened on macOS 15 to two rebuilt packages (a vendor app plus a license file
under `/Users/Shared`) whose original repackaged versions installed fine. Splitting
them fixed both, and both halves installed and licensed correctly. **The root cause
was not isolated.** The history attributed it to "flat packages lack a Distribution
`enable_anywhere` domain". But a third package from the same vendor with the same
structure installed without splitting. The only difference the notes found was an
extra `chown` entry on the data-volume parent directory. Treat the Distribution-XML
explanation as unproven. Don't put `chown` entries on shared parents such as
`Users`, `Users/Shared` or `Library`. Scope each entry to your own leaf directory.

**How to check:**
```bash
sudo installer -pkg ~/Library/AutoPkg/Cache/com.acmefruit.autopkg.pkg.App/Acme_App.pkg -target / -verboseR
pkgutil --expand Acme_App.pkg /tmp/x && lsbom -s /tmp/x/Bom | cut -d/ -f2 | sort -u   # top-level roots the pkg touches
```
If more than one top-level root shows up, next to `Applications`, plan the split from
the start.

### 20. Treat the package you're replacing as the requirements spec, and diff your rebuild against it before calling the recipe done.
**Rule: when a new recipe replaces an existing org-built package, every file, mode,
script and setting in the old package is a requirement until you can show it isn't.**

Rebuilding from the clean vendor artifact silently dropped the org's additions again
and again:
- a hidden license file at the DMG root (lesson 15)
- a 29-byte volume-license key in `/Users/Shared/<Vendor>/<App>/`
- a postinstall that set preferences, turned off auto-update, stripped quarantine and
  closed running copies
- a postinstall with a hardcoded path for an older major version (`22.0` when the app
  was `26.0`), plus a license-agreement flag set to `0` instead of `1`
- a config file whose "vendor" copy was 1.4 KB when the deployed copy was 36 KB

**How to check:**
```bash
bin/pkg-compare.sh --old-pkg original.pkg --new-pkg ~/Library/AutoPkg/Cache/<id>/Acme_App.pkg
pkgutil --expand original.pkg /tmp/orig && ls -la /tmp/orig/*/Scripts /tmp/orig/Scripts 2>/dev/null
grep -nE '[0-9]+\.[0-9]+' /tmp/orig/Scripts/postinstall        # hardcoded versions vs. CFBundleShortVersionString
```
If two sources of the "same" config or license file disagree in size or hash, the
deployed copy wins. Document why in the README.

### 21. Recognize org-built wrapper packages and split them by origin and update cadence.
**Rule: an in-house wrapper (for example one built with Jamf Composer) is several
things bundled together. Separate the vendor-signed parts from the org-authored parts,
and give each part with its own update cadence its own recipe.**

A "vendor" VPN-client package turned out to be an unsigned Composer distribution. It
held the vendor's signed installer (nested inside a zip in the payload) plus three
org-authored files: a config file, an uninstall script and a LaunchDaemon plist. The
single recipe shipped only the vendor part and put an org `Acme_` prefix on a copied
vendor package. The fix was four recipes:
- the vendor package, copied as-is and signature-checked (4a)
- the config file (6a)
- the uninstall helper (6a)
- the LaunchDaemon plus a postinstall that loads it (6b)

Deploying a LaunchDaemon file and loading it are separate decisions. Only the recipe
meant to activate it should run `launchctl`.

Two traps come with these wrappers:
- Some fail `pkgutil --expand` with `archive verify failed` because their xar
  checksums are invalid. `pkg-reverse.sh` and `pkg-compare.sh` then exit 5. `xar -xf`
  often still extracts `Distribution`, `PackageInfo`, `Bom` and `Scripts`. If the
  `Payload` won't come out either, go back to the vendor's original installer.
- A `FlatPkgUnpacker` → `PkgPayloadUnpacker` → `Versioner` chain written for a
  component package breaks on a distribution package, because the payload lives under
  `<unpack>/<Component>.pkg/Payload` and not `<unpack>/Payload`.

**How to check:**
```bash
xar -xf wrapper.pkg Distribution -C /tmp/w && grep -o 'authoringTool="[^"]*"' /tmp/w/Distribution
pkgutil --expand wrapper.pkg /tmp/w2 || (mkdir -p /tmp/w3 && cd /tmp/w3 && xar -xf /path/to/wrapper.pkg)
find /tmp/w2 -maxdepth 2 -name '*.pkg' -type d          # one component or several?
```

### 22. Versions and names come from the payload, not from filenames or generated blueprints. Check that your edits actually saved.
**Rule: read the version from `PackageInfo` or `Info.plist`. Review
`blueprint.conf` before running `blueprint-to-recipe.sh`, and confirm an edit
persisted before regenerating.**

A file named `…_2026.1.2.pkg` contained `version="2026.2.0"`. `pkg-reverse.sh` built
`app_name` from the source filename and carried the org prefix and a date suffix
into the result (`Acme-Banner-20191217`). After `sudo pkg-reverse.sh`, the output
files are owned by root. An edit to `blueprint.conf` from the normal user account
didn't persist, and the recipe was generated from stale content.

**How to check:**
```bash
xmllint --xpath 'string(/pkg-info/@version)' /tmp/x/PackageInfo
defaults read "$PWD/payload/Applications/App.app/Contents/Info.plist" CFBundleShortVersionString
sudo chown "$(id -un)" vendor_cache/Vendor/App/blueprint.conf vendor_cache/Vendor/App/*.txt   # not payload/
grep -E '^(app_name|version|pkg_id)=' vendor_cache/Vendor/App/blueprint.conf                # re-read after editing
```

### 23. Build payload archives from inside the root, and keep symlinks and modes intact.
**Rule: zip the contents of `payload/`, not the `payload/` directory itself. Use a
tool that stores symlinks and permissions. Check the archive before a recipe depends
on it.**

`Unarchiver` extracts `.zip` with `ditto -x -k` into `destination_path`. A zip made as
`zip -r payload.zip payload/` unpacks to `payload/payload/Users/…`, and `PkgCreator`
then fails with `chown path Users does not exist`. Plain `zip -r` also follows
symlinks, which bloats `.app` bundles and breaks their signatures, unless you pass
`-y`. Scripts archives need their execute bits kept (lesson 18). For repeat runs, use
`purge_destination: true` on `Unarchiver`, which does the same job as lesson 11's
`overwrite: true`.

**How to check:**
```bash
(cd vendor_cache/Vendor/App/payload && zip -ry ../payload.zip .)   # or: ditto -c -k --norsrc payload payload.zip
unzip -l vendor_cache/Vendor/App/payload.zip | head               # first entries must be Users/, Library/, … not payload/
zipinfo vendor_cache/Vendor/App/scripts.zip | grep -E 'postinstall|preinstall'   # expect -rwx
```

### 24. The vendor cache isn't a backup. `/tmp` gets purged and the normalizer used to delete files.
**Rule: keep original vendor files in a durable source, repopulate the working cache
from an index, and check the cache after normalizing it.**

The default `VENDOR_CACHE_ROOT` is `/tmp/autopkg/vendor_cache`. `/private/tmp` is
cleared at reboot, and the history keeps finding staged files "missing" that had been
staged in an earlier session. `normalize-vendor-cache.sh` used to rename the *newest*
file in each directory to the canonical name whatever its type. It turned a
`blueprint.conf` and a customer-key `.txt` into `payload.zip`, which led to a whole
backfill project. When the canonical file already existed, it deleted every other file
in that directory unless it was listed in `protected_files`. It now renames only files
of the canonical name's type and moves stale extras aside to a `relocated/` folder in the
vendor cache (KI-7), which `/tmp` purges too.

**How to check:** keep working notes (`blueprint.conf`, `bom.txt`, READMEs) out of
`vendor_cache/`, or list them in `protected_files`. Repopulate with
`bin/sync-vendor-cache.sh <index> <durable-source> <VENDOR_CACHE_ROOT>`. Normalize with
`--dry-run` first. After normalizing, run:
```bash
find "$VENDOR_CACHE_ROOT" -name '*.zip' -exec sh -c 'unzip -tq "$1" >/dev/null || echo "NOT A ZIP: $1"' _ {} \;
find "$VENDOR_CACHE_ROOT" -name '*.pkg' -type f -exec sh -c 'xar -tf "$1" >/dev/null 2>&1 || echo "NOT A FLAT PKG: $1"' _ {} \;
```

### 25. Some public URLs won't download on a corporate network. Tune `curl`, or fall back to vendor-drop and write down why.
**Rule: when `URLDownloader` fails on a URL that works in a browser, first rule out
throttling (`curl` speed limit). If the site is behind bot protection or a firewall
block, treat the app as vendor-drop and record the reason in the README.**

`URLDownloader` always passes `--speed-time 30` to `curl`, which aborts any transfer
that runs under 1 byte/s for 30 seconds. A throttled CDN path for a Microsoft download
hit `curl: (28) Operation too slow`. `curl_opts` is appended after the built-in
options, so a later `--speed-time` wins. Two other apps couldn't be fetched at all.
One vendor's download page sits behind a bot-protection challenge, and another
project's host was blocked by the corporate firewall. Both became Pattern 4
vendor-drop recipes, and each README says why so nobody "fixes" it back to a URL
recipe.

**How to check:**
```yaml
- Processor: URLDownloader
  Arguments:
    url: "%DOWNLOAD_URL%"
    curl_opts: ["--speed-time", "0"]    # or a larger number of seconds
```
```bash
curl -sSLI "$URL" | grep -iE '^(HTTP|server|cf-|location)'   # 403 + challenge headers → bot protection
```

### 26. Pattern labels, READMEs and scanners drift. Derive labels from the processors and prove every checker can fail.
**Rule: a recipe's `Comment:`, its README and any audit script's verdict are claims.
Check each one against what the processors do, and treat any checker you haven't seen
fail as untested.**

After the Copier-to-URLDownloader migration, about 15 READMEs still described `Copier`.
Recipe comments carried the wrong variant (4b on a copied package, 6d on a recipe that
had a payload). One README described a `Symlinker` step that didn't exist. Two READMEs'
`upload_url` pointed inside the payload tree instead of at the `payload.zip` the recipe
actually downloads. A throwaway compliance scanner reported four READMEs as missing
when they existed, and missed an `Acme_` prefix on two copied packages. For weeks the
linter itself could not fail any recipe: an off-by-one in its output protocol dropped
every failure, and the exit code was never set.

**How to check:**
- Run `bin/classify-recipe.sh <Vendor/App>`: it compares its result with the
  `Comment:` line and says whether they match.
- After any migration from processor X to Y, run `grep -rln 'X' recipes/*/*/README.md`
  in the same change.
- A README's download spec must name the exact file at the end of `DOWNLOAD_URL`.
- For every new or changed checker, keep a deliberately broken fixture and confirm the
  checker exits non-zero on it:
  `bin/recipe-linter.sh tests/fixtures/…/Broken.download.recipe.yaml; echo $?`

### 27. Never `%`-format or `printf` recipe text in a bulk-edit script.
**Rule: edit recipe and README text with literal string replacement. Grep for `%%`
after every bulk edit.**

AutoPkg's `%NAME%`, `%pathname%` and `%RECIPE_CACHE_DIR%` look like format directives.
An edit script escaped them as `%%…%%` for Python `%`-formatting, then wrote the
escaped text out as-is. That left `%%url%%` and `%%RECIPE_CACHE_DIR%%` throughout the
patterns README, and a second script was needed to undo it. The same happens with
`printf "$template"` in shell.

**How to check:** use `str.replace()` or `pathlib.Path.write_text()` in Python, and
`printf '%s\n' "$text"` in shell. After the edit, run:
```bash
grep -rn '%%' recipes/ templates/ docs/ && echo "doubled percent signs found"
```

## Standing tooling (build once, reuse every batch)

Everything below was built during batch-1's debugging and should carry forward as-is:

- `bin/scan-placeholders.sh` — greps for unresolved placeholder text across all
  recipes (and any `.overrides`), plus a structural check for missing certificate-chain entries
  (item #6)
- `bin/run-recipes.sh` — real-run harness with a `--clear-cache` flag
- `bin/clear-autopkg-cache.sh` — safety-checked cache clearer: hard-coded root
  (`~/Library/AutoPkg/Cache`), every deletion target verified to actually resolve
  inside that root before anything is removed, rejects identifiers containing `/` or
  `..` outright. Never touches `build/vendor_cache/` or any repo-relative path,
  regardless of what's passed in.
- `bin/generate-manifest.sh` / `bin/verify-manifest.sh` — checksum-based handoff
  verification (see the section below)
- `bin/pkg-reverse.sh` + `bin/blueprint-to-recipe.sh` — the rebuild path (Pattern 6):
  extract an existing package into a blueprint, then draft a recipe pair from it (#22)
- `bin/pkg-compare.sh` — original-vs-rebuilt package equivalence check (#20)
- `bin/normalize-vendor-cache.sh` / `bin/sync-vendor-cache.sh` — canonical vendor-cache
  names and repopulation from a durable source (#24)
- `bin/classify-recipe.sh` — derive a recipe's pattern from its processors (#26)
- `bin/autopkg-preflight.py` — runs the `guardrails/audit/*` checks plus the linter

## Suggested workflow order for a new batch, informed by this one

1. Inventory + pattern classification (which pattern in `docs/patterns.md` each app fits)
2. Draft skeletons per pattern, applying items #1–#7 above from the start rather than
   discovering them live
3. Manual/linter review (catches structural/convention issues — naming, identifiers,
   directory layout — but explicitly does NOT catch the runtime issues in this doc)
4. **Pick the single cheapest/simplest app per recipe shape and run it for real,
   before writing out the full batch of per-app skeletons.** This batch validated
   Pattern 4/PKG-sourced only after all 9 skeletons already existed — validating the
   shape against 1 app first would have caught the `PathDeleter`/path-depth/`%pathname%`/
   chain bugs before they were replicated across 6+ files each.
5. Only then generate the remaining per-app skeletons from the now-validated template
6. Real-run every app, not just the validation one — per-app specifics (signed vs.
   unsigned, version scheme, file layout) still vary and need individual confirmation
7. Before a recipe counts as done: diff it against the package it replaces
   (`bin/pkg-compare.sh`, #20) and install-test it on each supported macOS release (#19)

## Mandatory: checksum verification for every cross-session handoff

Batch-1 lost significant time to a specific, recurring failure mode: files handed off
across the assistant/user boundary (individual files or a zip) silently failed to land
correctly — a fix would be made on one side, but the receiving end would still be
running stale content, with no way to tell just by looking. This happened at least
four separate times in this batch alone, and **future batches will hit it just as
often, since they'll be equally dominated by locally-cached vendor-drop files** that
only exist on the user's machine, not in any shared location either side can directly
verify against.

**The fix, and it's now a required step, not optional:**

- `bin/generate-manifest.sh` — regenerates `manifest.sha256` at the repo root,
  covering every file in `recipes/`, `bin/`, and top-level `.md` docs. Run this any
  time a handoff is being prepared.
- `bin/verify-manifest.sh` — checks the current on-disk state against
  `manifest.sha256` in one command, reporting exactly which files are missing or
  mismatched (not just "something's wrong somewhere"). Exits non-zero on any
  discrepancy, so it's usable as a hard gate before running anything.

**Standing rule for every future batch:** any time recipes/tools content changes and
gets handed off in either direction, `manifest.sha256` goes with it, and the receiving
end runs `verify-manifest.sh` before running `autopkg` against anything. Zero
exceptions for "it's just a small change" — the small changes are exactly what's been
silently failing to land.
