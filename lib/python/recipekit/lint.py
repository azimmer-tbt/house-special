# lint.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""The recipe linter: config-driven checks from config/checks.yaml.

Specs: specs/recipe-linter/. A port of the bash linter that keeps its command
line, output and exit codes (toolkit constitution P-10). Rule *values* are read
from the recipe text exactly as the bash engine read them (line ranges, first
`key:` line, `grep -E` per line), so every rule means what it meant before; that
is what the parity test proves. Rules that need real structure belong in the
recipe model, not here.

Exit codes: 0 all checks passed, 1 lint errors or warnings, 2 usage or config error.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .customers import CustomerError, load_registry, select
from .org import TOOLKIT_ROOT, Org, read_org_config
from .repo import looks_like_recipe_repo, resolve_repo_root

DEFAULT_CHECKS = TOOLKIT_ROOT / "config" / "checks.yaml"
RED, GREEN, YELLOW, BLUE, NC = (
    "\033[0;31m",
    "\033[0;32m",
    "\033[1;33m",
    "\033[0;34m",
    "\033[0m",
)
VAL_TYPES = (
    "regex",
    "exact",
    "list",
    "exists",
    "not_exists",
    "absent",
    "exists_any",
    "classification",
)
CLAIM_RE = re.compile(r"^\s*Pattern\s+(\d[a-e]?)\b")
POSIX_CLASSES = {
    "[:space:]": r"\s",
    "[:blank:]": r" \t",
    "[:alpha:]": "a-zA-Z",
    "[:digit:]": "0-9",
    "[:alnum:]": "a-zA-Z0-9",
    "[:upper:]": "A-Z",
    "[:lower:]": "a-z",
    "[:xdigit:]": "0-9A-Fa-f",
    "[:punct:]": r"!-/:-@\[-`{-~",
}


class UsageError(Exception):
    """Exit 2 with an ERROR: message."""


# ── rules ──────────────────────────────────────────────────────────────────────
@dataclass
class Condition:
    source: str = ""
    key: str = ""
    pattern: str = ""
    related_type: str = ""
    related_key: str = ""


@dataclass
class Rule:
    id: str
    severity: str = ""
    description: str = ""
    recipe_type: str = ""
    key: str = ""
    source: str = "self"
    related_type: str = ""
    related_key: str = ""
    val_type: str = ""
    val_pattern: str = ""
    val_list: list[str] = field(default_factory=list)
    pass_msg: str = ""
    fail_msg: str = ""
    prompted_by: str = ""
    conditions: list[Condition] = field(default_factory=list)
    required: bool = True


def _s(value) -> str:
    """A config scalar as the bash parser saw it (booleans print lower case)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def validate_checks(path: Path) -> list[str]:
    """The bash validate_checks_yaml, message for message."""
    if not path.is_file():
        return [f"Specs file not found: {path}"]
    text = path.read_text(encoding="utf-8", errors="replace")
    if not re.search(r"^rules:", text, re.M):
        return [f"Missing 'rules:' top-level key in {path}"]
    ids = re.findall(r'^[ \t]+- id:.*"(.*)".*$', text, re.M)
    if not ids:
        return [f"No rules defined in {path}"]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    if dups:
        return ["Duplicate rule IDs found: " + "\n".join(dups)]
    errors: list[str] = []
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        return [f"{path} is not valid YAML: {exc}"]
    for i, rule in enumerate(data.get("rules") or []):
        if not isinstance(rule, dict):
            continue
        rid = _s(rule.get("id"))
        target = rule.get("check_target") or {}
        allowed = rule.get("allowed_values") or {}
        # As the bash check: a `key:` anywhere in the rule counts, including an
        # exists_any condition's.
        conditions = [c for c in allowed.get("conditions") or [] if isinstance(c, dict)]
        has_key = bool(target.get("key")) or any(c.get("key") for c in conditions)
        if not (
            rid
            and rule.get("severity")
            and rule.get("description")
            and has_key
            and allowed.get("type")
        ):
            errors.append(
                f"Rule starting at line {_rule_line(text, i)} "
                "is missing required fields "
                "(id, severity, description, check_target.key, allowed_values.type)"
            )
        sev = _s(rule.get("severity"))
        if sev and sev not in ("error", "warning", "info"):
            errors.append(
                f"Rule '{rid}' has invalid severity: '{sev}' "
                "(must be error|warning|info)"
            )
        vt = _s(allowed.get("type"))
        if vt and vt not in VAL_TYPES:
            errors.append(f"Rule '{rid}' has invalid allowed_values.type: '{vt}'")
        rt = _s(rule.get("recipe_type"))
        if rt and rt not in ("download", "pkg", "both"):
            errors.append(
                f"Rule '{rid}' has invalid recipe_type: '{rt}' "
                "(must be download|pkg|both)"
            )
    if errors:
        errors.append(f"{len(errors)} validation error(s) in {path}")
    return errors


def _rule_line(text: str, index: int) -> int:
    lines = [
        n for n, line in enumerate(text.splitlines(), 1) if re.match(r"^\s*- id:", line)
    ]
    return lines[index] if index < len(lines) else 0


def load_rules(path: Path, org: Org) -> list[Rule]:
    """Parse checks.yaml after rendering the org's {{TOKENS}} line by line."""
    return [_rule(raw) for raw in _load_yaml(path, org).get("rules") or []]


