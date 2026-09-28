# model.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""The recipe model: recipes, their chains, variable resolution and findings.

Spec: specs/recipekit/01-recipe-model.md. The model describes what AutoPkg sees.
It reports facts and findings, never verdicts, and never raises for recipe
content. The loaded folders are the whole world: parents are never looked up in
AutoPkg's search paths or added repos (FR-04, AIP-07).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import catalogue
from .loader import Finding, RawRecipe, is_recipe_file, read_overrides, read_recipe

VAR_RE = re.compile(r"%([A-Za-z_][A-Za-z0-9_]*)%")
ROLE_RE = re.compile(
    r"^(?P<stem>.+?)\.(?P<role>[A-Za-z0-9_-]+)\.recipe(\.yaml|\.plist)?$"
)
VIEWS = ("autopkg", "harness")


@dataclass(eq=False)
class Step:
    """One Process step, in the recipe that declares it. Compared by identity."""

    processor: str
    args: dict
    recipe: Recipe = field(repr=False)
    index: int
    line: int | None = None

    @property
    def is_shared(self) -> bool:
        return catalogue.is_shared(self.processor)

    def evidence(self, argument: str | None = None) -> dict:
        ev = {
            "recipe": self.recipe.path.name,
            "step": self.index,
            "processor": self.processor,
        }
        if argument:
            ev["argument"] = argument
        if self.line is not None:
            ev["line"] = self.line
        return ev


@dataclass(eq=False)
class Recipe:
    """A parsed recipe file. Compared by identity."""

    path: Path
    format: str
    data: dict
    steps: list[Step] = field(default_factory=list, repr=False)

    @classmethod
    def from_raw(cls, raw: RawRecipe) -> Recipe:
        recipe = cls(raw.path, raw.format, raw.data)
        process = raw.data.get("Process") or []
        for i, item in enumerate(process if isinstance(process, list) else []):
            if not isinstance(item, dict):
                continue
            line = raw.step_lines[i] if i < len(raw.step_lines) else None
            args = item.get("Arguments") or {}
            recipe.steps.append(
                Step(
                    str(item.get("Processor", "")),
                    args if isinstance(args, dict) else {},
                    recipe,
                    i,
                    line,
                )
            )
        return recipe

    @property
    def identifier(self) -> str:
        return str(self.data.get("Identifier") or "")

    @property
    def parent(self) -> str:
        return str(self.data.get("ParentRecipe") or "")

    @property
    def inputs(self) -> dict:
        value = self.data.get("Input") or {}
        return value if isinstance(value, dict) else {}

    @property
    def role(self) -> str:
        """`download`, `pkg`, or another role from the file name (`munki`, …)."""
        m = ROLE_RE.match(self.path.name)
        return m.group("role") if m else ""

    @property
    def stem(self) -> str:
        m = ROLE_RE.match(self.path.name)
        return m.group("stem") if m else self.path.stem


