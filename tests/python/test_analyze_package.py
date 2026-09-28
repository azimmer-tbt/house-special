# test_analyze_package.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""recipekit.analyze_package (specs/analysis/analyze-package/01-analyze-package.md):
the classifier on hand-made facts, clues loading, and the command end to end on
packages built with pkgbuild/productbuild (skipped where those are missing)."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from helpers import KIT_ROOT, FixtureCase
from recipekit import analyze_package
from recipekit.analyze_package import (
    Clues,
    Facts,
    UsageError,
    classify,
    load_clues,
)

ACME_CLUES = KIT_ROOT / "customer/acme/clues.yaml"
MS = "Developer ID Installer: Microsoft Corporation (UBF8T346G9)"


def facts(**kw) -> Facts:
    kw.setdefault("identifiers", ["com.example.app"])
    return Facts(Path(kw.pop("name", "App.pkg")), **kw)


class ClassifyTest(unittest.TestCase):
    def setUp(self):
        self.acme = load_clues(ACME_CLUES)

    def test_ac_04_1_signed_microsoft_is_high_confidence_vendor(self):
        c = classify(
            facts(
                name="Microsoft_Word_Installer.pkg",
                identifiers=["com.microsoft.package.Microsoft_Word.app"],
                signature="signed",
                authority=MS,
                apps=["Microsoft Word.app"],
            ),
            self.acme,
        )
        self.assertEqual(
            (c.origin, c.confidence, c.pattern), ("vendor-originated", "high", 4)
        )
        self.assertIn("Signing team ID UBF8T346G9 is a known vendor's", c.rationale)

    def test_ac_04_2_unsigned_legacy_org_build_is_high_confidence_custom(self):
        c = classify(
            facts(name="Acme_Banner.pkg", identifiers=["acmebanner20191121"]),
            self.acme,
        )
        self.assertEqual(
            (c.origin, c.confidence, c.pattern), ("custom-build", "medium", 6)
        )
        self.assertIn("Filename contains org code", c.rationale)
        self.assertIn("Identifier contains an org code", c.rationale)
        self.assertIn(
            "Identifier matches the org's legacy in-house identifier pattern",
            c.rationale,
        )

    def test_the_orgs_namespace_counts_as_in_house(self):
        c = classify(
            facts(name="Acme_Tool.pkg", identifiers=["com.acmefruit.pkg.Tool"]),
            self.acme,
            org_domain="com.acmefruit",
        )
        self.assertEqual(c.origin, "custom-build")
        self.assertIn("org's own namespace (com.acmefruit)", c.rationale[0])

    def test_ac_04_3_contradictory_and_weak_signals_are_low(self):
        # The spec's example: vendor-like identifier, unsigned, no .app (2 vs 2).
        c = classify(facts(identifiers=["com.example.app"]), Clues())
        self.assertEqual(
            (c.origin, c.confidence, c.pattern), ("unknown", "low", "other")
        )
        # Strong signals both ways and a tied score.
        f = facts(signature="signed", identifiers=["acmetool"], apps=["T.app"])
        c = classify(f, Clues(org_codes=["acme"]))
        self.assertEqual(
            (c.origin, c.confidence, c.pattern), ("contradictory", "low", "other")
        )

    def test_ac_04_4_no_clues_still_checks_reverse_domain(self):
        c = classify(
            facts(identifiers=["io.example.DemoApp"], apps=["Demo.app"]), Clues()
        )
        self.assertIn(
            "Identifier 'io.example.DemoApp' matches reverse-domain pattern"
            " (tld.org.name)",
            c.rationale,
        )

    def test_ki_15_unusual_location_in_the_payload(self):
        f = facts(
            install_location="/",
            payload_paths=["/Library", "/Library/Application Support/AcmeFruit/kit"],
        )
        c = classify(f, self.acme)
        self.assertIn(
            "Payload installs under '/Library/Application Support/AcmeFruit'"
            " (an unusual location)",
            c.rationale,
        )
        f = facts(install_location="/Users/Shared/Thing")
        self.assertIn(
            "Install location '/Users/Shared/Thing' is unusual (not /Applications)",
            classify(f, self.acme).rationale,
        )

    def test_a_team_id_not_in_the_clues_adds_nothing(self):
        f = facts(
            signature="signed", authority="Developer ID Installer: X (ABCDE12345)"
        )
        c = classify(f, self.acme)
        self.assertEqual(c.vendor_strong, 2)  # reverse-domain + signed

    def test_any_component_can_match_a_vendor_identifier(self):
        f = facts(kind="distribution", identifiers=["com.example.x", "com.hp.driver"])
        self.assertIn(
            "Identifier matches known vendor identifier pattern",
            classify(f, self.acme).rationale,
        )


