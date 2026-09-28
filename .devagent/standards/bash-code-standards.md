---
name: bash-code-standards
description: Debug, write, and review Bash/shell scripts that comply with Google Shell Style Guide, pass bashate linting, and pass ShellCheck analysis. Use this skill whenever you're writing shell scripts, debugging Bash issues (quoting problems, variable scope, subshell pitfalls), reviewing shell code for robustness, or handling errors/arguments/temp files in Bash. Covers indentation, naming, quoting rules, error handling, subshells, arrays, variable expansion, file operations, and common Bash anti-patterns. Does NOT apply to calling shell scripts from Python or other languages.
---

# Bash Code Standards

This skill combines three complementary rule sets for writing Bash code:
- **Google Shell Style Guide** — formatting, naming, structure, and design patterns
- **Bashate** — static style checker (runs in CI)
- **ShellCheck** — static bug detector (runs in CI)

When writing shell scripts in this project, follow all three. Code must pass both `bashate` and `shellcheck` linting in the CI pipeline, and should conform to the Google style conventions for human readability.

## File Structure and Shebang

- Use `#!/bin/bash` for all executable scripts
- Use `set -Eeo pipefail` for safety:
  - `set -E`: ERR trap propagates into functions and subshells
  - `set -e`: Exit on error (errexit)
  - `set -o pipefail`: Pipeline fails if any command fails
- Must start with a shebang or have `.sh` extension (bashate E005)
- Must end with a newline (bashate E004)

```bash
#!/bin/bash
#
# Brief description of what the script does.

set -Eeo pipefail
```

Prefer small, single-purpose scripts, and keep logic in functions so it can be tested. Tools that read structured data (recipe YAML, plists, bills of materials) belong in Python instead (`specs/toolkit/00-constitution.md` P-7, `python-code-standards.md`).

## Naming Conventions

- **Functions**: `lower_case_with_underscores()`, libraries use `package::function_name()`
- **Variables**: `lower_case_with_underscores`
- **Constants/Environment**: `UPPER_CASE_WITH_UNDERSCORES`, declared with `readonly` or `declare -xr`
- **Source files**: `lowercase` or `lower_case.sh`

## Formatting

### Indentation and Line Length

- **Indentation**: 4 spaces, no tabs (bashate E002, E003)
  - Indents must be multiples of 4 spaces
  - Exception: tabs allowed in `<<-` heredocs
- **Line length**: Max 79 characters (bashate E006)
- **Trailing whitespace**: None allowed (bashate E001)

### Braces and Structure

- **Function definition**: Same line as function name, no space before parentheses
- **Block control**: `;then`, `;do` on same line as `if`/`for`/`while`; `else`, `fi`, `done` on their own lines

```bash
my_func() {
  # body
}

if [[ "${var}" == "value" ]]; then
  do_something
else
  do_other
fi

for item in "${array[@]}"; do
  process "${item}"
done
```

## Constants and Declarations

```bash
readonly CONFIG_DIR='/etc/myapp'
declare -xr EXPORTED_VAR='value'

# Source statements and includes here
```

## Functions

Document functions clearly with a header block:

```bash
#######################################
# Function description.
# Globals:
#   VAR_NAME
# Arguments:
#   $1 - description
# Outputs:
#   Writes to STDOUT
# Returns:
#   0 on success, non-zero on error
#######################################
my_function() {
  local arg="$1"
  # function body
}
```

## Main Entry Point

```bash
#######################################
# Main entry point.
#######################################
main() {
  # main logic
}

main "$@"
```

## Variable Declaration and Assignment

### Variable Separation Rule

**Separate declaration from assignment for command substitution** (bashate E042, ShellCheck SC2155):

```bash
# CRITICAL - separate for command substitution
local result
result="$(some_command)"
if (( $? != 0 )); then
  return 1
fi

# Wrong - hides exit code of some_command
local result="$(some_command)"
# $? is now 0 (exit code of local, not some_command)
```

**Why?** The `local` keyword returns 0, masking the exit status of the command.

For simple assignments without command substitution, declaration and assignment together is fine:
```bash
local name="$1"
local count=0
```

## Variable Expansion and Quoting

### Quoting Rules

**Always quote variables and command substitutions** (ShellCheck SC2086, SC2046):
- Use braces for clarity: `"${var}"` over `"$var"`
- Exception: Single-char specials don't need braces: `$1`, `$?`, `$#`, `$@`

```bash
echo "Path: ${PATH}"
echo "Positional: $1 $2"
result="$(some_command)"
```

### Variable Assignment

