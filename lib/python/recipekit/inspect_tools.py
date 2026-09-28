# inspect_tools.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Read-only inspection of an .app bundle, a .dmg and an archive
(specs/analysis/inspect-tools/01-inspect-tools.md).

  tk_python -m recipekit.inspect_tools app <Example.app> [--output text|json]
  tk_python -m recipekit.inspect_tools dmg <file.dmg> [--output …] [--keep-mounted]
  tk_python -m recipekit.inspect_tools archive <archive> [--output …] [--max-entries N]

The front ends are bin/inspect-app.sh, bin/inspect-dmg.sh and
bin/inspect-archive.sh. Info.plist is read with plistlib, archives with zipfile
and tarfile; hdiutil, lipo and file are the only tools run. Exit codes: 0 done,
2 usage error, missing file or unreadable input.
"""

from __future__ import annotations

import json
import os
import plistlib
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


class UsageError(Exception):
    pass


def human_mb(size: int) -> str:
    return f"{size} bytes ({size // 1048576} MB)"


# ── .app ──────────────────────────────────────────────────────────────────────

PLIST_FIELDS = (
    ("name", "CFBundleName"),
    ("display_name", "CFBundleDisplayName"),
    ("identifier", "CFBundleIdentifier"),
    ("version", "CFBundleShortVersionString"),
    ("build", "CFBundleVersion"),
    ("minimum_os", "LSMinimumSystemVersion"),
)


def read_info(app: Path) -> dict:
    """The bundle's top-level Info.plist keys (XML or binary); UsageError if none."""
    plist = app / "Contents" / "Info.plist"
    if not plist.is_file():
        raise UsageError(
            f"No Info.plist found at {plist} — is this really an .app bundle?"
        )
    try:
        with open(plist, "rb") as f:
            data = plistlib.load(f)
    except (OSError, plistlib.InvalidFileException, ValueError) as exc:
        raise UsageError(f"Cannot read {plist}: {exc}") from exc
    return data if isinstance(data, dict) else {}


def architectures(binary: Path) -> list[str]:
    if not binary.is_file():
        return []
    done = subprocess.run(
        ["lipo", "-archs", str(binary)], capture_output=True, text=True, check=False
    )
    if done.returncode == 0 and done.stdout.strip():
        return done.stdout.split()
    done = subprocess.run(
        ["file", "-b", str(binary)], capture_output=True, text=True, check=False
    )
    return sorted({a for a in ("arm64", "x86_64") if a in done.stdout})


def app_info(app: Path) -> dict:
    info = read_info(app)
    result = {"path": str(app)}
    for key, plist_key in PLIST_FIELDS:
        value = info.get(plist_key, "")
        result[key] = value if isinstance(value, str) else str(value) if value else ""
    executable = info.get("CFBundleExecutable")
    binary = app / "Contents" / "MacOS" / str(executable) if executable else None
    result["architectures"] = architectures(binary) if binary else []
    result["has_code_signature"] = (app / "Contents" / "_CodeSignature").is_dir()
    return result


def app_main(args: list[str], output: str) -> int:
    if len(args) != 1:
        raise UsageError(
            "No app path specified. Usage: inspect-app.sh <path/to/Example.app>"
            " [--output text|json]"
        )
    app = Path(args[0])
    if not app.is_dir():
        raise UsageError(f"Not a directory: {app}")
    info = app_info(app)
    if output == "json":
        print(json.dumps(info, indent=2))
        return 0
    print("=== inspect-app.sh ===")
    for label, key in (
        ("Name:        ", "name"),
        ("Display name:", "display_name"),
        ("Identifier:  ", "identifier"),
        ("Version:     ", "version"),
        ("Build:       ", "build"),
        ("Minimum OS:  ", "minimum_os"),
    ):
        print(f"  {label} {info[key] or '(not set)'}")
    print(f"  Architectures: {','.join(info['architectures']) or '(not determined)'}")
    print(f"  Code signed:  {str(info['has_code_signature']).lower()}")
    return 0


# ── .dmg ──────────────────────────────────────────────────────────────────────