class CluesTest(FixtureCase):
    def test_acme_clues_load(self):
        clues = load_clues(ACME_CLUES)
        self.assertIn("UBF8T346G9", clues.vendor_team_ids)
        self.assertIn("^Microsoft_.*_Installer", clues.vendor_filename_patterns)
        self.assertTrue(clues.filename_contains_org_code)

    def test_invalid_clues_are_a_usage_error(self):
        for text in (
            "vendor_identifiers: [\n",
            "- a list\n",
            "vendor_identifiers: ['(']\n",
        ):
            with self.subTest(text):
                path = self.root / "clues.yaml"
                path.write_text(text)
                with self.assertRaises(UsageError):
                    load_clues(path)


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = analyze_package.main(list(argv))
    return code, out.getvalue(), err.getvalue()


@unittest.skipUnless(shutil.which("pkgbuild"), "macOS only")
class CommandTest(FixtureCase):
    def setUp(self):
        super().setUp()
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        for var in ("AUTOPKG_TOOLKIT_ORG", "AUTOPKG_TOOLKIT_CUSTOMERS"):
            os.environ.pop(var, None)

    def tearDown(self):
        self.env.stop()
        super().tearDown()

    def build(self, name, ident, location="/", app=True):
        root = self.root / f"{name}-root"
        (root / ("Demo.app/Contents" if app else "data")).mkdir(parents=True)
        (root / ("Demo.app/Contents/Info" if app else "data/file")).write_text("x\n")
        out = self.root / f"{name}.pkg"
        subprocess.run(
            ["pkgbuild", "--quiet", "--root", str(root), "--identifier", ident]
            + ["--version", "1.0", "--install-location", location, str(out)],
            check=True,
        )
        return out

    def test_ac_08_3_missing_file_and_non_package_exit_2(self):
        self.assertEqual(run(str(self.root / "nope.pkg"))[0], 2)
        text = self.root / "notes.pkg"
        text.write_text("not a package\n")
        code, _, err = run(str(text))
        self.assertEqual(code, 2)
        self.assertIn("pkgutil --expand-full failed", err)

    def test_ac_01_2_json_is_valid_and_carries_the_metadata(self):
        pkg = self.build("Demo", "io.example.DemoApp", "/Applications")
        code, out, _ = run(str(pkg), "--output", "json")
        data = json.loads(out)
        self.assertEqual(data["metadata"]["identifier"], "io.example.DemoApp")
        self.assertEqual(data["metadata"]["install_location"], "/Applications")
        self.assertEqual(data["payload"]["apps_found"], ["Demo.app"])
        self.assertEqual(code, 0)  # reverse-domain and an .app outweigh unsigned

    def test_a_distribution_is_read_through_its_component(self):
        comp = self.build("Driver", "com.hp.driver", app=False)
        dist = self.root / "HP_Driver_Installer.pkg"
        subprocess.run(
            ["productbuild", "--quiet", "--package", str(comp), str(dist)], check=True
        )
        code, out, _ = run(str(dist), "--clues", str(ACME_CLUES))
        self.assertIn("Identifier:   com.hp.driver", out)
        self.assertIn("Kind:         distribution (1 component(s): com.hp.driver)", out)
        self.assertIn("Identifier matches known vendor identifier pattern", out)
        self.assertEqual(code, 0)

    def test_ac_01_3_missing_clues_and_ac_01_4_customer_clues(self):
        pkg = self.build("Acme_Demo", "com.acmefruit.pkg.Demo")
        self.assertEqual(run(str(pkg), "--clues", "/nonexistent.yaml")[0], 2)
        code, out, _ = run(str(pkg), "--customer", "acme")
        self.assertIn(f"clues source: {ACME_CLUES}", out)
        self.assertIn("in the org's own namespace (com.acmefruit)", out)
        self.assertEqual(run(str(pkg), "--customer", "nope")[0], 2)


if __name__ == "__main__":
    unittest.main()
