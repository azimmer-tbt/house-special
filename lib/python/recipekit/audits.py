# audits.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""The guardrail audits, on the recipe model.

Spec: specs/guardrail-audits/00-constitution.md and 01-audits.md. Each audit checks
one runtime behaviour the static linter can't express, for one recipe pair, and
returns PASS, FAIL or SKIP ("could not check", constitution OQ-2). Nothing here
parses recipe text itself (recipekit AIP-01); the only raw-text read is the comment
check in `unsigned_declared`, which by definition is about comments.

The scripts in guardrails/audit/ are thin front ends for `cli()`.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .model import Pair, Recipe, RecipeSet, Step

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
CHAIN = ("Developer ID Certification Authority", "Apple Root CA")
STAGING = frozenset(
    {
        "URLDownloader",
        "Copier",
        "Unarchiver",
        "DmgMounter",
        "PkgRootCreator",
        "FlatPkgUnpacker",
        "PkgPayloadUnpacker",
        "FileCreator",
        "PkgCopier",
        "PkgCreator",
    }
)
TRUE = (True, "true", "True", "yes", "Yes", 1)


@dataclass
class AuditResult:
    """One audit's verdict for one pair: FAIL beats SKIP beats PASS."""

    name: str
    lines: list[tuple[str, str]] = field(default_factory=list)

    def add(self, status: str, text: str) -> None:
        self.lines.append((status, text))

    @property
    def status(self) -> str:
        statuses = {s for s, _ in self.lines}
        for status in (FAIL, SKIP):
            if status in statuses:
                return status
        return PASS

    def text(self) -> list[str]:
        return [f"{s}: {t}" for s, t in self.lines]


# ── the audits ─────────────────────────────────────────────────────────────────
def no_pathdeleter(pair: Pair) -> AuditResult:
    """FR-02, lesson 2: a PathDeleter before anything is staged fails on a fresh
    cache. One that cleans up what this run created is fine."""
    r = AuditResult("no_pathdeleter")
    staged = False
    for step in pair.steps():
        if step.processor == "PathDeleter" and not staged:
            r.add(
                FAIL,
                f"{_where(step)}: PathDeleter runs before anything is staged, so "
                "it errors on a fresh cache. Copier already overwrites its destination "
                "(methodology lesson 2).",
            )
        staged = staged or step.processor in STAGING
    if not r.lines:
        r.add(PASS, "no PathDeleter runs before something is staged")
    return r


def vendor_cache_path(pair: Pair) -> AuditResult:
    """FR-03, lessons 1 and 24: local vendor-cache paths exist. SKIP when the cache
    itself isn't on this machine; FAIL when it is and the file isn't (a wrong path)."""
    r = AuditResult("vendor_cache_path")
    inputs = pair.inputs()
    root_value = (
        pair.resolve(str(inputs["VENDOR_CACHE_ROOT"]))
        if "VENDOR_CACHE_ROOT" in inputs
        else ""
    )
    for recipe, label, raw in _cache_references(pair):
        text = pair.resolve(raw).replace("%RECIPE_DIR%", str(recipe.path.parent))
        text = text[len("file://") :] if text.startswith("file://") else text
        if "%" in text or "<set by" in text:
            r.add(SKIP, f"{label}: can't resolve {raw} statically")
            continue
        path = Path(text)
        if not path.is_absolute():
            path = recipe.path.parent / path
        path = Path(*path.parts).resolve() if path.exists() else _normalise(path)
        root = _cache_root(path, root_value)
        if root is not None and not root.exists():
            r.add(SKIP, f"{label}: the vendor cache ({root}) isn't on this machine")
        elif path.exists():
            r.add(PASS, f"{label} -> {path}")
        else:
            r.add(
                FAIL,
                f"{label} -> {path} does not exist. Check the ../ depth count "
                "and the Vendor/App folder names (methodology lessons 1 and 24).",
            )
    if not r.lines:
        r.add(PASS, "no local vendor-cache paths (nothing to check)")
    return r


def no_pathname_reliance(pair: Pair) -> AuditResult:
    """FR-04, lesson 3: %pathname% is only set by URLDownloader."""
    r = AuditResult("no_pathname_reliance")
    if pair.download is None:
        r.add(SKIP, "could not check: no download recipe in the folder")
        return r
    for f in pair.variable_findings():
        if f.subject == "pathname" and f.severity == "error":
            r.add(
                FAIL,
                f"{Path(f.file).name}: %pathname% is used, but no earlier step "
                "sets it (Copier doesn't). Use the literal path, e.g. "
                "%RECIPE_CACHE_DIR%/<App>.pkg (methodology lesson 3).",
            )
        elif f.subject == "pathname" and f.code == "unverifiable":
            r.add(SKIP, f"{Path(f.file).name}: {f.message}")
    if not r.lines:
        r.add(PASS, "%pathname% is only used after a step that sets it")
    return r


