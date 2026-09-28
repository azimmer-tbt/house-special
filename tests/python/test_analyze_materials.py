# test_analyze_materials.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""recipekit.analyze_materials
(specs/analysis/analyze-materials/01-analyze-materials.md): the scan, matching,
targets loading, and the command end to end."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

from helpers import KIT_ROOT, FixtureCase
from recipekit import analyze_materials
from recipekit.analyze_materials import candidates_for, extension, match, scan

TARGETS = """recipes:
- app_name: Orchard-Analytics
  vendor: OrchardLabs
  pattern: "4d"
- app_name: Pearcleaner
  vendor: Alienator88
  pattern: "2b"
- app_name: Nothing-Here
  vendor: Nobody
  pattern: "5"
"""


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = analyze_materials.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class ShareCase(FixtureCase):
    def setUp(self):
        super().setUp()
        self.share = self.root / "share"
        self.put("OrchardLabs/Orchard/Orchard Analytics 7.2.dmg", 3000)
        self.put("OrchardLabs/Orchard/license.lic")
        self.put("Alienator88/Pearcleaner/Pearcleaner-5.4.3.ZIP")
        self.put("Misc/Unrelated-Tool-3.1.4.tar.gz")
        self.put("top-level.pkg")
        self.targets = self.root / "end_result.yaml"
        self.targets.write_text(TARGETS)

    def put(self, rel: str, size: int = 10) -> Path:
        path = self.share / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * size)
        return path

    def names(self, files):
        return sorted(f["basename"] for f in files)


class ScanTest(ShareCase):
    def test_ac_02_1_and_2_distributables_only(self):
        self.assertEqual(
            self.names(scan(self.share)),
            [
                "Orchard Analytics 7.2.dmg",
                "Pearcleaner-5.4.3.ZIP",
                "Unrelated-Tool-3.1.4.tar.gz",
                "top-level.pkg",
            ],
        )

    def test_extensions_ignore_case_and_prefer_the_longest(self):
        cases = {"a.tar.gz": "tar.gz", "a.TGZ": "tar.gz", "a.tbz2": "tar.bz2"}
        cases.update({"a.PKG": "pkg", "a.gz": "", "a.pdf": ""})
        for name, kind in cases.items():
            with self.subTest(name):
                self.assertEqual(extension(name), kind)

    def test_ac_01_4_depth(self):
        self.assertEqual(self.names(scan(self.share, 1)), ["top-level.pkg"])
        self.assertEqual(len(scan(self.share, 2)), 2)  # + Misc/Unrelated-Tool
        self.assertEqual(len(scan(self.share, 3)), 4)

    def test_vendor_hint_is_two_levels_up_and_inside_the_share(self):
        hints = {f["basename"]: f["vendor_hint"] for f in scan(self.share)}
        self.assertEqual(hints["Orchard Analytics 7.2.dmg"], "OrchardLabs")
        self.assertEqual(hints["top-level.pkg"], "")
        self.put("OneLevel/file.dmg")
        hints = {f["basename"]: f["vendor_hint"] for f in scan(self.share)}
        self.assertEqual(hints["file.dmg"], "")  # not the share's own name

    def test_symlinks_are_followed_with_real_sizes_and_no_loops(self):
        outside = self.root / "elsewhere" / "Big.dmg"
        outside.parent.mkdir()
        outside.write_bytes(b"x" * 5000)
        (self.share / "Links").mkdir()
        os.symlink(outside, self.share / "Links" / "Big.dmg")
        os.symlink(self.share, self.share / "Links" / "loop")
        files = {f["basename"]: f for f in scan(self.share)}
        self.assertEqual(files["Big.dmg"]["size"], 5000)
        self.assertEqual(len(files), 5)


