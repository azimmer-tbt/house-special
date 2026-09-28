# test_lint.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Unit tests for the Python recipe linter (recipekit.lint).

Ports every example from the ShellSpec files that tested the bash engine's
internal functions by sourcing bin/recipe-linter.sh:

  tests/linter_apply_rule_spec.sh
  tests/linter_companions_spec.sh
  tests/linter_comparisons_spec.sh
  tests/linter_pairs_spec.sh
  tests/linter_signature_version_rules_spec.sh
  tests/linter_utils_spec.sh
  tests/linter_validation_spec.sh
  tests/linter_yaml_spec.sh

One test per ShellSpec `It`, in classes named after the file/Describe it came
from. `__PASS__` / `__FAIL__` map to Outcome.kind "pass" / "fail"; the bash
engine's "wrong recipe type" non-zero return maps to apply_rule returning None.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import helpers
from helpers import KIT_ROOT, FixtureCase
from recipekit.lint import (
    DEFAULT_CHECKS,
    Rule,
    _companion_pairs,
    apply_rule,
    check_pairs,
    companion,
    compare_exists,
    compare_regex,
    get_value,
    grep,
    load_rules,
    recipe_type,
    unescape,
    validate_checks,
)
from recipekit.org import read_org_config

FIXTURES = KIT_ROOT / "tests" / "fixtures" / "linter"
EXAMPLE_DL = FIXTURES / "ExampleApp.download.recipe.yaml"
EXAMPLE_PKG = FIXTURES / "ExampleApp.pkg.recipe.yaml"
EXACT_DL = FIXTURES / "ExactMatchApp.download.recipe.yaml"


def _org():
    org, error = read_org_config()
    if error:
        raise RuntimeError(error)
    return org


def _rules(path: Path = DEFAULT_CHECKS) -> list[Rule]:
    return load_rules(path, _org())


def _rule(rule_id: str, path: Path = DEFAULT_CHECKS) -> Rule:
    """Look a rule up by ID, not position (as the ShellSpec rule_idx did)."""
    for rule in _rules(path):
        if rule.id == rule_id:
            return rule
    raise KeyError(f"unknown rule {rule_id}")


class RuleAssertions(unittest.TestCase):
    def assert_kind(self, rule: Rule, recipe: Path, kind: str) -> None:
        outcome = apply_rule(rule, recipe)
        self.assertIsNotNone(outcome, f"{rule.id} did not apply to {recipe}")
        self.assertEqual(outcome.kind, kind, outcome.message)

    def assert_pass(self, rule_id: str, recipe: Path) -> None:
        self.assert_kind(_rule(rule_id), recipe, "pass")

    def assert_fail(self, rule_id: str, recipe: Path) -> None:
        self.assert_kind(_rule(rule_id), recipe, "fail")


