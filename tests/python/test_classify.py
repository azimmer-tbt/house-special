# test_classify.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""specs/analysis/classify-recipe/01-classify-recipe.md."""

import contextlib
import io
import json
import unittest

from helpers import KIT_ROOT, FixtureCase, download, pkg
from recipekit import RecipeSet
from recipekit.classify import claimed, classify, main

GITHUB = "- Processor: GitHubReleasesInfoProvider\n- Processor: URLDownloader"
COPY_PKG = "- Processor: PkgCopier"
BUILD = """
- Processor: PkgCreator
  Arguments:
    pkg_request:
      pkgroot: "%RECIPE_CACHE_DIR%/root"
"""
BUILD_SCRIPTS = """
- Processor: PkgCreator
  Arguments:
    pkg_request:
      pkgroot: "%RECIPE_CACHE_DIR%/root"
      scripts: "%RECIPE_DIR%/scripts"
"""
UNSIGNED = "NO_CODE_SIGNATURE_REQUIRED: true"
UNPACK = """
- Processor: Unarchiver
  Arguments:
    destination_path: "%RECIPE_CACHE_DIR%/root"
"""


def dl(url: str, filename: str) -> str:
    return (
        f'- Processor: URLDownloader\n  Arguments:\n    url: "{url}"\n'
        f'    filename: "{filename}"'
    )


def vendor(filename: str) -> str:
    return dl(f"file:///tmp/vendor_cache/Acme/App/{filename}", filename)


class TableTest(FixtureCase):
    """AC-5.2: one fixture per row of the FR-2 table."""

    def label(self, dl_inputs: str, dl_process: str, pkg_process: str) -> str:
        folder = self.pair(
            "App",
            download("App", dl_inputs, dl_process),
            pkg("App", process=pkg_process),
        )
        return classify(RecipeSet.load(folder).pairs()[0]).label

    def test_rows(self):
        rows = [
            (
                "1a",
                "",
                "- Processor: SparkleUpdateInfoProvider\n- Processor: URLDownloader",
                COPY_PKG,
            ),
            (
                "1b",
                "",
                "- Processor: SparkleUpdateInfoProvider\n- Processor: URLDownloader",
                BUILD,
            ),
            ("2a", "", GITHUB, COPY_PKG),
            ("2b", "", GITHUB, BUILD),
            ("2c", "", GITHUB, BUILD_SCRIPTS),
            (
                "2d",
                "",
                dl("https://github.com/o/r/archive/refs/heads/main.zip", "a.zip"),
                BUILD,
            ),
            (
                "5",
                "",
                dl("https://go.microsoft.com/fwlink/?linkid=1", "App.pkg"),
                COPY_PKG,
            ),
            (
                "3a",
                "",
                dl("https://example.com/downloads/App.pkg", "App.pkg"),
                COPY_PKG,
            ),
            ("3b", "", dl("https://example.com/latest", "App.dmg"), BUILD),
            (
                "3c",
                "",
                "- Processor: URLTextSearcher\n" + dl("%match%", "App.dmg"),
                BUILD,
            ),
            ("4a", "", vendor("App.pkg"), COPY_PKG),
            (
                "4b",
                "",
                vendor("App.pkg"),
                "- Processor: Copier\n  Arguments:\n"
                '    destination_path: "%RECIPE_CACHE_DIR%/App.pkg"',
            ),
            ("7", UNSIGNED, vendor("App.dmg"), BUILD),
            ("4d", "", vendor("App.dmg"), BUILD_SCRIPTS),
            ("4c", "", vendor("App.dmg"), BUILD),
            ("4e", "", vendor("App.zip"), BUILD),
            ("6b", UNSIGNED, vendor("payload.zip") + UNPACK, BUILD_SCRIPTS),
            ("6a", UNSIGNED, vendor("payload.zip") + UNPACK, BUILD),
            ("!", "", GITHUB, "- Processor: AppPkgCreator"),
        ]
        for want, inputs, dl_process, pkg_process in rows:
            with self.subTest(want):
                self.reset()
                self.assertEqual(self.label(inputs, dl_process, pkg_process), want)

    def test_pattern_6d_and_6c(self):
        payloadless = """
            - Processor: PkgRootCreator
              Arguments:
                pkgroot: "%RECIPE_CACHE_DIR%/root"
            - Processor: PkgCreator
              Arguments:
                pkg_request:
                  pkgroot: "%RECIPE_CACHE_DIR%/root"
            """
        self.assertEqual(
            self.label(UNSIGNED, "- Processor: EndOfCheckPhase", payloadless), "6d"
        )
        self.reset()
        single = """
            - Processor: PkgCreator
              Arguments:
                pkg_request:
                  pkgroot: "%RECIPE_CACHE_DIR%/root"
                  chown:
                    - path: private/etc/example.conf
                      user: root
                      group: wheel
                      mode: "0400"
            """
        self.assertEqual(self.label(UNSIGNED, vendor("payload.zip"), single), "6c")

    def test_uncertain_rows_list_their_alternatives(self):
        folder = self.pair(
            "App",
            download("App", UNSIGNED, vendor("App.dmg")),
            pkg("App", process=BUILD),
        )
        result = classify(RecipeSet.load(folder).pairs()[0])
        self.assertEqual((result.label, result.alternatives), ("7", ["4c"]))
        self.assertTrue(result.question)


class ClaimTest(FixtureCase):
    def test_ac_3_1_no_claim(self):
        folder = self.pair("App")
        self.assertIsNone(claimed(RecipeSet.load(folder).pairs()[0]))

    def test_claim_is_read_but_never_decides(self):
        folder = self.pair(
            "App",
            "Comment: Pattern 4d — says so\n" + download("App", "", GITHUB),
            pkg("App", process=BUILD),
        )
        pair = RecipeSet.load(folder).pairs()[0]
        self.assertEqual(claimed(pair), "4d")
        self.assertEqual(classify(pair).label, "2b")


class AccuracyTest(unittest.TestCase):
    """AC-5.1: every shipped example classifies as its Comment claims."""

    def test_ac_5_1_every_example_matches_its_claim(self):
        folders = sorted((KIT_ROOT / "customer/acme/output/recipes").glob("*/*"))
        folders += sorted((KIT_ROOT / "templates").glob("*/example-*"))
        misses = []
        for folder in folders:
            for pair in RecipeSet.load(folder).pairs():
                got, claim = classify(pair).label, claimed(pair)
                if got != claim:
                    misses.append(f"{folder.name}: got {got}, claims {claim}")
        self.assertEqual(misses, [])
        self.assertGreaterEqual(len(folders), 26)


class CliTest(FixtureCase):
    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            try:
                code = main(list(argv))
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue()

    def test_ac_1_1_and_1_4(self):
        code, out = self.run_main(
            "--output",
            "json",
            str(
                self.pair("App", download("App", "", GITHUB), pkg("App", process=BUILD))
            ),
        )
        self.assertEqual((code, json.loads(out)["classification"]), (0, "2b"))
        self.assertEqual(self.run_main(str(self.root / "nope"))[0], 1)
        self.assertEqual(self.run_main(str(self.folder("recipes/Acme/Empty")))[0], 1)
        self.assertEqual(self.run_main()[0], 2)

    def test_ac_1_3_interactive_without_a_terminal_just_prints(self):
        folder = self.pair(
            "App",
            download("App", UNSIGNED, vendor("App.dmg")),
            pkg("App", process=BUILD),
        )
        code, out = self.run_main("--interactive", str(folder))
        self.assertEqual(code, 0)
        self.assertIn("uncertain: also 4c", out)


if __name__ == "__main__":
    unittest.main()
