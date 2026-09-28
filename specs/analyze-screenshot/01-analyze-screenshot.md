# analyze-screenshot — Read a dialog screenshot with a local vision model (optional)

**Status:** Draft
**Date:** 2026-09-27
**Requires:** `specs/toolkit/00-constitution.md` (P-1, P-3, P-7), `specs/toolkit/01-toolkit-common.md` (FR-01, FR-09)
**Implementation:** `bin/analyze-screenshot.sh`

---

## Purpose

During install troubleshooting the evidence is often a screenshot: an installer
error, a licence prompt, a preferences pane. `analyze-screenshot.sh` sends one
screenshot to a vision-capable language model running **on the operator's own
machine**, and saves what the model reads: the visible text, the buttons and their
states, the app name and version. It reports what is on screen; it does not
diagnose.

The tool is **optional**. Nothing else in the kit calls it, and no workflow step
depends on it. It works only when a local model server is running and
`config/screenshot-analyzer.yaml` points at it. The owner keeps it because it
saves time in some cases. Without it, a person (or an agent that can read images)
reads the screenshot instead. The agent-facing instructions are in
[`.devagent/skills/analyze-screenshot.md`](../../.devagent/skills/analyze-screenshot.md).

Screenshots can show user names, host names, serial numbers and licence keys.
The design rests on one rule: **a screenshot goes to the configured local endpoint
and nowhere else.**

### Normative vs. Informative

- **Normative:** the single network destination, the local-only expectation,
  behaviour when config or endpoint is missing, what is sent, where results are
  written, exit codes.
- **Informative:** the default user prompt, the shipped system prompt, the
  `max_tokens` and `temperature` values, the layout of the saved Markdown file.

### Classification Key

- **[TESTABLE]** — automatable, mechanism named alongside.
- **[STRUCTURAL]** — enforced by layout or inspection.
- **[ADVISORY]** — review judgment.

No ShellSpec file covers this tool yet. Tests must never reach a real model: they
point `endpoint` at a stub HTTP server on `127.0.0.1` started by the test, or
stub `curl` on `PATH`.

---

## FR-01 — Optional tool

[ADVISORY]

The tool is an extra, not part of the kit's core workflow.

**Acceptance Criteria:**

- AC-01.1: [STRUCTURAL] No other script in `bin/`, `lib/` or `guardrails/` calls
  this tool, and no test outside its own spec requires a model endpoint.
  **Enforced via:** inspection.
- AC-01.2: [ADVISORY] Docs that mention the tool call it optional and name the
  fallback (read the image by hand). **Enforced via:** reviewer check.

## FR-02 — Command line

[TESTABLE]

```
analyze-screenshot.sh [-c <config>] [-m <prompt>] [-d] <screenshot>
```

| Argument | Meaning |
|---|---|
| `<screenshot>` | The image to analyse. Required. If more than one is given, the last wins. |
| `-c`, `--config <path>` | Config file. Default: `config/screenshot-analyzer.yaml` in the toolkit, found from the script's own location (constitution P-1). A relative path given here is relative to the current directory. |
| `-m`, `--message <text>` | The user prompt. Default: `Analyze this installation screenshot.` |
| `-d`, `--debug` | Print the request payload and the raw response to stderr (FR-07). |
| `-h`, `--help` | Print usage and exit 0. |

Any other word starting with `-` is an error: exit 2 with `ERROR: Unknown option`.

The tool takes no recipe repo, so toolkit-common's repo resolution does not
apply. The current directory matters only for relative paths the operator types.

**Acceptance Criteria:**

- AC-02.1: [TESTABLE] `--help` prints usage listing `-c`, `-m`, `-d` and `-h`, and
  exits 0 without reading the config. **Enforced via:** planned test
  `tests/analyze_screenshot_spec.sh` (planned)
- AC-02.2: [TESTABLE] No screenshot argument → exit 2 with `ERROR: Screenshot path
  is required.` **Enforced via:** planned test `tests/analyze_screenshot_spec.sh` (planned)