# ── linter_apply_rule_spec.sh: apply_rule() — full rule application ──────────
class ApplyRuleTests(RuleAssertions):
    # IDN-001 (download Identifier namespace)
    def test_idn_001_passes_for_download_recipe_with_correct_identifier(self):
        self.assert_pass("IDN-001", EXAMPLE_DL)

    def test_idn_001_does_not_apply_to_pkg_recipe_wrong_type(self):
        self.assertIsNone(apply_rule(_rule("IDN-001"), EXAMPLE_PKG))

    # IDN-002 (pkg Identifier namespace)
    def test_idn_002_passes_for_pkg_recipe_with_correct_identifier(self):
        self.assert_pass("IDN-002", EXAMPLE_PKG)

    # IDN-003 (no .pkg in download identifier)
    def test_idn_003_passes_for_download_recipe_without_pkg_contamination(self):
        self.assert_pass("IDN-003", EXAMPLE_DL)

    # IDN-004 (ParentRecipe matches download)
    def test_idn_004_passes_when_download_companion_has_matching_identifier(self):
        self.assert_pass("IDN-004", EXAMPLE_PKG)

    # IDN-006 (ParentRecipe in the org namespace)
    def test_idn_006_passes_an_org_namespace_parent(self):
        self.assert_pass("IDN-006", EXAMPLE_PKG)

    # IDN-005 (no doubled segments)
    def test_idn_005_passes_for_clean_identifier(self):
        self.assert_pass("IDN-005", EXAMPLE_DL)

    # SRC-001 (no ephemeral GitHub URLs)
    def test_src_001_passes_when_no_ephemeral_urls_are_present(self):
        self.assert_pass("SRC-001", EXAMPLE_DL)

    # SRC-003 (dynamic provider)
    def test_src_003_fails_when_only_urldownloader_is_present(self):
        self.assert_fail("SRC-003", EXAMPLE_DL)

    # PKG-001 (no AppPkgCreator)
    def test_pkg_001_passes_when_apppkgcreator_is_not_present(self):
        self.assert_pass("PKG-001", EXAMPLE_PKG)

    # PKG-002 (Acme_ prefix)
    def test_pkg_002_passes_when_prefix_is_present_in_pkg_recipe(self):
        self.assert_pass("PKG-002", EXAMPLE_PKG)

    # CSV-001 (CodeSignatureVerifier)
    def test_csv_001_passes_when_codesignatureverifier_is_present(self):
        self.assert_pass("CSV-001", EXAMPLE_DL)

    # CSV-005 (subject.OU)
    def test_csv_005_passes_when_subject_ou_is_in_requirement_string(self):
        self.assert_pass("CSV-005", EXAMPLE_DL)

    # VER-001 (version extraction)
    def test_ver_001_passes_when_version_extraction_processor_is_present(self):
        self.assert_pass("VER-001", EXAMPLE_DL)

    # NAM-001 (filename convention)
    def test_nam_001_passes_for_valid_filename(self):
        self.assert_pass("NAM-001", EXAMPLE_DL)

    # NAM-002 (no dots in filename)
    def test_nam_002_passes_for_filename_with_no_extra_dots(self):
        self.assert_pass("NAM-002", EXAMPLE_DL)

    # NAM-003 (NAME matches app name)
    def test_nam_003_passes_when_name_is_present(self):
        self.assert_pass("NAM-003", EXAMPLE_DL)

    # SEN-001 (download needs pkg recipe)
    def test_sen_001_passes_when_companion_pkg_recipe_exists(self):
        self.assert_pass("SEN-001", EXAMPLE_DL)

    # MIN-001 (MinimumVersion >= 2.3)
    def test_min_001_passes_with_minimum_version_2_3(self):
        self.assert_pass("MIN-001", EXAMPLE_DL)

    def test_min_001_passes_with_minimum_version_2_7(self):
        self.assert_pass("MIN-001", EXACT_DL)


class ApplyRuleIdn006FixtureTests(FixtureCase, RuleAssertions):
    """IDN-006: the one apply_rule example that needed a temp fixture."""

    def test_idn_006_fails_a_community_parent_referenced_not_adopted(self):
        lines = EXAMPLE_PKG.read_text(encoding="utf-8").split("\n")
        lines = [
            (
                "ParentRecipe: com.github.example-recipes.download.ExampleApp"
                if line.startswith("ParentRecipe: ")
                else line
            )
            for line in lines
        ]
        recipe = self.write(
            self.folder("idn006"), "ExampleApp.pkg.recipe.yaml", "\n".join(lines)
        )
        self.assert_fail("IDN-006", recipe)


# ── linter_apply_rule_spec.sh: exists_any multi-condition rules ─────────────
EXISTS_ANY_SPEC = """\
rules:
  - id: "EXA-001"
    severity: "error"
    description: "Version must be accounted for"
    recipe_type: "download"
    allowed_values:
      type: "exists_any"
      conditions:
        - source: "self"
          key: "Process"
          pattern: "(SparkleUpdateInfoProvider|GitHubReleasesInfoProvider|\
Versioner|AppDmgVersioner)"
        - source: "self"
          key: "Input.LOCAL_FILE_PATH"
          pattern: ".+"
        - source: "related-file"
          related_type: "pkg_recipe"
          key: "Process"
          pattern: "FlatPkgUnpacker.*Versioner"
    pass_message: "Version is accounted for"
    fail_message: "No version-extraction path found"

  - id: "EXA-002"
    severity: "error"
    description: "Must have companion or self condition"
    recipe_type: "download"
    allowed_values:
      type: "exists_any"
      conditions:
        - source: "related-file"
          related_type: "pkg_recipe"
          key: "Process"
          pattern: "NONEXISTENT_PROCESSOR"
    pass_message: "Some condition met"
    fail_message: "No condition met"

  - id: "EXA-003"
    severity: "error"
    description: "Empty conditions must fail"
    recipe_type: "download"
    allowed_values:
      type: "exists_any"
      conditions: []
    pass_message: "Should not pass"
    fail_message: "No conditions defined — should always fail"

  - id: "EXA-004"
    severity: "error"
    description: "Any of these self conditions must match"
    recipe_type: "download"
    allowed_values:
      type: "exists_any"
      conditions:
        - source: "self"
          key: "Process"
          pattern: "CodeSignatureVerifier"
        - source: "self"
          key: "Input.NAME"
          pattern: "ExampleApp"
    pass_message: "One condition met"
    fail_message: "No condition met"
"""


