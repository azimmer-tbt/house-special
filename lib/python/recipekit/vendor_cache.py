# vendor_cache.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Vendor-cache housekeeping: normalize dropped files to their canonical names,
and sync the files a manifest lists from a durable copy (specs/vendor-cache/).

  tk_python -m recipekit.vendor_cache normalize --repo <recipe-repo>
      --vendor-cache <dir> [--dry-run] [--relocate-dir <dir>]
  tk_python -m recipekit.vendor_cache sync [--dry-run] <index> <from_dir> <to_dir>

The front ends are bin/normalize-vendor-cache.sh and bin/sync-vendor-cache.sh.
Standard library and PyYAML only; no yq (KI-21).
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REGISTRY_NAME = "vendor-drop-registry.yaml"
COMPOUND_SUFFIXES = (".tar.gz", ".tar.bz2")
UNSAFE = re.compile(r"[^-._A-Za-z0-9]")
RELOCATED = "relocated"  # default folder, at the vendor-cache root


class ConfigError(Exception):
    pass


def file_type(name: str) -> str:
    """The lowercased type suffix, ``.tar.gz`` counted whole; empty for none."""
    lower = name.lower()
    for suffix in COMPOUND_SUFFIXES:
        if lower.endswith(suffix):
            return suffix
    return Path(lower).suffix


# ── Normalize ─────────────────────────────────────────────────────────────────


@dataclass
class Registry:
    canonical: dict[str, str] = field(default_factory=dict)  # "Vendor/App" -> name
    ignored_subdirs: list[str] = field(default_factory=list)
    protected_files: list[str] = field(default_factory=list)


def load_registry(path: Path) -> Registry:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Failed to parse config: {path} ({exc})") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Failed to parse config: {path} (expected a mapping)")
    canonical = data.get("canonical_filenames") or {}
    if not isinstance(canonical, dict):
        raise ConfigError(f"Failed to parse config: {path} (canonical_filenames)")
    return Registry(
        {str(k): str(v) for k, v in canonical.items()},
        [str(x) for x in data.get("ignored_subdirs") or []],
        [str(x) for x in data.get("protected_files") or []],
    )


def key_problem(key: str, name: str) -> str:
    parts = key.split("/")
    if len(parts) != 2 or not all(parts) or ".." in parts:
        return f"Registry key must be Vendor/App: {key}"
    if not name or "/" in name or name in (".", ".."):
        return f"Canonical name must be a plain file name: {name!r}"
    return ""