Never use spaces around `=` (ShellCheck SC1068):
```bash
# Correct
var="value"

# Wrong
var = "value"
```

### Tilde Expansion

Tilde doesn't expand in quotes (ShellCheck SC2088):
```bash
# Wrong
path="~/documents"

# Correct
path="${HOME}/documents"
```

### Command Substitution

- Use `$(command)` not backticks (bash-style, ShellCheck SC2006)
- Always quote the result: `"$(command)"`

```bash
var="$(command "$(nested_command)")"
```

### Passing Arguments

Use `"$@"` with quotes, not `$*` (bash-style, ShellCheck SC2048/SC2068):
```bash
for arg in "$@"; do
  echo "${arg}"
done
```

## Arrays (bash 3.2 constraints)

**macOS `/bin/bash` is version 3.2** — it has indexed arrays (`declare -a`),
`+=` element append, and `"${array[@]}"` expansion, but it does NOT have:
- `mapfile` / `readarray` (bash 4+)
- `declare -A` associative arrays (bash 4+)
- `${var,,}` / `${var^^}` case modification (bash 4+)

For any universal frontend covered by P-7 of the constitution, use only
bash 3.2 constructs. For Lane B scripts that assume the AutoPkg toolchain,
modern bash is fine.

```bash
declare -a my_array
my_array=(item1 item2)
my_array+=("item3")

# Iterate safely with quotes (ShellCheck SC2128)
for item in "${my_array[@]}"; do
  echo "${item}"
done

# Use spaces, not commas (ShellCheck SC2054)
declare -a flags=(--verbose --output="${file}")
command "${flags[@]}"
```

Instead of `mapfile`/`readarray` (bash 4+), use a `while read` loop with
process substitution (bash 3.2 compatible):
```bash
# Wrong (bash 3.2 incompatible)
mapfile -t array < <(command)

# Correct (bash 3.2 compatible)
array=()
while IFS= read -r line; do
  [ -n "$line" ] && array+=("$line")
done < <(command)
```

Use `+=` to append to arrays (ShellCheck SC2179):
```bash
array+=("newitem")
```

## Tests and Conditionals

### Use [[ ]] Not [ ]

Always use `[[ ... ]]` (not `[ ... ]` or `test`):
- Use `==` for string equality
- Use `-z`/`-n` for empty/non-empty strings
- Use `(( ... ))` for arithmetic comparisons (ShellCheck SC2071)

```bash
if [[ "${str}" == "value" ]]; then
  # string comparison
fi

if [[ -z "${var}" ]]; then
  # var is empty
fi

if (( num > 5 )); then
  # numeric comparison
fi
```

### Use [[ ]] for Regex

Use `[[ ]]` with `=~` for regex matching (ShellCheck SC2074):
```bash
# Correct
if [[ "${string}" =~ pattern ]]; then
  match="${BASH_REMATCH[1]}"
fi

# Wrong - don't use [ ] for regex
[ "${var}" =~ pattern ]
```

**Don't quote the regex pattern** (ShellCheck SC2076):
```bash
# Wrong - matches literally
[[ "${var}" =~ "^[0-9]+$" ]]

# Correct
[[ "${var}" =~ ^[0-9]+$ ]]
```

### Glob Matching

Quote the RHS of `==` to prevent unintended glob expansion (ShellCheck SC2053):
```bash
# Glob matching (may be unintended)
[[ "${var}" == *.txt ]]

# Literal matching
[[ "${var}" == "*.txt" ]]
```

### Avoid && || as if-then-else

`A && B || C` is not equivalent to if-then-else (ShellCheck SC2015):
```bash
# Wrong - C may run when A is true but B fails
command && success || failure

# Correct
if command; then
  success
else
  failure
fi
```

### Check Exit Codes Directly

Use `! command` or `if command; then` rather than checking `$?` after (ShellCheck SC2181):
```bash
# Less preferred
command
if [ $? -ne 0 ]; then
  err "Failed"
fi

# Preferred
if ! command; then
  err "Failed"
fi
```

## Arithmetic

Use `(( ... ))` or `$(( ... ))`, never `let`, `expr`, or `$[ ... ]` (bash-style, bashate E041, ShellCheck SC2007, SC2003):

```bash
(( count += 1 ))
result="$(( a + b ))"
```

Don't use unnecessary braces in arithmetic (ShellCheck SC2004):
```bash
# Unnecessary
result="$(( ${x} + ${y} ))"

# Cleaner
result="$(( x + y ))"
```

## Error Handling

Send errors to STDERR: `echo "Error" >&2`

