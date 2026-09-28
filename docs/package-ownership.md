# Package ownership: why recipes `chown` system folders, and how not to break them

**Short version.** A flat package built by AutoPkg must record an owner and a mode
for *every* folder on the path to what it installs, including folders macOS ships
(`/Library`, `/Library/Application Support`, `/Applications`). The recipe can't
leave them out; it can only choose *what* is recorded. By default AutoPkg records
**the account that ran AutoPkg**. The `chown` entries in our recipes exist to record
**the stock macOS values** instead. They don't reset anything on a Mac that already
has those folders; they make the package's claim match reality, so there's nothing
to break. Where a stock *mode* differs from what the recipe staged (today:
`/Applications` is 775), the fix is to stage the folder with that mode using
`PkgRootCreator` — see [How to avoid mismatches](#how-to-avoid-mismatches).

---

## 1. What a flat package records

A component package's payload is a folder tree rooted at the install location. For
PkgCreator that is always `/`. To install
`/Library/Application Support/AcmeFruit/StarterKit/`, the archive contains:

```text
.                                    ← "/" itself
./Library
./Library/Application Support
./Library/Application Support/AcmeFruit
./Library/Application Support/AcmeFruit/StarterKit
…
```

Every entry carries a mode, an owner and a group. The package's bill of materials
(BOM) lists them all, and the receipt left in `/var/db/receipts/` keeps that BOM.
Apple's packaging guide:

> "The files that the Installer application places on the target computer have the
> same ownership and access permissions as the payload's files. Therefore, you must
> set up the owner and access permissions of component files appropriately before
> building the installation package."
> — [PackageMaker User Guide, *Workflow*](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/PackageMakerUserGuide/Workflow/Workflow.html) (retired, still the most explicit Apple statement)

`pkgbuild` has three ownership modes (`man pkgbuild`):

| `--ownership` | What gets recorded |
|---|---|
| `recommended` (Apple's default) | "the recommended UID and GID … Generally, this will be root:wheel" |
| `preserve` | "the exact ownership of the on-disk files" |
| `preserve-other` | recommended for files owned by the user running pkgbuild; others unchanged |

## 2. What AutoPkg does

From `/Library/AutoPkg/autopkgserver/packager.py` (AutoPkg 2.9):

1. **`copy_pkgroot`** creates the temporary package root as **root:admin, mode 1775**
   (`os.chmod(tmp_pkgroot, 0o1775)`, `os.chown(tmp_pkgroot, 0, 80)`), then copies the
   recipe's `pkgroot` into it with `ditto`, **keeping the staged owners and modes**.
   The staged folders were created by AutoPkg running as you, so they are yours.
2. **`apply_chown`** runs **as root** (the packager is a privileged helper) and applies
   the recipe's `chown` list. An entry sets owner and group on the path *and every
   descendant*; an optional `mode` is applied to the **descendants only**, not to the
   folder named in `path`.
3. **`pkgbuild --ownership preserve`** records exactly what is now on disk.
4. There is **no install-location** option: the payload is always rooted at `/`.

So AutoPkg overrides Apple's `recommended` default with `preserve`. The `chown` list
is the only way a recipe can put root ownership into the package. It is, in effect,
the "preflight chown of the package root" run before `pkgbuild`.

Without any `chown`, the Fruta package would claim:

```text
drwxr-xr-x  <you>:staff  ./Library
drwxr-xr-x  <you>:staff  ./Library/Application Support
drwxr-xr-x  <you>:staff  ./Library/LaunchAgents
```

That is wrong for every Mac, and it bakes your account name into a package you ship.

## 3. What happens to folders that already exist

**Apple doesn't document it.** Neither the PackageMaker guide nor the
[Software Delivery Guide](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/SoftwareDistribution4/Install_Operations/Install_Operations.html)
says whether Installer re-applies payload ownership and permissions to folders that
already exist. The latter only warns: "You should not use install operations to fix
install problems, such as incorrect ownership and access permissions."
Community write-ups ([Scripting OS X, *Building Simple Component Packages*](https://scriptingosx.com/2025/08/building-simple-component-packages/))
say intermediate folders "will be created, should they not exist", and that existing
files of the same name are overwritten. Neither says anything about the metadata of
existing folders.

**History says it has mattered.** "Repair Permissions" existed because "a poorly
designed installer package" could alter permissions of system files and folders
([Wikipedia, *Repair permissions*](https://en.wikipedia.org/wiki/Repair_permissions)).
It relied on exactly these receipt BOMs
([Eclectic Light, *Installers and updates*](https://eclecticlight.co/2015/04/27/installers-and-updates/)).
Since OS X 10.11, System Integrity Protection blocks changes to protected system
locations, and permissions are repaired during system installs and updates. But
`/Library`, `/Library/Application Support` and `/Applications` are **not**
SIP-protected.

**Evidence on a real Mac.** These installed receipts declare non-stock values for
existing folders:

| Receipt | Declares `./Library` | Declares `./Library/Application Support` |
|---|---|---|
| `com.epson.Epson-Scan-OCR-Component-Pro.pkg` | `drwxrwxr-x root:admin` | `drwxrwxr-x root:admin` |
| `com.epson.pkg.Ocr` | `drwxrwxr-x root:wheel` | `drwxrwxr-x root:wheel` |
| `au.csiro.dialogcli` (swiftDialog) | `drwxr-xr-x root:wheel` | `drwxr-xr-x root:wheel` |

On that Mac, `/Library` is still `drwxr-xr-x root:wheel` and
`/Library/Application Support` is still `drwxr-xr-x root:admin`. That suggests the
installer left the existing folders alone, or that a later macOS update put them back.
It is evidence, not a guarantee.

**Conclusion: don't depend on undocumented behaviour.** If a package declares the
stock values, it doesn't matter what the installer does with existing folders.

## 4. What our packages declare today

Union of the six live Acme packages, compared with stock macOS:

| Path | Declared by our packages | Stock macOS | Match |
|---|---|---|---|
| `/` | `drwxrwxr-t root:admin` | `drwxr-xr-x root:wheel` | ✗ — injected by AutoPkg itself (step 1); `/` is on the sealed system volume and can't be changed. Every AutoPkg-built package has this. |
| `/Applications` | `drwxr-xr-x root:admin` | `drwxrwxr-x root:admin` | ✗ **mode** — staged at 755; `chown` can't set the named folder's own mode |
| `/Library` | `drwxr-xr-x root:wheel` | `drwxr-xr-x root:wheel` | ✓ |
| `/Library/Application Support` | `drwxr-xr-x root:admin` | `drwxr-xr-x root:admin` | ✓ |
| `/Library/LaunchAgents` | `drwxr-xr-x root:wheel` | `drwxr-xr-x root:wheel` | ✓ |
| `/Library/Screen Savers` | `drwxr-xr-x root:wheel` | `drwxr-xr-x root:wheel` | ✓ |
| our own paths (`AcmeFruit/…`, `Fruit.saver`, the two plists, the `.app`s) | root-owned, 755 / 644 | — | created by the install |

## How to avoid mismatches

| Option | Verdict |
|---|---|
| **A. Declare stock values** — `chown` entries with the stock owner for each shared parent (owner only), and stage parents with their stock **mode** using `PkgRootCreator` (`pkgdirs: {Applications: "0775", Library: "0755", …}`) before copying files in | **Recommended.** The package claims exactly what's on the Mac; installer behaviour on existing folders stops mattering. |
| B. Leave parents to AutoPkg's default | Records your account as owner of system folders and relies on undocumented installer behaviour. No. |
| C. Avoid parents in the payload (install-location below `/`) | `pkgbuild --install-location` would do it, but AutoPkg's PkgCreator doesn't expose it. It needs a custom build step, and one component package per destination. Not worth it. |
| D. `postinstall` that restores stock owners/modes | Repairs damage the package could have avoided causing. No. |

**Rules for recipe authors** (see also methodology lessons 17 and 19):

1. Every shared parent in the payload gets an **owner-only** `chown` entry with its
   stock owner. Never give it a `mode`: that would be applied to every descendant.
2. If a shared parent's stock mode isn't 755 (`/Applications` is 775), create it with
   `PkgRootCreator` and that mode before any `Copier` step writes into the pkgroot.
3. Your own paths get the owner and mode you actually want installed.
4. Check the result: `pkgutil --expand <pkg> /tmp/x && lsbom -p MUGf /tmp/x/Bom`, and
   compare each shared parent with `stat -f '%Sp %Su:%Sg' <path>` on a stock Mac.

## Settling it empirically (optional)

To find out what Installer does with existing folders on a given macOS release, do this
on a test Mac or VM, never a production machine. Build a package that installs a file
into `/Users/Shared/ownership-test/` and declares that folder `root:wheel 0700`.
Before installing, create the folder as `root:admin 0755`. After
`sudo installer -pkg … -target /`, run `stat` on the folder. The package is harmless,
and the answer applies to every non-SIP folder.