class Normalizer:
    """One pass over the registry. Lines go to ``out`` (and errors/warnings to
    ``err``) as ACTION<TAB>KEY<TAB>OLD<TAB>NEW<TAB>MESSAGE."""

    def __init__(self, registry, cache: Path, relocate_dir: Path, dry_run=False):
        self.registry, self.cache = registry, cache
        self.relocate_dir, self.dry_run = relocate_dir, dry_run
        self.lines: list[tuple[str, str]] = []  # (stream, line)
        self.failed = False

    def emit(self, action, key, old="", new="", message="", stream="out"):
        self.lines.append((stream, "\t".join((action, key, old, new, message))))

    def run(self) -> None:
        for key in sorted(self.registry.canonical):
            self.entry(key, self.registry.canonical[key])

    def entry(self, key: str, canonical: str) -> None:
        problem = key_problem(key, canonical)
        if problem:
            self.emit("ERROR", key, "", canonical, problem, "err")
            self.failed = True
            return
        folder = self.cache / key
        if not folder.is_dir():
            if folder.parent.is_dir():
                self.emit(
                    "MISSING", key, message=f"Target directory not found: {folder}"
                )
            return
        files = []
        for entry in sorted(folder.iterdir()):
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                if entry.name in self.registry.ignored_subdirs:
                    self.emit(
                        "IGNORE",
                        key,
                        entry.name,
                        message=f"Skipping {entry.name}/ subdirectory (ignored)",
                    )
                continue
            if entry.is_file():
                files.append(entry)
        if not files:
            self.emit("MISSING", key, message=f"No files found in {folder}")
            return

        wanted = file_type(canonical)
        protected = set(self.registry.protected_files)
        # Only files of the canonical name's type are versions of it (KI-7).
        same_type = [f for f in files if not wanted or file_type(f.name) == wanted]
        others = [f for f in files if f not in same_type]
        for f in others:
            if f.name not in protected:
                self.emit(
                    "KEEP", key, f.name, canonical, "Different type — left in place"
                )

        current = folder / canonical
        if current.is_file():
            usable = [f for f in same_type if f.name not in protected]
            # On a tie the canonical file stays.
            newest = min(
                usable,
                key=lambda f: (-f.stat().st_mtime, f.name != canonical, f.name),
            )
            if newest.name != canonical:
                self.replace(key, current, newest, usable, canonical)
                return
            extras = [f for f in same_type if f.name != canonical]
            for f in extras:
                if f.name in protected:
                    self.emit("SKIP", key, f.name, canonical, "Protected — kept")
                else:
                    self.prune(key, f, canonical)
            if not extras and not others:
                self.emit("SKIP", key, canonical, message="Already in place")
            return

        candidates = [f for f in same_type if f.name not in protected]
        for f in same_type:
            if f.name in protected:
                self.emit("SKIP", key, f.name, canonical, "Protected — kept")
        if not candidates:
            kind = f" {wanted}" if wanted else ""
            self.emit("MISSING", key, message=f"No{kind} file to rename in {folder}")
            return
        candidates.sort(key=lambda f: (-f.stat().st_mtime, f.name))
        newest = candidates[0]
        message = "DONE"
        if self.dry_run:
            message = "DRY RUN"
        else:
            try:
                newest.rename(folder / canonical)
            except OSError as exc:
                self.emit(
                    "ERROR", key, newest.name, canonical, f"Rename failed: {exc}", "err"
                )
                self.failed = True
                return
        if UNSAFE.search(newest.name):
            message += "|UNSAFE_CHARS"
        self.emit("RENAME", key, newest.name, canonical, message)
        rest = [f.name for f in candidates[1:]]
        if rest:
            self.emit(
                "WARN",
                key,
                message=f"{len(rest)} extra file(s) remain after rename:"
                f" {' '.join(rest)}",
                stream="err",
            )

    def replace(self, key, current, newest, usable, canonical) -> None:
        """A newer drop beside the canonical file: it becomes the canonical file;
        the old one and any other stale versions are relocated."""
        if not self.prune(key, current, canonical, f"Superseded by {newest.name}; "):
            return
        message = "DRY RUN|REPLACED" if self.dry_run else "DONE|REPLACED"
        if not self.dry_run:
            try:
                newest.rename(current)
            except OSError as exc:
                self.emit(
                    "ERROR", key, newest.name, canonical, f"Rename failed: {exc}", "err"
                )
                self.failed = True
                return
        if UNSAFE.search(newest.name):
            message += "|UNSAFE_CHARS"
        self.emit("RENAME", key, newest.name, canonical, message)
        for f in usable:
            if f not in (newest, current):
                self.prune(key, f, canonical)

    def prune(self, key: str, f: Path, canonical: str, why: str = "") -> bool:
        """Move a stale file aside, to the same Vendor/App path under the
        relocate folder; never delete (KI-7) and never overwrite."""
        dest = free_name(self.relocate_dir / key / f.name)
        if self.dry_run:
            self.emit(
                "PRUNE",
                key,
                f.name,
                canonical,
                f"{why}DRY RUN: would relocate to {dest}",
            )
            return True
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(dest))
        except OSError as exc:
            self.emit("ERROR", key, f.name, canonical, f"Could not move: {exc}", "err")
            self.failed = True
            return False
        self.emit("PRUNE", key, f.name, canonical, f"{why}Relocated to {dest}")
        return True


def free_name(path: Path) -> Path:
    """``path``, or ``name-2.ext``, ``name-3.ext``… when it is already taken."""
    if not path.exists() and not path.is_symlink():
        return path
    suffix = file_type(path.name)
    stem = path.name[: len(path.name) - len(suffix)] if suffix else path.name
    n = 2
    while True:
        candidate = path.with_name(f"{stem}-{n}{path.name[len(stem):]}")
        if not candidate.exists() and not candidate.is_symlink():
            return candidate
        n += 1


