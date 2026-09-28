#!/usr/local/autopkg/python
# autopkg-preflight.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Author-side preflight for AutoPkg recipes.

Runs the guardrail audits against one app folder or a whole recipe repo, then
chains the linter, so one command covers the static rules and the runtime
behaviours the linter can't express.

Usage:
  autopkg-preflight.py [--repo <recipe-repo>] [--app <app-folder>] [--no-lint]
                       [--customer <name> | --all-customers]

  --repo    the repo to check (default: $AUTOPKG_TOOLKIT_REPO, then the current
            directory if it contains recipes/)
  --app     check one app folder; a relative path is looked up in the repo first,
            then the current directory, and must be inside the repo
  --no-lint skip the recipe-linter.sh pass
  --customer <name>  check that customer's repo, linting as that customer
  --all-customers    check every customer in config/customers.yaml in turn

Each audit reports PASS, FAIL or SKIP ("could not check", e.g. the vendor cache
isn't on this machine). Skips don't fail the run.

Exit codes: 0 no failures, 1 any failure, 2 usage or repo error.
Spec: specs/guardrail-audits/02-autopkg-preflight.md
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
LINTER = TOOLKIT_ROOT / "bin" / "recipe-linter.sh"
sys.path.insert(0, str(TOOLKIT_ROOT / "lib" / "python"))

from recipekit import RecipeSet  # noqa: E402
from recipekit.audits import FAIL, PASS, SKIP, run_all  # noqa: E402
from recipekit.customers import CustomerError, load_registry, select  # noqa: E402
from recipekit.repo import (  # noqa: E402
    looks_like_recipe_repo,
    resolve_repo_root,
)

RULE = "=" * 66


def app_folder(repo_root: Path, app: str) -> tuple[Path | None, str | None]:
    """Resolve --app: repo-relative first, then the current directory; it must
    be inside the repo (constitution P-3, P-5)."""
    given = Path(app)
    candidates = (
        [given] if given.is_absolute() else [repo_root / given, Path.cwd() / given]
    )
    for candidate in candidates:
        if candidate.is_dir():
            folder = candidate.resolve()
            if folder != repo_root and repo_root not in folder.parents:
                return None, f"--app {app} is outside the repo ({repo_root})"
            return folder, None
    return (
        None,
        f"--app {app}: not a directory (looked in the repo and the current directory)",
    )


def run_linter(
    repo_root: Path, app: Path | None, customer=None
) -> tuple[str, list[str]]:
    """Chain recipe-linter.sh. Exit 1 is lint findings; exit 2 is the linter failing."""
    if not LINTER.exists():
        return FAIL, [f"linter not found at {LINTER}"]
    cmd = (
        [str(LINTER), "--dir", str(app)]
        if app
        else [str(LINTER), "--repo", str(repo_root)]
    )
    if customer is not None:
        cmd += ["--customer", customer.name]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    lines = (result.stdout + result.stderr).strip().splitlines()
    if result.returncode == 0:
        return PASS, lines
    if result.returncode == 2:
        return FAIL, ["the linter itself failed (exit 2), not a lint finding:", *lines]
    return FAIL, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--repo", help="path to the AutoPkg recipe repo")
    parser.add_argument(
        "--app", help="check a single app folder instead of the whole repo"
    )
    parser.add_argument(
        "--no-lint", action="store_true", help="skip the recipe-linter.sh pass"
    )
    parser.add_argument(
        "--customer", help="check this customer (config/customers.yaml)"
    )
    parser.add_argument(
        "--all-customers", action="store_true", help="check every registered customer"
    )
    args = parser.parse_args(argv)

    if args.all_customers:
        if args.customer or args.repo or args.app:
            print(
                "ERROR: --all-customers can't be combined with --customer, --repo "
                "or --app",
                file=sys.stderr,
            )
            return 2
        try:
            customers = load_registry().all()
        except CustomerError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        if not customers:
            print(
                "ERROR: --all-customers: no customers are registered", file=sys.stderr
            )
            return 2
        worst = 0
        for customer in customers:
            print(f"=== Customer: {customer.name}")
            code = check(str(customer.recipe_repo()), None, args.no_lint, customer)
            worst = max(worst, code)
        return worst

    explicit = bool(
        args.repo
        or os.environ.get("AUTOPKG_TOOLKIT_REPO")
        or looks_like_recipe_repo(Path.cwd())
    )
    try:
        customer = select(args.customer, needed=not explicit)
    except CustomerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    repo = args.repo if explicit or customer is None else str(customer.recipe_repo())
    return check(repo, args.app, args.no_lint, customer)


def check(repo: str | None, app_arg: str | None, no_lint: bool, customer) -> int:
    """One preflight run: audits over the repo (or one app), then the linter."""
    resolved = resolve_repo_root(repo)
    if not resolved.ok:
        for line in resolved.errors:
            print(f"ERROR: {line}", file=sys.stderr)
        return 2
    repo_root = resolved.root

    app = None
    if app_arg:
        app, error = app_folder(repo_root, app_arg)
        if error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
    recipes = RecipeSet.load(app) if app else RecipeSet.load_repo(repo_root)

    print(RULE)
    print("AUTOPKG PREFLIGHT")
    print(f"  toolkit: {TOOLKIT_ROOT}")
    print(f"  repo:    {repo_root}")
    if customer is not None:
        print(f"  customer: {customer.name}")
    print(RULE)

    counts = {PASS: 0, FAIL: 0, SKIP: 0}
    pairs = [p for p in recipes.pairs() if p.download or p.pkg]
    for problem in (f for f in recipes.findings if f.code == "recipe_invalid"):
        counts[FAIL] += 1
        folder = Path(problem.file).parent
        try:
            folder = folder.relative_to(repo_root)
        except ValueError:
            pass
        print(f"\nChecking: {folder}")
        print("  [FAIL] recipe_parse")
        where = problem.file + (f":{problem.line}" if problem.line else "")
        print(f"         FAIL: {where}: {problem.message}")
    if not pairs:
        print("\nWARNING: no app folders with recipes found; only the linter runs.")

    for pair in pairs:
        try:
            label = pair.folder.relative_to(repo_root)
        except ValueError:
            label = pair.folder
        print(f"\nChecking: {label}")
        for result in run_all(pair):
            counts[result.status] += 1
            print(f"  [{result.status}] {result.name}")
            if result.status != PASS:
                for status, text in result.lines:
                    if status != PASS:
                        print(f"         {status}: {text}")

    if not no_lint:
        print("\nChecking: static lint rules (recipe-linter.sh)")
        status, lines = run_linter(repo_root, app, customer)
        counts[status] += 1
        print(f"  [{status}] recipe_linter")
        if status != PASS:
            for line in lines:
                print(f"         {line}")

    total = sum(counts.values())
    print("\n" + "-" * 66)
    summary = f"Result: {counts[PASS]}/{total} PASSED"
    if counts[FAIL]:
        summary += f"  |  {counts[FAIL]} FAILED"
    if counts[SKIP]:
        summary += f"  |  {counts[SKIP]} SKIPPED (could not check on this machine)"
    print(summary)
    print("\nA clean preflight is not a substitute for a real `autopkg run`.")
    print("See reference/methodology.md -- every bug it catalogs passed review first.")
    print(RULE)
    return 1 if counts[FAIL] else 0


if __name__ == "__main__":
    sys.exit(main())
