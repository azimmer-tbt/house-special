# pkg_compare.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Compare an original .pkg with a rebuilt one (specs/pkg-compare/01-pkg-compare.md).

Usage:
  pkg-compare.sh --old-pkg <original.pkg> --new-pkg <rebuilt.pkg> [--work-dir <dir>]

Checks file inventory, permissions (mode, uid and gid from each BOM, so no root is
needed), scripts, and reports metadata. Exit codes: 0 equivalent, 1 inventory
mismatch, 2 permission mismatch (or a usage error), 3 script mismatch,
4 reserved, 5 expansion failure.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from .pkg import (
    BomEntry,
    Inventory,
    PkgError,
    ditto,
    expand,
    inventory,
    lsbom,
    package_info,
    parse_lsbom,
    script_names,
    signature,
)


class UsageError(Exception):
    pass


def err(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def parse_args(argv: list[str]) -> dict:
    opts: dict = {"old": "", "new": "", "work": ""}
    flags = {
        "--old-pkg": ("old", "a file path"),
        "--new-pkg": ("new", "a file path"),
        "--work-dir": ("work", "a directory path"),
    }
    args = list(argv)
    while args:
        arg = args.pop(0)
        if arg in flags:
            key, what = flags[arg]
            if not args or not args[0] or args[0].startswith("-"):
                raise UsageError(f"{arg} requires {what}")
            opts[key] = args.pop(0)
        elif arg in ("-h", "--help"):
            opts["help"] = True
            return opts
        elif arg.startswith("-"):
            raise UsageError(f"Unknown option: {arg}")
        else:
            raise UsageError(f"Unexpected argument: {arg}")
    for key, flag in (("old", "--old-pkg"), ("new", "--new-pkg")):
        if not opts[key]:
            raise UsageError(f"{flag} is required")
    for key in ("old", "new"):
        if not Path(opts[key]).is_file():
            raise UsageError(f"Not a file: {opts[key]}")
    return opts


def component(pkg: Path, out: Path) -> Path:
    """Expand ``pkg`` under ``out`` and return its single component (PkgError 5)."""
    try:
        expanded = expand(pkg, out / "expanded")
    except PkgError as exc:
        raise PkgError(f"{exc}\n  Is it actually a flat package?", 5) from exc
    if len(expanded.components) != 1:
        raise PkgError(
            f"Distribution package with {len(expanded.components)} components"
            " — not supported.",
            5,
            ["Components found:"]
            + [f"    {c.name}" for c in expanded.components]
            + ["", "Multi-component distributions cannot be meaningfully compared."],
        )
    return expanded.component


# ── Comparisons (pure; unit-tested) ───────────────────────────────────────────


def inventory_diff(old: Inventory, new: Inventory) -> list[tuple[str, list[str]]]:
    """(heading, lines) groups describing every inventory difference."""
    groups = []

    def add(heading: str, items: list[str], count: bool = True) -> None:
        if items:
            groups.append((f"{heading} ({len(items)})" if count else heading, items))

    add("Files only in original", sorted(old.files - new.files))
    add("Files only in rebuilt", sorted(new.files - old.files))
    add("Directories only in original", sorted(old.dirs - new.dirs))
    add("Directories only in rebuilt", sorted(new.dirs - old.dirs))
    only_old = sorted(set(old.symlinks) - set(new.symlinks))
    only_new = sorted(set(new.symlinks) - set(old.symlinks))
    add(
        "Symlinks only in original",
        [f"{p} -> {old.symlinks[p]}" for p in only_old],
        False,
    )
    add(
        "Symlinks only in rebuilt",
        [f"{p} -> {new.symlinks[p]}" for p in only_new],
        False,
    )
    changed = sorted(
        p
        for p in set(old.symlinks) & set(new.symlinks)
        if old.symlinks[p] != new.symlinks[p]
    )
    add(
        "Symlinks with different targets",
        [f"{p} -> {old.symlinks[p]}  vs  {p} -> {new.symlinks[p]}" for p in changed],
        False,
    )
    return groups


def perms_key(entry: BomEntry) -> str:
    # A symlink's own mode bits are meaningless on macOS; compare its owner only.
    if entry.is_link:
        return f"l:{entry.uid}:{entry.gid}"
    return entry.perms()


def permission_diff(
    old: dict[str, BomEntry], new: dict[str, BomEntry]
) -> list[tuple[str, str, str]]:
    """(path, old, new) for every path in both BOMs whose mode or owner differs.

    Files, directories and symlinks are all compared (KI-4); the payload root
    ``.`` is compared too, since its mode and owner are installed."""
    diffs = []
    for path in sorted(set(old) & set(new), key=lambda p: p.split("/")):
        if perms_key(old[path]) != perms_key(new[path]):
            diffs.append((path, old[path].perms(), new[path].perms()))
    return diffs


def mode_bits(path: Path) -> str:
    return format(path.stat().st_mode & 0o777, "o")


# ── Front end ─────────────────────────────────────────────────────────────────


def read_bom(comp: Path) -> dict[str, BomEntry] | None:
    bom = comp / "Bom"
    if not bom.is_file():
        return None
    try:
        return parse_lsbom(lsbom(bom))
    except PkgError as exc:
        print(f"WARN:  {exc}", file=sys.stderr)
        return None


def compare(old_pkg: Path, new_pkg: Path, work: Path) -> int:
    print("=== pkg-compare.sh ===")
    print(f"  old: {old_pkg}")
    print(f"  new: {new_pkg}")
    print(f"  work: {work}")
    print("")

    old_out, new_out = work / "old", work / "new"
    old_out.mkdir(parents=True, exist_ok=True)
    new_out.mkdir(parents=True, exist_ok=True)

    print("=== Expanding packages ===")
    comps = {}
    for label, pkg, out in (("old", old_pkg, old_out), ("new", new_pkg, new_out)):
        print(f"  {label} package... ", end="", flush=True)
        try:
            comps[label] = component(pkg, out)
        except PkgError as exc:
            print("FAILED", flush=True)
            err(str(exc))
            for line in exc.details:
                err(line)
            print(f"  Expanded tree left at {out}/expanded for inspection.")
            return 5
        print(f"done (component: {comps[label].name})")

    print("=== Package metadata ===")
    old_info, new_info = package_info(comps["old"]), package_info(comps["new"])
    for key, label in (
        ("identifier", "identifier:  "),
        ("version", "version:     "),
        ("install_location", "install-loc: "),
    ):
        none = "" if key == "install_location" else "<none>"
        print(f"  old {label} {old_info[key] or none}")
        print(f"  new {label} {new_info[key] or none}")
    print(f"  old signature:    {signature(old_pkg)[0]}")
    print(f"  new signature:    {signature(new_pkg)[0]}")
    meta_ok = True
    for key, name in (
        ("identifier", "identifier"),
        ("version", "version"),
        ("install_location", "install-location"),
    ):
        if old_info[key] != new_info[key]:
            print(f"  ✗ MISMATCH: {name} differs")
            meta_ok = False
    if meta_ok:
        print("  ✓ metadata matches")

    print("")
    print("=== Extracting payloads ===")
    payloads = {}
    for label, out in (("old", old_out), ("new", new_out)):
        payloads[label] = out / "payload"
        source = comps[label] / "Payload"
        if source.is_dir():
            ditto(source, payloads[label])
        else:
            payloads[label].mkdir(parents=True, exist_ok=True)
        print(f"  {label} payload extracted to {payloads[label]}")

    print("")
    print("=== Comparing file inventory ===")
    groups = inventory_diff(inventory(payloads["old"]), inventory(payloads["new"]))
    if not groups:
        print("  [PASS] file inventory: identical")
    else:
        print("  [FAIL] file inventory:")
        for heading, lines in groups:
            print(f"    {heading}:")
            for line in lines:
                print(f"      {line}")

    print("")
    print("=== Comparing permissions (from BOM) ===")
    old_bom, new_bom = read_bom(comps["old"]), read_bom(comps["new"])
    perm_diffs = []
    if old_bom is None or new_bom is None:
        print("  [SKIP] permissions: a package has no readable Bom")
    else:
        perm_diffs = permission_diff(old_bom, new_bom)
        if perm_diffs:
            print("  [FAIL] permissions:")
            for path, old, new in perm_diffs:
                print(f"    {path}")
                print(f"      old: {old}  new: {new}")
        else:
            print("  [PASS] permissions: all shared paths match")

    print("")
    print("=== Comparing scripts ===")
    script_fail = compare_scripts(comps["old"] / "Scripts", comps["new"] / "Scripts")

    print("")
    print("=== Summary ===")
    print("")
    code = 0
    if groups:
        print("  [FAIL] file inventory")
        code = 1
    elif perm_diffs:
        print("  [FAIL] permissions")
        code = 2
    elif script_fail:
        print("  [FAIL] scripts")
        code = 3
    if code:
        print("")
        print("✗ Deployable content differs. Fix and re-run.")
    else:
        print("  [PASS] file inventory")
        print("  [PASS] permissions")
        print("  [PASS] scripts")
        print("  [PASS] metadata (reported above)")
        print("")
        print("✓ Packages are equivalent (deployable content).")
    return code


def compare_scripts(old_dir: Path, new_dir: Path) -> bool:
    """Print the scripts section; True when the scripts differ."""
    old, new = script_names(old_dir), script_names(new_dir)
    if not old and not new:
        print("  [PASS] scripts: none in either package")
        return False
    if old and not new:
        print("  [FAIL] scripts: original has scripts, rebuilt does not:")
        for name in old:
            print(f"    {name}")
        return True
    if new and not old:
        print("  [FAIL] scripts: rebuilt has scripts, original does not:")
        for name in new:
            print(f"    {name}")
        return True
    if old != new:
        print("  [FAIL] scripts: different set of script files")
        print(f"    original: {' '.join(old)} ")
        print(f"    rebuilt:  {' '.join(new)} ")
        return True
    differ = False
    for name in old:
        a, b = old_dir / name, new_dir / name
        # Bytes, not filecmp: its cache keys on size and mtime, which a rebuilt
        # script of the same length and timestamp shares with the original.
        if a.read_bytes() != b.read_bytes():
            differ = True
        if mode_bits(a) != mode_bits(b):
            print(
                f"    {name}: mode {mode_bits(a)} (original)"
                f" vs {mode_bits(b)} (rebuilt)"
            )
            differ = True
    if differ:
        print("  [FAIL] scripts: content or mode differs (details above)")
    else:
        print("  [PASS] scripts: identical set, content, and modes")
    return differ


def main(argv: list[str] | None = None) -> int:
    try:
        opts = parse_args(sys.argv[1:] if argv is None else argv)
    except UsageError as exc:
        err(str(exc))
        return 2
    if opts.get("help"):
        print(__doc__)
        return 0
    old_pkg = Path(opts["old"]).resolve()
    new_pkg = Path(opts["new"]).resolve()
    keep = bool(opts["work"])
    if keep:
        work = Path(opts["work"])
        try:
            work.mkdir(parents=True, exist_ok=True)
        except OSError:
            err(f"Could not create --work-dir: {opts['work']}")
            return 2
        work = work.resolve()
    else:
        work = Path(tempfile.mkdtemp(prefix="pkg-compare.", dir="/tmp")).resolve()

    code = compare(old_pkg, new_pkg, work)

    if keep:
        print(f"  work dir kept: {work}")
    elif code == 0:
        shutil.rmtree(work, ignore_errors=True)
    else:
        print(f"  work dir left for inspection: {work}")
    return code


if __name__ == "__main__":
    # Warnings go to stderr between progress lines; keep them in order.
    sys.stdout.reconfigure(line_buffering=True)
    sys.exit(main())