class ExistsAnyTests(FixtureCase, RuleAssertions):
    def setUp(self) -> None:
        super().setUp()
        self.spec = self.write(self.root, "checks.yaml", EXISTS_ANY_SPEC)

    def exa(self, rule_id: str) -> Rule:
        return _rule(rule_id, self.spec)

    def test_exa_001_passes_when_first_condition_matches_short_circuit(self):
        self.assert_kind(self.exa("EXA-001"), EXAMPLE_DL, "pass")

    def test_exa_002_fails_when_companion_missing_and_nothing_else_matches(self):
        self.assert_kind(self.exa("EXA-002"), EXAMPLE_DL, "fail")

    def test_exa_003_fails_when_conditions_list_is_empty(self):
        self.assert_kind(self.exa("EXA-003"), EXAMPLE_DL, "fail")

    def test_exa_004_passes_when_a_non_first_condition_matches_late_match(self):
        self.assert_kind(self.exa("EXA-004"), EXAMPLE_DL, "pass")

    def test_exa_004_fails_when_no_condition_matches_all_miss(self):
        # ExactMatchApp has NAME=ExactMatchApp and no CodeSignatureVerifier.
        self.assert_kind(self.exa("EXA-004"), EXACT_DL, "fail")


# ── linter_companions_spec.sh: companion file parsers ───────────────────────
class ParseOverridesTests(FixtureCase):
    def pairs(self, text: str) -> list[tuple[str, str]]:
        return _companion_pairs(self.write(self.root, "overrides.txt", text), "=")

    def test_parses_key_value_from_valid_overrides_content(self):
        # Whitespace is stripped from lines, so "Microsoft Edge" would be
        # "MicrosoftEdge".
        self.assertEqual(
            self.pairs("teamid=UBF8T346G9\nversion=1.2.3\nappname=MicrosoftEdge\n"),
            [
                ("teamid", "UBF8T346G9"),
                ("version", "1.2.3"),
                ("appname", "MicrosoftEdge"),
            ],
        )

    def test_ignores_comment_lines(self):
        text = "# This is a comment\nteamid=UBF8T346G9\n# Another comment\n"
        text += "version=1.2.3\n"
        self.assertEqual(
            self.pairs(text), [("teamid", "UBF8T346G9"), ("version", "1.2.3")]
        )

    def test_ignores_blank_lines(self):
        text = "\nteamid=UBF8T346G9\n\n\nversion=1.2.3\n\n"
        self.assertEqual(
            self.pairs(text), [("teamid", "UBF8T346G9"), ("version", "1.2.3")]
        )

    def test_returns_nothing_for_empty_file(self):
        self.assertEqual(self.pairs(""), [])

    def test_skips_lines_with_smart_quotes(self):
        text = "teamid=UBF8T346G9\nappname=“Microsoft Edge”\nversion=1.2.3\n"
        self.assertEqual(
            self.pairs(text), [("teamid", "UBF8T346G9"), ("version", "1.2.3")]
        )

    def test_duplicate_keys_are_all_emitted(self):
        # The ShellSpec example was titled "last occurrence wins" but asserted
        # only that both lines are emitted; the lookup (bash `head -1`, and
        # get_value here) actually takes the first.
        overrides = self.write(
            self.root,
            ".overrides",
            "teamid=FIRSTTEAM\nteamid=LASTTEAM\nversion=1.0.0\n",
        )
        self.assertEqual(
            _companion_pairs(overrides, "="),
            [("teamid", "FIRSTTEAM"), ("teamid", "LASTTEAM"), ("version", "1.0.0")],
        )
        self.assertEqual(get_value(overrides, "teamid"), "FIRSTTEAM")


class ParseAutopkgConfigTests(FixtureCase):
    def pairs(self, text: str) -> list[tuple[str, str]]:
        return _companion_pairs(self.write(self.root, "config.txt", text), ":")

    def test_parses_key_value_from_valid_autopkg_config_content(self):
        text = (
            "auto_rebuild: true\npromote_to: prod\nregions: [global]\n"
            "tf_name: microsoft_teams\n"
        )
        self.assertEqual(
            self.pairs(text),
            [
                ("auto_rebuild", "true"),
                ("promote_to", "prod"),
                ("regions", "[global]"),
                ("tf_name", "microsoft_teams"),
            ],
        )

    def test_ignores_comment_lines(self):
        text = "# Workflow metadata\nauto_rebuild: true\n# Promotion target\n"
        text += "promote_to: prod\n"
        self.assertEqual(
            self.pairs(text), [("auto_rebuild", "true"), ("promote_to", "prod")]
        )

    def test_ignores_blank_lines(self):
        text = "\nauto_rebuild: true\n\n\npromote_to: prod\n\n"
        self.assertEqual(
            self.pairs(text), [("auto_rebuild", "true"), ("promote_to", "prod")]
        )

    def test_returns_nothing_for_empty_file(self):
        self.assertEqual(self.pairs(""), [])