Use an error function:
```bash
err() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: $*" >&2
}

if ! command; then
  err "Command failed"
  exit 1
fi
```

### Check Pipeline Status

```bash
cmd1 | cmd2
if (( PIPESTATUS[0] != 0 || PIPESTATUS[1] != 0 )); then
  err "Pipeline failed"
fi
```

### Directory Changes

Use `cd ... || exit` (ShellCheck SC2164):
```bash
# Correct
cd /some/dir || exit 1
rm -rf ./*

# Wrong
cd /some/dir
rm -rf ./*
```

### Read Without -r

Always use `read -r` to prevent backslash mangling (ShellCheck SC2162):
```bash
# Wrong
while read line; do

# Correct
while read -r line; do
```

## Subshells and Pipes

### Pipe to while Loop

Don't pipe to `while` — use process substitution instead (bash-style):

```bash
# Wrong - variable changes lost in subshell
echo "data" | while read -r line; do
  count=$((count + 1))
done
echo "${count}"  # Still 0!

# Correct - use process substitution
while read -r line; do
  count=$((count + 1))
done < <(echo "data")
```

### Break/Exit in Pipeline

`break` and `exit` only affect the subshell when piping (ShellCheck SC2106):
```bash
# Wrong - only exits subshell
cat file | while read -r line; do
  [[ "${line}" == "stop" ]] && break
done

# Correct
while read -r line; do
  [[ "${line}" == "stop" ]] && break
done < <(cat file)
```

### Variable Modification in Subshell

Modifications made in a subshell are lost (ShellCheck SC2030/SC2031). Always use process substitution `< <(...)` instead of pipes `|` when you need to modify outer-scope variables.

## File Operations

### Useless cat

Don't pipe a file to `grep` or other commands (ShellCheck SC2002):
```bash
# Wrong
cat file | grep pattern

# Correct
grep pattern file
# or
grep pattern < file
```

### Don't use ls | grep

Use globbing or `find` instead (ShellCheck SC2010, SC2012):
```bash
# Wrong
ls | grep "\.txt$"
for f in $(ls); do

# Correct
for f in *.txt; do
  [[ -e "${f}" ]] && echo "${f}"
done

# For complex operations
find . -name "*.txt" -exec process {} \;
```

### Use find Correctly

Use `find -exec` or `while read` with process substitution (ShellCheck SC2044):
```bash
# Wrong
for f in $(find . -name "*.txt"); do

# Correct
find . -name "*.txt" -exec process {} \;
# or
while IFS= read -r -d '' f; do
  process "${f}"
done < <(find . -name "*.txt" -print0)
```

### Wildcard Safety

Use explicit `./*` for globs to prevent files starting with `-` from being interpreted as options (ShellCheck SC2035):

```bash
# Wrong - files starting with - become options
rm *

# Correct
rm ./*
```

### Protect rm with Empty Variables

Use `${var:?}` to ensure variable is non-empty before dangerous operations (ShellCheck SC2115):
```bash
# Dangerous if var is empty
rm -rf "${var}/"*

# Safer
rm -rf "${var:?}/"*
```

## Redirections

### Order Matters

`2>&1` must come last (ShellCheck SC2069):
```bash
# Wrong
command 2>&1 > file

# Correct
command > file 2>&1
```

### sudo Doesn't Affect Redirects

sudo only elevates the command, not the shell redirection (ShellCheck SC2024):
```bash
# Wrong - redirection happens as unprivileged user
sudo echo "text" > /etc/file

# Correct
echo "text" | sudo tee /etc/file > /dev/null
```

## Printf Format Security

Don't use variables as printf format strings (ShellCheck SC2059):
```bash
# Wrong - security risk
printf "${var}"

# Correct
printf '%s' "${var}"
```

## Trap Handlers

Use single quotes in trap to prevent premature expansion (ShellCheck SC2064):
```bash
# Wrong - expands now
trap "rm ${tmpfile}" EXIT

# Correct - expands when trap is triggered
trap 'rm "${tmpfile}"' EXIT
```

## Advanced: Command Inspection

### Use command -v, Not which

`which` is non-standard (ShellCheck SC2230):
```bash
# Wrong
if which cmd > /dev/null; then

# Correct
if command -v cmd > /dev/null; then
```

### Avoid Deprecated Tools

- `egrep` / `fgrep` are deprecated (ShellCheck SC2196/SC2197)
- Use `grep -E` / `grep -F` instead

```bash
# Deprecated
egrep 'pattern' file
fgrep 'string' file

# Correct
grep -E 'pattern' file
grep -F 'string' file
```