def _load_yaml(path: Path, org: Org) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    data = yaml.safe_load("\n".join(org.render(line) for line in lines)) or {}
    return data if isinstance(data, dict) else {}


def _rule(raw: dict) -> Rule:
    target = raw.get("check_target") or {}
    allowed = raw.get("allowed_values") or {}
    return Rule(
        id=_s(raw.get("id")),
        severity=_s(raw.get("severity")),
        description=_s(raw.get("description")),
        recipe_type=_s(raw.get("recipe_type")),
        key=_s(target.get("key")),
        source=_s(target.get("source")) or "self",
        related_type=_s(target.get("related_type")),
        related_key=_s(target.get("related_key")),
        val_type=_s(allowed.get("type")),
        val_pattern=_s(allowed.get("pattern")),
        val_list=[_s(v) for v in allowed.get("list") or []],
        pass_msg=_s(raw.get("pass_message")),
        fail_msg=_s(raw.get("fail_message")),
        prompted_by=_s(raw.get("prompted_by")),
        conditions=[
            Condition(
                _s(c.get("source")),
                _s(c.get("key")),
                _s(c.get("pattern")),
                _s(c.get("related_type")),
                _s(c.get("related_key")),
            )
            for c in allowed.get("conditions") or []
            if isinstance(c, dict)
        ],
        required=raw.get("required", True) is not False,
    )


def customer_rules(rules: list[Rule], local: Path, org: Org) -> list[Rule]:
    """A customer's checks.local.yaml over the kit's rules (specs/toolkit/
    02-customers.md FR-04): add always; skip only rules marked required: false.
    Raises UsageError (exit 2) for anything else."""
    if not local.is_file():
        return rules
    try:
        data = _load_yaml(local, org)
    except yaml.YAMLError as exc:
        raise UsageError(f"{local} is not valid YAML: {exc}") from exc
    by_id = {r.id: r for r in rules}
    for rid in [_s(x) for x in data.get("skip") or []]:
        if rid not in by_id:
            raise UsageError(f"{local}: cannot skip {rid}: no such rule")
        if by_id[rid].required:
            raise UsageError(
                f"{local}: cannot skip {rid}: the kit marks it required "
                "(only rules with required: false can be skipped)"
            )
    skipped = {_s(x) for x in data.get("skip") or []}
    added = [_rule(raw) for raw in data.get("rules") or [] if isinstance(raw, dict)]
    for rule in added:
        if rule.id in by_id:
            raise UsageError(f"{local}: rule {rule.id} repeats a kit rule's id")
        problems = []
        if rule.severity not in ("error", "warning", "info"):
            problems.append(f"severity '{rule.severity}'")
        if rule.val_type not in VAL_TYPES:
            problems.append(f"type '{rule.val_type}'")
        if not rule.id or problems:
            raise UsageError(
                f"{local}: rule '{rule.id}' is invalid: "
                + ", ".join(problems or ["no id"])
            )
    return [r for r in rules if r.id not in skipped] + added