- AC-02.3: [TESTABLE] `--bogus` → exit 2 with `ERROR: Unknown option: --bogus`.
  **Enforced via:** planned test `tests/analyze_screenshot_spec.sh` (planned)
- AC-02.4: [TESTABLE] Run from an unrelated directory with no `-c`, the tool uses
  the toolkit's own config file. **Enforced via:** planned test
  `tests/analyze_screenshot_spec.sh` (planned)
- AC-02.5: [TESTABLE] `-c` or `-m` given as the last argument, with no value,
  exits 2 with a message. (Not yet met: `shift 2` fails under `set -e` and the
  script exits 1 with no message; see OQ-06.) **Enforced via:** planned test
  `tests/analyze_screenshot_spec.sh` (planned)

## FR-03 — Configuration

[TESTABLE]

The config is YAML, read one key at a time with AutoPkg's Python and PyYAML
(`tk_python`). No `yq` (KI-21, fixed).

| Key | Required | Meaning |
|---|---|---|
| `endpoint` | yes | Base URL of an OpenAI-compatible server on this machine, e.g. `http://localhost:12345`. |
| `model` | yes | Model name passed to the server. |
| `api_key_env` | no | The **name** of an environment variable holding an API key. The key itself never goes in the file. |
| `system_prompt` | no | Sent as the system message when non-empty. |
| `output_dir` | no | Where the analysis file goes. Relative paths are relative to the toolkit root. Empty or missing: the screenshot's own folder. |

The shipped `output_dir` is `customer/acme/troubleshooting`, which is gitignored
(except its README), so analyses of real screenshots do not end up tracked.

**Acceptance Criteria:**

- AC-03.1: [TESTABLE] A config without `endpoint` → exit 2 with `ERROR: endpoint
  not set in config: <path>`; without `model` → exit 2 with the matching message.
  No request is made. **Enforced via:** planned test `tests/analyze_screenshot_spec.sh` (planned)
- AC-03.2: [TESTABLE] A relative `output_dir` resolves under the toolkit root,
  whatever the current directory. **Enforced via:** planned test
  `tests/analyze_screenshot_spec.sh` (planned)
- AC-03.3: [TESTABLE] With `output_dir` empty, the analysis is written next to the
  screenshot. **Enforced via:** planned test `tests/analyze_screenshot_spec.sh` (planned)
- AC-03.4: [TESTABLE] The config is read without `yq`, using AutoPkg's Python and
  PyYAML (toolkit-common FR-09). **Enforced via:**
  planned test `tests/analyze_screenshot_spec.sh` (planned)

## FR-04 — Checks before anything is sent

[TESTABLE]

In this order, stopping at the first failure:

1. A screenshot argument was given (exit 2).
2. The screenshot file exists (exit 2, `ERROR: Screenshot not found: <path>`).
3. The config file exists (exit 2, `ERROR: Config not found: <path>`).
4. `curl` and `base64` are on `PATH` (exit 1, `ERROR: <cmd> not found.
   Install with: brew install <cmd>`).
5. `endpoint` and `model` are set (exit 2).

Only then is the image read and a request made. So a missing or incomplete config
never leads to a network call.

AutoPkg's Python (used to read the config, and to build the request, FR-05) is not
checked here. If it is missing, reading the config fails with the toolkit's own
error (`AutoPkg's Python not found`, or `AUTOPKG_TOOLKIT_PYTHON … not executable`)
and exit 127, before any request. See OQ-05.

**Acceptance Criteria:**

- AC-04.1: [TESTABLE] With the config file absent, the tool exits 2 and `curl` is
  never called. **Enforced via:** planned test `tests/analyze_screenshot_spec.sh` (planned)
- AC-04.2: [TESTABLE] With `base64` absent from `PATH` (and the config present),
  the tool exits 1 naming `base64`, and `curl` is never called. **Enforced via:** planned
  test `tests/analyze_screenshot_spec.sh` (planned)
- AC-04.3: [TESTABLE] With AutoPkg's Python unavailable, the tool exits with the
  prerequisite code and names the interpreter. (Not yet met; see OQ-05.)
  **Enforced via:** planned test `tests/analyze_screenshot_spec.sh` (planned)