def attach(dmg: Path) -> str:
    """Mount read-only at a random point under /tmp; the mount point."""
    done = subprocess.run(
        ["/usr/bin/hdiutil", "attach", "-nobrowse", "-readonly", "-noautoopen"]
        + ["-mountrandom", "/tmp", "-plist", str(dmg)],
        stdin=subprocess.DEVNULL,  # never answer a license prompt for the user
        capture_output=True,
        check=False,
    )
    if done.returncode != 0:
        detail = done.stderr.decode("utf-8", "replace").strip()
        if b"agree" in done.stdout.lower() or "agree" in detail.lower():
            detail = "the image asks to accept a license agreement; mount it by hand"
        raise UsageError(f"Failed to mount {dmg}: {detail or 'not a disk image?'}")
    try:
        entities = plistlib.loads(done.stdout).get("system-entities", [])
    except (plistlib.InvalidFileException, ValueError) as exc:
        raise UsageError(f"Failed to mount {dmg}: unreadable hdiutil output") from exc
    points = [e["mount-point"] for e in entities if e.get("mount-point")]
    if not points:
        raise UsageError(f"Failed to mount {dmg}: no mountable volume")
    return points[0]


def detach(mount_point: str) -> None:
    for extra in ([], ["-force"]):
        done = subprocess.run(
            ["/usr/bin/hdiutil", "detach", mount_point, "-quiet", *extra],
            capture_output=True,
            check=False,
        )
        if done.returncode == 0:
            return


def volume_info(root: Path) -> dict:
    """Top-level items, the count of every item (the volume root excluded), and
    the outermost .app bundles, not the helpers inside them. Symlinks such as
    /Applications are not followed."""
    top = sorted(p.name for p in root.iterdir() if p.name != ".DS_Store")
    total, apps = 0, []
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        total += sum(1 for n in dirnames + filenames if n != ".DS_Store")
        parts = here.relative_to(root).parts
        if any(part.endswith(".app") for part in parts) or len(parts) >= 10:
            continue  # helpers inside an app are counted, not listed
        for name in sorted(dirnames):
            path = here / name
            if name.endswith(".app") and not path.is_symlink():
                apps.append(path)
    entries = []
    for path in apps:
        try:
            info = app_info(path)
        except UsageError:
            info = {k: "" for k, _ in PLIST_FIELDS} | {"architectures": []}
        entries.append(
            {
                "path": str(path),
                "name": path.name,
                "identifier": info["identifier"],
                "version": info["version"],
                "build": info["build"],
                "architectures": info["architectures"],
            }
        )
    return {"apps": entries, "top_level_items": top, "total_items": total}


def dmg_main(args: list[str], output: str, keep: bool) -> int:
    if len(args) != 1:
        raise UsageError(
            "No DMG specified. Usage: inspect-dmg.sh <file.dmg>"
            " [--output text|json] [--keep-mounted]"
        )
    dmg = Path(args[0])
    if not dmg.is_file():
        raise UsageError(f"Not a file: {dmg}")
    dmg = dmg.resolve()
    mount_point = attach(dmg)
    try:
        volume = volume_info(Path(mount_point))
    finally:
        if not keep:
            detach(mount_point)
    size = dmg.stat().st_size
    if output == "json":
        result = {"file": str(dmg), "size_bytes": size, "mount_point": mount_point}
        result.update(volume)
        result["kept_mounted"] = keep
        print(json.dumps(result, indent=2))
        return 0
    print("=== inspect-dmg.sh ===")
    print(f"  File:         {dmg}")
    print(f"  Size:         {human_mb(size)}")
    print(f"  Mount:        {mount_point}")
    print("")
    print("=== Applications found ===")
    for app in volume["apps"]:
        version = app["version"] or "unknown"
        build = f" ({app['build']})" if app["build"] and app["build"] != version else ""
        archs = ",".join(app["architectures"]) or "?"
        print(f"  {app['name']}  {app['identifier'] or '?'}  {version}{build}  {archs}")
    if not volume["apps"]:
        print("  (none)")
    print("")
    print("=== DMG structure ===")
    print(f"  Top level:    {','.join(volume['top_level_items'])}")
    print(f"  Total items:  {volume['total_items']}")
    if keep:
        print("")
        print(f"  DMG left mounted at: {mount_point}")
        print(f"  Unmount with: hdiutil detach {mount_point}")
    return 0


# ── Archives ──────────────────────────────────────────────────────────────────

SUFFIXES = (
    (".tar.gz", "tar.gz"),
    (".tgz", "tar.gz"),
    (".tar.bz2", "tar.bz2"),
    (".tbz2", "tar.bz2"),
    (".tar", "tar"),
    (".zip", "zip"),
)


