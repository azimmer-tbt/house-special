# test_facts.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""FR-08 (AC-08.1): every derived fact on a minimal fixture pair."""

import unittest

from helpers import FixtureCase, download, pkg
from recipekit import RecipeSet, pair_facts

DL = """
- Processor: URLDownloader
  Arguments:
    url: "{url}"
    filename: "{filename}"
"""


class FactsCase(FixtureCase):
    def facts_for(
        self, download_text: str, pkg_text: str = "", overrides: str = ""
    ) -> dict:
        folder = self.pair("App", download_text, pkg_text or pkg("App"))
        if overrides:
            self.write(folder, ".overrides", overrides)
        return pair_facts(RecipeSet.load(folder).pairs()[0])


class SourceTest(FactsCase):
    def test_sources(self):
        cases = {
            "sparkle": "- Processor: SparkleUpdateInfoProvider",
            "github_release": "- Processor: GitHubReleasesInfoProvider",
            "url_scraped": "- Processor: URLTextSearcher",
            "github_archive": DL.format(
                url="https://github.com/o/r/archive/refs/heads/main.zip",
                filename="a.zip",
            ),
            "url_stable": DL.format(url="https://example.com/latest", filename="a.dmg"),
            "vendor_cache": DL.format(
                url="file:///tmp/vendor_cache/a.dmg", filename="a.dmg"
            ),
            "recipe_dir": """
                - Processor: Copier
                  Arguments:
                    source_path: "%RECIPE_DIR%/payload"
                    destination_path: "%RECIPE_CACHE_DIR%/payload"
                """,
            "none": "- Processor: EndOfCheckPhase",
        }
        for expected, process in cases.items():
            with self.subTest(expected):
                self.reset()
                f = self.facts_for(download("App", process=process))
                self.assertEqual(f["source"]["value"], expected)

    def test_evidence_names_recipe_and_step(self):
        f = self.facts_for(
            download("App", process=DL.format(url="https://x/a.dmg", filename="a.dmg"))
        )
        ev = f["source"]["evidence"]
        self.assertEqual(
            (ev["recipe"], ev["step"], ev["processor"]),
            ("App.download.recipe.yaml", 0, "URLDownloader"),
        )


class ArtifactTest(FactsCase):
    def test_artifacts(self):
        for filename, kind in (
            ("a.pkg", "pkg"),
            ("a.dmg", "dmg"),
            ("a.zip", "zip"),
            ("a.tar.gz", "tar"),
            ("a", "unknown"),
        ):
            with self.subTest(filename):
                self.reset()
                f = self.facts_for(
                    download(
                        "App", process=DL.format(url="https://x/y", filename=filename)
                    )
                )
                self.assertEqual(f["artifact"]["value"], kind)

    def test_github_asset_regex(self):
        f = self.facts_for(
            download(
                "App",
                process="""
            - Processor: GitHubReleasesInfoProvider
              Arguments:
                asset_regex: "^App-[\\\\d.]+\\\\.pkg$"
            - Processor: URLDownloader
            """,
            )
        )
        self.assertEqual(f["artifact"]["value"], "pkg")


class SignatureTest(FactsCase):
    def verifier(self, args: str, inputs: str = "") -> dict:
        return self.facts_for(
            download(
                "App",
                inputs=inputs,
                process=f"""
            - Processor: CodeSignatureVerifier
              Arguments:
            {args}
            """,
            )
        )["signature"]

    def test_requirement_pinning_the_team(self):
        sig = self.verifier(
            '    requirement: identifier "x" and '
            'certificate leaf[subject.OU] = "ABCDE12345"'
        )
        self.assertEqual((sig["value"], sig["pins_team_id"]), ("requirement", True))

    def test_identifier_only_and_declared_no_team(self):
        sig = self.verifier(
            '    requirement: identifier "io.example.app"',
            'teamid: "UNSIGNED_NO_TEAMID"',
        )
        self.assertEqual(
            (sig["value"], sig["declared_no_team"]), ("identifier_only", True)
        )

    def test_authority_names_with_and_without_the_chain(self):
        full = self.verifier(
            """    expected_authority_names:
                  - "Developer ID Installer: Example (ABCDE12345)"
                  - Developer ID Certification Authority
                  - Apple Root CA"""
        )
        self.assertEqual(
            (full["value"], full["chain_listed"]), ("authority_names", True)
        )
        self.reset()
        leaf = self.verifier(
            """    expected_authority_names:
                  - "Developer ID Installer: Example (ABCDE12345)\""""
        )
        self.assertFalse(leaf["chain_listed"])

    def test_declared_unsigned_and_missing(self):
        f = self.facts_for(download("App", inputs="NO_CODE_SIGNATURE_REQUIRED: true"))
        self.assertEqual(f["signature"]["value"], "declared_unsigned")
        self.reset()
        self.assertEqual(
            self.facts_for(download("App"))["signature"]["value"], "missing"
        )


