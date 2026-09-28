# org.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Org naming for Python front ends: the twin of read_org_config and org_render in
lib/toolkit-common.sh (specs/toolkit/01-toolkit-common.md FR-08). Same file
format, precedence, validation messages and tokens.

Precedence: the explicit file, then $AUTOPKG_TOOLKIT_ORG, then config/org.yaml.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ORG = TOOLKIT_ROOT / "config" / "org.yaml"


@dataclass
class Org:
    file: Path
    name: str
    identifier_prefix: str
    pkgname_prefix: str
    internal_domain: str
    vendor_dir: str
    fleet_min_macos: str

    @property
    def identifier_prefix_re(self) -> str:
        return self.identifier_prefix.replace(".", "\\.")

    def render(self, text: str) -> str:
        """Substitute {{TOKENS}} literally, in the same order as org_render."""
        if "{{" not in text:
            return text
        for token, value in (
            ("{{ORG_NAME}}", self.name),
            (
                "{{IDENTIFIER_PREFIX_RE_YAML}}",
                self.identifier_prefix.replace(".", "\\\\."),
            ),
            ("{{IDENTIFIER_PREFIX_RE}}", self.identifier_prefix_re),
            ("{{IDENTIFIER_PREFIX}}", self.identifier_prefix),
            ("{{PKGNAME_PREFIX}}", self.pkgname_prefix),
            ("{{INTERNAL_DOMAIN}}", self.internal_domain),
            ("{{VENDOR_DIR}}", self.vendor_dir),
        ):
            text = text.replace(token, value)
        return text


def _value(text: str, key: str) -> str:
    """The value of the first top-level `key:` line (as _org_yaml_value)."""
    for line in text.splitlines():
        if re.match(rf"^{key}:", line):
            val = line.split(":", 1)[1].lstrip()
            m = re.match(r'^"([^"]*)"', val) or re.match(r"^'([^']*)'", val)
            if m:
                return m.group(1)
            return val.split("#", 1)[0].rstrip()
    return ""


KEYS = (
    "org_name",
    "identifier_prefix",
    "pkgname_prefix",
    "internal_domain",
    "vendor_dir",
    "fleet_min_macos",
)


def _values(path: Path) -> dict[str, str]:
    """The keys a file sets (a key it leaves out is absent, not empty)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return {k: _value(text, k) for k in KEYS if re.search(rf"^{k}:", text, re.M)}


def read_org_config(
    file: str | Path | None = None, overlay: str | Path | None = None
) -> tuple[Org | None, str | None]:
    """(org, None) or (None, error message without the ERROR: prefix).

    `overlay` is a customer's org.yaml (specs/toolkit/02-customers.md FR-03): each
    key it sets replaces the base file's; the merged values are then validated.
    """
    path = Path(file or os.environ.get("AUTOPKG_TOOLKIT_ORG") or DEFAULT_ORG)
    if not path.is_file():
        return None, f"org config not found: {path}"
    values = _values(path)
    label = path
    if overlay is not None and Path(overlay).is_file():
        values.update(_values(Path(overlay)))
        label = Path(f"{overlay} (over {path})")
    return _build(values, label)


def _build(values: dict[str, str], path: Path) -> tuple[Org | None, str | None]:
    name = values.get("org_name", "")
    prefix = values.get("identifier_prefix", "")
    pkgname = values.get("pkgname_prefix", "")
    fleet = values.get("fleet_min_macos", "")
    if not re.fullmatch(r"[A-Za-z0-9]+(\.[A-Za-z0-9-]+)+", prefix):
        return None, (
            f"{path}: identifier_prefix '{prefix}' must be reverse-DNS, "
            "e.g. com.example.autopkg"
        )
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", pkgname):
        return None, (
            f"{path}: pkgname_prefix '{pkgname}' must be non-empty and filename-safe, "
            "e.g. Example_"
        )
    if fleet and not re.fullmatch(r"[0-9]+(\.[0-9]+){0,2}", fleet):
        return None, (
            f"{path}: fleet_min_macos '{fleet}' must be a macOS version, "
            "e.g. 14 or 14.6"
        )
    vendor_dir = values.get("vendor_dir") or (
        pkgname[:-1] if pkgname.endswith("_") else pkgname
    )
    return (
        Org(
            path,
            name or prefix,
            prefix,
            pkgname,
            values.get("internal_domain", ""),
            vendor_dir,
            fleet,
        ),
        None,
    )