class CompanionGetValueTests(FixtureCase):
    def test_returns_value_from_overrides_file(self):
        path = self.write(self.root, ".overrides", "teamid=UBF8T346G9\nversion=1.2.3\n")
        self.assertEqual(get_value(path, "teamid"), "UBF8T346G9")

    def test_returns_value_from_autopkg_config_file(self):
        path = self.write(
            self.root,
            ".autopkg_config",
            "auto_rebuild: true\ntf_name: microsoft_teams\n",
        )
        self.assertEqual(get_value(path, "tf_name"), "microsoft_teams")


# ── linter_comparisons_spec.sh: comparison functions ────────────────────────
class CompareRegexTests(unittest.TestCase):
    def test_matches_a_value_against_a_regex_pattern(self):
        self.assertTrue(
            compare_regex(
                "com.acmefruit.autopkg.download.ExampleApp",
                r"^com\.acmefruit\.autopkg\.download\..+$",
            )
        )

    def test_fails_when_value_does_not_match_regex(self):
        self.assertFalse(compare_regex("com.example.test", r"^com\.acmefruit\."))

    def test_fails_on_empty_value_with_non_empty_pattern(self):
        self.assertFalse(compare_regex("", ".+"))


class RuleOnValueCase(FixtureCase):
    """Apply a one-off rule to a download recipe whose `Key:` value we control
    (exact and absent are comparisons inside apply_rule)."""

    def kind(self, value: str | None, val_type: str, pattern: str = "") -> str:
        text = helpers.download("Probe")
        if value is not None:
            text = f"Key: {value}\n" + text
        recipe = self.write(self.folder(), "Probe.download.recipe.yaml", text)
        rule = Rule(
            "T-001", "error", recipe_type="download", key="Key", val_type=val_type
        )
        rule.val_pattern = pattern
        outcome = apply_rule(rule, recipe)
        self.assertIsNotNone(outcome)
        return outcome.kind


class CompareExactTests(RuleOnValueCase):
    def test_matches_when_values_are_identical(self):
        value = "com.acmefruit.autopkg.download.App"
        self.assertEqual(self.kind(value, "exact", value), "pass")

    def test_fails_when_values_differ(self):
        self.assertEqual(
            self.kind(
                "com.acmefruit.autopkg.download.App",
                "exact",
                "com.acmefruit.autopkg.download.Different",
            ),
            "fail",
        )

    def test_is_case_sensitive_and_fails_on_case_mismatch(self):
        self.assertEqual(
            self.kind(
                "com.acmefruit.autopkg.download.App",
                "exact",
                "com.acmefruit.autopkg.DOWNLOAD.App",
            ),
            "fail",
        )

    def test_matches_empty_strings(self):
        self.assertEqual(self.kind(None, "exact", ""), "pass")


class CompareListTests(unittest.TestCase):
    def test_matches_when_value_is_in_the_list(self):
        self.assertTrue(
            grep(
                "SparkleUpdateInfoProvider",
                "SparkleUpdateInfoProvider|GitHubReleasesInfoProvider|URLTextSearcher",
            )
        )

    def test_fails_when_value_is_not_in_the_list(self):
        self.assertFalse(
            grep("UnsupportedProvider", "SparkleUpdateInfoProvider|URLTextSearcher")
        )

    def test_matches_with_partial_text_match_on_list_items(self):
        self.assertTrue(
            grep(
                "GitHubReleasesInfoProvider",
                "SparkleUpdateInfoProvider|GitHubReleasesInfoProvider",
            )
        )


class CompareExistsTests(unittest.TestCase):
    def test_passes_when_value_matches_default_pattern(self):
        self.assertTrue(compare_exists("some-value", ""))

    def test_passes_when_value_matches_custom_pattern(self):
        self.assertTrue(
            compare_exists("CodeSignatureVerifier", "CodeSignatureVerifier")
        )

    def test_fails_when_value_does_not_match_custom_pattern(self):
        self.assertFalse(compare_exists("some-value", "CodeSignatureVerifier"))

    def test_fails_on_empty_value_with_default_pattern(self):
        self.assertFalse(compare_exists("", ".+"))