class OutputAndVersionTest(FactsCase):
    def test_outputs_and_pkgname(self):
        creator = pkg(
            "App",
            process="""
            - Processor: PkgCreator
              Arguments:
                pkg_request:
                  pkgname: "Acme_%NAME%"
            """,
        )
        f = self.facts_for(download("App"), creator)
        self.assertEqual(f["output"]["value"], "PkgCreator")
        self.assertEqual(f["pkgname"]["value"], "Acme_App")
        for text, value in (
            ("- Processor: PkgCopier", "PkgCopier"),
            (
                "- Processor: Copier\n  Arguments:\n"
                '    destination_path: "%RECIPE_CACHE_DIR%/%NAME%.pkg"',
                "Copier",
            ),
            ("- Processor: EndOfCheckPhase", "none"),
        ):
            with self.subTest(value):
                self.reset()
                self.assertEqual(
                    self.facts_for(download("App"), pkg("App", process=text))["output"][
                        "value"
                    ],
                    value,
                )

    def test_version_sources(self):
        f = self.facts_for(
            download("App", process="- Processor: GitHubReleasesInfoProvider")
        )
        self.assertEqual(
            (f["version_source"]["value"], f["version_source"]["processor"]),
            ("processor", "GitHubReleasesInfoProvider"),
        )
        self.reset()
        f = self.facts_for(download("App", inputs='version: "1.0"'))
        self.assertEqual(
            (f["version_source"]["value"], f["version_source"]["pinned"]),
            ("input", "1.0"),
        )
        self.reset()
        f = self.facts_for(download("App"), overrides="version=1.0\n")
        self.assertEqual(f["version_source"]["value"], "harness_only")
        self.reset()
        self.assertEqual(
            self.facts_for(download("App"))["version_source"]["value"], "none"
        )


class PayloadTest(FactsCase):
    def test_payload_from_the_recipe_folder_extras_scripts_and_parents(self):
        folder = self.pair(
            "App",
            download(
                "App",
                process="""
            - Processor: Copier
              Arguments:
                source_path: "%RECIPE_DIR%/payload"
                destination_path: "%RECIPE_CACHE_DIR%/payload"
            """,
            ),
            pkg(
                "App",
                process="""
            - Processor: Copier
              Arguments:
                source_path: "%pathname%/App.app"
                destination_path: "%RECIPE_CACHE_DIR%/payload/Applications/App.app"
            - Processor: PkgCreator
              Arguments:
                pkg_request:
                  pkgroot: "%RECIPE_CACHE_DIR%/payload"
                  scripts: "%RECIPE_DIR%/scripts"
                  chown:
                    - path: Library
                      user: root
                      group: wheel
                    - path: Applications
                      user: root
                      group: admin
            """,
            ),
        )
        self.write(
            folder, "payload/Library/LaunchAgents/com.acmefruit.app.plist", "<plist/>"
        )
        self.write(folder, "scripts/postinstall", "#!/bin/bash\n")
        f = pair_facts(RecipeSet.load(folder).pairs()[0])
        self.assertIn("Applications/App.app", f["payload_paths"])
        self.assertTrue(f["installs_app"])
        self.assertTrue(f["payload_complete"])
        self.assertEqual(f["extras"], ["Library/LaunchAgents/com.acmefruit.app.plist"])
        self.assertEqual(f["scripts"]["scripts"], ["postinstall"])
        self.assertEqual(
            sorted(p["path"] for p in f["pkgroot_parents"]), ["Applications", "Library"]
        )

    def test_unpacked_payload_is_incomplete(self):
        f = self.facts_for(
            download(
                "App",
                process="""
            - Processor: Unarchiver
              Arguments:
                destination_path: "%RECIPE_CACHE_DIR%/root"
            """,
            ),
            pkg(
                "App",
                process="""
            - Processor: PkgCreator
              Arguments:
                pkg_request:
                  pkgroot: "%RECIPE_CACHE_DIR%/root"
            """,
            ),
        )
        self.assertFalse(f["payload_complete"])

    def test_identity_and_claimed_are_reported_raw(self):
        f = self.facts_for("Comment: Pattern 9z — made up\n" + download("App"))
        self.assertEqual(
            f["claimed"]["App.download.recipe.yaml"], "Pattern 9z — made up"
        )
        self.assertEqual(
            f["identity"][1]["ParentRecipe"], "com.acmefruit.autopkg.download.App"
        )


if __name__ == "__main__":
    unittest.main()


class DmgPathArtifactTest(FactsCase):
    def test_a_dmg_named_in_a_path_is_the_artifact(self):
        process = (
            "- Processor: URLDownloader\n  Arguments:\n    url: https://x/y\n"
            "- Processor: Copier\n  Arguments:\n"
            '    source_path: "%RECIPE_CACHE_DIR%/downloads/%NAME%.dmg/App.app"'
        )
        f = self.facts_for(download("App", process=process))
        self.assertEqual(f["artifact"]["value"], "dmg")
