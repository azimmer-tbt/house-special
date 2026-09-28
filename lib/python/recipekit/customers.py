# customers.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Customers: several orgs from one kit (specs/toolkit/02-customers.md).

One registry (config/customers.yaml) says where each customer's folder is; each
customer carries its own optional files (org.yaml, paths.yaml, checks.local.yaml,
.leak-patterns). No registry means no customers, and every tool behaves as before.

Usage:
  tk_python -m recipekit.customers list [--output text|json|tsv]
  tk_python -m recipekit.customers show [<name>] [--output text|json|env]

`--output env` prints shell assignments (CUSTOMER_*, ORG_*) for
`eval "$(...)"`; `--output tsv` prints name, folder and denylist path per line.
Shell tools use these through resolve_customer in lib/toolkit-common.sh.

Exit codes: 0 ok, 2 usage or config error.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from .org import DEFAULT_ORG, TOOLKIT_ROOT, Org, read_org_config

DEFAULT_REGISTRY = TOOLKIT_ROOT / "config" / "customers.yaml"


class CustomerError(Exception):
    """A config error: the message names what's wrong (exit 2 in front ends)."""


@dataclass
class Customer:
    name: str
    root: Path

    @property
    def org_file(self) -> Path:
        return self.root / "org.yaml"

    @property
    def checks_local(self) -> Path:
        return self.root / "checks.local.yaml"

    @property
    def leak_patterns(self) -> Path:
        return self.root / ".leak-patterns"

    def paths(self) -> dict:
        path = self.root / "paths.yaml"
        if not path.is_file():
            return {}
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise CustomerError(f"{path} is not valid YAML: {exc}") from exc
        return data if isinstance(data, dict) else {}

    def recipe_repo(self) -> Path:
        """`recipe_repo.root` from paths.yaml, relative to the customer folder;
        `output` when unset (FR-03)."""
        repo = self.paths().get("recipe_repo")
        root = repo.get("root") if isinstance(repo, dict) else repo
        path = Path(os.path.expanduser(str(root or "output")))
        return path if path.is_absolute() else self.root / path

    def org(self, base: str | Path | None = None) -> Org:
        """The kit's org.yaml (or `base`) with this customer's keys laid over it."""
        org, error = read_org_config(base or DEFAULT_ORG, overlay=self.org_file)
        if error:
            raise CustomerError(error)
        return org

    def as_dict(self) -> dict:
        org = self.org()
        return {
            "name": self.name,
            "root": str(self.root),
            "recipe_repo": str(self.recipe_repo()),
            "org_file": str(self.org_file) if self.org_file.is_file() else None,
            "org": {
                "org_name": org.name,
                "identifier_prefix": org.identifier_prefix,
                "pkgname_prefix": org.pkgname_prefix,
                "vendor_dir": org.vendor_dir,
                "fleet_min_macos": org.fleet_min_macos,
            },
            "checks_local": (
                str(self.checks_local) if self.checks_local.is_file() else None
            ),
            "leak_patterns": (
                str(self.leak_patterns) if self.leak_patterns.is_file() else None
            ),
        }


@dataclass
class Registry:
    path: Path | None
    default: str | None
    customers: dict[str, Path]

    def get(self, name: str) -> Customer:
        if not self.customers:
            # No registry: a name still means customer/<name> in the kit, as it did
            # before customers were registered (FR-01, AC-01.3).
            legacy = TOOLKIT_ROOT / "customer" / name
            if legacy.is_dir():
                return Customer(name, legacy)
        if name not in self.customers:
            raise CustomerError(
                f"unknown customer '{name}'; registered: {self._names()}"
            )
        root = self.customers[name]
        if not root.is_dir():
            raise CustomerError(f"customer '{name}': folder not found: {root}")
        return Customer(name, root)

    def all(self) -> list[Customer]:
        return [self.get(n) for n in sorted(self.customers)]

    def _names(self) -> str:
        return ", ".join(sorted(self.customers)) or "(none)"


