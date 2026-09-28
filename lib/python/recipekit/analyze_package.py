# analyze_package.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Classify a .pkg as vendor-originated or custom-built and suggest a pattern.

The front end is bin/analyze-package.sh; its header is the usage text. Spec:
specs/analysis/analyze-package/01-analyze-package.md. Hints come from a
clues.yaml (docs/FORMATS.md §2): --clues <file>, or the customer's folder with
--customer <name>. Exit codes: 0 classified (high or medium confidence), 1 low
confidence, 2 usage error, missing file, invalid config or extraction failure.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .customers import Customer, CustomerError, load_registry
from .org import read_org_config
from .pkg import PkgError, expand, package_info, signature, team_id

# A lowercase TLD-like first segment and at least two more segments, any case
# (com.acmefruit.pkg.Moonlight, io.corkscrews.Fruit, si.biolab.orange).
REVERSE_DOMAIN = re.compile(r"^[a-z]{2,}(\.[A-Za-z0-9_-]+){2,}$")


class UsageError(Exception):
    pass


# ── Facts about the package ───────────────────────────────────────────────────


@dataclass
class Facts:
    path: Path
    size: int = 0
    kind: str = "component"
    identifiers: list[str] = field(default_factory=list)  # one per component
    version: str = ""
    install_location: str = ""
    signature: str = "unsigned"
    authority: str = ""
    files: int = 0
    dirs: int = 0
    symlinks: int = 0
    apps: list[str] = field(default_factory=list)
    payload_paths: list[str] = field(default_factory=list)  # absolute on install
    size_human: str = ""
    size_mb: int = 0
    scripts: list[str] = field(default_factory=list)

    @property
    def identifier(self) -> str:
        return self.identifiers[0] if self.identifiers else ""

    @property
    def team_id(self) -> str:
        return team_id(self.authority)


def gather(pkg: Path, work: Path) -> Facts:
    """Expand ``pkg`` under ``work`` and read what the classifier needs."""
    facts = Facts(pkg, size=pkg.stat().st_size)
    expanded = expand(pkg, work / "expanded")
    facts.kind = expanded.kind
    for index, comp in enumerate(expanded.components):
        info = package_info(comp)
        if info["identifier"]:
            facts.identifiers.append(info["identifier"])
        if index == 0:
            facts.version = info["version"]
            facts.install_location = info["install_location"]
        _payload(facts, comp / "Payload", info["install_location"])
        facts.scripts += _scripts(comp / "Scripts")
    if expanded.kind == "distribution":
        facts.scripts += _scripts(expanded.root / "Scripts")
    facts.signature, facts.authority = signature(pkg)
    return facts


def _payload(facts: Facts, payload: Path, install_location: str) -> None:
    if not payload.is_dir():
        return
    base = install_location or "/"
    for dirpath, dirnames, filenames in os.walk(payload):
        here = Path(dirpath)
        depth = len(here.relative_to(payload).parts)
        facts.dirs += 1
        for name in sorted(dirnames):
            path = here / name
            rel = path.relative_to(payload)
            facts.payload_paths.append(os.path.join(base, str(rel)))
            if path.is_symlink():
                facts.symlinks += 1
            elif name.endswith(".app") and depth < 10:
                facts.apps.append(name)
        for name in filenames:
            path = here / name
            facts.payload_paths.append(
                os.path.join(base, str(path.relative_to(payload)))
            )
            if path.is_symlink():
                facts.symlinks += 1
            else:
                facts.files += 1
    human, mb = _du(payload)
    facts.size_human = facts.size_human or human
    facts.size_mb += mb


def _du(path: Path) -> tuple[str, int]:
    def run(flag: str) -> str:
        done = subprocess.run(
            ["du", flag, str(path)], capture_output=True, text=True, check=False
        )
        return done.stdout.split("\t")[0].strip() if done.returncode == 0 else ""

    mb = run("-sm")
    return run("-sh"), int(mb) if mb.isdigit() else 0


def _scripts(folder: Path) -> list[str]:
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.rglob("*") if p.is_file())


# ── Clues ─────────────────────────────────────────────────────────────────────


@dataclass
class Clues:
    source: str = ""
    vendor_identifiers: list[str] = field(default_factory=list)
    vendor_team_ids: list[str] = field(default_factory=list)
    vendor_filename_patterns: list[str] = field(default_factory=list)
    filename_contains_org_code: bool = False
    org_codes: list[str] = field(default_factory=list)
    unusual_install_locations: list[str] = field(default_factory=list)
    non_reverse_domain_pattern: str = ""


