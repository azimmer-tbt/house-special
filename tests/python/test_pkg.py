# test_pkg.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""recipekit.pkg, pkg_compare and pkg_reverse: BOM parsing (KI-4), the chown
rollup, the comparisons, and both tools end to end on packages built here with
pkgbuild/productbuild (no root needed; skipped where those tools are missing)."""

import contextlib
import io
import os
import shutil
import subprocess
import unittest
from pathlib import Path

from helpers import FixtureCase
from recipekit import pkg_compare, pkg_reverse
from recipekit.pkg import (
    BomEntry,
    Inventory,
    chown_rollup,
    parse_lsbom,
)
from recipekit.pkg_compare import inventory_diff, permission_diff
from recipekit.pkg_reverse import app_name_from

# Real `lsbom -p mugsfl` output: tab-separated, directories have no size, a
# symlink carries its target in the sixth field.
LSBOM = (
    "40755\t0\t0\t\t.\t\n"
    "40755\t0\t0\t\t./Library\t\n"
    "40755\t0\t0\t\t./Library/My Dir\t\n"
    "100644\t0\t0\t3\t./Library/My Dir/a file.txt\t\n"
    "120755\t0\t0\t10\t./Library/My Dir/link\ta file.txt\n"
    "40755\t0\t0\t\t./Library/My Dir/sub\t\n"
)


def entries(*rows: tuple[str, str]) -> dict[str, BomEntry]:
    """BOM entries from (path, "uid:gid"); a path ending in / is a directory."""
    result = {}
    for path, owner in rows:
        uid, gid = (int(x) for x in owner.split(":"))
        is_dir = path.endswith("/") or path == "."
        clean = path.rstrip("/") or "."
        result[clean] = BomEntry(clean, 0o40755 if is_dir else 0o100644, uid, gid)
    return result


class ParseTest(unittest.TestCase):
    def test_directories_spaces_and_links_parse(self):
        bom = parse_lsbom(LSBOM)
        self.assertEqual(len(bom), 6)
        self.assertTrue(bom["Library/My Dir"].is_dir)
        self.assertEqual(bom["Library/My Dir/a file.txt"].size, "3")
        self.assertEqual(bom["Library/My Dir/link"].link, "a file.txt")
        self.assertTrue(bom["Library/My Dir/link"].is_link)
        self.assertEqual(bom["."].owner, "0:0")
        self.assertEqual(bom["Library/My Dir/a file.txt"].perms(), "-rw-r--r--:0:0")

    def test_unparseable_lines_are_skipped(self):
        text = "drwxr-xr-x \troot\twheel\t\t./x\n40755 0/0 ./old-format\n"
        self.assertEqual(parse_lsbom(text), {})


class RollupTest(unittest.TestCase):
    def test_a_uniform_tree_is_one_entry_per_top_level_item(self):
        bom = entries(
            (".", "0:0"),
            ("Applications/", "0:80"),
            ("Applications/App.app/", "0:80"),
            ("Applications/App.app/Info.plist", "0:80"),
            ("Library/", "0:0"),
        )
        self.assertEqual(
            chown_rollup(bom), [("Applications", "0:80"), ("Library", "0:0")]
        )

    def test_a_mixed_directory_lists_what_differs_after_it(self):
        bom = entries(
            ("Users/", "0:0"),
            ("Users/Shared/", "0:0"),
            ("Users/Shared/root.txt", "0:0"),
            ("Users/Shared/my file.sh", "501:20"),
            ("Users/Shared/tree/", "501:20"),
            ("Users/Shared/tree/deep", "501:20"),
            ("Users/Shared/tree/back", "0:0"),
        )
        self.assertEqual(
            chown_rollup(bom),
            [
                ("Users", "0:0"),
                ("Users/Shared/my file.sh", "501:20"),
                ("Users/Shared/tree", "501:20"),
                ("Users/Shared/tree/back", "0:0"),
            ],
        )

    def test_parents_come_before_children(self):
        # "a b" sorts before "a/b" as a string; parent-first order must not.
        bom = entries(("a/", "0:0"), ("a/b", "1:1"), ("a b", "2:2"))
        order = [path for path, _ in chown_rollup(bom)]
        self.assertLess(order.index("a"), order.index("a/b"))


class CompareLogicTest(unittest.TestCase):
    def test_directories_and_spaced_paths_are_compared(self):  # KI-4, AC-5.2
        old = parse_lsbom(LSBOM)
        new = dict(old)
        new["Library/My Dir"] = BomEntry("Library/My Dir", 0o40775, 0, 80)
        new["Library/My Dir/a file.txt"] = BomEntry(
            "Library/My Dir/a file.txt", 0o100755, 0, 0
        )
        diffs = permission_diff(old, new)
        self.assertEqual(
            diffs,
            [
                ("Library/My Dir", "drwxr-xr-x:0:0", "drwxrwxr-x:0:80"),
                ("Library/My Dir/a file.txt", "-rw-r--r--:0:0", "-rwxr-xr-x:0:0"),
            ],
        )

    def test_a_symlinks_mode_is_ignored_but_its_owner_is_not(self):
        old = parse_lsbom(LSBOM)
        new = dict(old)
        new["Library/My Dir/link"] = BomEntry("Library/My Dir/link", 0o120777, 0, 0)
        self.assertEqual(permission_diff(old, new), [])
        new["Library/My Dir/link"] = BomEntry("Library/My Dir/link", 0o120755, 501, 0)
        self.assertEqual(len(permission_diff(old, new)), 1)

    def test_inventory_groups(self):
        old = Inventory({"a", "b c"}, {"d"}, {"l": "a", "m": "x"})
        new = Inventory({"a"}, {"d", "e"}, {"l": "b"})
        groups = dict(inventory_diff(old, new))
        self.assertEqual(groups["Files only in original (1)"], ["b c"])
        self.assertEqual(groups["Directories only in rebuilt (1)"], ["e"])
        self.assertEqual(groups["Symlinks only in original"], ["m -> x"])
        self.assertEqual(
            groups["Symlinks with different targets"], ["l -> a  vs  l -> b"]
        )
        self.assertEqual(inventory_diff(old, old), [])


class AppNameTest(unittest.TestCase):
    def test_names_are_sanitised(self):
        cases = {
            "My App_2.pkg": "My-App-2",
            "Tool$(rm -rf).pkg": "Toolrm--rf",
            "Café.pkg": "Caf",
            "plain.pkg": "plain",
        }
        for given, expected in cases.items():
            with self.subTest(given):
                self.assertEqual(app_name_from(Path(given)), expected)


def run(module, *argv):
    out, errs = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(errs):
        code = module.main(list(argv))
    return code, out.getvalue(), errs.getvalue()


@unittest.skipUnless(shutil.which("pkgbuild") and shutil.which("lsbom"), "macOS only")
class PackagesTest(FixtureCase):
    """Both tools on real flat packages."""

    def build(self, name, *, extra="", script="", preserve=False, ident="io.example.t"):
        root = self.root / f"{name}-root"
        folder = root / "Library" / "My Dir"
        folder.mkdir(parents=True)
        (folder / "a file.txt").write_text("hi\n")
        os.symlink("a file.txt", folder / "link")
        if extra:
            (folder / extra).write_text("extra\n")
        cmd = ["pkgbuild", "--quiet", "--root", str(root), "--identifier", ident]
        cmd += ["--version", "1"]
        if preserve:
            cmd += ["--ownership", "preserve"]
        if script:
            scripts = self.root / f"{name}-scripts"
            scripts.mkdir()
            (scripts / "postinstall").write_text(script)
            (scripts / "postinstall").chmod(0o755)
            cmd += ["--scripts", str(scripts)]
        out = self.root / f"{name}.pkg"
        subprocess.run(cmd + [str(out)], check=True)
        return out

    def compare(self, old, new):
        work = self.root / "work"
        shutil.rmtree(work, ignore_errors=True)
        return run(
            pkg_compare,
            "--old-pkg",
            str(old),
            "--new-pkg",
            str(new),
            "--work-dir",
            str(work),
        )

    def test_compare_exit_codes(self):
        base = self.build("base", script="#!/bin/sh\nexit 0\n")
        same = self.build("same", script="#!/bin/sh\nexit 0\n", ident="io.example.u")
        extra = self.build("extra", extra="more.txt", script="#!/bin/sh\nexit 0\n")
        owned = self.build("owned", preserve=True, script="#!/bin/sh\nexit 0\n")
        script = self.build("script", script="#!/bin/sh\nexit 1\n")
        cases = [(same, 0, "MISMATCH: identifier differs"), (extra, 1, "more.txt")]
        cases += [(owned, 2, "Library/My Dir\n"), (script, 3, "content or mode")]
        for new, code, text in cases:
            with self.subTest(new.name):
                got, out, _ = self.compare(base, new)
                self.assertEqual(got, code, out)
                self.assertIn(text, out)

    def test_compare_rejects_a_multi_component_distribution(self):
        one, two = self.build("one"), self.build("two", ident="io.example.two")
        dist = self.root / "dist.pkg"
        subprocess.run(
            ["productbuild", "--quiet", "--package", str(one), "--package", str(two)]
            + [str(dist)],
            check=True,
        )
        code, _, errs = self.compare(one, dist)
        self.assertEqual(code, 5)
        self.assertIn("2 components", errs)

    def reverse(self, pkg, *extra):
        return run(
            pkg_reverse,
            str(pkg),
            "--dest",
            str(self.root / "out"),
            "--allow-unprivileged",
            *extra,
        )

    @unittest.skipIf(os.geteuid() == 0, "tests the unprivileged path")
    def test_reverse_writes_numeric_bom_and_rollup(self):
        code, out, _ = self.reverse(self.build("App One", script="#!/bin/sh\n"))
        self.assertEqual(code, 0, out)
        folder = self.root / "out" / "App-One"
        bom = (folder / "bom.txt").read_text()
        self.assertIn("100644\t0\t0\t3\t./Library/My Dir/a file.txt", bom)
        # Files this process creates carry com.apple.provenance, which pkgbuild
        # may pack as ._ AppleDouble entries; the rollup must hold either way.
        rollup = (folder / "chown-entries.txt").read_text().splitlines()
        self.assertIn("OWN\tLibrary\t0:0", rollup)
        self.assertTrue(all(line.endswith("\t0:0") for line in rollup), rollup)
        blueprint = (folder / "blueprint.conf").read_text()
        for line in (
            "chown_block_needed=true",
            "scripts=postinstall ",
            "pkg_id=io.example.t",
        ):
            self.assertIn(line, blueprint)
        self.assertTrue(os.access(folder / "scripts" / "postinstall", os.X_OK))
        self.assertFalse((folder / ".expanded").exists())

    @unittest.skipIf(os.geteuid() == 0, "tests the unprivileged path")
    def test_reverse_notes_a_bom_owned_by_the_invoking_user(self):  # AC-14.4
        code, out, _ = self.reverse(self.build("mine", preserve=True))
        self.assertEqual(code, 0, out)
        self.assertIn(f"BOM records all files as uid {os.getuid()}", out)

    def test_reverse_refuses_multi_component_and_existing_output(self):
        one, two = self.build("one"), self.build("two", ident="io.example.two")
        dist = self.root / "dist.pkg"
        subprocess.run(
            ["productbuild", "--quiet", "--package", str(one), "--package", str(two)]
            + [str(dist)],
            check=True,
        )
        self.assertEqual(self.reverse(dist)[0], 3)
        self.assertEqual(self.reverse(dist)[0], 2)  # output left from the first run

    def test_reverse_proceeds_with_a_single_component_distribution(self):
        one = self.build("one")
        dist = self.root / "single.pkg"
        subprocess.run(
            ["productbuild", "--quiet", "--package", str(one), str(dist)], check=True
        )
        code, out, errs = self.reverse(dist)
        self.assertEqual(code, 0, out + errs)
        self.assertIn("Distribution wrapper around a single component", errs)
        self.assertIn(
            "pkg_kind=distribution",
            (self.root / "out/single/blueprint.conf").read_text(),
        )


if __name__ == "__main__":
    unittest.main()
