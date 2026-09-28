# test_resolution.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""FR-05 (processors in order), FR-06 (resolution, both views) and FR-07 (catalogue)."""

import unittest
from pathlib import Path

import yaml
from helpers import KIT_ROOT, FixtureCase, download, pkg
from recipekit import RecipeSet, catalogue


def findings(recipes: RecipeSet) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for f in recipes.all_findings():
        out.setdefault(f.code, []).append(f.message)
    return out


class ProcessorOrderTest(FixtureCase):
    def test_ac_05_1_order_and_arguments_by_name(self):
        folder = self.pair(
            "App",
            download(
                "App",
                process="""
            - Processor: URLDownloader
              Arguments:
                url: https://example.com/App.dmg
            - Processor: EndOfCheckPhase
            """,
            ),
            pkg(
                "App",
                inputs="PKG_ID: com.acmefruit.pkg.App",
                process="""
            - Processor: PkgCreator
              Arguments:
                pkg_request:
                  pkgname: "Acme_%NAME%"
                  id: "%PKG_ID%"
            """,
            ),
        )
        steps = RecipeSet.load(folder).pairs()[0].steps()
        self.assertEqual(
            [s.processor for s in steps],
            ["URLDownloader", "EndOfCheckPhase", "PkgCreator"],
        )
        self.assertEqual(steps[2].args["pkg_request"]["pkgname"], "Acme_%NAME%")

    def test_ac_05_3_shared_processors_keep_their_reference(self):
        folder = self.pair(
            "App",
            download(
                "App",
                process="""
            - Processor: com.github.someone.shared/VersionSplitter
            """,
            ),
        )
        step = RecipeSet.load(folder).pairs()[0].steps()[0]
        self.assertTrue(step.is_shared)
        self.assertFalse(catalogue.is_known(step.processor))


class ResolutionTest(FixtureCase):
    def test_ac_06_1_file_url_resolves_through_input(self):
        folder = self.pair(
            "App",
            download(
                "App",
                inputs="""
            VENDOR_CACHE_ROOT: /tmp/vendor_cache
            DOWNLOAD_URL: "file://%VENDOR_CACHE_ROOT%/Acme/App/App.dmg"
            """,
                process="""
            - Processor: URLDownloader
              Arguments:
                url: "%DOWNLOAD_URL%"
            """,
            ),
        )
        pair = RecipeSet.load(folder).pairs()[0]
        self.assertEqual(
            pair.resolve("%DOWNLOAD_URL%"), "file:///tmp/vendor_cache/Acme/App/App.dmg"
        )

    def test_processor_set_variables_resolve_symbolically_and_only_after_their_step(
        self,
    ):
        folder = self.pair(
            "App",
            download(
                "App",
                process="""
            - Processor: URLDownloader
              Arguments:
                url: https://example.com/App.zip
            """,
            ),
        )
        pair = RecipeSet.load(folder).pairs()[0]
        self.assertEqual(pair.resolve("%pathname%"), "<set by URLDownloader: pathname>")
        self.assertEqual(pair.resolve("%pathname%", before=0), "%pathname%")
        self.assertEqual(pair.resolve("%RECIPE_CACHE_DIR%/x"), "%RECIPE_CACHE_DIR%/x")

    def test_child_input_overrides_parent_and_harness_adds_overrides(self):
        folder = self.pair(
            "App",
            download("App", inputs="LEVEL: parent"),
            pkg("App", inputs="LEVEL: child"),
        )
        self.write(folder, ".overrides", "LEVEL=harness\nEXTRA=1\n")
        pair = RecipeSet.load(folder).pairs()[0]
        self.assertEqual(pair.resolve("%LEVEL%"), "child")
        self.assertEqual(pair.resolve("%LEVEL%", view="harness"), "harness")
        self.assertEqual(pair.resolve("%EXTRA%"), "%EXTRA%")

    def test_ac_06_2_undeclared_variable(self):
        folder = self.pair(
            "App",
            download(
                "App",
                process="""
            - Processor: URLDownloader
              Arguments:
                url: "%NOWHERE%"
            """,
            ),
        )
        self.assertIn("undeclared_variable", findings(RecipeSet.load(folder)))

    def test_ac_06_3_overrides_only_is_harness_supplied_not_an_error(self):
        folder = self.pair(
            "App",
            pkg_text=pkg(
                "App",
                process="""
            - Processor: PkgCreator
              Arguments:
                pkg_request:
                  version: "%version%"
            """,
            ),
        )
        self.write(folder, ".overrides", "version=1.0\n")
        found = findings(RecipeSet.load(folder))
        self.assertIn("harness_supplied", found)
        self.assertNotIn("undeclared_variable", found)

    def test_ac_06_4_used_before_set(self):
        folder = self.pair(
            "App",
            download(
                "App",
                process="""
            - Processor: URLDownloader
              Arguments:
                url: https://example.com/App.dmg
                filename: "App-%version%.dmg"
            - Processor: Versioner
              Arguments:
                input_plist_path: "%pathname%/App.app/Contents/Info.plist"
            """,
            ),
        )
        self.assertIn("used_before_set", findings(RecipeSet.load(folder)))

    def test_ac_06_5_unknown_processor_makes_later_variables_unverifiable(self):
        folder = self.pair(
            "App",
            download(
                "App",
                process="""
            - Processor: com.github.someone.shared/MagicVersioner
            - Processor: URLDownloader
              Arguments:
                url: "https://example.com/App-%magic_version%.dmg"
            """,
            ),
        )
        found = findings(RecipeSet.load(folder))
        self.assertIn("unverifiable", found)
        self.assertIn("unknown_processor", found)
        self.assertNotIn("undeclared_variable", found)

    def test_url_text_searcher_named_groups_from_an_input_pattern(self):
        folder = self.pair(
            "App",
            download(
                "App",
                inputs=r"""
            SEARCH_PATTERN: "(?P<url>https://example\\.com/App-[0-9.]+\\.dmg)"
            """,
                process="""
            - Processor: URLTextSearcher
              Arguments:
                url: https://example.com/download
                re_pattern: "%SEARCH_PATTERN%"
            - Processor: URLDownloader
              Arguments:
                url: "%url%"
            """,
            ),
        )
        self.assertEqual(findings(RecipeSet.load(folder)), {})


class CatalogueTest(unittest.TestCase):
    def test_ac_07_1_every_processor_in_the_kit_has_an_entry(self):
        used = set()
        for base in ("customer/acme/output/recipes", "templates"):
            for path in (KIT_ROOT / base).rglob("*.recipe.yaml"):
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                for step in data.get("Process") or []:
                    if isinstance(step, dict) and "Processor" in step:
                        used.add(str(step["Processor"]))
        missing = sorted(
            p for p in used if not catalogue.is_shared(p) and not catalogue.is_known(p)
        )
        self.assertEqual(missing, [])

    def test_url_downloader_does_not_set_version(self):
        self.assertNotIn("version", catalogue.outputs("URLDownloader", {}, str))
        self.assertIn("pathname", catalogue.outputs("URLDownloader", {}, str))

    def test_versioner_output_var_name(self):
        self.assertIn(
            "app_version",
            catalogue.outputs("Versioner", {"output_var_name": "app_version"}, str),
        )


class AcmeTest(unittest.TestCase):
    def test_the_acme_repo_has_no_findings(self):
        recipes = RecipeSet.load_repo(Path(KIT_ROOT) / "customer/acme/output")
        self.assertEqual([f.as_dict() for f in recipes.all_findings()], [])


if __name__ == "__main__":
    unittest.main()
