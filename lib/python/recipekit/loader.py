# loader.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Read recipe files and `.overrides` from disk (spec FR-03).

YAML recipes are the kit's format. Plist recipes are read, never written (AIP-04).
Nothing here raises for bad *content*: a file that can't be parsed comes back as a
`recipe_invalid` finding.
"""

from __future__ import annotations

import plistlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml

YAML_SUFFIX = ".recipe.yaml"
PLIST_SUFFIXES = (".recipe", ".recipe.plist")


@dataclass
class Finding:
    """One problem or note about recipe content (spec FR-09)."""

    code: str
    severity: str  # error | warning | info
    file: str
    message: str
    line: int | None = None
    subject: str | None = None  # e.g. the variable a variable finding is about

    def as_dict(self) -> dict:
        d = {
            "code": self.code,
            "severity": self.severity,
            "file": self.file,
            "message": self.message,
        }
        if self.line is not None:
            d["line"] = self.line
        if self.subject is not None:
            d["subject"] = self.subject
        return d


@dataclass
class RawRecipe:
    """A parsed recipe file, with the line of each Process step when known."""

    path: Path
    data: dict
    format: str  # yaml | plist
    step_lines: list[int | None] = field(default_factory=list)


def is_recipe_file(path: Path) -> bool:
    name = path.name
    return name.endswith(YAML_SUFFIX) or name.endswith(PLIST_SUFFIXES)


def read_recipe(path: Path) -> tuple[RawRecipe | None, Finding | None]:
    """Parse one recipe file. Returns (recipe, None) or (None, finding)."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, Finding("recipe_invalid", "error", str(path), f"unreadable: {exc}")

    if path.name.endswith(YAML_SUFFIX):
        return _read_yaml(path, raw)
    return _read_plist(path, raw)


def _read_yaml(path: Path, raw: bytes) -> tuple[RawRecipe | None, Finding | None]:
    text = raw.decode("utf-8", errors="replace")
    try:
        data = yaml.safe_load(text)
        node = yaml.compose(text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        line = mark.line + 1 if mark is not None else None
        return None, Finding(
            "recipe_invalid", "error", str(path), f"not valid YAML: {exc}", line
        )
    if not isinstance(data, dict):
        return None, Finding(
            "recipe_invalid", "error", str(path), "a recipe must be a YAML mapping"
        )
    return RawRecipe(path, data, "yaml", _step_lines(node)), None


def _read_plist(path: Path, raw: bytes) -> tuple[RawRecipe | None, Finding | None]:
    try:
        data = plistlib.loads(raw)
    except (plistlib.InvalidFileException, ValueError) as exc:
        return None, Finding(
            "recipe_invalid", "error", str(path), f"not a valid plist: {exc}"
        )
    if not isinstance(data, dict):
        return None, Finding(
            "recipe_invalid", "error", str(path), "a recipe must be a dictionary"
        )
    return RawRecipe(path, data, "plist"), None


def _step_lines(node) -> list[int | None]:
    """1-based line of each item in the top-level Process list."""
    if not isinstance(node, yaml.MappingNode):
        return []
    for key, value in node.value:
        if getattr(key, "value", None) == "Process" and isinstance(
            value, yaml.SequenceNode
        ):
            return [item.start_mark.line + 1 for item in value.value]
    return []


def read_overrides(path: Path) -> dict[str, str]:
    """Parse a `.overrides` file: `key=value` lines, `#` comments, blank lines.
    A last line without a trailing newline still counts."""
    values: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return values
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values