class Pair:
    """A download recipe, its pkg recipe, and the folder they share."""

    def __init__(self, recipes: RecipeSet, folder: Path, stem: str):
        self.recipes = recipes
        self.folder = folder
        self.stem = stem
        members = [r for r in recipes.in_folder(folder) if r.stem == stem]
        self.download = next((r for r in members if r.role == "download"), None)
        self.pkg = next((r for r in members if r.role == "pkg"), None)
        self.others = [r for r in members if r not in (self.download, self.pkg)]
        self.overrides = recipes.overrides.get(folder, {})

    # ── chain ────────────────────────────────────────────────────────────────
    @property
    def leaf(self) -> Recipe | None:
        """The recipe whose chain covers the pair: the pkg recipe if there is one."""
        return self.pkg or self.download

    def chain(self) -> list[Recipe]:
        return self.recipes.chain(self.leaf) if self.leaf else []

    def steps(self) -> list[Step]:
        return [s for r in self.chain() for s in r.steps]

    def facts(self) -> dict:
        """The FR-08 derived facts for this pair."""
        from .derive import facts  # derive imports this module

        return facts(self)

    # ── resolution (FR-06) ─────────────────────────────────────────────────────
    def inputs(self, view: str = "autopkg") -> dict:
        """Input merged along the chain, child over parent; the harness view adds
        `.overrides` on top."""
        merged: dict = {}
        for recipe in self.chain():
            merged.update(recipe.inputs)
        if view == "harness":
            merged.update(self.overrides)
        return merged

    def resolve(
        self, text: str, view: str = "autopkg", before: int | None = None
    ) -> str:
        """Substitute %VARIABLES% the way AutoPkg would, statically. AutoPkg's own
        run variables stay as %NAME% so paths compare textually; a variable a
        processor sets becomes `<set by Processor: var>`."""
        values = {k: str(v) for k, v in self.inputs(view).items()}
        setters = self._setters(before)
        text = str(text)
        for _ in range(10):
            new = VAR_RE.sub(
                lambda m: self._value(m.group(1), values, setters, m.group(0)), text
            )
            if new == text:
                break
            text = new
        return text

    @staticmethod
    def _value(name: str, values: dict, setters: dict, raw: str) -> str:
        if name in values:
            return values[name]
        if name in setters:
            return f"<set by {setters[name]}: {name}>"
        return raw

    def _setters(self, before: int | None) -> dict[str, str]:
        """Which processor sets each variable, from the chain's steps before position
        `before` (all steps when None)."""
        found: dict[str, str] = {}
        steps = self.steps()
        for step in steps[:before] if before is not None else steps:
            outs = catalogue.outputs(
                step.processor, step.args, lambda t: self.resolve_inputs(t)
            )
            for name in outs or ():
                found.setdefault(name, step.processor)
        return found

    def resolve_inputs(self, text: str) -> str:
        """Substitute Input values only (used to read patterns held in Input)."""
        values = {k: str(v) for k, v in self.inputs().items()}
        for _ in range(10):
            new = VAR_RE.sub(lambda m: values.get(m.group(1), m.group(0)), text)
            if new == text:
                return new
            text = new
        return text

    # ── findings (FR-06, FR-09) ────────────────────────────────────────────────
    def variable_findings(self) -> list[Finding]:
        findings: list[Finding] = []
        seen: set[tuple[str, str]] = set()
        steps = self.steps()
        inputs = self.inputs()
        static = set(catalogue.AUTOPKG_VARS) | set(inputs)
        outputs = [
            catalogue.outputs(s.processor, s.args, self.resolve_inputs) for s in steps
        ]
        all_set = set().union(*(o for o in outputs if o))

        def add(code: str, severity: str, var: str, where: Path, line, message: str):
            if (code, var) in seen:
                return
            seen.add((code, var))
            findings.append(Finding(code, severity, str(where), message, line, var))

        def unresolved(var: str, where: Path, line, unknown_before: bool, later: bool):
            if later:
                add(
                    "used_before_set",
                    "error",
                    var,
                    where,
                    line,
                    f"%{var}% is used before the step that sets it",
                )
            elif unknown_before:
                add(
                    "unverifiable",
                    "warning",
                    var,
                    where,
                    line,
                    f"%{var}% could only come from a shared or unknown processor",
                )
            elif var in self.overrides:
                add(
                    "harness_supplied",
                    "info",
                    var,
                    where,
                    line,
                    f"%{var}% is supplied only by .overrides; a bare `autopkg run` "
                    "would not have it",
                )
            else:
                add(
                    "undeclared_variable",
                    "error",
                    var,
                    where,
                    line,
                    f"%{var}% is used but nothing declares or sets it",
                )

        # Input values: may use anything known anywhere in the chain.
        for recipe in self.chain():
            for text in _strings(recipe.inputs):
                for var in VAR_RE.findall(text):
                    if var not in static and var not in all_set:
                        unresolved(var, recipe.path, None, None in outputs, False)

        # Process arguments: only what is known before the step.
        set_so_far: set[str] = set()
        unknown_seen = False
        for i, step in enumerate(steps):
            if not catalogue.is_known(step.processor):
                add(
                    "unknown_processor",
                    "warning",
                    step.processor,
                    step.recipe.path,
                    step.line,
                    f"no catalogue entry for processor {step.processor}",
                )
            for text in _strings(step.args):
                for var in VAR_RE.findall(text):
                    if var in static or var in set_so_far:
                        continue
                    later = any(var in (o or ()) for o in outputs[i:])
                    unresolved(var, step.recipe.path, step.line, unknown_seen, later)
            if outputs[i] is None:
                unknown_seen = True
            else:
                set_so_far |= outputs[i]
        return findings