def archive_type(path: Path) -> str:
    lower = path.name.lower()
    for suffix, kind in SUFFIXES:
        if lower.endswith(suffix):
            return kind
    if zipfile.is_zipfile(path):
        return "zip"
    if tarfile.is_tarfile(path):
        with open(path, "rb") as f:
            magic = f.read(3)
        if magic[:2] == b"\x1f\x8b":
            return "tar.gz"
        return "tar.bz2" if magic == b"BZh" else "tar"
    detected = subprocess.run(
        ["file", "-b", str(path)], capture_output=True, text=True, check=False
    ).stdout.strip()
    raise UsageError(
        f"Unknown archive format. Detected type: {detected}."
        " Supported: .zip, .tar.gz, .tgz, .tar.bz2, .tar"
    )


def archive_entries(path: Path, kind: str) -> list[dict]:
    try:
        if kind == "zip":
            with zipfile.ZipFile(path) as z:
                return [
                    {
                        "path": i.filename,
                        "size": i.file_size,
                        "compressed_size": i.compress_size,
                    }
                    for i in z.infolist()
                ]
        with tarfile.open(path) as tar:
            return [
                {"path": m.name + ("/" if m.isdir() else ""), "size": m.size}
                for m in tar.getmembers()
            ]
    except (zipfile.BadZipFile, tarfile.TarError, OSError, EOFError) as exc:
        raise UsageError(
            f"Failed to list archive contents (may be corrupted): {exc}"
        ) from exc


def archive_main(args: list[str], output: str, max_entries: int) -> int:
    if len(args) != 1:
        raise UsageError(
            "No archive specified. Usage: inspect-archive.sh <archive>"
            " [--output text|json] [--max-entries <n>]"
        )
    path = Path(args[0])
    if not path.is_file():
        raise UsageError(f"Not a file: {path}")
    path = path.resolve()
    kind = archive_type(path)
    entries = archive_entries(path, kind)
    top = sorted({e["path"].split("/")[0] for e in entries if e["path"].split("/")[0]})
    truncated = len(entries) > max_entries
    size = path.stat().st_size
    if output == "json":
        print(
            json.dumps(
                {
                    "file": str(path),
                    "size_bytes": size,
                    "archive_type": kind,
                    "entry_count": len(entries),
                    "entries": entries[:max_entries],
                    "top_level_items": top,
                    "truncated": truncated,
                },
                indent=2,
            )
        )
        return 0
    note = f" (listing truncated at {max_entries})" if truncated else ""
    print("=== inspect-archive.sh ===")
    print(f"  File:         {path}")
    print(f"  Size:         {human_mb(size)}")
    print(f"  Type:         {kind}")
    print(f"  Entries:      {len(entries)}{note}")
    print("")
    print("=== Top-level contents ===")
    for item in top:
        print(f"  {item}")
    print("")
    print("  Run with --output json for full file listing.")
    return 0


# ── Entry point ───────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("app", "dmg", "archive"):
        print("ERROR: expected a command: app, dmg or archive", file=sys.stderr)
        return 2
    command, rest = argv[0], argv[1:]
    output, keep, max_entries, positional = "text", False, 200, []
    try:
        while rest:
            arg = rest.pop(0)
            if arg == "--output":
                if not rest or rest[0].startswith("-"):
                    raise UsageError("--output requires text or json")
                output = rest.pop(0)
                if output not in ("text", "json"):
                    raise UsageError("--output must be text or json")
            elif arg == "--keep-mounted" and command == "dmg":
                keep = True
            elif arg == "--max-entries" and command == "archive":
                if not rest or rest[0].startswith("-"):
                    raise UsageError("--max-entries requires a number")
                value = rest.pop(0)
                if not value.isdigit() or int(value) < 1:
                    raise UsageError("--max-entries must be >= 1")
                max_entries = int(value)
            elif arg.startswith("-"):
                raise UsageError(f"Unknown option: {arg}")
            else:
                if positional:
                    raise UsageError(f"Unexpected argument: {arg}")
                positional.append(arg)
        if command == "app":
            return app_main(positional, output)
        if command == "dmg":
            return dmg_main(positional, output, keep)
        return archive_main(positional, output, max_entries)
    except UsageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
