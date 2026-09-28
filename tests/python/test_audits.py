# test_audits.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""specs/guardrail-audits/01-audits.md: every audit can pass, fail and (where it
can't check) skip (constitution G-4). Fixtures live in temporary folders, so the
results don't depend on what is on this machine."""

import contextlib
import io
import unittest

from helpers import FixtureCase, download, pkg
from recipekit import RecipeSet
from recipekit.audits import FAIL
from recipekit.audits import PAIR_AUDITS as A
from recipekit.audits import PASS, SKIP, cli, readme_exists, run_all


class AuditCase(FixtureCase):
    def status(
        self, audit: str, dl: str = "", pk: str = "", readme: bool = True
    ) -> str:
        folder = self.pair("App", dl or download("App"), pk or pkg("App"))
        if readme:
            self.write(folder, "README.md", "# App\n")
        return A[audit](RecipeSet.load(folder).pairs()[0]).status


class PathDeleterTest(AuditCase):
    def test_fr_02(self):
        opening = "- Processor: PathDeleter\n- Processor: URLDownloader"
        closing = "- Processor: URLDownloader\n- Processor: PathDeleter"
        self.assertEqual(
            self.status("no_pathdeleter", download("App", process=opening)), FAIL
        )
        self.reset()
        self.assertEqual(
            self.status("no_pathdeleter", download("App", process=closing)), PASS
        )
        self.reset()
        info_first = (
            "- Processor: GitHubReleasesInfoProvider\n"
            "- Processor: PathDeleter\n- Processor: URLDownloader"
        )
        self.assertEqual(
            self.status("no_pathdeleter", download("App", process=info_first)), FAIL
        )
        self.reset()
        commented = "# - Processor: PathDeleter\n" + download("App")
        self.assertEqual(self.status("no_pathdeleter", commented), PASS)


class VendorCacheTest(AuditCase):
    def recipe_for(self, root: str) -> str:
        return download(
            "App",
            inputs=f"""
            VENDOR_CACHE_ROOT: "{root}"
            DOWNLOAD_URL: "file://%VENDOR_CACHE_ROOT%/Acme/App/App.dmg"
            """,
            process="- Processor: URLDownloader\n  Arguments:\n"
            '    url: "%DOWNLOAD_URL%"',
        )

    def test_fr_03_file_url_pass_fail_and_skip(self):
        cache = self.root / "vendor_cache"
        self.assertEqual(
            self.status("vendor_cache_path", self.recipe_for(str(cache))), SKIP
        )
        cache.mkdir()
        self.assertEqual(
            self.status("vendor_cache_path", self.recipe_for(str(cache))), FAIL
        )
        (cache / "Acme/App").mkdir(parents=True)
        (cache / "Acme/App/App.dmg").write_text("x")
        self.assertEqual(
            self.status("vendor_cache_path", self.recipe_for(str(cache))), PASS
        )

    def test_fr_03_relative_local_path(self):
        rel = '"%RECIPE_DIR%/../../../vendor_cache/Acme/App/App.pkg"'
        recipe = download("App", inputs=f"LOCAL_FILE_PATH: {rel}")
        (self.root / "vendor_cache").mkdir()
        self.assertEqual(self.status("vendor_cache_path", recipe), FAIL)
        self.reset()
        (self.root / "vendor_cache/Acme/App").mkdir(parents=True)
        (self.root / "vendor_cache/Acme/App/App.pkg").write_text("x")
        self.assertEqual(self.status("vendor_cache_path", recipe), PASS)

    def test_nothing_to_check_passes(self):
        self.assertEqual(self.status("vendor_cache_path"), PASS)


class PathnameTest(AuditCase):
    PKG = pkg(
        "App",
        process='- Processor: PkgCopier\n  Arguments:\n    source_pkg: "%pathname%"',
    )

    def test_fr_04(self):
        copier = "- Processor: Copier\n  Arguments:\n    source_path: /tmp/x.pkg"
        self.assertEqual(
            self.status(
                "no_pathname_reliance", download("App", process=copier), self.PKG
            ),
            FAIL,
        )
        self.reset()
        dl = "- Processor: URLDownloader\n  Arguments:\n    url: https://x/y.pkg"
        self.assertEqual(
            self.status("no_pathname_reliance", download("App", process=dl), self.PKG),
            PASS,
        )

    def test_ac_04_2_missing_download_is_skip(self):
        folder = self.folder("recipes/Acme/Half")
        self.write(folder, "Half.pkg.recipe.yaml", pkg("Half"))
        result = A["no_pathname_reliance"](RecipeSet.load(folder).pairs()[0])
        self.assertEqual(result.status, SKIP)