class CompareNotExistsTests(unittest.TestCase):
    # not_exists in apply_rule is `not grep(value, unescape(pattern))`.
    def not_exists(self, value: str, pattern: str) -> bool:
        return not grep(value, unescape(pattern))

    def test_passes_when_value_does_not_match_pattern(self):
        self.assertTrue(
            self.not_exists(
                "com.acmefruit.autopkg.download.App", r"com\.acmefruit\.autopkg\.pkg"
            )
        )

    def test_fails_when_value_matches_pattern(self):
        self.assertFalse(
            self.not_exists(
                "com.acmefruit.autopkg.pkg.App", r"com\.acmefruit\.autopkg\.pkg"
            )
        )


class CompareAbsentTests(RuleOnValueCase):
    def test_passes_when_value_is_empty(self):
        self.assertEqual(self.kind(None, "absent"), "pass")

    def test_passes_when_value_is_null(self):
        self.assertEqual(self.kind("null", "absent"), "pass")

    def test_fails_when_value_is_non_empty(self):
        self.assertEqual(self.kind("something", "absent"), "fail")


# ── linter_pairs_spec.sh: check_pairs() ─────────────────────────────────────
class CheckPairsTests(FixtureCase):
    def setUp(self) -> None:
        super().setUp()
        for rel in (
            "A/Paired.download.recipe.yaml",
            "A/Paired.pkg.recipe.yaml",
            "B/Orphan.download.recipe.yaml",
            "B/Standalone.pkg.recipe.yaml",
        ):
            self.write(self.root, rel, "")

    def report(self) -> str:
        out: list[str] = []
        check_pairs(str(self.root), out)
        return "\n".join(out)

    def test_fails_a_download_recipe_with_no_pkg_recipe(self):
        report = self.report()
        self.assertIn(
            f"Download recipe '{self.root}/B/Orphan.download.recipe.yaml' "
            "has no matching pkg recipe",
            report,
        )
        self.assertIn("[FAIL] SEN-001", report)
        self.assertIn("1 incomplete pairs", report)

    def test_warns_on_a_standalone_pkg_recipe(self):
        report = self.report()
        self.assertIn(
            f"Pkg recipe '{self.root}/B/Standalone.pkg.recipe.yaml' "
            "has no matching download recipe",
            report,
        )
        self.assertIn("[WARN] SEN-001", report)
        self.assertIn("1 standalone pkg recipes", report)

    def test_does_not_flag_a_complete_pair(self):
        self.assertNotIn("Paired", self.report())

    def test_reports_all_pairs_complete_when_they_are(self):
        for path in (self.root / "B").iterdir():
            path.unlink()
        self.assertIn("All recipe pairs are complete", self.report())


# ── linter_signature_version_rules_spec.sh: KI-2 rule alternatives ──────────
def _sigver_recipe(inputs: str, process: str) -> str:
    return (
        "Comment: Pattern 2d — test fixture\n"
        "Identifier: com.acmefruit.autopkg.download.Fixture\n"
        'MinimumVersion: "2.3"\n'
        "Input:\n"
        "  NAME: Fixture\n"
        f"{inputs}\n"
        "Process:\n"
        f"{process}\n"
    )


def _pkg_recipe(processor: str, arguments: str) -> str:
    return (
        f"Identifier: x\nProcess:\n  - Processor: {processor}\n"
        f"    Arguments:\n{arguments}\n"
    )


