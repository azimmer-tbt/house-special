#!/usr/local/autopkg/python
# check_vendor_cache_path.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Local vendor-cache paths exist (SKIP when the cache isn't on this machine).

Usage: check_vendor_cache_path.py <target>   (a recipe file or its app folder)
Why:   methodology lessons 1 and 24
Spec:  specs/guardrail-audits/01-audits.md FR-03

A front end for recipekit.audits, which reads recipes through the shared recipe
model. Prints PASS:, FAIL: or SKIP: lines. Exit 0 pass or skip (could not check),
1 fail, 2 usage or input error.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib" / "python"))

from recipekit.audits import cli  # noqa: E402

if __name__ == "__main__":
    sys.exit(cli("vendor_cache_path"))