# ── grep -E, as the bash engine used it ────────────────────────────────────────
def ere_to_python(pattern: str) -> str:
    """POSIX ERE → Python regex. Only what differs: POSIX character classes."""
    for posix, py in POSIX_CLASSES.items():
        pattern = pattern.replace(posix, py)
    return pattern


def grep(value: str, pattern: str) -> bool:
    """`echo "$value" | grep -qE "$pattern"`: true if any line matches. An invalid
    pattern matches nothing (grep exits 2, which the engine read as no match)."""
    try:
        compiled = re.compile(ere_to_python(pattern))
    except re.error:
        return False
    return any(compiled.search(line) for line in value.split("\n"))


def unescape(pattern: str) -> str:
    return pattern.replace("\\\\", "\\")


def compare_regex(value: str, raw: str) -> bool:
    pattern = unescape(raw)
    if pattern.startswith("^(") and "?" in pattern:
        inner = pattern[2:]
        if inner.startswith("?!"):
            inner = inner[2:]
            neg, depth = "", 0
            for ch in inner:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    if depth == 0:
                        break
                    depth -= 1
                neg += ch
            if neg:
                return not grep(value, neg)
    if re.search(r"\\[0-9]$", pattern):
        for line in value.split("\n"):
            prev = ""
            for part in line.split("."):
                if prev and part == prev:
                    return False
                prev = part
        return True
    return grep(value, pattern)


def compare_exists(value: str, pattern: str) -> bool:
    return grep(value, unescape(pattern or ".+"))


# ── reading values from a recipe (bash get_yaml_value) ──────────────────────────
def _companion_pairs(path: Path, sep: str) -> list[tuple[str, str]]:
    pairs = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = re.sub(r"\s", "", line.split("#", 1)[0])
        if not line or any(q in line for q in "“”‘’"):
            continue
        if sep in line:
            key, val = line.split(sep, 1)
            if key:
                pairs.append((key, val))
    return pairs


def get_value(file: Path, key_path: str, source: str = "self") -> str:
    if source == "directory":
        return str(file.parent)
    parts = key_path.split(".") if key_path else []
    if not parts:
        return ""
    if file.name in (".overrides", ".autopkg_config"):
        sep = "=" if file.name == ".overrides" else ":"
        for key, val in _companion_pairs(file, sep):
            if re.match(rf"^{key_path} ", f"{key} {val}"):
                return val
        return ""
    try:
        text = file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    # bash's `while read` never sees a last line that has no newline.
    read_lines = lines if text.endswith("\n") or not lines else lines[:-1]
    first = parts[0]
    if len(parts) == 1 and first == "filename":
        return file.name
    if first == "Process":
        start = next(
            (i for i, line in enumerate(lines) if line.startswith("Process:")), None
        )
        if start is None:
            return ""
        kept = [line for line in lines[start:] if not re.match(r"^\s*#", line)]
        return "\n".join(kept).rstrip("\n")
    if len(parts) == 1:
        for line in lines:
            if re.match(rf"^{first}:", line):
                val = re.sub(r"^[^:]*:\s*", "", line, count=1)
                return re.sub(r'"$', "", re.sub(r'^"', "", val))
        return ""
    if len(parts) == 2:
        in_section = False
        for line in read_lines:
            if re.match(rf"^{first}:", line):
                in_section = True
                continue
            if in_section:
                m = re.match(rf"^\s*{parts[1]}: (.*)", line)
                if m:
                    return re.sub(r'"$', "", re.sub(r'^"', "", m.group(1)))
                if not re.match(r"^\s", line) and re.match(r"^[A-Za-z]", line):
                    in_section = False
        return ""
    return ""


def companion(recipe: Path, related_type: str) -> Path | None:
    name = recipe.name
    app = ""
    for suffix in (".download.recipe.yaml", ".pkg.recipe.yaml"):
        if name.endswith(suffix):
            app = name[: -len(suffix)]
    return {
        "download_recipe": recipe.parent / f"{app}.download.recipe.yaml",
        "pkg_recipe": recipe.parent / f"{app}.pkg.recipe.yaml",
        "overrides": recipe.parent / ".overrides",
        "autopkg_config": recipe.parent / ".autopkg_config",
    }.get(related_type)


def recipe_type(recipe: Path) -> str:
    if recipe.name.endswith(".download.recipe.yaml"):
        return "download"
    if recipe.name.endswith(".pkg.recipe.yaml"):
        return "pkg"
    return ""