class SignatureVersionRuleTests(FixtureCase, RuleAssertions):
    def setUp(self) -> None:
        super().setUp()
        d = self.root
        self.pinned = self.write(
            d,
            "pinned.download.recipe.yaml",
            _sigver_recipe(
                '  version: "1.0.0"\n  NO_CODE_SIGNATURE_REQUIRED: true',
                "  - Processor: URLDownloader\n    Arguments:\n"
                '      url: "https://example.com/latest.zip"',
            ),
        )
        self.bare = self.write(
            d,
            "bare.download.recipe.yaml",
            _sigver_recipe(
                "  X: y",
                "  - Processor: URLDownloader\n    Arguments:\n"
                '      url: "https://example.com/App-1.2.3.dmg"',
            ),
        )
        self.oid = self.write(
            d,
            "oid.download.recipe.yaml",
            _sigver_recipe(
                "  X: y",
                "  - Processor: GitHubReleasesInfoProvider\n"
                "  - Processor: URLDownloader\n"
                "  - Processor: CodeSignatureVerifier\n"
                "    Arguments:\n"
                "      requirement: >-\n"
                '        identifier "x" and certificate '
                "1[field.1.2.840.113635.100.6.2.6] /* exists */",
            ),
        )
        self.adhoc = self.write(
            d,
            "adhoc.download.recipe.yaml",
            _sigver_recipe(
                '  teamid: "UNSIGNED_NO_TEAMID"',
                "  - Processor: CodeSignatureVerifier\n    Arguments:\n"
                '      requirement: identifier "io.example.adhoc"',
            ),
        )
        # .overrides is an optional harness file; AutoPkg never reads it, so
        # no rule may.
        self.write(d, ".overrides", "teamid=UNSIGNED_NO_TEAMID\nversion=1.0\n")
        self.copy = self.write(
            d,
            "copy.pkg.recipe.yaml",
            _pkg_recipe(
                "Copier", '      destination_path: "%RECIPE_CACHE_DIR%/%NAME%.pkg"'
            ),
        )
        self.build = self.write(
            d,
            "build.pkg.recipe.yaml",
            _pkg_recipe("PkgCreator", '      pkg_request:\n        pkgname: "%NAME%"'),
        )
        self.buildok = self.write(
            d,
            "buildok.pkg.recipe.yaml",
            _pkg_recipe(
                "PkgCreator", '      pkg_request:\n        pkgname: "Acme_%NAME%"'
            ),
        )

    def test_ver_001_passes_with_a_pinned_input_version(self):
        self.assert_pass("VER-001", self.pinned)

    def test_ver_001_fails_with_no_processor_and_no_pinned_version(self):
        self.assert_fail("VER-001", self.bare)

    def test_csv_001_passes_when_no_code_signature_required_is_declared(self):
        self.assert_pass("CSV-001", self.pinned)

    def test_csv_001_fails_with_neither_a_verifier_nor_the_declaration(self):
        self.assert_fail("CSV-001", self.bare)

    def test_csv_005_passes_when_input_records_teamid_unsigned_no_teamid(self):
        self.assert_pass("CSV-005", self.adhoc)

    def test_csv_005_ignores_unsigned_no_teamid_in_overrides(self):
        self.assert_fail("CSV-005", self.bare)

    def test_ver_001_ignores_a_version_pinned_only_in_overrides(self):
        self.assert_fail("VER-001", self.bare)

    def test_src_002_ignores_certificate_oids_in_requirement_strings(self):
        self.assert_pass("SRC-002", self.oid)

    def test_src_002_still_flags_a_versioned_url(self):
        self.assert_fail("SRC-002", self.bare)

    def test_pkg_002_passes_a_vendor_copy_without_the_prefix(self):
        self.assert_pass("PKG-002", self.copy)

    def test_pkg_002_fails_a_pkgcreator_build_without_the_prefix(self):
        self.assert_fail("PKG-002", self.build)

    def test_pkg_002_passes_a_pkgcreator_build_with_the_prefix(self):
        self.assert_pass("PKG-002", self.buildok)


# ── linter_utils_spec.sh: extract_app_name() ────────────────────────────────
class ExtractAppNameTests(unittest.TestCase):
    """No direct twin: companion() derives the app name from the filename."""

    def app_name(self, filename: str) -> str:
        return companion(Path(filename), "pkg_recipe").name[: -len(".pkg.recipe.yaml")]

    def test_extracts_app_name_from_download_recipe_filename(self):
        self.assertEqual(
            self.app_name("Microsoft-Teams.download.recipe.yaml"), "Microsoft-Teams"
        )

    def test_extracts_app_name_from_pkg_recipe_filename(self):
        self.assertEqual(
            self.app_name("Microsoft-Word.pkg.recipe.yaml"), "Microsoft-Word"
        )

    def test_extracts_simple_app_name_from_download_recipe_filename(self):
        self.assertEqual(self.app_name("Smartsheet.download.recipe.yaml"), "Smartsheet")

    def test_returns_empty_for_unrecognized_recipe_type(self):
        self.assertEqual(self.app_name("App.munki.recipe.yaml"), "")
        self.assertEqual(recipe_type(Path("App.munki.recipe.yaml")), "")

    def test_returns_empty_for_unrecognized_file(self):
        self.assertEqual(self.app_name("some-random-file.txt"), "")
        self.assertEqual(recipe_type(Path("some-random-file.txt")), "")

    def test_extracts_app_name_with_numbers(self):
        self.assertEqual(self.app_name("App2.download.recipe.yaml"), "App2")


