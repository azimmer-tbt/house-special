# __init__.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""recipekit: one shared model of AutoPkg recipe pairs.

Spec: specs/recipekit/01-recipe-model.md. Every tool that reasons about recipes asks
this package instead of parsing recipe files itself (AIP-01).

    from recipekit import RecipeSet
    recipes = RecipeSet.load_repo("customer/acme/output")
    for pair in recipes.pairs():
        print(pair.stem, pair.facts()["source"]["value"])
"""

from .derive import facts as pair_facts
from .loader import Finding
from .model import Pair, Recipe, RecipeSet, Step

__all__ = ["Finding", "Pair", "Recipe", "RecipeSet", "Step", "pair_facts"]