def load_registry(path: str | Path | None = None) -> Registry:
    """The registry, or an empty one when there's no file (FR-01, AC-01.3)."""
    path = Path(path or os.environ.get("AUTOPKG_TOOLKIT_CUSTOMERS") or DEFAULT_REGISTRY)
    if not path.is_file():
        return Registry(None, None, {})
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise CustomerError(f"{path} is not valid YAML: {exc}") from exc
    raw = data.get("customers") or {}
    if not isinstance(raw, dict):
        raise CustomerError(f"{path}: 'customers' must map names to folders")
    customers = {}
    for name, folder in raw.items():
        folder = Path(os.path.expanduser(str(folder)))
        customers[str(name)] = folder if folder.is_absolute() else TOOLKIT_ROOT / folder
    default = data.get("default")
    if default is not None and str(default) not in customers:
        raise CustomerError(f"{path}: default customer '{default}' is not in customers")
    return Registry(path, str(default) if default is not None else None, customers)


def select(name: str | None = None, needed: bool = True) -> Customer | None:
    """FR-02: --customer, then $AUTOPKG_TOOLKIT_CUSTOMER, then the registry default.

    With `needed=False` (the caller has an explicit target), only a named customer
    is used: the default never applies silently to an explicit --repo or --dir.
    """
    registry = load_registry()
    chosen = name or os.environ.get("AUTOPKG_TOOLKIT_CUSTOMER") or None
    if chosen:
        return registry.get(chosen)
    if not needed or not registry.customers:
        return None
    if registry.default:
        return registry.get(registry.default)
    if len(registry.customers) == 1:
        return registry.get(next(iter(registry.customers)))
    raise CustomerError(
        "several customers are registered and none is selected; use --customer "
        f"<name> or set a default in {registry.path}. Registered: {registry._names()}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="recipekit.customers",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("command", choices=("list", "show"))
    parser.add_argument("name", nargs="?")
    parser.add_argument(
        "--output", choices=("text", "json", "env", "tsv"), default="text"
    )
    args = parser.parse_args(argv)
    try:
        registry = load_registry()
        if args.command == "list":
            rows = [
                {"name": n, "root": str(p), "default": n == registry.default}
                for n, p in sorted(registry.customers.items())
            ]
            if args.output == "json":
                print(json.dumps(rows, indent=2))
            elif args.output == "tsv":
                for customer in registry.all():
                    leak = (
                        customer.leak_patterns
                        if customer.leak_patterns.is_file()
                        else ""
                    )
                    print(f"{customer.name}\t{customer.root}\t{leak}")
            else:
                for row in rows:
                    mark = " (default)" if row["default"] else ""
                    print(f"{row['name']}{mark}: {row['root']}")
            return 0
        customer = registry.get(args.name) if args.name else select()
        if customer is None:
            print("ERROR: no customers are registered", file=sys.stderr)
            return 2
        info = customer.as_dict()
        org = customer.org()
    except CustomerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.output == "env":
        values = {
            "CUSTOMER_NAME": customer.name,
            "CUSTOMER_ROOT": str(customer.root),
            "CUSTOMER_REPO": str(customer.recipe_repo()),
            "CUSTOMER_LEAK_PATTERNS": info["leak_patterns"] or "",
            "ORG_CONFIG_FILE": str(org.file),
            "ORG_NAME": org.name,
            "ORG_IDENTIFIER_PREFIX": org.identifier_prefix,
            "ORG_PKGNAME_PREFIX": org.pkgname_prefix,
            "ORG_INTERNAL_DOMAIN": org.internal_domain,
            "ORG_VENDOR_DIR": org.vendor_dir,
            "ORG_FLEET_MIN_MACOS": org.fleet_min_macos,
        }
        for key, value in values.items():
            print(f"{key}={shlex.quote(value)}")
        return 0
    if args.output == "json":
        print(json.dumps(info, indent=2))
    else:
        for key, value in info.items():
            print(f"{key + ':':16} {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
