# test_rr_batch.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""recipekit.rr_batch (specs/rr-batch/01-batch-definitions.md): CSV parsing, the
status filter, finding the recipes Recipe Robot reports, and the renaming that
replaced rr-rename-postprocess.sh. The recipe text below is real Recipe Robot
2.5.0 output (Raspberry Pi Imager), trimmed."""

import unittest

from helpers import FixtureCase
from recipekit.rr_batch import (
    Row,
    normalize_text,
    parse_line,
    reported_recipes,
    skip_reason,
)

DOWNLOAD = """Comment: Created with Recipe Robot v2.5.0
Description: Downloads the latest version of Raspberry Pi Imager.
Identifier: com.acmefruit.autopkg.download.RaspberryPiImager
Input:
  NAME: Raspberry Pi Imager
MinimumVersion: '2.3'
Process:
- Arguments:
    github_repo: raspberrypi/rpi-imager
  Processor: GitHubReleasesInfoProvider
"""
PKG = """Comment: Created with Recipe Robot v2.5.0
Identifier: com.acmefruit.autopkg.pkg.RaspberryPiImager
Input:
  NAME: Raspberry Pi Imager
MinimumVersion: '2.3'
ParentRecipe: com.acmefruit.autopkg.download.RaspberryPiImager
Process:
- Processor: AppPkgCreator
"""


class ParseTest(unittest.TestCase):
    def test_fields_quotes_and_commas(self):
        cases = {
            '"","slack","Slack","https://slack.com/downloads/mac"': Row(
                "", "slack", "Slack", "https://slack.com/downloads/mac"
            ),
            '"TEST", "ms" ,"Word, Excel","https://x/?a=1&b=2"': Row(
                "TEST", "ms", "Word, Excel", "https://x/?a=1&b=2"
            ),
            ",vendor,App,https://x/app.dmg": Row(
                "", "vendor", "App", "https://x/app.dmg"
            ),
        }
        for line, row in cases.items():
            with self.subTest(line):
                self.assertEqual(parse_line(line), row)

    def test_wrong_field_counts(self):
        self.assertIsNone(parse_line('"","a","b"'))
        self.assertIsNone(parse_line('"","a","b","c","d"'))


class StatusTest(FixtureCase):
    def test_status_filter(self):
        (self.root / "vendor" / "Existing").mkdir(parents=True)
        cases = {
            ("DONE", "App"): "DONE",
            ("SKIP", "App"): "SKIP-status",
            ("", "App"): "",
            ("TEST", "App"): "",
            ("TEST", "Existing"): "TEST-existing",
            ("MAYBE", "App"): "unrecognized",
        }
        for (status, name), reason in cases.items():
            with self.subTest(status=status, name=name):
                row = Row(status, "vendor", name, "https://x")
                self.assertEqual(skip_reason(row, self.root), reason)


class DiscoveryTest(FixtureCase):
    def test_reported_paths_are_found_whatever_the_folder(self):
        folder = self.root / "RASPBERRY PI LTD"
        folder.mkdir()
        made = [
            folder / "Raspberry Pi Imager.download.recipe.yaml",
            folder / "x.pkg.recipe",
        ]
        for path in made:
            path.write_text("x")
        output = (
            "Processing: https://github.com/raspberrypi/rpi-imager\x1b[0m\n"
            f"Generating download recipe...\x1b[0m\n    {made[0]}\x1b[0m\n"
            f"Generating pkg recipe...\x1b[0m\n    {made[1]}\x1b[0m\n"
            f"    {folder / 'gone.download.recipe.yaml'}\n"  # reported but missing
            "You've created 2 recipes\n"
        )
        self.assertEqual(reported_recipes(output), made)


class RenameTest(unittest.TestCase):
    def test_download(self):
        text = normalize_text(
            DOWNLOAD, "download", "Raspberry-Pi-Imager", "com.acmefruit.autopkg"
        )
        self.assertIn(
            "Identifier: com.acmefruit.autopkg.download.Raspberry-Pi-Imager\n", text
        )
        self.assertIn("  NAME: Raspberry-Pi-Imager\n", text)
        self.assertIn("github_repo: raspberrypi/rpi-imager", text)  # the rest unchanged
        self.assertNotIn("ParentRecipe", text)

    def test_pkg_and_a_different_prefix(self):
        # Recipe Robot set up with another prefix (the bash version's .pkg.pkg. case).
        text = PKG.replace("com.acmefruit.autopkg.", "com.acmefruit.autopkg.pkg.")
        text = normalize_text(
            text, "pkg", "Raspberry-Pi-Imager", "com.acmefruit.autopkg"
        )
        self.assertIn(
            "Identifier: com.acmefruit.autopkg.pkg.Raspberry-Pi-Imager\n", text
        )
        self.assertIn(
            "ParentRecipe: com.acmefruit.autopkg.download.Raspberry-Pi-Imager\n", text
        )
        self.assertEqual(text.count("NAME: Raspberry-Pi-Imager"), 1)

    def test_only_the_input_name_changes(self):
        text = DOWNLOAD + "- Arguments:\n    NAME: keep-this\n"
        text = normalize_text(text, "download", "App", "com.acmefruit.autopkg")
        self.assertIn("    NAME: keep-this", text)


if __name__ == "__main__":
    unittest.main()
