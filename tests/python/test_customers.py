# test_customers.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""specs/toolkit/02-customers.md: registry, selection, layering, local rules, and
the linter per customer. Every test uses its own registry in a temp folder
($AUTOPKG_TOOLKIT_CUSTOMERS), so the kit's config/customers.yaml doesn't matter."""

import contextlib
import io
import os
import shlex
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from helpers import KIT_ROOT, FixtureCase
from recipekit.customers import CustomerError, load_registry, main, select
from recipekit.lint import run

MOONLIGHT = KIT_ROOT / "customer/acme/output/recipes/MoonlightGameStreaming/Moonlight"
LOCAL_RULE = """
rules:
  - id: "WID-001"
    severity: "error"
    description: "Widgets recipes carry a Description"
    recipe_type: "both"
    check_target:
      key: "Description"
      source: "self"
    allowed_values:
      type: "regex"
      pattern: "^Nothing matches this$"
    pass_message: "ok"
    fail_message: "Description '%value%' is not the Widgets house style"
"""


class CustomerCase(FixtureCase):
    def setUp(self):
        super().setUp()
        self.registry = self.root / "customers.yaml"
        self.env = mock.patch.dict(
            os.environ, {"AUTOPKG_TOOLKIT_CUSTOMERS": str(self.registry)}
        )
        self.env.start()
        for var in (
            "AUTOPKG_TOOLKIT_CUSTOMER",
            "AUTOPKG_TOOLKIT_ORG",
            "AUTOPKG_TOOLKIT_REPO",
        ):
            os.environ.pop(var, None)
        self.acme = self.customer("acme")
        self.widgets = self.customer(
            "widgets",
            org='org_name: "Widgets Inc."\nidentifier_prefix: com.example.widgets\n'
            'pkgname_prefix: "Wid_"\n',
        )

    def tearDown(self):
        self.env.stop()
        super().tearDown()

    def customer(self, name: str, org: str = "") -> Path:
        """A customer folder holding a copy of Moonlight, renamed to its org."""
        folder = self.root / "folders" / name
        recipes = folder / "output" / "recipes" / "Moonlight" / "Moonlight"
        shutil.copytree(MOONLIGHT, recipes)
        if org:
            (folder / "org.yaml").write_text(org)
            for recipe in recipes.glob("*.recipe.yaml"):
                text = recipe.read_text().replace(
                    "com.acmefruit.autopkg", "com.example.widgets"
                )
                recipe.write_text(text.replace("Acme_", "Wid_"))
        return folder

    def write_registry(self, text: str) -> None:
        self.registry.write_text(text)

    def two(self, default: str = "") -> None:
        self.write_registry(
            (f"default: {default}\n" if default else "")
            + f"customers:\n  acme: {self.acme}\n  widgets: {self.widgets}\n"
        )


class RegistryTest(CustomerCase):
    def test_ac_01_1_relative_absolute_and_home_paths(self):
        self.write_registry(
            f"customers:\n  a: customer/acme\n  b: {self.acme}\n  c: ~/x\n"
        )
        reg = load_registry()
        self.assertEqual(reg.customers["a"], KIT_ROOT / "customer/acme")
        self.assertEqual(reg.customers["b"], self.acme)
        self.assertEqual(reg.customers["c"], Path.home() / "x")

    def test_ac_01_2_bad_default_and_missing_folder(self):
        self.write_registry(f"default: nope\ncustomers:\n  acme: {self.acme}\n")
        with self.assertRaises(CustomerError):
            load_registry()
        self.write_registry(f"customers:\n  gone: {self.root / 'missing'}\n")
        with self.assertRaises(CustomerError):
            load_registry().get("gone")

    def test_ac_01_3_no_registry_means_no_customers(self):
        self.registry.unlink(missing_ok=True)
        self.assertEqual(load_registry().customers, {})
        self.assertIsNone(select())

    def test_ac_01_4_no_registry_a_name_is_a_kit_folder(self):
        self.registry.unlink(missing_ok=True)
        self.assertEqual(select("acme").root, KIT_ROOT / "customer/acme")
        with self.assertRaises(CustomerError):
            select("nope")

    def test_ac_01_5_the_shipped_example_is_a_valid_registry(self):
        os.environ["AUTOPKG_TOOLKIT_CUSTOMERS"] = str(
            KIT_ROOT / "config/customers.example.yaml"
        )
        reg = load_registry()
        self.assertEqual(reg.default, "acme")
        self.assertEqual(reg.get("acme").root, KIT_ROOT / "customer/acme")

    @unittest.skipUnless((KIT_ROOT / ".git").exists(), "not a git checkout")
    def test_ac_01_5_the_real_registry_is_never_tracked(self):
        def git(*args):
            return subprocess.run(
                ["git", "-C", str(KIT_ROOT), *args], capture_output=True, text=True
            )

        self.assertEqual(git("ls-files", "config/customers.yaml").stdout, "")
        self.assertEqual(
            git("check-ignore", "-q", "config/customers.yaml").returncode, 0
        )
        self.assertNotEqual(git("ls-files", "config/customers.example.yaml").stdout, "")


class SelectionTest(CustomerCase):
    def test_ac_02_1_precedence(self):
        self.two(default="acme")
        self.assertEqual(select().name, "acme")
        os.environ["AUTOPKG_TOOLKIT_CUSTOMER"] = "widgets"
        self.assertEqual(select().name, "widgets")
        self.assertEqual(select("acme").name, "acme")

    def test_ac_02_2_unknown_name_lists_the_registered(self):
        self.two(default="acme")
        with self.assertRaisesRegex(CustomerError, "registered: acme, widgets"):
            select("nope")

    def test_ac_02_3_ambiguity_and_a_single_customer(self):
        self.two()
        with self.assertRaisesRegex(CustomerError, "none is selected"):
            select()
        self.write_registry(f"customers:\n  only: {self.acme}\n")
        self.assertEqual(select().name, "only")

    def test_an_explicit_target_does_not_pick_up_the_default(self):
        self.two(default="acme")
        self.assertIsNone(select(needed=False))


class LayeringTest(CustomerCase):
    def test_ac_03_1_org_keys_layer_over_the_kit(self):
        self.two()
        (self.widgets / "org.yaml").write_text(
            "identifier_prefix: com.example.widgets\n"
        )
        org = load_registry().get("widgets").org()
        self.assertEqual(org.identifier_prefix, "com.example.widgets")
        self.assertEqual(org.pkgname_prefix, "Acme_")  # from config/org.yaml

    def test_ac_03_2_default_recipe_repo_is_output(self):
        self.two()
        self.assertEqual(
            load_registry().get("acme").recipe_repo(), self.acme / "output"
        )
        (self.acme / "paths.yaml").write_text("recipe_repo:\n  root: elsewhere\n")
        self.assertEqual(
            load_registry().get("acme").recipe_repo(), self.acme / "elsewhere"
        )


class LinterTest(CustomerCase):
    def lint(self, *argv):
        return run(list(argv))

    def test_ac_05_1_each_lints_clean_as_itself_and_fails_as_the_other(self):
        self.two()
        for name in ("acme", "widgets"):
            with self.subTest(name):
                code, out, err = self.lint("--customer", name)
                self.assertEqual((code, err), (0, []), out)
        code, out, _ = self.lint(
            "--customer", "widgets", "--repo", str(self.acme / "output")
        )
        self.assertEqual(code, 1)
        self.assertTrue(any("IDN-001" in line for line in out))

    def test_ac_05_2_all_customers_reports_each_and_exits_worst(self):
        self.two()
        (self.widgets / "checks.local.yaml").write_text(LOCAL_RULE)
        code, out, _ = self.lint("--all-customers")
        self.assertIn("=== Customer: acme", out)
        self.assertIn("=== Customer: widgets", out)
        self.assertEqual(code, 1)  # WID-001 fails for widgets only

    def test_ac_04_1_local_rules_run_for_that_customer_only(self):
        self.two()
        (self.widgets / "checks.local.yaml").write_text(LOCAL_RULE)
        self.assertEqual(self.lint("--customer", "widgets")[0], 1)
        self.assertEqual(self.lint("--customer", "acme")[0], 0)

    def test_ac_04_2_and_4_skipping_optional_rules(self):
        self.two()
        (self.acme / "checks.local.yaml").write_text("skip: [DIR-001, CMT-004]\n")
        _, out, _ = self.lint("--customer", "acme", "--list-rules")
        listed = "\n".join(out)
        self.assertNotIn("DIR-001", listed)
        self.assertNotIn("CMT-004", listed)
        self.assertIn("IDN-001", listed)

    def test_ac_04_3_skipping_required_or_unknown_rules_and_id_reuse(self):
        self.two()
        cases = {
            "skip: [IDN-001]\n": "the kit marks it required",
            "skip: [NOPE-9]\n": "no such rule",
            LOCAL_RULE.replace("WID-001", "IDN-001"): "repeats a kit rule's id",
        }
        for text, message in cases.items():
            with self.subTest(message):
                (self.acme / "checks.local.yaml").write_text(text)
                code, _, err = self.lint("--customer", "acme")
                self.assertEqual(code, 2)
                self.assertIn(message, err[0])

    def test_config_replaces_local_rules(self):
        self.two()
        (self.widgets / "checks.local.yaml").write_text(LOCAL_RULE)
        code, _, _ = self.lint(
            "--customer", "widgets", "--config", str(KIT_ROOT / "config/checks.yaml")
        )
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()


class PrecedenceFixesTest(CustomerCase):
    def test_standing_in_a_recipe_repo_beats_the_default(self):
        self.two(default="acme")
        cwd = os.getcwd()
        os.chdir(self.widgets / "output")
        try:
            code, out, _ = run([])
        finally:
            os.chdir(cwd)
        # Widgets' recipes linted as the kit (Acme naming): they fail IDN-001,
        # which proves the widgets repo was chosen, not the default customer's.
        self.assertEqual(code, 1)
        self.assertFalse(any(line.startswith("  customer:") for line in out))

    def test_all_customers_ignores_the_repo_env_var(self):
        self.two()
        with mock.patch.dict(os.environ, {"AUTOPKG_TOOLKIT_REPO": str(self.root)}):
            code, out, err = run(["--all-customers"])
        self.assertEqual((code, err), (0, []), out)


class ShellOutputTest(CustomerCase):
    """The formats the shell tools read: `show --output env` and `list --output tsv`."""

    def cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(list(argv))
        return code, out.getvalue()

    def test_show_env_is_quoted_and_layered(self):
        self.two(default="widgets")
        (self.widgets / "org.yaml").write_text(
            'org_name: "Widgets\' Inc."\nidentifier_prefix: com.example.widgets\n'
        )
        code, out = self.cli("show", "--output", "env")
        self.assertEqual(code, 0)
        values = dict(shlex.split(line)[0].split("=", 1) for line in out.splitlines())
        self.assertEqual(values["CUSTOMER_NAME"], "widgets")
        self.assertEqual(values["CUSTOMER_REPO"], str(self.widgets / "output"))
        self.assertEqual(values["ORG_NAME"], "Widgets' Inc.")
        self.assertEqual(values["ORG_PKGNAME_PREFIX"], "Acme_")  # from the kit

    def test_list_tsv_has_name_root_and_leak_file(self):
        self.two()
        (self.acme / ".leak-patterns").write_text("x\n")
        code, out = self.cli("list", "--output", "tsv")
        self.assertEqual(code, 0)
        rows = [line.split("\t") for line in out.splitlines()]
        self.assertEqual(
            rows[0], ["acme", str(self.acme), str(self.acme / ".leak-patterns")]
        )
        self.assertEqual(rows[1][0], "widgets")
