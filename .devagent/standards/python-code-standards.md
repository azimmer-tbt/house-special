---
name: python-code-standards
description: How to write, test and review Python in this kit — AutoPkg's bundled interpreter, standard library plus PyYAML only, a fixed front-end shape (argparse, main() returning an exit code, results to stdout, diagnostics to stderr), black/isort/flake8 formatting, and unittest tests run through ShellSpec. Use whenever you write or change a .py file, port a bash tool to Python, or review Python code here.
---

# Python Code Standards

The rules for *whether* and *where* Python is used are in the toolkit constitution,
[`specs/toolkit/00-constitution.md`](../../specs/toolkit/00-constitution.md) (P-7,
P-9, P-10). This file covers *how* to write it.

## Runtime

- **Interpreter:** AutoPkg's, via the shebang `#!/usr/local/autopkg/python` for
  `.py` files and `tk_python` from shell (toolkit-common FR-09). Never a bare
  `python3`.
- **Version:** the one AutoPkg ships, Python 3.10 as of AutoPkg 2.9. No 3.11+
  features: no `tomllib`, no `ExceptionGroup`/`except*`, no `typing.Self`.
- **Dependencies:** the standard library and PyYAML. Nothing else, not even when
  AutoPkg's Python happens to include it (it also carries pyobjc and a few tools;
  those are AutoPkg's, not ours to rely on).
- **YAML:** always `yaml.safe_load`, never `yaml.load`.

## File header

Every executable `.py` file starts the same way:

```python
#!/usr/local/autopkg/python
# tool-name.py
#
# Author: <maintainer>
# SPDX-License-Identifier: MIT
"""One-line summary.

Usage and behaviour in a few lines: inputs, outputs, exit codes, and the spec
that governs it (specs/<family>/NN-name.md).
"""
```

The module docstring is the `--help` description (`argparse`'s `description=__doc__`),
so help text and docs can't drift apart.

## Layout

| What | Where |
|---|---|
| Shared code (the recipe model, repo resolution) | `lib/python/<package>/`, e.g. `lib/python/recipekit/` |
| A command someone runs | `bin/<name>` (Python) or a bash front end calling `tk_python -m <package>.<tool>` |
| Guardrail audits | `guardrails/audit/check_<thing>.py` |
| Unit tests | `tests/python/test_<module>.py` |

- A front end in `bin/` is thin: parse arguments, call library functions, print,
  return an exit code. Logic that deserves a test lives in `lib/python/`.
- Front ends find `lib/python` from their own location
  (`Path(__file__).resolve().parent.parent / "lib" / "python"`), never from the
  current directory or an installed package (constitution P-1).
- Recipe-repo resolution follows toolkit-common's precedence (explicit argument,
  then `AUTOPKG_TOOLKIT_REPO`, then the current directory only if it's a recipe
  repo) through **one** shared Python routine. Don't write another copy
  (constitution P-2, AIP-02).

## Front-end shape

```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, ...)
    args = parser.parse_args(argv)
    ...
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- `main()` takes `argv` and **returns** the exit code. Only the `__main__` block
  calls `sys.exit`, so tests can call `main([...])` directly.
- **Exit codes:** `0` success or clean, `1` findings or check failed, `2` usage or
  input error. A tool that's replacing a bash one keeps that tool's codes (P-10).
- **Streams:** results on stdout, diagnostics and progress on stderr. A
  `--output json` mode prints only JSON on stdout.
- **Flags:** long options with hyphens (`--pair-check`), matching the bash tools'
  spelling. `--help` works everywhere.

## Style

- **Formatting:** `black` (line length 88) and `isort --profile black`, both
  bundled with AutoPkg's Python, so nothing to install.
- **Lint:** `flake8 --max-line-length 88 --extend-ignore E203` must be clean.
- **Types:** annotate every function signature (`list[str]`, `Path | None` are
  fine in 3.10). No type checker is bundled; the annotations are documentation.
- **Paths:** `pathlib.Path`, not string joins.
- **Strings:** f-strings. Quote paths in messages (`f"not a directory: {path!s}"`).
- **Names:** `snake_case` functions and variables, `CapWords` classes,
  `UPPER_CASE` module constants.

```bash
tk_python -m black --check bin/*.py guardrails/audit lib/python tests/python
tk_python -m isort --check-only --profile black bin/*.py guardrails/audit lib/python tests/python
tk_python -m flake8 --max-line-length 88 --extend-ignore E203 bin/*.py guardrails/audit lib/python tests/python
```

## Errors

- **Recipe content never crashes a tool.** Bad YAML, a missing half of a pair or an
  undeclared variable is a *finding* (code, file, line, message) that the front end
  reports and turns into an exit code. Exceptions are for programmer errors.
- Catch the specific exception (`yaml.YAMLError`, `FileNotFoundError`), never a
  bare `except:`. Don't hide a traceback behind a message that loses the cause.
- Say what to do next in the message, the way the bash tools do
  ("no recipe repo: pass --repo or set AUTOPKG_TOOLKIT_REPO").

## Side effects

- **Read-only by default.** A tool that writes, moves or deletes needs a spec that
  says so, and a `--dry-run` that prints what it would do.
- **No network access** unless the tool's purpose is to fetch, and its spec says so.
- **Subprocesses** only for things the standard library can't do (`pkgutil`,
  `hdiutil`, `codesign`, `lsbom`). Use `subprocess.run([...], check=..., text=True,
  capture_output=True)` with a list, never `shell=True`. Use absolute paths to
  system tools (`/usr/sbin/pkgutil`).
- **Plists** with `plistlib`, not `defaults` or `PlistBuddy`.
- Temporary files with `tempfile`, cleaned up in `finally` or a context manager.

## Tests

- `unittest` only (constitution P-9). Test files: `tests/python/test_<module>.py`,
  classes `class <Thing>Test(unittest.TestCase)`.
- Fixtures as small files under `tests/fixtures/`, or built in `setUp` inside a
  `tempfile.TemporaryDirectory()`.
- Name each test after the acceptance criterion it enforces
  (`test_ac_05_1_file_url_resolves`), as the ShellSpec examples do.
- Run: `tk_python -m unittest discover -s tests/python`. ShellSpec runs the same
  command, so `shellspec` stays the one entry point.
- A later move to `pytest` needs no rewrite: `pytest` runs `unittest.TestCase`
  classes as they are.

## Porting a bash tool

1. The spec comes first: read the tool's spec folder and update it where the port
   changes behaviour (usually it shouldn't).
2. Same command name, flags, exit codes and output (P-10). If the bash tool is a
   documented command, keep a bash front end that `exec`s the Python one, or
   replace it with a Python file of the same name.
3. Run old and new over every recipe and fixture the tests cover; the outputs must
   match before the bash implementation is removed. Keep that parity test until then.
4. Remove the bash implementation, its now-dead helpers, and any `yq` or `xmllint`
   dependency it had.

## Pitfalls

- **`yaml.load` with no loader, or `yaml.FullLoader`.** Use `safe_load`.
- **Reading recipes as text with regex.** Ask the recipe model instead (constitution
  AIP-08); that's how the guardrail audits got KI-8.
- **Printing progress to stdout.** It breaks `--output json` and anything piping the
  results.
- **`sys.exit` deep inside a function.** Return a code or raise; let `main` decide.
- **Relying on dict order from YAML for meaning.** Order in `Process` lists matters;
  order of keys in a mapping doesn't.