## Avoid

- `eval` — dangerous and unclear
- Aliases in scripts — use functions instead
- SUID/SGID on shell scripts
- `expr`, `let`, `$[ ]` for arithmetic
- Backticks for command substitution
- `function` keyword — use POSIX `name()` syntax (ShellCheck SC2112)

## Prefer Builtins

Use parameter expansion and builtins over external commands:

```bash
# Parameter expansion over sed
substitution="${string/#foo/bar}"

# Arithmetic over expr
addition="$(( x + y ))"

# Regex matching
if [[ "${string}" =~ pattern ]]; then
  match="${BASH_REMATCH[1]}"
fi
```

## Unused Variables

ShellCheck warns on unused variables (SC2034). Verify they're actually unused or export them if needed elsewhere.

## Dynamic Source Files

When sourcing files dynamically, specify with a directive (ShellCheck SC1090/SC1091):
```bash
# shellcheck source=./lib.sh
source "${script_dir}/lib.sh"

# For files ShellCheck can't follow
# shellcheck source=/dev/null
source "${dynamic_file}"
```

## ShellCheck Directives

Disable specific checks only when necessary:
```bash
# shellcheck disable=SC2086
echo $intentionally_unquoted

# Specify shell
# shellcheck shell=bash
```

## Syntax Errors

Scripts must pass `bash -n` syntax checking (bashate E040). Heredocs must terminate before EOF (bashate E012):

```bash
# Correct
cat <<EOF
content here
EOF

# Wrong - missing terminator
cat <<EOF
content here
# file ends without EOF terminator
```

## Linting

- **ShellCheck** (`shellcheck -S warning`) detects bugs and anti-patterns. A change
  must not add warnings; compare against the file's previous version.
- **bashate** style rules are followed where they don't conflict with this file.

Write code that passes from the start — don't rely on review feedback loops.

## This repository's conventions

These override the generic guidance above where they differ.

- **Target stock macOS bash 3.2** (`/bin/bash`). No associative arrays
  (`declare -A`), `mapfile`/`readarray`, `${var,,}`/`${var^^}`, `&>>`, `|&`.
  Use parallel indexed arrays or a lookup function instead of associative arrays.
- **Pattern substitution with special replacements is not portable.** In
  `${var//pattern/replacement}`, bash 5.2+ treats `\` and `&` in the *replacement*
  specially and 3.2 does not. When the replacement can contain them (regexes, org
  names), use prefix/suffix removal in a loop — see `_org_replace` in
  `lib/toolkit-common.sh`.
- **Stock tools only**: `/usr/bin/grep` (BSD — no `-P`; `\b` is not portable, use
  `(^|[^A-Za-z0-9])`), BSD `sed` (`sed -i ''`, no `\b`), BSD `awk`, `find`, `stat -f`.
  The linter must not call Python; other tools call AutoPkg's bundled Python through
  `tk_python` (never a bare `python3` from PATH); `.py` tools use `#!/usr/local/autopkg/python`.
- **Every front end sources the library** and uses its helpers:
  ```bash
  _X_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
  # shellcheck source=../lib/toolkit-common.sh
  . "${_X_BIN_DIR}/../lib/toolkit-common.sh"
  ```
  - Logging: `tk_err`, `tk_warn`, `tk_info` (stderr), `tk_die` (exit 2), `tk_section`.
  - Recipe repo: `resolve_repo_root "${REPO_ARG}"`, then `${REPO_ROOT}`. Never rely on the CWD.
  - Org naming: `read_org_config [file]` → `ORG_*`; `org_render` for `{{TOKENS}}`.
    Never write an org's identifier prefix or package prefix into a script.
- **Exit codes**: 0 success, 1 findings/failure, 2 usage or configuration error.
- **`set -e` and lookups**: in read-only analyzers built from many `grep` lookups,
  a lookup that finds nothing is an answer, not an error. Either don't use `-e`
  (`set -uo pipefail`) or guard each lookup with `|| true`. `grep -c … || echo 0`
  prints `0` twice — use `|| true`.
- **Status to stderr, data to stdout**, so `--output json` stays pipeable.
- **NUL-delimited file lists** (`find -print0 | sort -z | xargs -0`): shipped
  filenames can contain spaces and quotes.
- **Testability**: end scripts with `${__SOURCED__:+return}` before the main call
  so ShellSpec can `Include` them (see `.devagent/standards/shellspec.md`).
- **Help text** lives in the header comment and is printed by `--help`
  (`sed -n 'A,Bp' "${BASH_SOURCE[0]}"`).