## FR-05 — What is sent, and where

[TESTABLE]

The tool makes exactly **one** HTTP request: a `POST` to
`<endpoint>/v1/chat/completions` (the OpenAI chat-completions shape). It contacts
no other host, fetches nothing, and sends no telemetry.

The request body is JSON:

- `model`: the configured model.
- `messages`: the system prompt (if set), then one user message with two parts:
  the user prompt as text, and the image as a `data:` URL
  (`data:image/png;base64,…`). The MIME type is `image/jpeg` for `.jpg`/`.jpeg`,
  and `image/png` for everything else, including formats that are not PNG.
- `max_tokens`: 1024; `temperature`: 0.1.

Headers: `Content-Type: application/json`, plus `Authorization: Bearer <key>` only
when `api_key_env` names a variable that is set and non-empty.

The body is built by AutoPkg's Python through `tk_python` (toolkit-common FR-09).
The image's base64 text goes through a temporary file, which is deleted once the
body is built.

**Acceptance Criteria:**

- AC-05.1: [TESTABLE] Against a stub server, exactly one request arrives, at path
  `/v1/chat/completions`, with the fields above. **Enforced via:** planned test
  `tests/analyze_screenshot_spec.sh` (planned)
- AC-05.2: [STRUCTURAL] The script has one network call (`curl`), and its URL is
  built only from the configured `endpoint`. **Enforced via:** inspection.
- AC-05.3: [TESTABLE] No `Authorization` header is sent when `api_key_env` is
  empty or names an unset variable. **Enforced via:** planned test
  `tests/analyze_screenshot_spec.sh` (planned)
- AC-05.4: [TESTABLE] A prompt or model name containing `'''`, quotes or
  backslashes is sent unchanged. (Not yet met: the values are pasted into Python
  source inside `'''…'''` at `bin/analyze-screenshot.sh` lines 150–153, so such
  text breaks the request with exit 3; see OQ-03.) **Enforced via:** planned test
  `tests/analyze_screenshot_spec.sh` (planned)
- AC-05.5: [TESTABLE] A screenshot larger than about 750 KB (a typical Retina
  capture) is sent successfully. (Not yet met: the whole body is passed to `curl`
  as one `-d` argument at line 206; above the 1 MB argument limit the call fails
  with "argument list too long" and exit 3; see OQ-04.) **Enforced via:** planned
  test `tests/analyze_screenshot_spec.sh` (planned)

## FR-06 — Privacy: local endpoint only

[ADVISORY]

Screenshots may hold sensitive data. They MUST go only to a model server on the
operator's own machine. The kit must never ship a config that names a remote
host, and the tool should refuse one.

Today the rule is enforced by the shipped config (`http://localhost:12345`) and by
the skill's instructions, not by the code: the script sends to whatever
`endpoint` says.

Related exposure points:

- The API key is placed on `curl`'s command line, where other local processes can
  see it in the process list.
- `-d` prints the full request, including the whole base64 image, to stderr.
  Terminal logs or CI logs then hold the image.
- The temporary base64 file lives in the per-user temp folder. It is removed after
  the body is built, but not if the script is stopped before that point (there is
  no `trap`).
- The saved analysis records the endpoint, the model, the date and the prompt, and
  the model's transcription of the screen. It is as sensitive as the screenshot.

**Acceptance Criteria:**

- AC-06.1: [STRUCTURAL] The shipped `config/screenshot-analyzer.yaml` names a
  loopback endpoint (`localhost`, `127.0.0.1` or `[::1]`). **Enforced via:**
  planned test `tests/analyze_screenshot_spec.sh` (planned)
- AC-06.2: [TESTABLE] An endpoint whose host is not loopback is refused with exit
  2 and no request. (Not yet met; see OQ-01.) **Enforced via:** planned test
  `tests/analyze_screenshot_spec.sh` (planned)
- AC-06.3: [TESTABLE] The API key never appears in the process arguments of any
  child process. (Not yet met; see OQ-02.) **Enforced via:** planned test
  `tests/analyze_screenshot_spec.sh` (planned)