# ── applying a rule ────────────────────────────────────────────────────────────
@dataclass
class Outcome:
    kind: str  # pass | fail | companion_missing
    message: str = ""


def apply_rule(rule: Rule, recipe: Path) -> Outcome | None:
    """None when the rule doesn't apply to this recipe."""
    actual = recipe_type(recipe)
    if not actual or rule.recipe_type not in ("both", actual):
        return None
    value = primary = ""
    comp: Path | None = None
    if rule.source == "related-file" and rule.related_type:
        comp = companion(recipe, rule.related_type)
        if comp is None or not comp.is_file():
            return Outcome(
                "companion_missing", f"Required companion file not found: {comp or ''}"
            )
        if rule.related_key == "exists":
            return Outcome("pass")
        value = get_value(comp, rule.related_key)
        if rule.key:
            primary = get_value(recipe, rule.key)
    else:
        value = get_value(recipe, rule.key, rule.source)

    vt, ok = rule.val_type, False
    if vt == "regex":
        ok = compare_regex(value, rule.val_pattern)
    elif vt == "exact":
        if rule.source == "related-file" and primary:
            ok = primary == value
        else:
            ok = value == rule.val_pattern
    elif vt == "list":
        ok = grep(value, "|".join(rule.val_list))
    elif vt == "exists":
        ok = compare_exists(value, rule.val_pattern)
    elif vt == "not_exists":
        ok = not grep(value, unescape(rule.val_pattern))
    elif vt == "absent":
        ok = value in ("", "null")
    elif vt == "classification":
        ok, value, primary = _classification(recipe, value)
    elif vt == "exists_any":
        if not rule.conditions:
            value = "(no conditions defined)"
        for cond in rule.conditions:
            cond_comp: Path | None = None
            if cond.source == "related-file" and cond.related_type:
                cond_comp = companion(recipe, cond.related_type)
                if cond_comp is None or not cond_comp.is_file():
                    continue
                cond_value = (
                    "present"
                    if cond.related_key == "exists"
                    else get_value(cond_comp, cond.related_key)
                )
            else:
                cond_value = get_value(recipe, cond.key, cond.source)
            pattern, negate = cond.pattern, cond.pattern.startswith("!")
            if negate:
                pattern = pattern[1:]
            if compare_exists(cond_value, pattern) != negate:
                ok, value, comp = True, cond_value, cond_comp
                break
    if ok:
        return Outcome("pass")

    # The bash engine passed value, related value and companion as consecutive
    # output lines, so a multi-line value spilled into the next two fields.
    fields = value.split("\n") + primary.split("\n") + [str(comp) if comp else ""]
    val, related, comp_line = (fields + ["", "", ""])[:3]
    message = rule.fail_msg
    message = message.replace("%value%", val).replace("%related_value%", related)
    message = message.replace(
        "%related_file%", Path(comp_line).name if comp_line else ""
    )
    message = message.replace("%file%", recipe.name).replace("%key%", rule.key)
    return Outcome("fail", message)


def _classification(recipe: Path, comment: str) -> tuple[bool, str, str]:
    """rule-definitions §2.8: the recipe's claimed pattern must be what the
    classifier concludes from its processors (or one of its alternatives when it
    is uncertain). Passes when there is nothing to judge. Returns (ok, claimed,
    classified)."""
    from .classify import classify
    from .model import RecipeSet

    m = CLAIM_RE.match(comment)
    if not m:
        return True, comment, ""  # no claim: CMT-003's business
    claimed = m.group(1)
    target = recipe.resolve()
    pairs = [
        p
        for p in RecipeSet.load(recipe.parent).pairs()
        if p.download
        and p.pkg
        and target in (p.download.path.resolve(), p.pkg.path.resolve())
    ]
    if not pairs:
        return True, claimed, ""  # half a pair: SEN-001's business
    result = classify(pairs[0])
    if result.label in ("?", "!"):
        return True, claimed, result.label  # can't classify, or PKG-001's business
    options = [result.label, *result.alternatives]
    # A claim of the number alone ("Pattern 4") accepts any letter in that family.
    family = claimed.isdigit() and any(
        re.fullmatch(rf"{claimed}[a-e]?", o) for o in options
    )
    return claimed in options or family, claimed, " or ".join(options)