def cert_chain_complete(pair: Pair) -> AuditResult:
    """FR-05, lesson 6: authority-name lists include Apple's chain."""
    r = AuditResult("cert_chain_complete")
    for step in pair.steps():
        if step.processor != "CodeSignatureVerifier":
            continue
        names = step.args.get("expected_authority_names")
        if names is None:
            continue
        resolved = [pair.resolve(str(n)) for n in names or []]
        missing = [c for c in CHAIN if c not in resolved]
        if missing:
            r.add(
                FAIL,
                f"{_where(step)}: expected_authority_names is missing "
                f"{' and '.join(repr(m) for m in missing)}; add them after the "
                "vendor's leaf certificate (methodology lesson 6).",
            )
    if not r.lines:
        r.add(
            PASS, "every authority-name list includes the Apple chain (or none is used)"
        )
    return r


def unsigned_declared(pair: Pair) -> AuditResult:
    """FR-06, lesson 7: no verifier means NO_CODE_SIGNATURE_REQUIRED with a reason."""
    r = AuditResult("unsigned_declared")
    if any(s.processor == "CodeSignatureVerifier" for s in pair.steps()):
        r.add(PASS, "a CodeSignatureVerifier step is present")
        return r
    declaring = next(
        (
            rec
            for rec in reversed(pair.chain())
            if rec.inputs.get("NO_CODE_SIGNATURE_REQUIRED") in TRUE
        ),
        None,
    )
    if declaring is None:
        r.add(
            FAIL,
            "no CodeSignatureVerifier and no NO_CODE_SIGNATURE_REQUIRED: true in "
            "Input. Never omit the verifier silently: declare why signing isn't "
            "checked (methodology lesson 7).",
        )
    elif declaring.format == "yaml" and not _flag_explained(declaring.path):
        r.add(
            FAIL,
            f"{declaring.path.name}: NO_CODE_SIGNATURE_REQUIRED has no comment "
            "saying why; put one on its line or the line above "
            "(methodology lesson 7).",
        )
    else:
        r.add(PASS, f"unsigned status declared in {declaring.path.name}")
    return r


def variables_declared(pair: Pair) -> AuditResult:
    """FR-07, lesson 12: every %variable% is declared or set by an earlier step."""
    r = AuditResult("variables_declared")
    if pair.download is None or pair.pkg is None:
        r.add(SKIP, "could not check: the folder has only half a recipe pair")
        return r
    for f in pair.variable_findings():
        where = Path(f.file).name + (f":{f.line}" if f.line else "")
        if f.severity == "error":
            r.add(
                FAIL,
                f"{where}: {f.message}. Declare it in Input; .overrides doesn't "
                "count for a bare autopkg run (methodology lesson 12).",
            )
        elif f.code == "unverifiable":
            r.add(SKIP, f"{where}: {f.message}")
        elif f.code == "harness_supplied":
            r.add(PASS, f"{where}: {f.message} (fine when your pipeline supplies it)")
    if not r.lines:
        r.add(PASS, "every %variable% is declared in Input or set by an earlier step")
    return r


def copier_overwrite(pair: Pair) -> AuditResult:
    """FR-08, lessons 11 and 13: a Copier that copies a folder sets overwrite: true."""
    r = AuditResult("copier_overwrite")
    for step in pair.steps():
        if step.processor != "Copier" or not _copies_a_folder(pair, step):
            continue
        if step.args.get("overwrite") not in TRUE:
            r.add(
                FAIL,
                f"{_where(step)}: Copier copies a folder without overwrite: true; "
                "a second run fails with [Errno 17] File exists "
                "(methodology lesson 11).",
            )
    if not r.lines:
        r.add(
            PASS, "every folder Copier sets overwrite: true (or none copies a folder)"
        )
    return r


def readme_exists(folder: Path) -> AuditResult:
    """FR-09: the app folder has a non-empty README.md (exact name)."""
    r = AuditResult("readme_exists")
    readme = folder / "README.md"
    if (
        "README.md" in {p.name for p in folder.iterdir()}
        and readme.is_file()
        and readme.stat().st_size > 0
    ):
        r.add(PASS, f"README.md found in {folder.name}")
    else:
        r.add(
            FAIL,
            f"{folder.name} has no README.md: record the pattern, why, and any "
            "bugs found (guardrails/GUARDRAILS.md).",
        )
    return r


def recipe_pairing(pair: Pair) -> AuditResult:
    """The model's own findings about this pair's recipes (recipekit FR-04, FR-09):
    a missing or mismatched ParentRecipe, half a pair, a plist in a recipe repo.
    Without this, a pkg recipe whose parent is wrong would have its sibling
    download recipe go unchecked by every other audit."""
    r = AuditResult("recipe_pairing")
    files = {str(rec.path) for rec in (pair.download, pair.pkg, *pair.others) if rec}
    codes = ("pair_incomplete", "parent_mismatch", "parent_missing", "plist_recipe")
    for f in pair.recipes.findings:
        if f.code in codes and f.file in files:
            r.add(FAIL, f"{Path(f.file).name}: {f.message}")
    if not r.lines:
        r.add(PASS, "the pkg recipe's ParentRecipe is its sibling download recipe")
    return r


