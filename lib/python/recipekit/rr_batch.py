# rr_batch.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""Run Recipe Robot over a CSV of apps and file the recipes into a recipe repo
(specs/rr-batch/). The front end is bin/rr-batch.sh; its header is the usage.

For each row ("Status","Vendor","AppName","URL") that the status filter lets
through, Recipe Robot runs with the URL; the recipes it reports writing are
copied to <output>/recipes/<Vendor>/<AppName>/<AppName>.<type>.recipe.yaml with
NAME, Identifier and ParentRecipe set from the org prefix and the CSV AppName
(this replaces rr-rename-postprocess.sh). Exit codes: 0 all passed, 1 a Recipe
Robot run failed, 2 usage or config error (or the linter could not run).
"""

from __future__ import annotations

import csv
import os
import plistlib
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from .org import read_org_config

DEFAULT_RR = "/Applications/Recipe Robot.app/Contents/Resources/scripts/recipe-robot"
RR_PREFS = Path("~/Library/Preferences/com.elliotjordan.recipe-robot.plist")
SMART_QUOTES = "“”‘’"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
# Recipe Robot's own file names: <App>.<type>.recipe, plus .yaml in YAML mode.
GENERATED = re.compile(
    r"^(?P<stem>.+)\.(?P<type>[A-Za-z0-9-]+)\.recipe(?P<yaml>\.yaml)?$"
)
KIT_ROOT = Path(__file__).resolve().parents[3]


class UsageError(Exception):
    pass


# ── CSV ───────────────────────────────────────────────────────────────────────


@dataclass
class Row:
    status: str
    vendor: str
    name: str
    url: str


def parse_line(line: str) -> Row | None:
    """A "Status","Vendor","AppName","URL" line, quotes optional, commas inside
    quotes kept; None unless there are exactly four fields."""
    fields = next(csv.reader([line.strip()], skipinitialspace=True), [])
    if len(fields) != 4:
        return None
    status, vendor, name, url = (f.strip().strip('"').strip() for f in fields)
    return Row(status, vendor, name, url)


def skip_reason(row: Row, recipes_dir: Path) -> str:
    """Why a row is not processed; empty to process it (spec FR-2)."""
    if row.status == "DONE":
        return "DONE"
    if row.status == "SKIP":
        return "SKIP-status"
    if row.status == "TEST":
        return "TEST-existing" if (recipes_dir / row.vendor / row.name).is_dir() else ""
    if row.status == "":
        return ""
    return "unrecognized"


# ── Recipe Robot output ───────────────────────────────────────────────────────


def reported_recipes(output: str) -> list[Path]:
    """The recipe files a Recipe Robot run says it wrote (FR-5 discovery): each
    is printed on a line of its own after "Generating <type> recipe..."."""
    found = []
    for line in output.splitlines():
        text = ANSI.sub("", line).strip()
        path = Path(text)
        if text.startswith("/") and GENERATED.match(path.name) and path.is_file():
            if path not in found:
                found.append(path)
    return found


def normalize_text(text: str, kind: str, name: str, prefix: str) -> str:
    """Set Identifier, ParentRecipe (pkg) and Input NAME for a CSV AppName."""
    ident = f"{prefix}.{kind}.{name}"
    text = re.sub(r"(?m)^Identifier:.*$", f"Identifier: {ident}", text, count=1)
    if kind == "pkg":
        parent = f"{prefix}.download.{name}"
        text = re.sub(
            r"(?m)^ParentRecipe:.*$", f"ParentRecipe: {parent}", text, count=1
        )
    # NAME under the top-level Input: block (two-space indent, as Recipe Robot writes).
    match = re.search(r"(?ms)^Input:\n(?P<body>(?:[ \t]+.*\n?)*)", text)
    if match:
        body = re.sub(r"(?m)^  NAME:.*$", f"  NAME: {name}", match["body"], count=1)
        text = text[: match.start("body")] + body + text[match.end("body") :]
    return text


# ── The run ───────────────────────────────────────────────────────────────────


@dataclass
class Options:
    input: Path | None = None
    log_dir: Path | None = None
    output_dir: Path | None = None
    vendor: str = ""
    ignore_existing: bool = False
    verbose: bool = False
    lint: bool = False
    config: Path = KIT_ROOT / "config" / "checks.yaml"
    org: str = ""
    force: bool = False


@dataclass
class Batch:
    opts: Options
    prefix: str
    org_file: Path
    rr_bin: str
    stamp: str = field(default_factory=lambda: time.strftime("%Y%m%d_%H%M%S"))
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    failures: list[str] = field(default_factory=list)

    def start(self) -> None:
        self.run_log_dir = self.opts.log_dir / self.stamp
        self.run_log_dir.mkdir(parents=True, exist_ok=True)
        self.combined = self.run_log_dir / f"rr-batch_{self.stamp}.log"
        self.recipes_dir = self.opts.output_dir / "recipes"
        self.recipes_dir.mkdir(parents=True, exist_ok=True)

    def log(self, message: str = "") -> None:
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        print(line, flush=True)
        with open(self.combined, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def rr_args(self) -> list[str]:
        args = []
        if self.opts.ignore_existing:
            args.append("--ignore-existing")
        if self.opts.verbose:
            args.append("--verbose")
        return args

    def process(self, row: Row) -> None:
        self.total += 1
        app_log_dir = self.run_log_dir / row.name
        app_log_dir.mkdir(parents=True, exist_ok=True)
        app_log = app_log_dir / f"{row.name}_{self.stamp}.log"
        self.log(f"START [{row.name}] {row.url}")
        try:
            done = subprocess.run(
                [self.rr_bin, *self.rr_args(), row.url],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            output, code = done.stdout.decode("utf-8", "replace"), done.returncode
        except OSError as exc:
            output, code = f"{exc}\n", 127
        with open(app_log, "a", encoding="utf-8") as f:
            f.write(output)
        if code != 0:
            self.failed += 1
            self.failures.append(row.name)
            self.log(f"FAIL  [{row.name}] exit {code} — see {app_log}")
            return
        self.passed += 1
        self.log(f"PASS  [{row.name}] exit {code}")
        found = reported_recipes(output)
        if not found:
            self.log(f"WARN  [{row.name}] Recipe Robot reported no recipe files")
        for path in found:
            self.file_recipe(path, row)
        # The folder exists even if nothing was written (.overrides is optional
        # and org-defined: never generated).
        (self.recipes_dir / row.vendor / row.name).mkdir(parents=True, exist_ok=True)

    def file_recipe(self, src: Path, row: Row) -> None:
        match = GENERATED.match(src.name)
        kind = match["type"]
        if kind not in ("download", "pkg"):
            self.log(f"SKIP  [{row.name}] {src.name}: only download and pkg recipes")
            return
        if not match["yaml"]:
            self.log(
                f"WARN  [{row.name}] {src.name} is a plist recipe; set Recipe Robot's"
                " RecipeFormat to yaml (recipe-robot --config)"
            )
            return
        target = (
            self.recipes_dir / row.vendor / row.name / f"{row.name}.{kind}.recipe.yaml"
        )
        if target.exists() and not self.opts.force:
            self.log(
                f"WARN  [{row.name}] Target exists, skipping: {target}"
                " (use --force to overwrite)"
            )
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8")
        target.write_text(normalize_text(text, kind, row.name, self.prefix), "utf-8")
        self.log(f"DIST  [{row.name}] {src.name} → {target}")

    def lint(self) -> int:
        self.log("")
        self.log("=== Running linter on generated recipes ===")
        linter = KIT_ROOT / "bin" / "recipe-linter.sh"
        done = subprocess.run(
            [
                str(linter),
                "--config",
                str(self.opts.config),
                "--org",
                str(self.org_file),
                "--dir",
                str(self.recipes_dir),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        sys.stdout.write(done.stdout)
        with open(self.combined, "a", encoding="utf-8") as f:
            f.write(done.stdout)
        if done.returncode == 1:
            self.log("LINT FAILURE — one or more generated recipes failed lint checks")
        elif done.returncode >= 2:
            self.log(f"LINTER ERROR — invalid config? (exit {done.returncode})")
            self.total = self.passed = self.failed = 0
        return done.returncode

    def summary(self) -> None:
        self.log("")
        self.log("=== rr-batch complete ===")
        self.log(
            f"Total: {self.total}  |  Pass: {self.passed}  |  Fail: {self.failed}"
            f"  |  Skip: {self.skipped}"
        )
        if self.failures:
            self.log("Failed packages:")
            for name in self.failures:
                self.log(f"  - {name}")
        self.log(f"Combined log: {self.combined}")
        self.log(f"Per-app logs: {self.run_log_dir}/<name>/")


# ── Front end ─────────────────────────────────────────────────────────────────


def parse_args(argv: list[str]) -> Options | None:
    """Options, or None for --help."""
    opts = Options()
    value_flags = {
        "-i": "input",
        "--input": "input",
        "--log-dir": "log_dir",
        "-o": "output_dir",
        "--output-dir": "output_dir",
        "--vendor": "vendor",
        "--config": "config",
        "--specs": "config",
        "--org": "org",
    }
    switches = {
        "-e": "ignore_existing",
        "--ignore-existing": "ignore_existing",
        "-v": "verbose",
        "--verbose": "verbose",
        "-l": "lint",
        "--lint": "lint",
        "--force": "force",
    }
    args = list(argv)
    while args:
        arg = args.pop(0)
        if arg in ("-h", "--help"):
            return None
        if arg in switches:
            setattr(opts, switches[arg], True)
        elif arg in value_flags:
            if not args or not args[0] or args[0].startswith("-"):
                raise UsageError(f"{arg} requires a value")
            value = args.pop(0)
            attr = value_flags[arg]
            setattr(opts, attr, value if attr in ("vendor", "org") else Path(value))
        else:
            raise UsageError(f"Unknown option: {arg}")
    if opts.input is None:
        raise UsageError("-i input file is required.")
    if opts.log_dir is None:
        raise UsageError("--log-dir is required.")
    if not opts.input.is_file():
        raise UsageError(f"Input file not found: {opts.input}")
    return opts


def check_prefs(prefix: str) -> None:
    """Warn (and on a terminal, pause) when Recipe Robot isn't set for YAML and
    the org prefix (spec FR-10)."""
    path = Path(os.environ.get("RR_PREFS") or RR_PREFS).expanduser()  # tests set it
    problems = []
    try:
        with open(path, "rb") as f:
            prefs = plistlib.load(f)
    except (OSError, plistlib.InvalidFileException, ValueError):
        prefs = None
        problems.append(f"Recipe Robot preferences not found at {path}.")
    if prefs is not None:
        if str(prefs.get("RecipeFormat", "")).lower() != "yaml":
            problems.append("Recipe Robot's RecipeFormat is not yaml.")
        if prefs.get("RecipeIdentifierPrefix") != prefix:
            problems.append(
                f"Recipe Robot's RecipeIdentifierPrefix is not {prefix}"
                " (identifiers are rewritten anyway)."
            )
    if not problems:
        return
    for problem in problems:
        print(f"WARNING: {problem}", file=sys.stderr)
    print(
        "         Run 'recipe-robot --config' to set format and recipe prefix.",
        file=sys.stderr,
    )
    if sys.stdin.isatty():
        print(
            "         Press Enter to continue anyway, or Ctrl-C to abort.",
            file=sys.stderr,
        )
        input()


def main(argv: list[str] | None = None) -> int:
    try:
        opts = parse_args(sys.argv[1:] if argv is None else argv)
    except UsageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if opts is None:
        print(__doc__)
        return 0
    rr_bin = os.environ.get("RR_BIN") or DEFAULT_RR
    if not os.access(rr_bin, os.X_OK):
        print(
            f"ERROR: Recipe Robot not found or not executable at: {rr_bin}",
            file=sys.stderr,
        )
        return 2
    org, error = read_org_config(opts.org or None)
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    opts.output_dir = (opts.output_dir or Path.cwd()).resolve()
    try:
        opts.output_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        print(
            f"ERROR: Cannot access output directory: {opts.output_dir}", file=sys.stderr
        )
        return 2
    text = opts.input.read_text(encoding="utf-8", errors="replace")
    if any(q in text for q in SMART_QUOTES):
        print(
            f"ERROR: Smart quotes detected in {opts.input}."
            " Replace with straight quotes before running.",
            file=sys.stderr,
        )
        return 2
    check_prefs(org.identifier_prefix)

    batch = Batch(opts, org.identifier_prefix, org.file, rr_bin)
    batch.start()
    batch.log("=== rr-batch start ===")
    batch.log(f"Input file:  {opts.input}")
    batch.log(f"Output dir:  {opts.output_dir}")
    batch.log(f"Log dir:     {batch.run_log_dir}")
    batch.log(f"Ignore existing: {str(opts.ignore_existing).lower()}")
    batch.log(f"Verbose: {str(opts.verbose).lower()}")
    batch.log(f"Lint: {str(opts.lint).lower()}")
    batch.log(f"Specs: {opts.config}")
    batch.log(f"Force: {str(opts.force).lower()}")
    if opts.vendor:
        batch.log(f"Vendor override: {opts.vendor}")
    batch.log("")

    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        row = parse_line(raw)
        if row is None or not all((row.vendor or opts.vendor, row.name, row.url)):
            batch.log(f"SKIP  [malformed line]: {raw}")
            batch.skipped += 1
            continue
        if opts.vendor:
            row.vendor = opts.vendor
        reason = skip_reason(row, batch.recipes_dir)
        if reason:
            batch.log(f'SKIP  [{reason}] [{row.name}] (status: "{row.status}")')
            batch.skipped += 1
            continue
        batch.process(row)

    lint_code = batch.lint() if opts.lint else 0
    batch.summary()
    if lint_code >= 2:
        return 2
    return 1 if batch.failed else 0


if __name__ == "__main__":
    sys.exit(main())
