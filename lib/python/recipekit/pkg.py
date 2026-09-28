# pkg.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Flat-package plumbing shared by pkg-compare and pkg-reverse.

Expansion (pkgutil --expand-full), PackageInfo, signatures, the payload inventory,
and the Bill of Materials. The BOM is read with ``lsbom -p mugsfl``: numeric mode,
uid and gid, size, path and link target, tab-separated (docs/known-issues.md KI-4).
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

LSBOM_FORMAT = "mugsfl"


class PkgError(Exception):
    """A package that can't be expanded or read; ``code`` is the tool's exit code."""

    def __init__(self, message: str, code: int = 2, details: list[str] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or []


# ── BOM ───────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class BomEntry:
    path: str  # relative to the payload root, "." for the root itself
    mode: int  # st_mode: type and permission bits
    uid: int
    gid: int
    size: str = ""
    link: str = ""

    @property
    def owner(self) -> str:
        return f"{self.uid}:{self.gid}"

    @property
    def is_dir(self) -> bool:
        return stat.S_ISDIR(self.mode)

    @property
    def is_link(self) -> bool:
        return stat.S_ISLNK(self.mode)

    def perms(self) -> str:
        """Symbolic mode plus numeric owner, e.g. ``-rw-r--r--:0:80``."""
        return f"{stat.filemode(self.mode)}:{self.uid}:{self.gid}"


def parse_lsbom(text: str) -> dict[str, BomEntry]:
    """Parse ``lsbom -p mugsfl`` output, keyed by path without the leading ``./``.

    Fields are tab-separated, so directories (empty size) and paths with spaces
    parse correctly. Unparseable lines are skipped."""
    entries: dict[str, BomEntry] = {}
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        mode, uid, gid, size, path = parts[:5]
        link = parts[5] if len(parts) > 5 else ""
        try:
            entry = BomEntry(
                relative(path), int(mode, 8), int(uid), int(gid), size, link
            )
        except ValueError:
            continue
        entries[entry.path] = entry
    return entries


def relative(path: str) -> str:
    if path in (".", "./", ""):
        return "."
    return path[2:] if path.startswith("./") else path


def lsbom(bom: Path) -> str:
    """Raw ``lsbom -p mugsfl`` output for a Bom file (raises PkgError on failure)."""
    try:
        done = subprocess.run(
            ["lsbom", "-p", LSBOM_FORMAT, str(bom)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise PkgError(f"lsbom failed on {bom}: {exc}") from exc
    if done.returncode != 0:
        raise PkgError(f"lsbom failed on {bom}: {done.stderr.strip()}")
    return done.stdout


def chown_rollup(entries: dict[str, BomEntry]) -> list[tuple[str, str]]:
    """The fewest ``(path, "uid:gid")`` chown entries that reproduce the BOM.

    PkgCreator's chown is recursive and applied in order, so entries come parent
    first: a path is listed only when its owner differs from the one its nearest
    listed ancestor sets. The payload root itself is never listed."""
    ordered = sorted((p for p in entries if p != "."), key=lambda p: p.split("/"))
    listed: dict[str, str] = {}
    result: list[tuple[str, str]] = []
    for path in ordered:
        owner = entries[path].owner
        inherited = None
        parent = path
        while "/" in parent:
            parent = parent.rsplit("/", 1)[0]
            if parent in listed:
                inherited = listed[parent]
                break
        if owner != inherited:
            listed[path] = owner
            result.append((path, owner))
    return result


# ── Expansion and metadata ────────────────────────────────────────────────────


@dataclass
class Expanded:
    root: Path
    kind: str  # "component" or "distribution"
    components: list[Path] = field(default_factory=list)

    @property
    def component(self) -> Path:
        return self.components[0]


def expand(pkg: Path, dest: Path) -> Expanded:
    """``pkgutil --expand-full`` into ``dest`` and find the component.

    Raises PkgError(code=2) when pkgutil fails or the layout is unrecognised.
    A distribution's components are returned whatever their number; callers
    decide what a count other than one means."""
    done = subprocess.run(
        ["pkgutil", "--expand-full", str(pkg), str(dest)],
        capture_output=True,
        check=False,
    )
    if done.returncode != 0:
        raise PkgError(f"pkgutil --expand-full failed on {pkg}")
    if (dest / "PackageInfo").is_file():
        return Expanded(dest, "component", [dest])
    if (dest / "Distribution").is_file():
        components = sorted(
            p for p in dest.iterdir() if p.is_dir() and p.name.endswith(".pkg")
        )
        return Expanded(dest, "distribution", components)
    raise PkgError(
        "Neither PackageInfo nor Distribution found in the expanded package"
        " — unrecognised format."
    )


def package_info(component: Path) -> dict[str, str]:
    """identifier, version and install-location (default ``/``) from PackageInfo."""
    info = {"identifier": "", "version": "", "install_location": ""}
    try:
        root = ET.parse(component / "PackageInfo").getroot()
    except (OSError, ET.ParseError):
        root = None
    if root is not None and root.tag == "pkg-info":
        info["identifier"] = root.get("identifier", "")
        info["version"] = root.get("version", "")
        info["install_location"] = root.get("install-location", "")
    info["install_location"] = info["install_location"] or "/"
    return info


def signature(pkg: Path) -> tuple[str, str]:
    """``("signed", authority)`` or ``("unsigned", "")`` from pkgutil."""
    done = subprocess.run(
        ["pkgutil", "--check-signature", str(pkg)],
        capture_output=True,
        text=True,
        check=False,
    )
    if "Status: signed" not in done.stdout:
        return "unsigned", ""
    for line in done.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("1. "):
            return "signed", stripped[3:]
    return "signed", ""


def team_id(authority: str) -> str:
    """The team ID in a Developer ID authority, e.g. ``… Inc. (UBF8T346G9)``."""
    match = re.search(r"\(([A-Z0-9]{10})\)\s*$", authority)
    return match.group(1) if match else ""


def ditto(src: Path, dest: Path) -> None:
    done = subprocess.run(["/usr/bin/ditto", str(src), str(dest)], check=False)
    if done.returncode != 0:
        raise PkgError(f"ditto failed copying {src}")


# ── Payload inventory ─────────────────────────────────────────────────────────


@dataclass
class Inventory:
    files: set[str] = field(default_factory=set)
    dirs: set[str] = field(default_factory=set)
    symlinks: dict[str, str] = field(default_factory=dict)  # path -> target


def inventory(root: Path) -> Inventory:
    """Files, directories (not the root) and symlinks under ``root``, relative."""
    inv = Inventory()
    for dirpath, dirnames, filenames in os.walk(root):
        base = Path(dirpath)
        for name in dirnames + filenames:
            path = base / name
            rel = str(path.relative_to(root))
            if path.is_symlink():
                inv.symlinks[rel] = os.readlink(path)
            elif path.is_dir():
                inv.dirs.add(rel)
            else:
                inv.files.add(rel)
    return inv


def script_names(scripts: Path) -> list[str]:
    """Regular files directly in a Scripts folder; empty when there is none."""
    if not scripts.is_dir():
        return []
    return sorted(p.name for p in scripts.iterdir() if p.is_file())
