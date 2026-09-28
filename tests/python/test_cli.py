# test_cli.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""FR-10: `python -m recipekit.facts`."""

import contextlib
import io
import json
import unittest

from helpers import KIT_ROOT, FixtureCase, download, pkg
from recipekit.facts import main

ACME = str(KIT_ROOT / "customer" / "acme" / "output")


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(list(argv))
        except SystemExit as exc:  # argparse usage errors
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class CliTest(FixtureCase):
    def test_ac_10_1_json_is_the_only_stdout(self):
        code, out, _ = run("--repo", ACME, "--output", "json")
        self.assertEqual(code, 0)
        report = json.loads(out)
        self.assertEqual(report["view"], "autopkg")
        self.assertEqual(len(report["pairs"]), 17)
        self.assertEqual(report["findings"], [])

    def test_ac_10_2_exit_1_on_an_error_finding(self):
        folder = self.pair(
            "App", pkg_text=pkg("App", parent="com.github.someone.download.App")
        )
        code, out, _ = run(str(folder))
        self.assertEqual(code, 1)
        self.assertIn("parent_missing", out)

    def test_ac_10_2_exit_2_on_usage_errors(self):
        self.assertEqual(run()[0], 2)
        self.assertEqual(run(str(self.root / "nope"))[0], 2)

    def test_harness_view_shows_overrides(self):
        folder = self.pair("App", download("App"))
        self.write(folder, ".overrides", "LICENSE_KEY=secret-from-pipeline\n")
        _, out, _ = run(str(folder), "--view", "harness", "--output", "json")
        self.assertEqual(
            json.loads(out)["pairs"][0]["inputs"]["LICENSE_KEY"], "secret-from-pipeline"
        )


if __name__ == "__main__":
    unittest.main()