# ── linter_utils_spec.sh: recipe_type_matches() ─────────────────────────────
class RecipeTypeMatchesTests(unittest.TestCase):
    """recipe_type() plus apply_rule returning None when the type is wrong."""

    def matches(self, recipe: Path, wanted: str) -> bool:
        rule = Rule("T-001", "error", recipe_type=wanted, key="Identifier")
        rule.val_type = "exists"
        return apply_rule(rule, recipe) is not None

    def test_matches_download_recipe_to_download_type(self):
        self.assertEqual(recipe_type(EXAMPLE_DL), "download")
        self.assertTrue(self.matches(EXAMPLE_DL, "download"))

    def test_rejects_download_recipe_for_pkg_type(self):
        self.assertFalse(self.matches(EXAMPLE_DL, "pkg"))

    def test_matches_pkg_recipe_to_pkg_type(self):
        self.assertEqual(recipe_type(EXAMPLE_PKG), "pkg")
        self.assertTrue(self.matches(EXAMPLE_PKG, "pkg"))

    def test_rejects_pkg_recipe_for_download_type(self):
        self.assertFalse(self.matches(EXAMPLE_PKG, "download"))

    def test_matches_both_types_when_recipe_type_is_both(self):
        self.assertTrue(self.matches(EXAMPLE_DL, "both"))

    def test_rejects_unrecognized_recipe_type(self):
        self.assertEqual(recipe_type(Path("some-file.txt")), "")
        self.assertFalse(self.matches(Path("some-file.txt"), "download"))


# ── linter_utils_spec.sh: resolve_companion() ───────────────────────────────
class ResolveCompanionTests(unittest.TestCase):
    def test_resolves_download_recipe_companion_for_a_pkg_recipe(self):
        self.assertTrue(
            str(companion(EXAMPLE_PKG, "download_recipe")).endswith(
                "ExampleApp.download.recipe.yaml"
            )
        )

    def test_resolves_pkg_recipe_companion_for_a_download_recipe(self):
        self.assertTrue(
            str(companion(EXAMPLE_DL, "pkg_recipe")).endswith(
                "ExampleApp.pkg.recipe.yaml"
            )
        )

    def test_resolves_overrides_companion(self):
        self.assertTrue(str(companion(EXAMPLE_DL, "overrides")).endswith("/.overrides"))

    def test_resolves_autopkg_config_companion(self):
        self.assertTrue(
            str(companion(EXAMPLE_DL, "autopkg_config")).endswith("/.autopkg_config")
        )


# ── linter_validation_spec.sh: validate_checks_yaml() ───────────────────────
class ValidateChecksTests(FixtureCase):
    def test_passes_on_valid_checks_yaml(self):
        self.assertEqual(validate_checks(DEFAULT_CHECKS), [])

    def test_fails_on_missing_file(self):
        errors = validate_checks(self.root / "nonexistent.yaml")
        self.assertTrue(any("Specs file not found" in e for e in errors), errors)

    def test_fails_on_file_without_rules_key(self):
        path = self.write(self.root, "no_rules.yaml", "test: value\n")
        errors = validate_checks(path)
        self.assertTrue(any("Missing 'rules:'" in e for e in errors), errors)

    def test_fails_on_empty_rules_list(self):
        path = self.write(self.root, "empty_rules.yaml", 'rules:\n  # - id: "empty"\n')
        errors = validate_checks(path)
        self.assertTrue(any("No rules defined" in e for e in errors), errors)


# ── linter_validation_spec.sh: parse_checks_yaml() ──────────────────────────
class LoadRulesTests(unittest.TestCase):
    def test_parses_all_rules_from_checks_yaml(self):
        self.assertTrue(_rules())

    def test_populates_rule_ids_with_at_least_one_rule(self):
        self.assertTrue(all(rule.id for rule in _rules()))

    def test_sets_severity_for_the_first_rule(self):
        self.assertNotEqual(_rules()[0].severity, "")

    def test_sets_key_for_the_first_rule(self):
        self.assertNotEqual(_rules()[0].key, "")


# ── linter_yaml_spec.sh: YAML key path resolution (get_yaml_value) ──────────
class GetValueTests(unittest.TestCase):
    def test_resolves_top_level_identifier_key(self):
        self.assertEqual(
            get_value(EXAMPLE_DL, "Identifier"),
            "com.acmefruit.autopkg.download.ExampleApp",
        )

    def test_resolves_input_name_nested_key(self):
        self.assertEqual(get_value(EXAMPLE_DL, "Input.NAME"), "ExampleApp")

    def test_resolves_input_download_url_nested_key(self):
        self.assertEqual(
            get_value(EXAMPLE_DL, "Input.DOWNLOAD_URL"),
            "https://vendor.com/download/ExampleApp-latest.dmg",
        )

    def test_resolves_process_section(self):
        value = get_value(EXAMPLE_DL, "Process")
        self.assertNotEqual(value, "")
        self.assertIn("URLDownloader", value.split("\n")[1])

    def test_returns_filename_for_special_filename_key(self):
        self.assertEqual(
            get_value(EXAMPLE_DL, "filename"), "ExampleApp.download.recipe.yaml"
        )

    def test_returns_directory_path_for_source_directory(self):
        self.assertEqual(get_value(EXAMPLE_DL, "filename", "directory"), str(FIXTURES))
        relative = Path("tests/fixtures/linter/ExampleApp.download.recipe.yaml")
        self.assertEqual(
            get_value(relative, "filename", "directory"), "tests/fixtures/linter"
        )

    def test_resolves_pkg_recipe_top_level_identifier(self):
        self.assertEqual(
            get_value(EXAMPLE_PKG, "Identifier"), "com.acmefruit.autopkg.pkg.ExampleApp"
        )

    def test_resolves_pkg_recipe_parent_recipe(self):
        self.assertEqual(
            get_value(EXAMPLE_PKG, "ParentRecipe"),
            "com.acmefruit.autopkg.download.ExampleApp",
        )

    def test_resolves_input_name_from_pkg_recipe(self):
        self.assertEqual(get_value(EXAMPLE_PKG, "Input.NAME"), "ExampleApp")