class MatchTest(ShareCase):
    def test_ac_03_1_name_and_vendor_is_strong(self):
        files = scan(self.share)
        cands = candidates_for(
            {"app_name": "Orchard-Analytics", "vendor": "OrchardLabs"}, files
        )
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["match_strength"], "strong")
        self.assertEqual(
            cands[0]["match_signals"],
            [
                "app_name_match",
                "vendor_match",
                "version_in_filename",
                "archivable_file",
            ],
        )

    def test_a_version_alone_is_not_a_match(self):
        cands = candidates_for({"app_name": "Tool", "vendor": "X"}, scan(self.share))
        self.assertEqual(
            [c["match_strength"] for c in cands], ["moderate"]
        )  # "Tool" in the name
        cands = candidates_for({"app_name": "Zzz", "vendor": "X"}, scan(self.share))
        self.assertEqual(cands, [])

    def test_ac_03_2_to_4_summary_unmatched_and_order(self):
        self.put("Other/Pearcleaner/Pearcleaner.dmg")
        targets = analyze_materials.load_targets(self.targets)
        matches, unmatched, summary = match(targets, scan(self.share))
        pear = matches[1]["candidates"]
        self.assertEqual([c["match_strength"] for c in pear], ["strong", "moderate"])
        self.assertEqual(matches[2]["candidates"], [])
        self.assertEqual(
            sorted(os.path.basename(f["path"]) for f in unmatched),
            ["Unrelated-Tool-3.1.4.tar.gz", "top-level.pkg"],
        )
        self.assertEqual(
            summary,
            {
                "total_targets": 3,
                "targets_with_candidates": 2,
                "targets_without_candidates": 1,
                "unmatched_source_files": 2,
            },
        )


class CommandTest(ShareCase):
    def test_ac_01_2_json_is_pure_on_stdout(self):
        code, out, err = run(
            str(self.share), "--targets", str(self.targets), "--output", "json"
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["files_found"], 4)
        self.assertEqual(data["unmatched"], 2)
        self.assertEqual(len(data["unmatched_files"]), 2)
        self.assertIn("=== Scanning", err)

    def test_text_lists_unmatched_files(self):
        code, out, _ = run(str(self.share), "--targets", str(self.targets))
        self.assertIn("=== Unmatched source files ===", out)
        self.assertIn("OrchardLabs/Orchard-Analytics (1 candidate)", out)
        self.assertIn("Nobody/Nothing-Here (0 candidates)", out)

    def test_usage_errors_exit_2(self):
        bad = self.root / "bad.yaml"
        bad.write_text("recipes: [\n")
        cases = [
            [str(self.root / "missing")],
            [str(self.share), "--depth", "two"],
            [str(self.share), "--depth", "0"],
            [str(self.share), "--targets", str(self.root / "nope.yaml")],
            [str(self.share), "--targets", str(bad)],
            [str(self.share), "--customer", "nobody-registered"],
            [str(self.share), "--output", "xml"],
        ]
        for argv in cases:
            with self.subTest(argv[1:]):
                self.assertEqual(run(*argv)[0], 2)

    @unittest.skipUnless(shutil.which("pkgbuild"), "macOS only")
    def test_fr_4_packages_are_classified_with_clues(self):
        root = self.root / "pkgroot" / "Demo.app" / "Contents"
        root.mkdir(parents=True)
        (root / "Info").write_text("x\n")
        pkg = self.share / "Acme" / "Demo" / "Acme_Demo.pkg"
        pkg.parent.mkdir(parents=True)
        subprocess.run(
            ["pkgbuild", "--quiet", "--root", str(self.root / "pkgroot")]
            + ["--identifier", "acmedemo2019", "--version", "1", str(pkg)],
            check=True,
        )
        clues = KIT_ROOT / "customer/acme/clues.yaml"
        _, out, _ = run(str(self.share), "--clues", str(clues), "--output", "json")
        files = {f["basename"]: f for f in json.loads(out)["files"]}
        self.assertEqual(
            files["Acme_Demo.pkg"]["classification"]["origin"], "custom-build"
        )
        self.assertTrue(files["Acme_Demo.pkg"]["classifiable"])
        self.assertEqual(
            files["top-level.pkg"]["classification"]["error"][:6], "pkguti"
        )
        self.assertFalse(files["Pearcleaner-5.4.3.ZIP"]["classifiable"])
        _, out, _ = run(str(self.share), "--output", "json")
        self.assertNotIn("classification", json.loads(out)["files"][0])


if __name__ == "__main__":
    unittest.main()
