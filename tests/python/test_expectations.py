# test_expectations.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""AC-08.2: derived facts for every shipped example match a checked-in file.

When a change to the model is intended, regenerate and review the diff:

    RECIPEKIT_REGEN=1 tk_python -m unittest discover -s tests/python
    git diff tests/python/expected/
"""

import json
import os
import unittest

from helpers import KIT_ROOT
from recipekit import RecipeSet, pair_facts

EXPECTED = KIT_ROOT / "tests" / "python" / "expected"


def example_folders():
    acme = KIT_ROOT / "customer" / "acme" / "output" / "recipes"
    folders = sorted({p.parent for p in acme.rglob("*.recipe.yaml")})
    folders += sorted(
        p for p in (KIT_ROOT / "templates").glob("*/example-*") if p.is_dir()
    )
    return folders


def expected_name(folder) -> str:
    rel = folder.relative_to(KIT_ROOT).as_posix()
    return (
        rel.replace("customer/acme/output/recipes/", "acme/").replace("/", "__")
        + ".json"
    )


def snapshot(folder) -> dict:
    recipes = RecipeSet.load(folder)
    return {
        "pairs": {pair.stem: pair_facts(pair) for pair in recipes.pairs()},
        "findings": sorted(
            (f.code, f.severity, os.path.basename(f.file))
            for f in recipes.all_findings()
        ),
    }


class ExpectationsTest(unittest.TestCase):
    def test_ac_08_2_facts_match_the_checked_in_expectations(self):
        regen = os.environ.get("RECIPEKIT_REGEN") == "1"
        if regen:
            EXPECTED.mkdir(parents=True, exist_ok=True)
        for folder in example_folders():
            name = expected_name(folder)
            got = json.loads(json.dumps(snapshot(folder), sort_keys=True, default=str))
            path = EXPECTED / name
            if regen:
                path.write_text(
                    json.dumps(got, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
                continue
            with self.subTest(name):
                self.assertTrue(
                    path.is_file(), f"no expectation file {name}; regenerate"
                )
                want = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(got, want)

    def test_no_stale_expectation_files(self):
        names = {expected_name(f) for f in example_folders()}
        stale = sorted(p.name for p in EXPECTED.glob("*.json") if p.name not in names)
        self.assertEqual(stale, [])


if __name__ == "__main__":
    unittest.main()
