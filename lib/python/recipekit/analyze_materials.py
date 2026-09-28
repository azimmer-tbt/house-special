# analyze_materials.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Find distributable files in a folder of vendor materials and match them to
target recipes (specs/analysis/analyze-materials/01-analyze-materials.md).

The front end is bin/analyze-materials.sh; its header is the usage text. Targets
come from an end_result.yaml (docs/FORMATS.md §3): --targets <file>, or the
customer's folder with --customer <name>. With clues (--clues, or the
customer's), each .pkg found is classified as analyze-package would. Progress
goes to stderr, so --output json is pure JSON. Exit codes: 0 scan completed,
2 usage error, missing file or invalid config.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import yaml

from .analyze_package import Clues, UsageError, analyze, resolve
from .pkg import PkgError

# Longest first, so Foo.tar.gz is tar.gz, not gz.
EXTENSIONS = (
    (".tar.bz2", "tar.bz2"),
    (".tar.gz", "tar.gz"),
    (".tbz2", "tar.bz2"),
    (".tgz", "tar.gz"),
    (".tar", "tar"),
    (".pkg", "pkg"),
    (".dmg", "dmg"),
    (".zip", "zip"),
)
VERSION = re.compile(r"\d+\.\d+\.\d+|\d+\.\d+")
STRENGTH_ORDER = {"strong": 0, "moderate": 1, "weak": 2}


def extension(name: str) -> str:
    lower = name.lower()
    for suffix, kind in EXTENSIONS:
        if lower.endswith(suffix):
            return kind
    return ""


# ── Scan ──────────────────────────────────────────────────────────────────────


def scan(source: Path, depth: int | None = None) -> list[dict]:
    """Distributable files under ``source``, following symlinks (vendor shares
    are often assembled from them) but never looping. ``depth`` 1 is the top
    level only. The vendor hint is the folder two levels above the file, when
    that folder is inside ``source``."""
    found = []
    seen: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(source, followlinks=True):
        here = Path(dirpath)
        real = os.path.realpath(here)
        if real in seen:
            dirnames[:] = []
            continue
        seen.add(real)
        level = len(here.relative_to(source).parts) + 1  # depth of files here
        if depth is not None and level >= depth:
            dirnames[:] = []
        if depth is not None and level > depth:
            continue
        dirnames.sort()
        for name in sorted(filenames):
            path = here / name
            kind = extension(name)
            if not kind or not path.is_file():
                continue
            stat = path.stat()
            grandparent = path.parent.parent
            inside = grandparent != source and source in grandparent.parents
            found.append(
                {
                    "path": str(path),
                    "basename": name,
                    "extension": kind,
                    "size": stat.st_size,
                    "modified": int(stat.st_mtime),
                    "vendor_hint": grandparent.name if inside else "",
                }
            )
    return found


# ── Matching (pure; unit-tested) ──────────────────────────────────────────────


def norm(text: str) -> str:
    """Lowercase, letters and digits only: Orchard-Analytics ~ Orchard Analytics."""
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def candidates_for(target: dict, files: list[dict]) -> list[dict]:
    app, vendor = norm(target.get("app_name", "")), norm(target.get("vendor", ""))
    result = []
    for f in files:
        signals, strength = [], 0
        if app and app in norm(f["basename"]):
            signals.append("app_name_match")
            strength += 2
        if vendor and vendor == norm(f.get("vendor_hint", "")):
            signals.append("vendor_match")
            strength += 2
        # A version alone says nothing about WHICH target a file belongs to.
        if strength and VERSION.search(f["basename"]):
            signals.append("version_in_filename")
            strength += 1
        if strength >= 2:
            signals.append("archivable_file")
        if strength:
            level = (
                "strong" if strength >= 4 else "moderate" if strength >= 2 else "weak"
            )
            result.append(
                {
                    "path": f["path"],
                    "size": f["size"],
                    "match_signals": signals,
                    "match_strength": level,
                }
            )
    result.sort(key=lambda c: STRENGTH_ORDER[c["match_strength"]])
    return result


def match(targets: list[dict], files: list[dict]) -> tuple[list, list, dict]:
    """(matches per target, unmatched files, summary)."""
    matches, matched = [], set()
    for target in targets:
        cands = candidates_for(target, files)
        matched.update(c["path"] for c in cands)
        matches.append(
            {
                "target_app": target.get("app_name", ""),
                "target_vendor": target.get("vendor", ""),
                "pattern": target.get("pattern", 0),
                "candidates": cands,
                "candidate_count": len(cands),
            }
        )
    unmatched = [f for f in files if f["path"] not in matched]
    with_any = sum(1 for m in matches if m["candidate_count"])
    summary = {
        "total_targets": len(targets),
        "targets_with_candidates": with_any,
        "targets_without_candidates": len(targets) - with_any,
        "unmatched_source_files": len(unmatched),
    }
    return matches, unmatched, summary


def load_targets(path: Path) -> list[dict]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise UsageError(f"Invalid targets file {path}: {exc}") from exc
    recipes = data.get("recipes") if isinstance(data, dict) else None
    if not isinstance(recipes, list):
        raise UsageError(f"Invalid targets file {path}: no 'recipes:' list")
    return [r for r in recipes if isinstance(r, dict)]


# ── Output ────────────────────────────────────────────────────────────────────