if __name__ == "__main__":
    unittest.main()


class ClassificationRuleTest(FixtureCase):
    """rule-definitions §2.8 / CMT-004: the Comment's pattern matches the
    classifier's verdict."""

    GITHUB_DMG = (
        "- Processor: GitHubReleasesInfoProvider\n"
        "- Processor: URLDownloader\n"
        "  Arguments:\n"
        '    filename: "%NAME%.dmg"'
    )
    BUILD = (
        "- Processor: PkgCreator\n  Arguments:\n    pkg_request:\n"
        '      pkgroot: "%RECIPE_CACHE_DIR%/root"'
    )

    def cmt_004(self, claim: str, dl_inputs: str = "", dl_process: str = "") -> str:
        from helpers import download, pkg

        folder = self.pair(
            "App",
            (f"Comment: {claim}\n" if claim else "")
            + download("App", dl_inputs, dl_process or self.GITHUB_DMG),
            pkg("App", process=self.BUILD),
        )
        org, _ = read_org_config()
        rule = next(r for r in load_rules(DEFAULT_CHECKS, org) if r.id == "CMT-004")
        return apply_rule(rule, folder / "App.download.recipe.yaml").kind

    def test_a_matching_claim_passes(self):
        self.assertEqual(self.cmt_004("Pattern 2b — GitHub DMG"), "pass")

    def test_a_wrong_claim_fails(self):
        self.assertEqual(self.cmt_004("Pattern 4c — vendor drop"), "fail")

    def test_the_acmesupport_legacy_mislabel_is_caught(self):
        # In-house payload with install scripts claimed as 6a (no scripts).
        from helpers import download, pkg

        folder = self.pair(
            "App",
            "Comment: Pattern 6a — flat payload\n"
            + download(
                "App",
                "NO_CODE_SIGNATURE_REQUIRED: true",
                "- Processor: Copier\n  Arguments:\n"
                '    source_path: "%LOCAL_DIR_PATH%"\n'
                '    destination_path: "%RECIPE_CACHE_DIR%/payload"',
            ),
            pkg(
                "App",
                process=(
                    "- Processor: PkgCreator\n  Arguments:\n    pkg_request:\n"
                    '      pkgroot: "%RECIPE_CACHE_DIR%/payload"\n'
                    '      scripts: "%RECIPE_CACHE_DIR%/scripts"'
                ),
            ),
        )
        org, _ = read_org_config()
        rule = next(r for r in load_rules(DEFAULT_CHECKS, org) if r.id == "CMT-004")
        outcome = apply_rule(rule, folder / "App.download.recipe.yaml")
        self.assertEqual(outcome.kind, "fail")
        self.assertIn("the processors say Pattern 6b", outcome.message)

    def test_an_uncertain_alternative_passes(self):
        faux = (
            "- Processor: URLDownloader\n  Arguments:\n"
            '    url: "file:///tmp/vendor_cache/App.dmg"\n    filename: "App.dmg"'
        )
        self.assertEqual(
            self.cmt_004(
                "Pattern 4c — unsigned vendor DMG",
                "NO_CODE_SIGNATURE_REQUIRED: true",
                faux,
            ),
            "pass",
        )

    def test_a_family_claim_accepts_any_letter(self):
        self.assertEqual(self.cmt_004("Pattern 2 — GitHub"), "pass")

    def test_no_claim_and_half_a_pair_are_not_judged(self):
        self.assertEqual(self.cmt_004(""), "pass")
        from helpers import download

        half = self.folder("recipes/Acme/Half")
        self.write(
            half,
            "Half.download.recipe.yaml",
            "Comment: Pattern 9z\n" + download("Half"),
        )
        org, _ = read_org_config()
        rule = next(r for r in load_rules(DEFAULT_CHECKS, org) if r.id == "CMT-004")
        self.assertEqual(
            apply_rule(rule, half / "Half.download.recipe.yaml").kind, "pass"
        )