# ── output ─────────────────────────────────────────────────────────────────────
def echo_e(text: str) -> str:
    """Interpret backslash escapes the way bash's `echo -e` does."""
    out, i = [], 0
    simple = {
        "\\": "\\",
        "a": "\a",
        "b": "\b",
        "e": "\033",
        "E": "\033",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "v": "\v",
    }
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            if nxt in simple:
                out.append(simple[nxt])
                i += 2
                continue
            if nxt == "c":
                break
            if nxt == "0":
                m = re.match(r"0([0-7]{0,3})", text[i + 1 :])
                out.append(chr(int(m.group(1) or "0", 8)))
                i += 1 + len(m.group(0))
                continue
            if nxt == "x":
                m = re.match(r"x([0-9A-Fa-f]{1,2})", text[i + 1 :])
                if m:
                    out.append(chr(int(m.group(1), 16)))
                    i += 1 + len(m.group(0))
                    continue
        out.append(ch)
        i += 1
    return "".join(out)


def fail_line(rule_id: str, severity: str, message: str) -> str | None:
    tag = {
        "error": f"{RED}[FAIL]{NC}",
        "warning": f"{YELLOW}[WARN]{NC}",
        "info": f"{BLUE}[INFO]{NC}",
    }.get(severity)
    return echo_e(f"  {tag} {rule_id}: {message}") if tag else None


def lint_recipe(recipe: Path, label: str, rules: list[Rule], out: list[str]) -> bool:
    """Append this recipe's report to `out`; True if it had errors or warnings."""
    out.append(f"{BLUE}═══ Checking:{NC} {label}")
    counts = {"error": 0, "warning": 0, "info": 0}
    for rule in rules:
        outcome = apply_rule(rule, recipe)
        if outcome is None or outcome.kind == "pass":
            continue
        line = fail_line(rule.id, rule.severity, outcome.message)
        if line is not None:
            out.append(line)
        if rule.severity in counts:
            counts[rule.severity] += 1
    if not any(counts.values()):
        out.append(f"  {GREEN}✓ All checks passed{NC}")
    else:
        out.append(
            f"  {RED}{counts['error']} errors{NC}, {YELLOW}{counts['warning']} "
            f"warnings{NC}, {BLUE}{counts['info']} info{NC}"
        )
    out.append("")
    return bool(counts["error"] or counts["warning"])


def check_pairs(lint_dir: str, out: list[str]) -> None:
    root = Path(lint_dir)
    downloads = sorted(root.rglob("*.download.recipe.yaml"))
    pkgs = sorted(root.rglob("*.pkg.recipe.yaml"))
    dl_names = {p.name[: -len(".download.recipe.yaml")] for p in downloads}
    pk_names = {p.name[: -len(".pkg.recipe.yaml")] for p in pkgs}
    out += [f"{BLUE}═══ Checking download/pkg recipe pairs in:{NC} {lint_dir}", ""]
    errors = warnings = 0
    for p in downloads:
        if p.name[: -len(".download.recipe.yaml")] not in pk_names:
            out.append(
                f"  {RED}[FAIL] SEN-001:{NC} Download recipe "
                f"'{_label(p, root, lint_dir)}' has no matching pkg recipe"
            )
            errors += 1
    for p in pkgs:
        if p.name[: -len(".pkg.recipe.yaml")] not in dl_names:
            out.append(
                f"  {YELLOW}[WARN] SEN-001:{NC} Pkg recipe "
                f"'{_label(p, root, lint_dir)}' has no matching download recipe "
                "(standalone?)"
            )
            warnings += 1
    if not errors and not warnings:
        out.append(f"  {GREEN}✓ All recipe pairs are complete{NC}")
    if errors:
        out.append(f"  {RED}{errors} incomplete pairs{NC}")
    if warnings:
        out.append(f"  {YELLOW}{warnings} standalone pkg recipes{NC}")
    out.append("")


def _label(path: Path, root: Path, given: str) -> str:
    """The path as `find <given>` would print it."""
    rel = path.relative_to(root).as_posix()
    return f"{given.rstrip('/')}/{rel}" if given not in (".", "") else f"./{rel}"