- AC-06.4: [TESTABLE] The shipped `output_dir` is ignored by git.
  **Enforced via:** planned test `tests/analyze_screenshot_spec.sh` (planned)
- AC-06.5: [TESTABLE] No temporary file remains after any exit, including exit 3.
  (Not yet met for interruptions before the body is built; see OQ-02.)
  **Enforced via:** planned test `tests/analyze_screenshot_spec.sh` (planned)

## FR-07 — Endpoint absent or failing

[TESTABLE]

- Nothing listening at the endpoint: `curl` reports HTTP code `000`, and the tool
  prints `ERROR: API returned HTTP 000` and `Use -d for full response dump.` to
  stderr and exits 3.
- Any non-2xx status: the same message with that status, then the response body,
  and exit 3.
- A 2xx response that is not JSON, or has no `choices[0].message.content`:
  `ERROR: Could not parse API response`, the body on stderr, exit 3.
- `curl` has no time limit, so a server that accepts the connection and never
  answers hangs the tool. See OQ-07.

The response body on error, and the raw response under `-d`, are pretty-printed to
**stdout** when they parse as JSON, and to stderr otherwise (lines 214 and 223).
Diagnostic output belongs on stderr. See OQ-08.

**Acceptance Criteria:**

- AC-07.1: [TESTABLE] With the endpoint set to a closed loopback port, the tool
  exits 3 with `HTTP 000` on stderr and writes no analysis file. **Enforced via:**
  planned test `tests/analyze_screenshot_spec.sh` (planned)
- AC-07.2: [TESTABLE] A stub returning HTTP 500 gives exit 3 and no analysis file.
  **Enforced via:** planned test `tests/analyze_screenshot_spec.sh` (planned)
- AC-07.3: [TESTABLE] A stub returning `{}` with HTTP 200 gives exit 3 and
  `Could not parse API response`. **Enforced via:** planned test
  `tests/analyze_screenshot_spec.sh` (planned)
- AC-07.4: [TESTABLE] On any failure, stdout is empty. (Not yet met when the error
  body is JSON; see OQ-08.) **Enforced via:** planned test
  `tests/analyze_screenshot_spec.sh` (planned)
- AC-07.5: [TESTABLE] A stub that never answers makes the tool exit 3 within a
  bounded time. (Not yet met; see OQ-07.) **Enforced via:** planned test
  `tests/analyze_screenshot_spec.sh` (planned)

## FR-08 — Output

[TESTABLE]

On success the tool creates `output_dir` if needed and writes
`<output_dir>/<screenshot name without its extension>_analysis.md`, replacing any
file already there:

```
# Screenshot Analysis — dialog.png

**Model:** <model>
**Endpoint:** <endpoint>
**Date:** 2026-09-27 14:03:11
**User prompt:** Analyze this installation screenshot.

---

<model's answer>
```

It then prints to stdout:

```
---
Analysis saved to: <path of the analysis file>

<model's answer>
```

**Acceptance Criteria:**

- AC-08.1: [TESTABLE] For `dialog.png`, the file `dialog_analysis.md` is written in
  `output_dir`, and its body after `---` equals the stub's `content`.
  **Enforced via:** planned test `tests/analyze_screenshot_spec.sh` (planned)
- AC-08.2: [TESTABLE] stdout contains `Analysis saved to: ` with that path, then
  the answer. **Enforced via:** planned test `tests/analyze_screenshot_spec.sh` (planned)
- AC-08.3: [TESTABLE] If `output_dir` cannot be created, the tool exits non-zero
  with a message naming the folder. (Partly met: the `mkdir` error is hidden and
  the write fails under `set -e` with a shell error and exit 1, the
  missing-dependency code; see OQ-06.) **Enforced via:** planned test
  `tests/analyze_screenshot_spec.sh` (planned)

## FR-09 — Exit codes

[TESTABLE]

