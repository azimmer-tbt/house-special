#!/usr/local/autopkg/python
# check_readme_exists.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""The app folder has a non-empty README.md.

Usage: check_readme_exists.py <target>   (an app folder (or a recipe file in it))
Why:   guardrails/GUARDRAILS.md
Spec:  specs/guardrail-audits/01-audits.md FR-09

A front end for recipekit.audits, which reads recipes through the shared recipe
model. Prints PASS:, FAIL: or SKIP: lines. Exit 0 pass or skip (could not check),
1 fail, 2 usage or input error.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib" / "python"))

from recipekit.audits import cli  # noqa: E402

if __name__ == "__main__":
    sys.exit(cli("readme_exists"))