class RecipeSet:
    """Every recipe in the loaded folders, indexed by Identifier."""

    def __init__(self):
        self.recipes: list[Recipe] = []
        self.findings: list[Finding] = []
        self.overrides: dict[Path, dict[str, str]] = {}
        self.folders: list[Path] = []
        self.audit = False

    @classmethod
    def load(cls, *folders: Path | str, audit: bool = False) -> RecipeSet:
        """Load the recipes directly inside each folder. With `audit=True`, plist
        recipes are expected (reviewing a community repo) and not flagged."""
        rs = cls()
        rs.audit = audit
        for folder in folders:
            rs._load_folder(Path(folder))
        rs._check_pairing()
        return rs

    @classmethod
    def load_repo(cls, root: Path | str, audit: bool = False) -> RecipeSet:
        """Load every recipe folder under `<root>/recipes` (or `root` itself)."""
        root = Path(root)
        base = root / "recipes" if (root / "recipes").is_dir() else root
        folders = sorted(
            {p.parent for p in base.rglob("*") if p.is_file() and is_recipe_file(p)}
        )
        return cls.load(*folders, audit=audit)

    def _load_folder(self, folder: Path) -> None:
        folder = folder.resolve()
        self.folders.append(folder)
        for path in sorted(folder.iterdir()) if folder.is_dir() else []:
            if not (path.is_file() and is_recipe_file(path)):
                continue
            raw, problem = read_recipe(path)
            if problem:
                self.findings.append(problem)
                continue
            recipe = Recipe.from_raw(raw)
            self.recipes.append(recipe)
            if raw.format == "plist" and not self.audit and _inside_recipe_repo(path):
                self.findings.append(
                    Finding(
                        "plist_recipe",
                        "error",
                        str(path),
                        "plist recipe in a recipe repo: convert it to YAML when "
                        "adopting it "
                        "(Standards §6.10.3)",
                    )
                )
        overrides = folder / ".overrides"
        if overrides.is_file():
            self.overrides[folder] = read_overrides(overrides)

    # ── lookup ─────────────────────────────────────────────────────────────────
    def in_folder(self, folder: Path) -> list[Recipe]:
        return [r for r in self.recipes if r.path.parent == folder]

    def by_identifier(self, identifier: str) -> Recipe | None:
        return next((r for r in self.recipes if r.identifier == identifier), None)

    def chain(self, recipe: Recipe) -> list[Recipe]:
        """Root first, `recipe` last. Stops at a missing parent or a cycle."""
        chain = [recipe]
        while chain[0].parent:
            parent = self.by_identifier(chain[0].parent)
            if parent is None or parent in chain:
                break
            chain.insert(0, parent)
        return chain

    def pairs(self) -> list[Pair]:
        found = []
        for folder in self.folders:
            for stem in sorted({r.stem for r in self.in_folder(folder)}):
                found.append(Pair(self, folder, stem))
        return found

    # ── pairing findings (FR-04) ───────────────────────────────────────────────
    def _check_pairing(self) -> None:
        for recipe in self.recipes:
            if recipe.parent and self.by_identifier(recipe.parent) is None:
                self.findings.append(
                    Finding(
                        "parent_missing",
                        "error",
                        str(recipe.path),
                        f"ParentRecipe {recipe.parent} is not in the loaded folders; a "
                        "community parent must be adopted, not referenced",
                    )
                )
        for pair in self.pairs():
            if pair.download is None and pair.pkg is None:
                continue
            if pair.download is None or pair.pkg is None:
                have = pair.download or pair.pkg
                missing = "pkg" if pair.pkg is None else "download"
                self.findings.append(
                    Finding(
                        "pair_incomplete",
                        "error",
                        str(have.path),
                        f"no {missing} recipe for {pair.stem} in {pair.folder.name}/",
                    )
                )
                continue
            parent = pair.pkg.parent
            if (
                parent
                and parent != pair.download.identifier
                and self.by_identifier(parent)
            ):
                self.findings.append(
                    Finding(
                        "parent_mismatch",
                        "error",
                        str(pair.pkg.path),
                        f"ParentRecipe {parent} is not the sibling download recipe "
                        f"({pair.download.identifier})",
                    )
                )

    def all_findings(self) -> list[Finding]:
        found = list(self.findings)
        for pair in self.pairs():
            found.extend(pair.variable_findings())
        return found


def _strings(value) -> list[str]:
    """Every string inside a parsed value. Comments are already gone."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def _inside_recipe_repo(path: Path) -> bool:
    return "recipes" in path.resolve().parts[:-1]