def list_rules(checks: Path, org: Org, rules: list[Rule] | None = None) -> list[str]:
    out = [
        f"AutoPKG Recipe Lint Rules (from {checks})",
        f"  org: {org.name} ({org.file})",
        "",
    ]
    current = None
    for rule in load_rules(checks, org) if rules is None else rules:
        if rule.severity != current:
            current = rule.severity
            out.append(f"  [{current}]")
        out.append(f"    {rule.id}: {rule.description}")
    return out


# ── command line ────────────────────────────────────────────────────────────────
USAGE = """Usage: {0} <recipe-file.yaml> [...]
       {0} --dir <directory> [--pair-check]
       {0} --repo <recipe-repo> [--pair-check]
       {0} --config <path> <file> [...]
       {0} --org <org.yaml> ...   (default: config/org.yaml or $AUTOPKG_TOOLKIT_ORG)
       {0} --customer <name> ...  (or $AUTOPKG_TOOLKIT_CUSTOMER, or the default)
       {0} --all-customers [--pair-check]
       {0} --list-rules"""

VALUE_FLAGS = {
    "--dir": ("dir", "--dir requires a directory path"),
    "--config": ("checks", "--config requires a file path"),
    "--specs": ("checks", "--specs requires a file path"),
    "--repo": ("repo", "--repo requires a directory path"),
    "--org": ("org", "--org requires a file path"),
    "--customer": ("customer", "--customer requires a name"),
}


def _parse_args(argv: list[str], prog: str) -> dict:
    opts = {
        "checks": str(DEFAULT_CHECKS),
        "checks_given": False,
        "files": [],
        "dir": "",
        "repo": "",
        "org": None,
        "customer": None,
        "all": False,
        "pairs": False,
        "list": False,
    }
    i = 0
    while i < len(argv):
        arg = argv[i]
        value = argv[i + 1] if i + 1 < len(argv) else ""
        if arg in VALUE_FLAGS:
            key, message = VALUE_FLAGS[arg]
            if not value or value.startswith("-"):
                raise UsageError(message)
            opts[key] = value
            if key == "checks":
                opts["checks_given"] = True
            if arg == "--org":
                org, error = read_org_config(value)
                if error:
                    raise UsageError(error)
                opts["org_obj"] = org
            i += 2
        elif arg == "--all-customers":
            opts["all"], i = True, i + 1
        elif arg == "--pair-check":
            opts["pairs"], i = True, i + 1
        elif arg == "--list-rules":
            opts["list"], i = True, i + 1
        elif arg in ("-h", "--help"):
            opts["help"] = USAGE.format(prog)
            return opts
        elif arg.startswith("-"):
            raise UsageError(f"Unknown option: {arg}")
        else:
            if not Path(arg).is_file():
                raise UsageError(f"Recipe file not found: {arg}")
            opts["files"].append(arg)
            i += 1
    return opts


def run(
    argv: list[str], prog: str = "recipe-linter.sh"
) -> tuple[int, list[str], list[str]]:
    """(exit code, stdout lines, stderr lines)."""
    try:
        opts = _parse_args(argv, prog)
    except UsageError as exc:
        return 2, [], [f"ERROR: {exc}"]
    if "help" in opts:
        return 0, opts["help"].split("\n"), []
    if not opts["all"]:
        return _run_one(opts)

    # --all-customers: each customer in isolation (customers FR-05).
    if opts["customer"] or opts["dir"] or opts["files"] or opts["repo"]:
        return (
            2,
            [],
            [
                "ERROR: --all-customers can't be combined with --customer, "
                "--dir, --repo or recipe files"
            ],
        )
    try:
        customers = load_registry().all()
    except CustomerError as exc:
        return 2, [], [f"ERROR: {exc}"]
    if not customers:
        return 2, [], ["ERROR: --all-customers: no customers are registered"]
    worst, out, err = 0, [], []
    for customer in customers:
        code, c_out, c_err = _run_one(
            dict(opts, customer=customer.name, customer_repo=True)
        )
        out += [f"=== Customer: {customer.name}", *c_out, ""]
        err += c_err
        worst = max(worst, code)
    return worst, out, err


