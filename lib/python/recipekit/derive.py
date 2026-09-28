# derive.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Derived facts about a recipe pair, each with its evidence (spec FR-08).

Facts, not verdicts: whether a fact is acceptable is the linter's business, and
which pattern the facts add up to is the classifier's. Nothing here reads
`Comment:`, `Description:` or a README to decide anything (AIP-02); the comment is
reported raw as `claimed`, for consumers to check against the facts.
"""

from __future__ import annotations

import re
from pathlib import Path

from .model import Pair, Step

ARTIFACT_SUFFIXES = (
    (".tar.gz", "tar"),
    (".tgz", "tar"),
    (".tar.bz2", "tar"),
    (".tar", "tar"),
    (".mpkg", "pkg"),
    (".pkg", "pkg"),
    (".dmg", "dmg"),
    (".zip", "zip"),
    (".app", "app"),
)

# Bundles that are the vendor's product rather than something the org adds.
PRODUCT_BUNDLE = (
    r"\.(app|saver|prefPane|plugin|bundle|kext|qlgenerator|mdimporter|component)"
)

# Folders macOS ships; a package records their stock owner, never takes them over
# (docs/package-ownership.md).
SHARED_FOLDERS = frozenset(
    {
        "Applications",
        "Library",
        "Library/Application Support",
        "Library/LaunchAgents",
        "Library/LaunchDaemons",
        "Library/Preferences",
        "Library/PrivilegedHelperTools",
        "Library/Screen Savers",
        "Library/Desktop Pictures",
        "Users",
        "Users/Shared",
        "usr",
        "usr/local",
        "usr/local/bin",
        "opt",
        "private",
        "private/etc",
        "etc",
    }
)


def facts(pair: Pair) -> dict:
    """Every FR-08 fact for one pair."""
    steps = pair.steps()
    download_steps = (
        [s for s in steps if s.recipe is pair.download] if pair.download else []
    )
    return {
        "identity": _identity(pair),
        "claimed": {r.path.name: r.data.get("Comment") for r in pair.chain()},
        "source": _source(pair, download_steps),
        "artifact": _artifact(pair, steps),
        "signature": _signature(pair, steps),
        "output": _output(pair, steps),
        "pkgname": _pkgname(pair, steps),
        "version_source": _version_source(pair, steps),
        **_payload(pair, steps),
    }


# ── identity ───────────────────────────────────────────────────────────────────
def _identity(pair: Pair) -> list[dict]:
    return [
        {
            "file": r.path.name,
            "Identifier": r.identifier,
            "ParentRecipe": r.parent or None,
            "MinimumVersion": r.data.get("MinimumVersion"),
            "format": r.format,
        }
        for r in pair.chain()
    ]


# ── source ─────────────────────────────────────────────────────────────────────
def _source(pair: Pair, steps: list[Step]) -> dict:
    for step in steps:
        p = step.processor
        if p == "SparkleUpdateInfoProvider":
            return {"value": "sparkle", "evidence": step.evidence()}
        if p == "GitHubReleasesInfoProvider":
            return {"value": "github_release", "evidence": step.evidence("github_repo")}
        if p == "URLTextSearcher":
            return {"value": "url_scraped", "evidence": step.evidence("re_pattern")}
        if p == "URLDownloader":
            url = pair.resolve(str(step.args.get("url", "")), before=_index(pair, step))
            if url.startswith("file://"):
                return {
                    "value": "vendor_cache",
                    "evidence": step.evidence("url"),
                    "url": url,
                }
            if re.search(r"github\.com/[^/]+/[^/]+/archive/", url):
                return {
                    "value": "github_archive",
                    "evidence": step.evidence("url"),
                    "url": url,
                }
            if url.startswith(("http://", "https://")):
                return {
                    "value": "url_stable",
                    "evidence": step.evidence("url"),
                    "url": url,
                }
        if p == "Copier":
            src = str(step.args.get("source_path", ""))
            if src.startswith("%RECIPE_DIR%"):
                return {"value": "recipe_dir", "evidence": step.evidence("source_path")}
            if re.search(r"%LOCAL_[A-Z_]*PATH%", src) or "vendor_cache" in pair.resolve(
                src
            ):
                return {
                    "value": "vendor_cache",
                    "evidence": step.evidence("source_path"),
                }
    return {"value": "none", "evidence": None}


# ── artifact ───────────────────────────────────────────────────────────────────
def _kind(name: str) -> str | None:
    lower = name.lower().rstrip("$/")
    for suffix, kind in ARTIFACT_SUFFIXES:
        if lower.endswith(suffix) or lower.endswith(suffix.replace(".", "\\.")):
            return kind
    return None


def _artifact(pair: Pair, steps: list[Step]) -> dict:
    for step in steps:
        if step.processor != "URLDownloader":
            continue
        before = _index(pair, step)
        for arg in ("filename", "url"):
            value = pair.resolve(str(step.args.get(arg, "")), before=before)
            kind = _kind(value)
            if kind:
                return {"value": kind, "evidence": step.evidence(arg)}
    for step in steps:
        # A vendor drop staged with Copier: the file it picks up is the artifact.
        src = (
            str(step.args.get("source_path", "")) if step.processor == "Copier" else ""
        )
        if re.search(r"%LOCAL_[A-Z_]*PATH%", src) or "vendor_cache" in src:
            kind = _kind(pair.resolve(src)) or (
                "files" if "_DIR_PATH%" in src else None
            )
            if kind:
                return {"value": kind, "evidence": step.evidence("source_path")}
    for step in steps:
        if step.processor == "GitHubReleasesInfoProvider":
            kind = _kind(pair.resolve(str(step.args.get("asset_regex", ""))))
            if kind:
                return {"value": kind, "evidence": step.evidence("asset_regex")}
    for step in steps:
        if step.processor in ("DmgMounter",):
            return {"value": "dmg", "evidence": step.evidence()}
        # AutoPkg mounts a DMG named in a path: `…/downloads/App.dmg/App.app`.
        if step.processor in ("Copier", "CodeSignatureVerifier", "Versioner"):
            for arg in ("source_path", "input_path", "input_plist_path"):
                if ".dmg/" in pair.resolve(str(step.args.get(arg, ""))):
                    return {"value": "dmg", "evidence": step.evidence(arg)}
        if step.processor == "Unarchiver":
            return {"value": "zip", "evidence": step.evidence()}
        if step.processor == "Copier" and str(
            step.args.get("source_path", "")
        ).startswith("%RECIPE_DIR%"):
            return {"value": "files", "evidence": step.evidence("source_path")}
    return {"value": "unknown", "evidence": None}


# ── signature ──────────────────────────────────────────────────────────────────
def _signature(pair: Pair, steps: list[Step]) -> dict:
    inputs = pair.inputs()
    no_team = str(inputs.get("teamid", "")) == "UNSIGNED_NO_TEAMID"
    for step in steps:
        if step.processor != "CodeSignatureVerifier":
            continue
        if "expected_authority_names" in step.args:
            names = [str(n) for n in step.args.get("expected_authority_names") or []]
            names = [pair.resolve(n) for n in names]
            chain = all(
                any(want in n for n in names)
                for want in ("Developer ID Certification Authority", "Apple Root CA")
            )
            return {
                "value": "authority_names",
                "chain_listed": chain,
                "declared_no_team": no_team,
                "evidence": step.evidence("expected_authority_names"),
            }
        if "requirement" in step.args:
            req = pair.resolve(str(step.args["requirement"]))
            pins = "subject.OU" in req
            value = "requirement" if pins or "certificate" in req else "identifier_only"
            return {
                "value": value,
                "pins_team_id": pins,
                "declared_no_team": no_team,
                "evidence": step.evidence("requirement"),
            }
        return {
            "value": "missing",
            "declared_no_team": no_team,
            "evidence": step.evidence(),
        }
    declared = inputs.get("NO_CODE_SIGNATURE_REQUIRED") in (
        True,
        "true",
        "True",
        "yes",
        1,
    )
    return {
        "value": "declared_unsigned" if declared else "missing",
        "declared_no_team": no_team,
        "evidence": None,
    }


# ── output ─────────────────────────────────────────────────────────────────────
def _output(pair: Pair, steps: list[Step]) -> dict:
    found = {"value": "none", "evidence": None}
    for step in steps:
        p = step.processor
        if p in ("PkgCreator", "PkgCopier", "AppPkgCreator"):
            found = {"value": p, "evidence": step.evidence()}
        elif p == "Copier" and pair.resolve(
            str(step.args.get("destination_path", ""))
        ).endswith(".pkg"):
            found = {"value": "Copier", "evidence": step.evidence("destination_path")}
    return found


def _pkgname(pair: Pair, steps: list[Step]) -> dict | None:
    for step in reversed(steps):
        request = (
            step.args.get("pkg_request") if step.processor == "PkgCreator" else None
        )
        if isinstance(request, dict) and "pkgname" in request:
            return {
                "value": pair.resolve(
                    str(request["pkgname"]), before=_index(pair, step)
                ),
                "evidence": step.evidence("pkg_request.pkgname"),
            }
    return None


# ── version ────────────────────────────────────────────────────────────────────
def _version_source(pair: Pair, steps: list[Step]) -> dict:
    from . import catalogue

    for step in steps:
        outs = catalogue.outputs(step.processor, step.args, pair.resolve_inputs)
        if outs and "version" in outs:
            return {
                "value": "processor",
                "processor": step.processor,
                "evidence": step.evidence(),
            }
    for recipe in reversed(pair.chain()):
        if "version" in recipe.inputs:
            return {
                "value": "input",
                "pinned": str(recipe.inputs["version"]),
                "evidence": {"recipe": recipe.path.name, "input": "version"},
            }
    if "version" in pair.overrides:
        return {"value": "harness_only", "evidence": {"file": ".overrides"}}
    return {"value": "none", "evidence": None}


# ── payload ────────────────────────────────────────────────────────────────────
def _payload(pair: Pair, steps: list[Step]) -> dict:
    creator = next(
        (
            s
            for s in reversed(steps)
            if s.processor == "PkgCreator"
            and isinstance(s.args.get("pkg_request"), dict)
        ),
        None,
    )
    empty = {
        "payload_paths": [],
        "payload_complete": True,
        "installs_app": False,
        "scripts": {"value": "none"},
        "extras": [],
        "chown": [],
        "pkgroot_parents": [],
    }
    if creator is None:
        return empty
    request = creator.args["pkg_request"]
    root = pair.resolve(str(request.get("pkgroot", ""))).rstrip("/")
    paths: set[str] = set()
    complete = True

    for step in steps:
        if step.processor == "Unarchiver":
            dest = pair.resolve(str(step.args.get("destination_path", ""))).rstrip("/")
            if root and (dest == root or dest.startswith(root + "/")):
                complete = False  # unpacked at build time: contents unknown statically
            continue
        if step.processor != "Copier":
            continue
        dest = pair.resolve(str(step.args.get("destination_path", ""))).rstrip("/")
        if root and (dest == root or dest.startswith(root + "/")):
            rel = dest[len(root) :].lstrip("/")
            local = _local_dir(pair, str(step.args.get("source_path", "")))
            if local is not None:
                paths.update(_join(rel, p) for p in _walk(local))
            elif rel:
                paths.add(rel)
            else:
                complete = False  # a whole folder from the cache: contents unknown

    chown = request.get("chown") or []
    parents = []
    for entry in chown if isinstance(chown, list) else []:
        if not isinstance(entry, dict) or "path" not in entry:
            continue
        path = str(entry["path"]).strip("/")
        parents.append(
            {
                "path": path,
                "user": entry.get("user"),
                "group": entry.get("group"),
                "mode": entry.get("mode"),
                "shared_folder": path in SHARED_FOLDERS,
            }
        )
        if path not in SHARED_FOLDERS:
            paths.add(path)

    ordered = sorted(paths)
    apps = [p for p in ordered if re.search(r"\.app$", p)]
    extras = [
        p
        for p in ordered
        if p not in SHARED_FOLDERS
        and not re.search(PRODUCT_BUNDLE + r"(/|$)", p)
        and not any(q.startswith(p + "/") for q in ordered)
    ]
    return {
        "payload_paths": ordered,
        "payload_complete": complete,
        "installs_app": bool(apps),
        "scripts": _scripts(pair, creator, request),
        "extras": extras,
        "chown": parents,
        "pkgroot_parents": [p for p in parents if p["shared_folder"]],
    }


def _scripts(pair: Pair, creator: Step, request: dict) -> dict:
    if "scripts" not in request:
        return {"value": "none"}
    raw = str(request["scripts"])
    local = _local_dir(pair, raw)
    if local is None:
        found = None  # outside the recipe folder (e.g. the cache): contents unknown
    else:
        found = sorted(
            n for n in ("preinstall", "postinstall") if (local / n).is_file()
        )
    return {
        "value": "present",
        "directory": raw,
        "scripts": found,
        "evidence": creator.evidence("pkg_request.scripts"),
    }


def _local_dir(pair: Pair, source: str) -> Path | None:
    """The folder a `%RECIPE_DIR%/…` source refers to, if it exists on disk."""
    if not source.startswith("%RECIPE_DIR%"):
        return None
    for recipe in pair.chain():
        candidate = recipe.path.parent / source[len("%RECIPE_DIR%") :].lstrip("/")
        if candidate.is_dir():
            return candidate
    return None


def _walk(folder: Path) -> list[str]:
    return sorted(
        str(p.relative_to(folder))
        for p in folder.rglob("*")
        if p.is_file() and p.name != ".DS_Store"
    )


def _join(prefix: str, rel: str) -> str:
    return f"{prefix}/{rel}" if prefix else rel


def _index(pair: Pair, step: Step) -> int:
    return pair.steps().index(step)