def normalize_main(argv: list[str]) -> int:
    opts = {"repo": "", "vendor-cache": "", "relocate-dir": "", "dry-run": False}
    usage = (
        "Usage: normalize-vendor-cache.sh --repo /path/to/recipe-repo"
        " --vendor-cache /path/to/vendor_cache [--dry-run] [--relocate-dir <dir>]"
    )
    args = list(argv)
    while args:
        arg = args.pop(0)
        if arg in ("--repo", "--vendor-cache", "--relocate-dir"):
            if not args or not args[0] or args[0].startswith("-"):
                return fail(f"{arg} requires a path", 1)
            opts[arg[2:]] = args.pop(0)
        elif arg == "--dry-run":
            opts["dry-run"] = True
        else:
            return fail(f"Unknown argument: {arg}", 1)
    for flag in ("repo", "vendor-cache"):
        if not opts[flag]:
            return fail(f"--{flag} is required\n{usage}", 1)
    registry_path = Path(opts["repo"]) / REGISTRY_NAME
    if not registry_path.is_file():
        return fail(f"Vendor-drop registry not found at: {registry_path}", 1)
    cache = Path(opts["vendor-cache"])
    if not cache.is_dir():
        return fail(f"Vendor cache root not found: {cache}", 1)
    try:
        registry = load_registry(registry_path)
    except ConfigError as exc:
        return fail(str(exc), 1)
    if not registry.canonical:
        print("WARN: Registry is empty — nothing to normalize", file=sys.stderr)
        return 0
    relocate_dir = Path(opts["relocate-dir"] or cache / RELOCATED)
    # A vendor folder with the relocate folder's name would be relocated into.
    if relocate_dir.resolve().parent == cache.resolve():
        clash = [k for k in registry.canonical if k.split("/")[0] == relocate_dir.name]
        if clash:
            return fail(
                f"Registry vendor '{relocate_dir.name}' clashes with the relocate"
                " folder; pass --relocate-dir <other folder>",
                1,
            )
    run = Normalizer(registry, cache, relocate_dir, opts["dry-run"])
    run.run()
    for stream, line in run.lines:
        print(line, file=sys.stderr if stream == "err" else sys.stdout)
    return 1 if run.failed else 0


# ── Sync ──────────────────────────────────────────────────────────────────────


def load_index(path: Path) -> list[str]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Cannot parse index {path}: {exc}") from exc
    files = data.get("files") if isinstance(data, dict) else None
    return [str(f) for f in files or [] if f]


def unsafe_entry(rel: str) -> bool:
    """An index entry that would reach outside the cache roots."""
    return os.path.isabs(rel) or ".." in Path(rel).parts or not rel.strip()


def up_to_date(src: Path, dst: Path) -> bool:
    if not (src.is_file() and dst.is_file()):
        return False
    s, d = src.stat(), dst.stat()
    return s.st_size == d.st_size and int(s.st_mtime) <= int(d.st_mtime)


def sync_main(argv: list[str]) -> int:
    args = list(argv)
    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    usage = (
        "Usage: sync-vendor-cache.sh [--dry-run] <index> <from_dir> <to_dir>\n\n"
        "Arguments:\n  index     Path to files_to_copy.yaml\n"
        "  from_dir  Source vendor_cache root\n  to_dir    Target vendor_cache root"
    )
    unknown = [a for a in args if a.startswith("-")]
    if unknown or len(args) != 3:
        print(usage, file=sys.stderr)
        return 2
    index, src_root, dst_root = (Path(a) for a in args)
    if not index.is_file():
        return fail(f"Index file not found: {index}", 2)
    if not src_root.is_dir():
        return fail(f"Source directory not found: {src_root}", 2)
    try:
        entries = load_index(index)
    except ConfigError as exc:
        return fail(str(exc), 2)
    if not entries:
        return fail(f"No files listed in index: {index}", 2)
    if not dry_run:
        try:
            dst_root.mkdir(parents=True, exist_ok=True)
        except OSError:
            return fail(f"Cannot create target directory: {dst_root}", 2)

    copied = skipped = errors = 0
    note = "  (dry run)" if dry_run else ""
    for rel in entries:
        if unsafe_entry(rel):
            print(
                f"ERROR {rel}  (outside the vendor cache; not copied)", file=sys.stderr
            )
            errors += 1
            continue
        src, dst = src_root / rel, dst_root / rel
        if not src.exists():
            print(f"ERROR: Source not found: {src}", file=sys.stderr)
            errors += 1
            continue
        if up_to_date(src, dst):
            print(f"SKIP  {rel}  (target is same size and newer or equal)")
            skipped += 1
            continue
        label = f"COPY  {rel}{'  (directory)' if src.is_dir() else ''}{note}"
        if dry_run:
            print(label)
            copied += 1
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                # A mirror: the target folder is replaced, timestamps kept.
                if dst.is_dir() and not dst.is_symlink():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst, symlinks=True)
            else:
                shutil.copy2(src, dst)
        except OSError as exc:
            print(f"ERROR {rel}  (copy failed: {exc})", file=sys.stderr)
            errors += 1
            continue
        print(label)
        copied += 1

    print("")
    print("=== sync complete ===" + (" (dry run: nothing copied)" if dry_run else ""))
    print(f"  Copied: {copied}")
    print(f"  Skipped (up-to-date): {skipped}")
    print(f"  Errors: {errors}")
    return 1 if errors else 0


# ── Entry point ───────────────────────────────────────────────────────────────


def fail(message: str, code: int) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    commands = {"normalize": normalize_main, "sync": sync_main}
    if not argv or argv[0] not in commands:
        return fail("expected a command: normalize or sync", 2)
    return commands[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    sys.exit(main())