class CopierOverwriteTest(AuditCase):
    def step(self, source: str, overwrite: str = "") -> str:
        extra = f"\n    overwrite: {overwrite}" if overwrite else ""
        return download(
            "App",
            process=(
                f'- Processor: Copier\n  Arguments:\n    source_path: "{source}"\n'
                f'    destination_path: "%RECIPE_CACHE_DIR%/x"{extra}'
            ),
        )

    def test_fr_08_folder_copies_need_overwrite(self):
        for source in ("%LOCAL_DIR_PATH%", "%pathname%/App.app", "/tmp/folder/"):
            with self.subTest(source):
                self.reset()
                self.assertEqual(
                    self.status("copier_overwrite", self.step(source)), FAIL
                )
                self.reset()
                self.assertEqual(
                    self.status("copier_overwrite", self.step(source, "true")), PASS
                )

    def test_a_file_copy_is_not_checked(self):
        self.assertEqual(
            self.status("copier_overwrite", self.step("/tmp/App.pkg")), PASS
        )

    def test_pkg_recipe_copiers_are_checked_too(self):
        pk = pkg(
            "App",
            process="- Processor: Copier\n  Arguments:\n"
            '    source_path: "%pathname%/App.app"',
        )
        self.assertEqual(self.status("copier_overwrite", pk=pk), FAIL)


class ReadmeTest(FixtureCase):
    def test_fr_09(self):
        folder = self.folder("recipes/Acme/App")
        self.assertEqual(readme_exists(folder).status, FAIL)
        self.write(folder, "README.md", "")
        self.assertEqual(readme_exists(folder).status, FAIL)  # empty
        self.write(folder, "README.md", "# App\n")
        self.assertEqual(readme_exists(folder).status, PASS)


class RunAllAndCliTest(AuditCase):
    def test_run_all_covers_every_audit(self):
        folder = self.pair("App")
        self.write(folder, "README.md", "# App\n")
        names = [r.name for r in run_all(RecipeSet.load(folder).pairs()[0])]
        self.assertEqual(names, [*A.keys(), "readme_exists"])

    def test_cli_exit_codes_and_targets(self):
        folder = self.pair("App", download("App", process="- Processor: PathDeleter"))
        for target in (folder, folder / "App.download.recipe.yaml"):
            with self.subTest(str(target.name)), contextlib.redirect_stdout(
                io.StringIO()
            ):
                self.assertEqual(cli("no_pathdeleter", [str(target)]), 1)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli("no_pathdeleter", [str(self.root / "nope")]), 2)
            self.write(folder, "App.download.recipe.yaml", "Input: [broken\n")
            self.assertEqual(cli("no_pathdeleter", [str(folder)]), 2)


if __name__ == "__main__":
    unittest.main()


class CertChainTest(AuditCase):
    def verifier(self, names: str) -> str:
        return download(
            "App",
            process=(
                "- Processor: CodeSignatureVerifier\n  Arguments:\n"
                f"    expected_authority_names:\n{names}"
            ),
        )

    def test_fr_05(self):
        leaf = '      - "Developer ID Installer: Example (ABCDE12345)"\n'
        full = (
            leaf
            + "      - Developer ID Certification Authority\n      - Apple Root CA\n"
        )
        self.assertEqual(self.status("cert_chain_complete", self.verifier(leaf)), FAIL)
        self.reset()
        self.assertEqual(self.status("cert_chain_complete", self.verifier(full)), PASS)
        self.reset()
        requirement = download(
            "App",
            process=(
                "- Processor: CodeSignatureVerifier\n  Arguments:\n"
                '    requirement: identifier "x"'
            ),
        )
        self.assertEqual(self.status("cert_chain_complete", requirement), PASS)


