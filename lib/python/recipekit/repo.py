# repo.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Recipe-repo resolution for Python front ends: the twin of `resolve_repo_root`
in lib/toolkit-common.sh (specs/toolkit/01-toolkit-common.md; constitution
P-2 to P-6). Same precedence, same refusals, same messages; it returns a result
instead of exiting, and `tests/python/test_repo.py` checks it against the bash
routine.

Precedence: the explicit argument, then $AUTOPKG_TOOLKIT_REPO, then the current
directory only if it is a recipe repo. A named source that can't be honoured is an
error, never a fallback.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RepoResult:
    root: Path | None
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.root is not None


def looks_like_recipe_repo(candidate: Path) -> bool:
    return (candidate / "recipes").is_dir()


def resolve_repo_root(
    explicit: str | None = None, cwd: Path | None = None
) -> RepoResult:
    """Resolve the recipe repo. Errors carry the bash routine's wording."""
    env = os.environ.get("AUTOPKG_TOOLKIT_REPO", "")
    if explicit:
        candidate, source = Path(explicit), "--repo"
    elif env:
        candidate, source = Path(env), "$AUTOPKG_TOOLKIT_REPO"
    else:
        candidate = (cwd or Path.cwd()).resolve()
        source = "current directory"
        if not looks_like_recipe_repo(candidate):
            return RepoResult(
                None,
                [
                    "No recipe repo specified, and the current directory is not one.",
                    "  (a recipe repo is a directory containing recipes/)",
                    "",
                    "Specify one of:",
                    "  --repo /path/to/recipe-repo",
                    "  export AUTOPKG_TOOLKIT_REPO=/path/to/recipe-repo",
                    "  cd into the recipe repo before running",
                ],
            )

    if not candidate.is_dir():
        return RepoResult(
            None, [f"Repo path from {source} does not exist: {candidate}"]
        )
    candidate = candidate.resolve()
    if not looks_like_recipe_repo(candidate):
        return RepoResult(
            None,
            [
                f"Repo path from {source} does not look like an AutoPkg recipe repo:",
                f"  {candidate}",
                "  (expected a recipes/ directory inside it)",
                "",
                "Refusing to guess. If this really is the repo, create recipes/ first.",
            ],
        )
    return RepoResult(candidate)
