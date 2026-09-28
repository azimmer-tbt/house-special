# test_loading_and_pairing.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""FR-03 (loading) and FR-04 (pairing by ParentRecipe)."""

import unittest

from helpers import FixtureCase, download, pkg
from recipekit import RecipeSet, pair_facts
from recipekit.loader import read_overrides

GITHUB = """
- Processor: GitHubReleasesInfoProvider
  Arguments:
    github_repo: example/app
    asset_regex: "App-[\\\\d.]+\\\\.dmg$"
- Processor: URLDownloader
  Arguments:
    filename: "%NAME%.dmg"
"""


def codes(recipes: RecipeSet) -> list[str]:
    return sorted(f.code for f in recipes.all_findings())


class LoadingTest(FixtureCase):
    def test_ac_03_1_yaml_and_plist_give_the_same_facts(self):
        a = self.pair("App", download("App", process=GITHUB), rel="yaml/App")
        b = self.pair("App", download("App", process=GITHUB), rel="plist/App")
        self.as_plist(b / "App.download.recipe.yaml")
        self.as_plist(b / "App.pkg.recipe.yaml")
        fa = pair_facts(RecipeSet.load(a).pairs()[0])
        fb = pair_facts(RecipeSet.load(b, audit=True).pairs()[0])
        for key in ("source", "artifact", "signature", "output", "version_source"):
            self.assertEqual(fa[key]["value"], fb[key]["value"], key)

    def test_ac_03_2_invalid_yaml_is_a_finding_with_a_line(self):
        folder = self.pair("App")
        self.write(folder, "App.download.recipe.yaml", "Input:\n  NAME: [unclosed\n")
        recipes = RecipeSet.load(folder)
        bad = [f for f in recipes.all_findings() if f.code == "recipe_invalid"]
        self.assertEqual(len(bad), 1)
        self.assertIsNotNone(bad[0].line)

    def test_ac_03_3_comments_never_change_facts(self):
        plain = self.pair("App", download("App", process=GITHUB), rel="plain/App")
        noisy_text = (
            "# Processor: SparkleUpdateInfoProvider\n# url: file:///x.pkg\n"
            + download("App", process=GITHUB)
        )
        noisy = self.pair("App", noisy_text, rel="noisy/App")
        self.assertEqual(
            pair_facts(RecipeSet.load(plain).pairs()[0])["source"]["value"],
            pair_facts(RecipeSet.load(noisy).pairs()[0])["source"]["value"],
        )

    def test_ac_03_4_plist_in_a_recipe_repo_is_flagged_unless_auditing(self):
        folder = self.pair("App")
        self.as_plist(folder / "App.download.recipe.yaml")
        self.assertIn("plist_recipe", codes(RecipeSet.load(folder)))
        self.assertNotIn("plist_recipe", codes(RecipeSet.load(folder, audit=True)))

    def test_overrides_keep_an_unterminated_last_line_and_skip_comments(self):
        folder = self.folder()
        self.write(
            folder, ".overrides", "# comment\nteamid=ABCDE12345\n\nversion=1.2.3"
        )
        self.assertEqual(
            read_overrides(folder / ".overrides"),
            {"teamid": "ABCDE12345", "version": "1.2.3"},
        )


class PairingTest(FixtureCase):
    def test_ac_04_1_matching_parent_forms_a_pair(self):
        recipes = RecipeSet.load(self.pair("App"))
        pair = recipes.pairs()[0]
        self.assertIsNotNone(pair.download)
        self.assertIsNotNone(pair.pkg)
        self.assertEqual([r.role for r in pair.chain()], ["download", "pkg"])
        self.assertEqual(codes(recipes), [])

    def test_ac_04_2_mismatch_missing_and_incomplete(self):
        other = self.pair("Other")
        wrong = self.pair(
            "App", pkg_text=pkg("App", parent="com.acmefruit.autopkg.download.Other")
        )
        self.assertIn("parent_mismatch", codes(RecipeSet.load(wrong, other)))

        missing = self.pair(
            "Lone",
            pkg_text=pkg("Lone", parent="com.github.someone.download.Lone"),
            rel="recipes/Acme/Lone",
        )
        self.assertIn("parent_missing", codes(RecipeSet.load(missing)))

        half = self.folder("recipes/Acme/Half")
        self.write(half, "Half.download.recipe.yaml", download("Half"))
        self.assertIn("pair_incomplete", codes(RecipeSet.load(half)))

    def test_ac_04_3_pairing_ignores_file_order(self):
        folder = self.folder("recipes/Acme/Many")
        for name in ("Zeta", "Alpha"):
            self.write(folder, f"{name}.download.recipe.yaml", download(name))
            self.write(folder, f"{name}.pkg.recipe.yaml", pkg(name))
        recipes = RecipeSet.load(folder)
        for pair in recipes.pairs():
            self.assertEqual(pair.pkg.parent, pair.download.identifier)
        self.assertEqual(codes(recipes), [])

    def test_ac_04_4_a_parent_elsewhere_on_disk_is_still_missing(self):
        # The parent exists, but only in a folder that wasn't loaded (like a repo
        # added with `autopkg repo-add`). The model never looks there.
        elsewhere = self.folder("RecipeRepos/com.github.someone/App")
        self.write(
            elsewhere,
            "App.download.recipe.yaml",
            download("App").replace("com.acmefruit.autopkg", "com.github.someone"),
        )
        folder = self.folder("recipes/Acme/App")
        self.write(
            folder,
            "App.pkg.recipe.yaml",
            pkg("App", parent="com.github.someone.download.App"),
        )
        self.assertIn("parent_missing", codes(RecipeSet.load(folder)))


if __name__ == "__main__":
    unittest.main()