class UnsignedTest(AuditCase):
    def test_fr_06(self):
        reason = (
            "# Org-authored scripts: nothing to verify.\n"
            "NO_CODE_SIGNATURE_REQUIRED: true"
        )
        self.assertEqual(
            self.status("unsigned_declared", download("App", reason)), PASS
        )
        self.reset()
        bare = "NO_CODE_SIGNATURE_REQUIRED: true"
        self.assertEqual(self.status("unsigned_declared", download("App", bare)), FAIL)
        self.reset()
        self.assertEqual(self.status("unsigned_declared", download("App")), FAIL)


class VariablesTest(AuditCase):
    def test_fr_07_fail_pass_and_skip(self):
        used = pkg(
            "App",
            process=(
                "- Processor: PkgCreator\n  Arguments:\n    pkg_request:\n"
                '      version: "%version%"'
            ),
        )
        self.assertEqual(self.status("variables_declared", pk=used), FAIL)
        self.reset()
        pinned = download("App", 'version: "1.0"')
        self.assertEqual(self.status("variables_declared", pinned, used), PASS)
        self.reset()
        shared = download("App", process="- Processor: com.github.someone.x/Magic")
        self.assertEqual(self.status("variables_declared", shared, used), SKIP)

    def test_used_before_set_fails(self):
        early = download(
            "App",
            process=(
                "- Processor: URLDownloader\n  Arguments:\n"
                '    url: "https://x/App-%version%.dmg"\n'
                "- Processor: Versioner"
            ),
        )
        self.assertEqual(self.status("variables_declared", early), FAIL)

    def test_pathname_from_an_unknown_processor_is_skip(self):
        shared = download("App", process="- Processor: com.github.someone.x/Fetch")
        used = pkg(
            "App",
            process=(
                '- Processor: PkgCopier\n  Arguments:\n    source_pkg: "%pathname%"'
            ),
        )
        self.assertEqual(self.status("no_pathname_reliance", shared, used), SKIP)


class PairingTest(AuditCase):
    def test_a_parent_that_is_not_the_sibling_fails(self):
        wrong = pkg("App", parent="com.github.someone.download.App")
        self.assertEqual(self.status("recipe_pairing", pk=wrong), FAIL)
        self.reset()
        self.assertEqual(self.status("recipe_pairing"), PASS)


class CliExtraTest(AuditCase):
    def test_skip_only_exits_0(self):
        folder = self.pair(
            "App",
            download("App", process="- Processor: com.x/Magic"),
            pkg(
                "App",
                process="- Processor: PkgCopier\n  Arguments:\n"
                '    source_pkg: "%pathname%"',
            ),
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cli("no_pathname_reliance", [str(folder)]), 0)
        self.assertIn("SKIP:", out.getvalue())

    def test_an_invalid_sibling_does_not_block_a_named_recipe(self):
        folder = self.pair("App")
        self.write(folder, "Other.download.recipe.yaml", "Input: [broken\n")
        with contextlib.redirect_stdout(io.StringIO()):
            code = cli("no_pathdeleter", [str(folder / "App.download.recipe.yaml")])
        self.assertEqual(code, 0)


class PreflightTest(FixtureCase):
    """specs/guardrail-audits/02-autopkg-preflight.md, called as main([...])."""

    def preflight(self, *argv):
        import importlib.util

        from helpers import KIT_ROOT

        spec = importlib.util.spec_from_file_location(
            "preflight", KIT_ROOT / "bin" / "autopkg-preflight.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_repo_errors_exit_2(self):
        code, _, err = self.preflight("--repo", str(self.root / "missing"), "--no-lint")
        self.assertEqual(code, 2)
        self.assertIn("does not exist", err)

    def test_skips_do_not_fail_and_parse_errors_do(self):
        folder = self.pair(
            "App",
            download(
                "App",
                "VENDOR_CACHE_ROOT: /nowhere/vendor_cache\n"
                'DOWNLOAD_URL: "file://%VENDOR_CACHE_ROOT%/a.dmg"\n'
                "NO_CODE_SIGNATURE_REQUIRED: true  # test fixture",
            ),
        )
        self.write(folder, "README.md", "# App\n")
        code, out, _ = self.preflight("--repo", str(self.root), "--no-lint")
        self.assertEqual(code, 0, out)
        self.assertIn("SKIPPED", out)
        self.write(folder, "App.pkg.recipe.yaml", "Input: [broken\n")
        code, out, _ = self.preflight("--repo", str(self.root), "--no-lint")
        self.assertEqual(code, 1)
        self.assertIn("[FAIL] recipe_parse", out)
