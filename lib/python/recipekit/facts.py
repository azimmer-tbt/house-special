# facts.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Print the facts and findings for recipe folders (spec FR-10).

Usage:
  tk_python -m recipekit.facts <recipe-dir> [<recipe-dir> ...]
  tk_python -m recipekit.facts --repo <recipe-repo>
  options: --view autopkg|harness   --output text|json   --audit

--audit reads plist recipes without flagging them (reviewing a community repo).
Exit codes: 0 no error findings, 1 any error finding, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .model import RecipeSet


def build(recipes: RecipeSet, view: str) -> dict:
    pairs = []
    for pair in recipes.pairs():
        entry = {
            "folder": str(pair.folder),
            "stem": pair.stem,
            "facts": pair.facts(),
        }
        if view == "harness":
            entry["inputs"] = {k: str(v) for k, v in pair.inputs("harness").items()}
        pairs.append(entry)
    findings = [f.as_dict() for f in recipes.all_findings()]
    return {"view": view, "pairs": pairs, "findings": findings}


def as_text(report: dict) -> str:
    lines = []
    for entry in report["pairs"]:
        f = entry["facts"]
        lines.append(f"=== {Path(entry['folder']).name}/{entry['stem']}")
        for key in ("source", "artifact", "signature", "output", "version_source"):
            lines.append(f"  {key:15} {f[key]['value']}")
        if f.get("pkgname"):
            lines.append(f"  {'pkgname':15} {f['pkgname']['value']}")
        lines.append(f"  {'installs_app':15} {f['installs_app']}")
        if f["extras"]:
            lines.append(f"  {'extras':15} " + ", ".join(f["extras"]))
        scripts = f["scripts"]
        if scripts["value"] != "none":
            lines.append(f"  {'scripts':15} {scripts.get('scripts')}")
    if report["findings"]:
        lines.append("")
        for item in report["findings"]:
            where = item["file"] + (f":{item['line']}" if "line" in item else "")
            lines.append(
                f"{item['severity'].upper():7} {item['code']}: {where}: "
                f"{item['message']}"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="recipekit.facts",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("folders", nargs="*", type=Path, help="recipe folders")
    parser.add_argument(
        "--repo", type=Path, help="a recipe repo: every folder under recipes/"
    )
    parser.add_argument("--view", choices=("autopkg", "harness"), default="autopkg")
    parser.add_argument("--output", choices=("text", "json"), default="text")
    parser.add_argument("--audit", action="store_true", help="plist recipes expected")
    args = parser.parse_args(argv)

    if bool(args.repo) == bool(args.folders):
        parser.error("give recipe folders or --repo, not both and not neither")
    missing = [
        p for p in ([args.repo] if args.repo else args.folders) if not p.is_dir()
    ]
    if missing:
        parser.error(f"not a directory: {missing[0]}")

    if args.repo:
        recipes = RecipeSet.load_repo(args.repo, audit=args.audit)
    else:
        recipes = RecipeSet.load(*args.folders, audit=args.audit)
    report = build(recipes, args.view)

    if args.output == "json":
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        print(as_text(report))
    return 1 if any(f["severity"] == "error" for f in report["findings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