PAIR_AUDITS: dict[str, Callable[[Pair], AuditResult]] = {
    "recipe_pairing": recipe_pairing,
    "no_pathdeleter": no_pathdeleter,
    "vendor_cache_path": vendor_cache_path,
    "cert_chain_complete": cert_chain_complete,
    "unsigned_declared": unsigned_declared,
    "copier_overwrite": copier_overwrite,
    "no_pathname_reliance": no_pathname_reliance,
    "variables_declared": variables_declared,
}


def run_all(pair: Pair) -> list[AuditResult]:
    return [audit(pair) for audit in PAIR_AUDITS.values()] + [
        readme_exists(pair.folder)
    ]


# ── helpers ────────────────────────────────────────────────────────────────────
def _where(step: Step) -> str:
    line = f":{step.line}" if step.line else ""
    return f"{step.recipe.path.name}{line} (step {step.index + 1})"


def _cache_references(pair: Pair) -> list[tuple[Recipe, str, str]]:
    """(recipe, label, raw value) for LOCAL_*PATH inputs and file:// URLs."""
    refs: list[tuple[Recipe, str, str]] = []
    for recipe in pair.chain():
        for key, value in recipe.inputs.items():
            if re.fullmatch(r"LOCAL_\w*PATH", str(key)):
                refs.append((recipe, key, str(value)))
            elif str(value).startswith("file://"):
                refs.append((recipe, key, str(value)))
        for step in recipe.steps:
            url = (
                str(step.args.get("url", ""))
                if step.processor == "URLDownloader"
                else ""
            )
            if url.startswith("file://"):
                refs.append((recipe, f"{_where(step)} url", url))
    return refs


def _normalise(path: Path) -> Path:
    """Collapse `..` without touching the disk (the path may not exist)."""
    parts: list[str] = []
    for part in path.parts:
        if part == ".." and parts and parts[-1] != "/":
            parts.pop()
        elif part != ".":
            parts.append(part)
    return Path(*parts)


def _cache_root(path: Path, root_value: str) -> Path | None:
    if root_value and str(path).startswith(root_value.rstrip("/") + "/"):
        return Path(root_value)
    parts = path.parts
    if "vendor_cache" in parts:
        return Path(*parts[: parts.index("vendor_cache") + 1])
    return None


def _copies_a_folder(pair: Pair, step: Step) -> bool:
    raw = str(step.args.get("source_path", ""))
    if "LOCAL_DIR_PATH" in raw or raw.rstrip().endswith("/"):
        return True
    resolved = pair.resolve(raw).replace("%RECIPE_DIR%", str(step.recipe.path.parent))
    last = resolved.rstrip("/").rsplit("/", 1)[-1]
    if re.search(r"\.(app|saver|prefPane|plugin|bundle|framework)$", last):
        return True
    local = Path(resolved)
    return local.is_absolute() and local.is_dir()


def _flag_explained(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^\s*NO_CODE_SIGNATURE_REQUIRED\s*:", line):
            if "#" in line.split(":", 1)[1]:
                return True
            return i > 0 and bool(re.match(r"^\s*#\s*\S", lines[i - 1]))
    return False


# ── command line (the guardrails/audit/check_*.py scripts) ──────────────────────
def _pairs_for(target: Path) -> tuple[list[Pair], str | None]:
    folder = target if target.is_dir() else target.parent
    recipes = RecipeSet.load(folder)
    bad = [
        f
        for f in recipes.findings
        if f.code == "recipe_invalid"
        and (target.is_dir() or Path(f.file).resolve() == target.resolve())
    ]
    if bad:
        return [], f"{bad[0].file} is not a valid recipe: {bad[0].message}"
    pairs = recipes.pairs()
    if target.is_file():
        pairs = [
            p
            for p in pairs
            if target.resolve() in {r.path.resolve() for r in (p.download, p.pkg) if r}
        ]
    return pairs, None


def cli(name: str, argv: list[str] | None = None) -> int:
    """Run one audit from the command line. Exit 0 PASS or SKIP, 1 FAIL, 2 error."""
    parser = argparse.ArgumentParser(
        prog=f"check_{name}.py",
        description=f"Guardrail audit '{name}' (specs/guardrail-audits/01-audits.md). "
        "The target is a recipe file or its app folder.",
    )
    parser.add_argument("target", type=Path)
    args = parser.parse_args(argv)
    if not args.target.exists():
        print(f"ERROR: not found: {args.target}", file=sys.stderr)
        return 2
    if name == "readme_exists":
        folder = args.target if args.target.is_dir() else args.target.parent
        results = [readme_exists(folder)]
    else:
        pairs, error = _pairs_for(args.target)
        if error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        if not pairs:
            print(f"ERROR: no recipe pair for {args.target}", file=sys.stderr)
            return 2
        results = [PAIR_AUDITS[name](p) for p in pairs]
    for result in results:
        print("\n".join(result.text()))
    return 1 if any(r.status == FAIL for r in results) else 0
