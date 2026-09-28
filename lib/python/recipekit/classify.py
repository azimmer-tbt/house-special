# classify.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Classify a recipe pair by its pattern (docs/patterns.md) and compare the claim.

Usage:
  tk_python -m recipekit.classify [--output text|json] [--interactive] <recipe-dir>

Spec: specs/analysis/classify-recipe/01-classify-recipe.md. Every fact comes from
the recipe model; the classifier parses nothing itself. The recipe's `Comment:`
claim is compared, never used to decide.

Exit codes: 0 classified, 1 no recipe pair in the folder, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .model import Pair, RecipeSet

CLAIM_RE = re.compile(r"^\s*Pattern\s+(\d[a-e]?)\b")
REDIRECT_RE = re.compile(r"fwlink|go\.microsoft\.com|/latest\b", re.IGNORECASE)


@dataclass
class Result:
    """A classification: the label, whether it's certain, and why."""

    label: str
    reasons: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    question: str = ""

    @property
    def uncertain(self) -> bool:
        return bool(self.alternatives)


def classify(pair: Pair) -> Result:
    """Apply the FR-2 decision table to one pair's facts."""
    f = pair.facts()
    source = f["source"]["value"]
    output = f["output"]["value"]
    artifact = f["artifact"]["value"]
    signature = f["signature"]["value"]
    adds = f["scripts"]["value"] != "none" or bool(f["extras"])
    why = [
        f"source is {source}",
        f"artifact is {artifact}",
        f"output processor is {output}",
    ]

    if output == "AppPkgCreator":
        return Result("!", why + ["AppPkgCreator is forbidden (Standards §6.7)"])

    if source == "sparkle":
        return Result("1a" if output == "PkgCopier" else "1b", why)

    if source == "github_release":
        if output == "PkgCopier":
            return Result("2a", why + ["the vendor's .pkg is copied as-is"])
        if adds:
            return Result("2c", why + [_adds_reason(f)])
        return Result("2b", why + ["the app is rebuilt with nothing added"])

    if source == "github_archive":
        return Result("2d", why + ["a source archive is unpacked and reassembled"])

    if source == "url_stable":
        if output == "PkgCopier":
            url = f["source"].get("url", "")
            inside = _version_from_inside(pair)
            if REDIRECT_RE.search(url) or inside:
                cue = (
                    "redirect URL"
                    if REDIRECT_RE.search(url)
                    else "version read from inside the pkg"
                )
                return Result(
                    "5", why + [f"a signed vendor .pkg at a stable link ({cue})"]
                )
            return Result("3a", why + ["a vendor .pkg at a stable link, copied as-is"])
        return Result("3b", why + ["a stable link to a DMG or app, rebuilt"])

    if source == "url_scraped":
        if output == "PkgCopier":
            return Result(
                "3a",
                why + ["the link is scraped from a page, but the .pkg is copied as-is"],
                ["3c"],
                "Is the scraped file a .pkg copied as-is (3a) or an app rebuilt (3c)?",
            )
        return Result(
            "3c", why + ["the versioned link is scraped from the download page"]
        )

    in_house = signature == "declared_unsigned"
    if source == "none" and in_house and output == "PkgCreator":
        letter, reason = _pattern_6_letter(f)
        return Result(f"6{letter}", why + ["in-house, nothing downloaded", reason])
    if source in ("vendor_cache", "recipe_dir"):
        if output == "PkgCopier":
            return Result("4a", why + ["a vendor-drop .pkg copied as-is"])
        if output == "Copier":
            return Result("4b", why + ["a vendor-drop distribution .pkg copied as-is"])
        if artifact == "dmg":
            if in_house:
                return Result(
                    "7",
                    why + ["an unsigned DMG wrapping an app: a faux vendor DMG"],
                    ["4c"],
                    "Did the vendor ship this DMG unsigned (4c), "
                    "or did the org build it (7)?",
                )
            if adds:
                return Result("4d", why + [_adds_reason(f)])
            return Result("4c", why + ["a vendor DMG, app extracted and rebuilt"])
        if in_house or source == "recipe_dir":
            letter, reason = _pattern_6_letter(f)
            return Result(f"6{letter}", why + ["in-house content, rebuilt", reason])
        if artifact in ("zip", "tar"):
            return Result("4e", why + ["a signed vendor archive, reassembled"])

    if artifact == "app" and signature == "declared_unsigned":
        return Result(
            "8",
            why + ["an unsigned app with no signed build"],
            ["6a"],
            "Is this an experimental app awaiting a signed build (8)?",
        )

    return Result("?", why + ["no row of the decision table matches"])


