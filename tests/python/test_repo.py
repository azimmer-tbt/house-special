# test_repo.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""recipekit.repo must agree with resolve_repo_root in lib/toolkit-common.sh
(constitution P-2 to P-6; guardrail-audits 02 OQ-1)."""

import os
import subprocess
import unittest
from unittest import mock

from helpers import KIT_ROOT, FixtureCase
from recipekit.repo import resolve_repo_root


def bash_resolve(cwd, explicit="", env=None) -> tuple[int, str]:
    """(exit code, REPO_ROOT or stderr) from the bash routine."""
    script = (
        f'. "{KIT_ROOT}/lib/toolkit-common.sh"; '
        'resolve_repo_root "$1"; echo "$REPO_ROOT"'
    )
    environ = {k: v for k, v in os.environ.items() if k != "AUTOPKG_TOOLKIT_REPO"}
    environ.update(env or {})
    proc = subprocess.run(
        ["/bin/bash", "-c", script, "resolve", explicit],
        cwd=cwd,
        env=environ,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, (
        proc.stdout.strip() if proc.returncode == 0 else proc.stderr
    )


class RepoParityTest(FixtureCase):
    def setUp(self):
        super().setUp()
        self.repo = self.root / "repo"
        (self.repo / "recipes").mkdir(parents=True)
        self.other = self.root / "other"
        self.other.mkdir()

    def python(self, cwd, explicit="", env=None):
        environ = {k: v for k, v in os.environ.items() if k != "AUTOPKG_TOOLKIT_REPO"}
        environ.update(env or {})
        with mock.patch.dict(os.environ, environ, clear=True):
            return resolve_repo_root(explicit or None, cwd=cwd)

    def check(self, cwd, explicit="", env=None):
        code, out = bash_resolve(cwd, explicit, env)
        result = self.python(cwd, explicit, env)
        self.assertEqual(result.ok, code == 0)
        if result.ok:
            self.assertEqual(str(result.root), out)
        else:
            for line in result.errors:
                if line.strip():
                    self.assertIn(line.strip(), out)

    def test_explicit_env_and_cwd(self):
        self.check(self.other, explicit=str(self.repo))
        self.check(self.other, env={"AUTOPKG_TOOLKIT_REPO": str(self.repo)})
        self.check(self.repo)

    def test_refusals(self):
        self.check(self.other)  # nothing named, cwd isn't a repo
        self.check(self.other, explicit=str(self.root / "missing"))
        self.check(self.other, explicit=str(self.other))  # exists, no recipes/
        # an explicit repo that can't be honoured never falls back to the env
        self.check(
            self.other,
            explicit=str(self.other),
            env={"AUTOPKG_TOOLKIT_REPO": str(self.repo)},
        )


if __name__ == "__main__":
    unittest.main()