def load_clues(path: Path) -> Clues:
    """Read a clues.yaml (FORMATS §2); UsageError when it isn't valid."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise UsageError(f"Invalid clues file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise UsageError(f"Invalid clues file {path}: expected a mapping")
    signals = data.get("custom_build_signals") or {}
    patterns = []
    for item in data.get("vendor_filename_patterns") or []:
        pattern = item.get("pattern", "") if isinstance(item, dict) else item
        if pattern:
            patterns.append(str(pattern))
    clues = Clues(
        source=str(path),
        vendor_identifiers=_strings(data.get("vendor_identifiers")),
        vendor_team_ids=_strings(data.get("vendor_team_ids")),
        vendor_filename_patterns=patterns,
        filename_contains_org_code=bool(signals.get("filename_contains_org_code")),
        org_codes=_strings(signals.get("org_codes")),
        unusual_install_locations=[
            loc.rstrip("/") or "/"
            for loc in _strings(signals.get("unusual_install_locations"))
        ],
        non_reverse_domain_pattern=str(signals.get("non_reverse_domain_pattern") or ""),
    )
    for pattern in (
        clues.vendor_identifiers
        + clues.vendor_filename_patterns
        + clues.org_codes
        + (
            [clues.non_reverse_domain_pattern]
            if clues.non_reverse_domain_pattern
            else []
        )
    ):
        try:
            re.compile(pattern)
        except re.error as exc:
            raise UsageError(f"Invalid regex in {path}: {pattern!r}: {exc}") from exc
    return clues


def _strings(value) -> list[str]:
    return [str(v) for v in value] if isinstance(value, list) else []


# ── Classification (pure; unit-tested) ────────────────────────────────────────


@dataclass
class Classification:
    origin: str
    confidence: str
    pattern: int | str
    rationale: list[str]
    vendor_strong: int = 0
    vendor_medium: int = 0
    custom_strong: int = 0
    custom_medium: int = 0
    custom_low: int = 0


def classify(facts: Facts, clues: Clues, org_domain: str = "") -> Classification:
    """Weigh the signals (spec FR-4) and pick origin, confidence and pattern."""
    c = Classification("", "", "other", [])
    why = c.rationale
    ident = facts.identifier
    stem = facts.path.name[:-4] if facts.path.name.endswith(".pkg") else facts.path.name

    # 1. Reverse-domain identifier; the org's own namespace means in-house.
    if org_domain and (ident == org_domain or ident.startswith(org_domain + ".")):
        c.custom_strong += 1
        why.append(
            f"Identifier '{ident}' is in the org's own namespace ({org_domain})"
            " — built in-house"
        )
    elif REVERSE_DOMAIN.match(ident):
        c.vendor_strong += 1
        why.append(
            f"Identifier '{ident}' matches reverse-domain pattern (tld.org.name)"
        )
    else:
        c.custom_strong += 1
        why.append(
            f"Identifier '{ident}' is NOT reverse-domain — suggests custom build"
        )

    # 2. A known vendor identifier (any component's).
    if any(
        re.search(p, i) for p in clues.vendor_identifiers for i in facts.identifiers
    ):
        c.vendor_strong += 1
        why.append("Identifier matches known vendor identifier pattern")

    # 2b. The org code in the identifier; the org's legacy identifier shape.
    if any(re.search(code, ident, re.IGNORECASE) for code in clues.org_codes):
        c.custom_medium += 1
        why.append("Identifier contains an org code")
    if (
        clues.non_reverse_domain_pattern
        and ident
        and re.search(clues.non_reverse_domain_pattern, ident)
    ):
        c.custom_medium += 1
        why.append("Identifier matches the org's legacy in-house identifier pattern")

    # 3. Signature, and a signing team the clues know.
    if facts.signature == "signed":
        c.vendor_strong += 1
        by = f" by '{facts.authority}'" if facts.authority else ""
        why.append(f"Package is signed{by}")
        if facts.team_id and facts.team_id in clues.vendor_team_ids:
            c.vendor_strong += 1
            why.append(f"Signing team ID {facts.team_id} is a known vendor's")
    else:
        c.custom_medium += 1
        why.append("Package is unsigned — cannot confirm vendor by cert")

    # 4. Vendor filename; 5. org code in the filename.
    if any(re.search(p, stem) for p in clues.vendor_filename_patterns):
        c.vendor_medium += 1
        why.append("Filename matches vendor naming pattern")
    if clues.filename_contains_org_code and any(
        re.search(code, stem, re.IGNORECASE) for code in clues.org_codes
    ):
        c.custom_medium += 1
        why.append("Filename contains org code")

    # 6. An unusual destination: the install location, or anything in the payload.
    unusual = _unusual(facts, clues.unusual_install_locations)
    if unusual:
        c.custom_medium += 1
        why.append(unusual)

    # 7. .app bundles; 8. scripts.
    if facts.apps:
        c.vendor_medium += 1
        why.append(f"Payload contains .app bundles: {','.join(facts.apps)}")
    else:
        c.custom_medium += 1
        why.append("No .app bundles found in payload")
    if facts.scripts:
        c.custom_low += 1
        why.append(f"Contains installer scripts ({','.join(facts.scripts)})")

    _decide(c)
    return c


def _unusual(facts: Facts, locations: list[str]) -> str:
    def under(path: str, loc: str) -> bool:
        return path == loc or path.startswith(loc.rstrip("/") + "/")

    il = facts.install_location
    for loc in locations:
        if il and under(il, loc):
            return f"Install location '{il}' is unusual (not /Applications)"
    for loc in locations:
        if any(under(path, loc) for path in facts.payload_paths):
            return f"Payload installs under '{loc}' (an unusual location)"
    return ""


def _decide(c: Classification) -> None:
    vendor = c.vendor_strong * 2 + c.vendor_medium
    custom = c.custom_strong * 2 + c.custom_medium
    if vendor > custom and c.vendor_strong >= 1:
        c.origin = "vendor-originated"
        c.confidence = "high" if c.vendor_strong >= 2 else "medium"
    elif custom > vendor and c.custom_strong >= 1:
        c.origin = "custom-build"
        c.confidence = "high" if c.custom_strong >= 2 else "medium"
    elif c.vendor_strong == 0 and c.custom_strong == 0:
        c.origin, c.confidence = "unknown", "low"
        c.rationale.append(
            "No strong signals in either direction — manual review needed"
        )
    elif c.vendor_strong >= 1 and c.custom_strong >= 1:
        c.origin, c.confidence = "contradictory", "low"
        c.rationale.append("Contradictory strong signals — manual review needed")
    else:
        c.origin, c.confidence = "unknown", "low"
        c.rationale.append("Insufficient strong signals for confident classification")
    c.pattern = {"vendor-originated": 4, "custom-build": 6}.get(c.origin, "other")


# ── Output ────────────────────────────────────────────────────────────────────


def human_size(size: int) -> str:
    if size >= 1048576:
        return f"{size // 1048576} MB"
    if size >= 1024:
        return f"{size // 1024} KB"
    return f"{size} bytes"


def as_json(facts: Facts, c: Classification) -> dict:
    return {
        "file": str(facts.path),
        "size_bytes": facts.size,
        "metadata": {
            "identifier": facts.identifier,
            "version": facts.version,
            "install_location": facts.install_location,
            "signature": facts.signature,
            "authority": facts.authority,
            "team_id": facts.team_id,
            "kind": facts.kind,
            "identifiers": facts.identifiers,
        },
        "classification": {
            "origin": c.origin,
            "confidence": c.confidence,
            "pattern": c.pattern,
            "rationale": c.rationale,
        },
        "payload": {
            "files": facts.files,
            "dirs": facts.dirs,
            "symlinks": facts.symlinks,
            "apps_found": facts.apps,
            "size_mb": facts.size_mb,
        },
    }


def as_text(facts: Facts, c: Classification, clues: Clues) -> list[str]:
    kind = facts.kind
    if kind == "distribution":
        kind += (
            f" ({len(facts.identifiers)} component(s): {', '.join(facts.identifiers)})"
        )
    sig_note = facts.signature + (f" ({facts.authority})" if facts.authority else "")
    lines = [
        "=== analyze-package.sh ===",
        f"  File:         {facts.path}",
        f"  Size:         {facts.size} bytes ({human_size(facts.size)})",
        "",
        "=== Package metadata ===",
        f"  Identifier:   {facts.identifier}",
        f"  Version:      {facts.version}",
        f"  Install loc:  {facts.install_location}",
        f"  Kind:         {kind}",
        f"  Signature:    {facts.signature}",
        f"  Authority:    {facts.authority or '(none)'}",
        "",
        "=== Classification ===",
        f"  Origin:       {c.origin}",
        f"  Confidence:   {c.confidence}",
        f"  Pattern:      {c.pattern}",
        "  Rationale:",
    ]
    lines += [f"- {line}" for line in c.rationale]
    lines += [
        "",
        "=== Payload summary ===",
        f"  Files:        {facts.files}",
        f"  Dirs:         {facts.dirs}",
        f"  Symlinks:     {facts.symlinks}",
        f"  Apps found:   {','.join(facts.apps) or '(none)'}",
    ]
    if facts.size_human:
        lines.append(f"  Estimated:    {facts.size_human}")
    lines += ["", "=== Heuristic notes ===", f"- signature_status={sig_note}"]
    if clues.source:
        lines.append(f"- clues source: {clues.source}")
    else:
        lines.append("- no clues.yaml supplied — using only generic heuristics")
    if facts.apps:
        lines.append(f"- apps found: {','.join(facts.apps)}")
    lines.append(
        f"- vendor strong={c.vendor_strong} medium={c.vendor_medium}"
        f" custom strong={c.custom_strong} medium={c.custom_medium}"
        f" low={c.custom_low}"
    )
    return lines


# ── Front end ─────────────────────────────────────────────────────────────────


def parse_args(argv: list[str]) -> dict:
    opts: dict = {"pkg": "", "output": "text", "clues": "", "customer": ""}
    args = list(argv)
    while args:
        arg = args.pop(0)
        if arg in ("--output", "--clues", "--customer"):
            what = {
                "--output": "text or json",
                "--clues": "a file path",
                "--customer": "a name",
            }[arg]
            if not args or not args[0] or args[0].startswith("-"):
                raise UsageError(f"{arg} requires {what}")
            opts[arg[2:]] = args.pop(0)
        elif arg in ("-h", "--help"):
            opts["help"] = True
            return opts
        elif arg.startswith("-"):
            raise UsageError(f"Unknown option: {arg}")
        elif opts["pkg"]:
            raise UsageError(f"Unexpected argument: {arg}")
        else:
            opts["pkg"] = arg
    if opts["output"] not in ("text", "json"):
        raise UsageError("--output must be text or json")
    if not opts["pkg"]:
        raise UsageError(
            "No package specified. Usage: analyze-package.sh <package.pkg>"
            " [--output text|json] [--clues <path>] [--customer <name>]"
        )
    if not Path(opts["pkg"]).is_file():
        raise UsageError(f"Not a file: {opts['pkg']}")
    return opts


def resolve(opts: dict, warn: bool = True) -> tuple[Clues, str, Customer | None]:
    """The clues, the org's own namespace (first two identifier segments) and
    the customer, from ``opts["clues"]`` and ``opts["customer"]``. Shared with
    analyze-materials; ``warn`` reports a customer folder without clues."""
    base = os.environ.get("AUTOPKG_TOOLKIT_ORG") or None
    clues_path = Path(opts["clues"]) if opts.get("clues") else None
    if clues_path is not None and not clues_path.is_file():
        raise UsageError(f"Clues file not found: {opts['clues']}")
    customer = None
    if opts.get("customer"):
        try:
            customer = load_registry().get(opts["customer"])
            org = customer.org(base)
        except CustomerError as exc:
            raise UsageError(str(exc)) from exc
        if clues_path is None:
            clues_path = customer.root / "clues.yaml"
            if not clues_path.is_file():
                if warn:
                    print(
                        f"WARN:  No clues file for customer '{opts['customer']}'"
                        f" at {clues_path}",
                        file=sys.stderr,
                    )
                clues_path = None
    else:
        org, _error = read_org_config(base)
    clues = load_clues(clues_path) if clues_path else Clues()
    domain = ".".join(org.identifier_prefix.split(".")[:2]) if org else ""
    return clues, domain, customer


def analyze(pkg: Path, clues: Clues, org_domain: str = "") -> Classification:
    """Expand and classify one package (PkgError when it can't be expanded)."""
    with tempfile.TemporaryDirectory(prefix="analyze-package.") as work:
        facts = gather(pkg, Path(work))
    return classify(facts, clues, org_domain)


def main(argv: list[str] | None = None) -> int:
    try:
        opts = parse_args(sys.argv[1:] if argv is None else argv)
        if opts.get("help"):
            print(__doc__)
            return 0
        clues, domain, _customer = resolve(opts)
    except UsageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    pkg = Path(opts["pkg"]).resolve()
    with tempfile.TemporaryDirectory(prefix="analyze-package.") as work:
        try:
            facts = gather(pkg, Path(work))
        except PkgError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            print(
                "ERROR:   Is it a flat package? Bundle-style .pkg folders"
                " are not supported.",
                file=sys.stderr,
            )
            return 2
    result = classify(facts, clues, domain)
    if opts["output"] == "json":
        print(json.dumps(as_json(facts, result), indent=2))
    else:
        print("\n".join(as_text(facts, result, clues)))
    return 1 if result.confidence == "low" else 0


if __name__ == "__main__":
    sys.exit(main())