| Exit | Meaning |
|---|---|
| 0 | Analysis received and saved. |
| 1 | `curl` or `base64` missing. (Also any unexpected shell error, because of `set -e`.) |
| 2 | Usage error, screenshot or config not found, `endpoint` or `model` not set. |
| 3 | Request could not be built, sent, answered with 2xx, or parsed. |

**Acceptance Criteria:**

- AC-09.1: [TESTABLE] Each row above is produced by the matching fixture in
  FR-02, FR-04 and FR-07. **Enforced via:** planned test
  `tests/analyze_screenshot_spec.sh` (planned)

## FR-10 — Runtime

[STRUCTURAL]

Bash, run as `/bin/bash` (3.2 on stock macOS), with `set -Eeo pipefail`
(constitution P-7). JSON is built and parsed with AutoPkg's Python via `tk_python`,
never a bare `python3` (constitution AIP-07). It sources `lib/toolkit-common.sh`
for the toolkit root and `tk_python`, and finds it from its own location.

**Acceptance Criteria:**

- AC-10.1: [STRUCTURAL] No bare `python3` and no bash 4 constructs.
  **Enforced via:** `tests/kit_hygiene_spec.sh` (no bare `python3`); ShellSpec
  under `/bin/bash`; inspection.

## Out of scope

Diagnosing the problem shown; batches of screenshots in one call; remote or cloud
model services; image formats other than PNG and JPEG; redacting screenshots
before sending (the local-only rule is the protection); managing the model server.

---

## Architecture-Incompatible Patterns

**AIP-01: A remote endpoint.** Any shipped config, default or fallback that names a
host other than loopback. Screenshots routinely carry personal and machine data.
**Enforced via:** AC-06.1, AC-06.2.

**AIP-02: A second destination.** Any extra network call: a model list lookup,
an upload of the analysis, telemetry. **Enforced via:** AC-05.2.

**AIP-03: A key in the config file.** `api_key_env` names a variable; a literal
key in YAML ends up in git. **Enforced via:** reviewer check;
`bin/check-sanitized.sh`.

**AIP-04: Making the tool required.** A core workflow step, test or guardrail that
fails when no model server is running. **Enforced via:** AC-01.1.

**AIP-05: Pasting values into code.** Building Python or shell source by string
interpolation of config or prompt text. Pass values as arguments, environment or
stdin instead. **Enforced via:** AC-05.4.

---

## Open Questions

**OQ-01:** Should the tool refuse non-loopback endpoints, with an explicit
override flag for a trusted machine on the local network, or refuse them outright?
Today nothing in the code stops a remote endpoint.

**OQ-02:** Move the API key off the command line (for example `curl -H @file` or
`--config` on stdin), and add a `trap` so the temporary file is always removed.

**OQ-03:** Pass model, prompts and the temp-file path to Python through the
environment or `sys.argv` instead of pasting them into the source (lines 145–180).

**OQ-04:** Send the body from a file (`curl --data-binary @file`) so large
screenshots work. The comment at line 132 avoids the argument limit for Python
but the same body is then passed to `curl` as an argument.

**OQ-05:** Check for AutoPkg's Python with the other prerequisites, and give it
exit 1 with a clear message, instead of failing as exit 127.

**OQ-06:** Validate that `-c` and `-m` have values, and report `output_dir`
creation failures by name, so exit 1 means only "missing dependency".

**OQ-07:** Add a connect and total timeout to the request (for example
`--connect-timeout 5 --max-time 300`), and make them configurable?

**OQ-08:** Send the pretty-printed error body and the `-d` response dump to stderr
(lines 214 and 223 print JSON to stdout).

**OQ-09:** The skill's "Pitfalls" section says the shipped `output_dir` is
a folder under the tracked `reference/` tree. The shipped config now uses the
gitignored `customer/acme/troubleshooting`. The skill needs updating.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-09-27 | Initial spec, written from the existing implementation. |
| 0.2 | 2026-09-27 | FR-03, FR-04, exit codes: the config is read with AutoPkg's Python and PyYAML; `yq` is no longer a prerequisite (KI-21 fixed, AC-03.4 met). A missing Python now exits 127 while reading the config. |