def human_size(size: int) -> str:
    if size >= 1048576:
        return f"{size // 1048576} MB"
    if size >= 1024:
        return f"{size // 1024} KB"
    return f"{size} bytes"


def as_text(files, matches, unmatched, summary) -> list[str]:
    lines = ["=== Files found ===", f"  Total: {len(files)}"]
    for f in files:
        hint = f", vendor: {f['vendor_hint']}" if f["vendor_hint"] else ""
        what = ""
        if f.get("classification"):
            c = f["classification"]
            what = f"  [{c['origin']}, {c['confidence']}, pattern {c['pattern']}]"
        lines.append(f"  {f['basename']}  ({human_size(f['size'])}{hint}){what}")
    if matches:
        lines += ["", "=== Target matches ==="]
        for m in matches:
            n = m["candidate_count"]
            lines.append(
                f"  {m['target_vendor']}/{m['target_app']}"
                f" ({n} candidate{'' if n == 1 else 's'})"
            )
            for c in m["candidates"]:
                strength = c["match_strength"].upper()
                lines.append(f"    [{strength:8s}] {os.path.basename(c['path'])}")
        if unmatched:
            lines += ["", "=== Unmatched source files ==="]
            lines += [f"  {f['path']}" for f in unmatched]
        lines += [
            "",
            "=== Summary ===",
            f"  Targets with candidates:    {summary['targets_with_candidates']}"
            f" of {summary['total_targets']}",
            f"  Targets without candidates: {summary['targets_without_candidates']}",
            f"  Unmatched source files:     {summary['unmatched_source_files']}",
            "",
        ]
    return lines


# ── Front end ─────────────────────────────────────────────────────────────────


def parse_args(argv: list[str]) -> dict:
    opts: dict = {"source": "", "output": "text", "targets": "", "clues": ""}
    opts.update(customer="", depth=None)
    needs = {
        "--output": "text or json",
        "--targets": "a file path",
        "--clues": "a file path",
        "--customer": "a name",
        "--depth": "a number",
    }
    args = list(argv)
    while args:
        arg = args.pop(0)
        if arg in needs:
            if not args or not args[0] or args[0].startswith("-"):
                raise UsageError(f"{arg} requires {needs[arg]}")
            opts[arg[2:]] = args.pop(0)
        elif arg in ("-h", "--help"):
            opts["help"] = True
            return opts
        elif arg.startswith("-"):
            raise UsageError(f"Unknown option: {arg}")
        elif opts["source"]:
            raise UsageError(f"Unexpected argument: {arg}")
        else:
            opts["source"] = arg
    if opts["output"] not in ("text", "json"):
        raise UsageError("--output must be text or json")
    if opts["depth"] is not None:
        if not str(opts["depth"]).isdigit() or int(opts["depth"]) < 1:
            raise UsageError("--depth must be a whole number, 1 or more")
        opts["depth"] = int(opts["depth"])
    if not opts["source"]:
        raise UsageError("No source directory specified.")
    if not Path(opts["source"]).is_dir():
        raise UsageError(f"Not a directory: {opts['source']}")
    if opts["targets"] and not Path(opts["targets"]).is_file():
        raise UsageError(f"Targets file not found: {opts['targets']}")
    return opts


def info(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def classify_packages(files: list[dict], clues: Clues, domain: str) -> None:
    """FR-4: each .pkg found, classified as analyze-package would."""
    for f in files:
        f["classifiable"] = f["extension"] == "pkg" and bool(clues.source)
        if not f["classifiable"]:
            continue
        try:
            c = analyze(Path(f["path"]), clues, domain)
        except PkgError as exc:
            f["classification"] = {"error": str(exc)}
            continue
        f["classification"] = {
            "origin": c.origin,
            "confidence": c.confidence,
            "pattern": c.pattern,
        }


def main(argv: list[str] | None = None) -> int:
    try:
        opts = parse_args(sys.argv[1:] if argv is None else argv)
        if opts.get("help"):
            print(__doc__)
            return 0
        clues, domain, customer = resolve(opts, warn=False)
        targets_path = Path(opts["targets"]) if opts["targets"] else None
        if targets_path is None and customer is not None:
            candidate = customer.root / "end_result.yaml"
            targets_path = candidate if candidate.is_file() else None
        targets = load_targets(targets_path) if targets_path else None
    except UsageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    source = Path(os.path.realpath(opts["source"]))
    info(f"=== Scanning {source} ===")
    info(f"  Depth:        {opts['depth'] or 'unlimited'}")
    files = scan(source, opts["depth"])
    info(f"  Files found:  {len(files)}")
    classify_packages(files, clues, domain)

    matches, unmatched, summary = match(targets, files) if targets else ([], [], {})
    if opts["output"] == "json":
        output: dict = {
            "source_dir": str(source),
            "files_found": len(files),
            "files": files,
        }
        if targets:
            output["target_matches"] = matches
            output["summary"] = summary
            output["unmatched"] = summary["unmatched_source_files"]
            output["unmatched_files"] = [f["path"] for f in unmatched]
        print(json.dumps(output, indent=2))
    else:
        print("\n".join(as_text(files, matches, unmatched, summary)))

    info("=== Done ===")
    info(f"  Scanned {len(files)} distributable files in {source}")
    if targets_path:
        info(f"  (matching against {targets_path})")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    sys.exit(main())