def _run_one(opts: dict) -> tuple[int, list[str], list[str]]:
    out: list[str] = []
    checks = Path(opts["checks"])
    lint_dir, files = opts["dir"], list(opts["files"])
    # A named target, the env var, or standing in a recipe repo all count as
    # choosing a repo: the registry default then stays out of the way.
    explicit = bool(
        lint_dir
        or files
        or opts["repo"]
        or os.environ.get("AUTOPKG_TOOLKIT_REPO")
        or looks_like_recipe_repo(Path.cwd())
    ) and not opts.get("customer_repo")
    try:
        customer = select(opts["customer"], needed=not explicit or opts["list"])
    except CustomerError as exc:
        return 2, out, [f"ERROR: {exc}"]

    # Org: --org, then $AUTOPKG_TOOLKIT_ORG, then the customer's, then the kit's.
    org = opts.get("org_obj")
    if (
        org is None
        and customer is not None
        and not os.environ.get("AUTOPKG_TOOLKIT_ORG")
    ):
        try:
            org = customer.org()
        except CustomerError as exc:
            return 2, out, [f"ERROR: {exc}"]

    if opts["list"]:
        if not checks.is_file():
            return 2, out, [f"ERROR: Specs file not found: {checks}"]
        if org is None:
            org, error = read_org_config()
            if error:
                return 2, out, [f"ERROR: {error}"]
        try:
            rules = _rules_for(checks, org, customer, opts)
        except UsageError as exc:
            return 2, out, [f"ERROR: {exc}"]
        return 0, list_rules(checks, org, rules), []

    if not lint_dir and not files:
        use_customer = customer is not None and (
            opts.get("customer_repo")
            or not (opts["repo"] or os.environ.get("AUTOPKG_TOOLKIT_REPO"))
        )
        if not use_customer:
            resolved = resolve_repo_root(opts["repo"] or None)
        else:
            resolved = resolve_repo_root(str(customer.recipe_repo()))
        if not resolved.ok:
            return 2, out, [f"ERROR: {line}" for line in resolved.errors]
        lint_dir = str(resolved.root / "recipes")
    elif opts["repo"]:
        resolved = resolve_repo_root(opts["repo"])
        if not resolved.ok:
            return 2, out, [f"ERROR: {line}" for line in resolved.errors]

    if lint_dir:
        root = Path(lint_dir)
        if not root.is_dir():
            return 2, out, [f"ERROR: Directory not found: {lint_dir}"]
        files += [
            _label(p, root, lint_dir) for p in sorted(root.rglob("*.recipe.yaml"))
        ]
        if not files:
            return 0, [f"No .recipe.yaml files found in {lint_dir}"], []

    errors = validate_checks(checks)
    if errors:
        return 2, out, [f"ERROR: {e}" for e in errors]
    if org is None:
        org, error = read_org_config()
        if error:
            return 2, out, [f"ERROR: {error}"]
    try:
        rules = _rules_for(checks, org, customer, opts)
    except UsageError as exc:
        return 2, out, [f"ERROR: {exc}"]

    out += [
        f"AutoPKG Recipe Linter (config-driven) — using specs from: {checks}",
        f"  org naming from: {org.file}",
    ]
    if customer is not None:
        out.append(f"  customer: {customer.name} ({customer.root})")
    out += [f"  {len(rules)} rules loaded", ""]
    if opts["pairs"] and lint_dir:
        check_pairs(lint_dir, out)
    failed = False
    for label in files:
        failed |= lint_recipe(Path(label), label, rules, out)
    if failed:
        out.append(
            f"{RED}✗ Lint checks failed for one or more of {len(files)} recipe(s){NC}"
        )
    else:
        out.append(f"{GREEN}✓ All {len(files)} recipe(s) passed lint checks{NC}")
    return (1 if failed else 0), out, []


def _rules_for(checks: Path, org: Org, customer, opts: dict) -> list[Rule]:
    """The kit's rules, plus the customer's local ones unless --config replaced
    the rule file (customers FR-02, FR-04)."""
    rules = load_rules(checks, org)
    if customer is not None and not opts["checks_given"]:
        rules = customer_rules(rules, customer.checks_local, org)
    return rules


def main(argv: list[str] | None = None, prog: str = "recipe-linter.sh") -> int:
    code, out, err = run(sys.argv[1:] if argv is None else argv, prog)
    for line in out:
        print(line)
    for line in err:
        print(line, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
