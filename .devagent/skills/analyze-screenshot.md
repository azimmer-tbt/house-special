---
name: analyze-screenshot
description: OPTIONAL — read installer dialogs, error windows and preference panes from screenshots with a local vision LLM via bin/analyze-screenshot.sh. Use when someone says "what does this screenshot say", "read this installer error", "analyze these screenshots", or drops a PNG of a macOS dialog.
---
# Analyze Screenshot (optional)

## When to use

Only when a local vision-capable LLM is configured. It extracts text, buttons and
state from a dialog screenshot during install troubleshooting. If no endpoint is
set up, read the image yourself (if you can) or ask the operator what it shows —
this skill is a convenience, not part of the core workflow.

## Inputs

- Screenshots saved in `customer/<name>/troubleshooting/` (gitignored except its
  README — screenshots routinely show user names and hostnames).
- [`config/screenshot-analyzer.yaml`](../../config/screenshot-analyzer.yaml):
  `endpoint` (an OpenAI-compatible chat-completions server on this machine),
  `model`, `api_key_env` (the *name* of an env var holding the key, never the key),
  `output_dir`, `system_prompt`.
- `curl` and `base64`. The config is read with AutoPkg's Python and PyYAML (no `yq`).

## Steps

1. Check prerequisites: `command -v curl base64` and that the endpoint answers
   (`curl -s <endpoint>/v1/models`).
2. Point `output_dir` at the troubleshooting folder for this run (or pass a copied
   config with `-c`), so the `<basename>_analysis.md` it writes stays gitignored.
3. Run per screenshot:
   ```bash
   bin/analyze-screenshot.sh customer/<name>/troubleshooting/dialog.png
   bin/analyze-screenshot.sh -m "What error code is shown?" customer/<name>/troubleshooting/dialog.png
   bin/analyze-screenshot.sh -c /path/to/other-config.yaml -d customer/<name>/troubleshooting/dialog.png
   ```
4. Use the extracted text as evidence for the next step (install log, recipe fix);
   it reports what's visible and does not diagnose.

## Outputs

The analysis on stdout and in `<output_dir>/<basename>_analysis.md`.
Exit 0 ok, 1 missing dependency (curl, base64), 2 config or screenshot not
found, 3 API request failed.

## Verify

- Exit 0 and the analysis quotes the dialog's actual text.
- `git status --short` shows no new tracked file (nothing landed outside
  `troubleshooting/`).

## Pitfalls

- The shipped config sets `output_dir: "customer/acme/troubleshooting"`, Acme's
  gitignored drop folder. For another customer, point it at that customer's
  `troubleshooting/`; a tracked folder would put real evidence in git (check with
  `git status` and `bin/check-sanitized.sh`).
- Highlighted regions (a drawn box or arrow) focus the model — mark the part you care about.
- Never send screenshots to a remote endpoint; the config is meant for a local model.

## References

- [`customer/acme/troubleshooting/README.md`](../../customer/acme/troubleshooting/README.md)
- [`docs/known-issues.md`](../../docs/known-issues.md) (KI-21)
- [sanitize-check.md](sanitize-check.md)
