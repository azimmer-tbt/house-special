# helpers.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Small fixture builders for the recipekit tests."""

from __future__ import annotations

import plistlib
import tempfile
import textwrap
import unittest
from pathlib import Path

import yaml

KIT_ROOT = Path(__file__).resolve().parents[2]


def download(name: str = "App", inputs: str = "", process: str = "") -> str:
    return (
        f"Identifier: com.acmefruit.autopkg.download.{name}\n"
        f"Input:\n  NAME: {name}\n{_indent(inputs, 2)}"
        f"Process:\n{_indent(process, 2) or '  []'}\n"
    )


def pkg(
    name: str = "App", inputs: str = "", process: str = "", parent: str | None = None
) -> str:
    parent = parent or f"com.acmefruit.autopkg.download.{name}"
    return (
        f"Identifier: com.acmefruit.autopkg.pkg.{name}\n"
        f"ParentRecipe: {parent}\n"
        f"Input:\n  NAME: {name}\n{_indent(inputs, 2)}"
        f"Process:\n{_indent(process, 2) or '  []'}\n"
    )


def _indent(text: str, spaces: int) -> str:
    text = textwrap.dedent(text).strip("\n")
    if not text:
        return ""
    return textwrap.indent(text, " " * spaces) + "\n"


class FixtureCase(unittest.TestCase):
    """A TestCase with a throwaway directory and helpers to fill it."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def reset(self) -> None:
        """Start over with an empty directory (between sub-tests)."""
        self.tearDown()
        self.setUp()

    def folder(self, rel: str = "recipes/Acme/App") -> Path:
        path = self.root / rel
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write(self, folder: Path, name: str, text: str) -> Path:
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def pair(
        self,
        name: str = "App",
        download_text: str = "",
        pkg_text: str = "",
        rel: str | None = None,
    ) -> Path:
        folder = self.folder(rel or f"recipes/Acme/{name}")
        self.write(
            folder, f"{name}.download.recipe.yaml", download_text or download(name)
        )
        self.write(folder, f"{name}.pkg.recipe.yaml", pkg_text or pkg(name))
        return folder

    def as_plist(self, yaml_path: Path) -> Path:
        """Write the same recipe as a plist next to it and remove the YAML."""
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        target = yaml_path.with_name(yaml_path.name.replace(".recipe.yaml", ".recipe"))
        target.write_bytes(plistlib.dumps(data))
        yaml_path.unlink()
        return target