def _adds_reason(f: dict) -> str:
    parts = []
    if f["scripts"]["value"] != "none":
        parts.append("install scripts")
    if f["extras"]:
        parts.append(f"{len(f['extras'])} org file(s)")
    return "the org adds " + " and ".join(parts)


def _version_from_inside(pair: Pair) -> bool:
    """Pattern 5 reads the version from inside the pkg after unpacking it."""
    names = [s.processor for s in pair.steps()]
    unpack = any(p in ("FlatPkgUnpacker", "PkgPayloadUnpacker") for p in names)
    return unpack and "Versioner" in names


def _pattern_6_letter(f: dict) -> tuple[str, str]:
    """6d, then 6b, then 6c, then 6a (docs/patterns.md)."""
    payload = f["payload_paths"]
    if f["payload_complete"] and not payload:
        return "d", "the package installs no files (payloadless)"
    if f["scripts"]["value"] != "none":
        return "b", "payload plus install scripts"
    moded = [c["path"] for c in f["chown"] if c.get("mode") and not c["shared_folder"]]
    if len(moded) == 1:
        target = moded[0]
        others = [p for p in payload if p != target and not target.startswith(p + "/")]
        if not others:
            return "c", f"one file with a specific owner and mode ({target})"
    return "a", "a flat payload, no scripts"


def claimed(pair: Pair) -> str | None:
    """The pattern the recipes claim in `Comment:` (download first)."""
    for recipe in (pair.download, pair.pkg):
        comment = str((recipe.data.get("Comment") if recipe else "") or "")
        m = CLAIM_RE.match(comment)
        if m:
            return m.group(1)
    return None


def report(pair: Pair) -> dict:
    result = classify(pair)
    f = pair.facts()
    claim = claimed(pair)
    return {
        "recipe": f"{pair.folder.parent.name}/{pair.folder.name}",
        "classification": result.label,
        "uncertain": result.uncertain,
        "alternatives": result.alternatives,
        "question": result.question,
        "claimed": claim,
        "matches_claim": None if claim is None else claim == result.label,
        "reasons": result.reasons,
        "prefix_expected": f["output"]["value"] in ("PkgCreator", "AppPkgCreator"),
        "facts": {
            k: f[k]["value"]
            for k in ("source", "artifact", "signature", "output", "version_source")
        }
        | {"scripts": f["scripts"].get("scripts"), "extras": f["extras"]},
    }


def as_text(r: dict) -> str:
    lines = [f"Recipe: {r['recipe']}", "", "Facts:"]
    for key, value in r["facts"].items():
        lines.append(f"  {key + ':':16} {value}")
    lines.append("")
    label = f"Classification: Pattern {r['classification']}"
    if r["uncertain"]:
        label += f"  (uncertain: also {', '.join(r['alternatives'])})"
    lines.append(label)
    if r["claimed"] is None:
        lines.append("Claimed: none")
    else:
        lines.append(f"Claimed: Pattern {r['claimed']}")
        lines.append(f"Matches claim: {'yes' if r['matches_claim'] else 'no'}")
    lines += ["", "Reasoning:"] + [f"  - {why}" for why in r["reasons"]]
    if r["question"]:
        lines += ["", f"To settle it: {r['question']}"]
    naming = (
        "the org prefix (ORG_PKGNAME_PREFIX) is expected (PkgCreator builds it)"
        if r["prefix_expected"]
        else "no org prefix: the vendor's package keeps its name"
    )
    lines += ["", f"Output naming: {naming}"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="classify-recipe",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("recipe_dir", type=Path)
    parser.add_argument("--output", choices=("text", "json"), default="text")
    parser.add_argument("-i", "--interactive", action="store_true")
    parser.add_argument("-n", "--dry-run", action="store_true")
    parser.add_argument("--org", type=Path, help="accepted for compatibility")
    args = parser.parse_args(argv)

    if not args.recipe_dir.is_dir():
        print(f"ERROR: not a directory: {args.recipe_dir}", file=sys.stderr)
        return 1
    pairs = [p for p in RecipeSet.load(args.recipe_dir).pairs() if p.download and p.pkg]
    if not pairs:
        print(
            f"ERROR: no download/pkg recipe pair in {args.recipe_dir}", file=sys.stderr
        )
        return 1

    reports = [report(p) for p in pairs]
    if args.output == "json":
        print(json.dumps(reports[0] if len(reports) == 1 else reports, indent=2))
        return 0
    if args.dry_run:
        print("DRY RUN — read-only analysis; no files are written.\n")
    for r in reports:
        print(as_text(r))
        if args.interactive and r["uncertain"] and sys.stdin.isatty():
            options = [r["classification"]] + r["alternatives"]
            answer = input(f"\n{r['question']} [{'/'.join(options)}] ").strip()
            if answer in options:
                print(f"Operator chose: Pattern {answer}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
