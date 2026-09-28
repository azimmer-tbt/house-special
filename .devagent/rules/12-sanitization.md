# Sanitization

This repository is a public upstream. Organizations fork it, and a fork's data
must never flow back. Treat every write as potentially public.

1. **Kit files stay org-neutral.** Scripts, `config/checks.yaml`, templates, specs
   and docs use the org config (`config/org.yaml`, `{{TOKENS}}`, `ORG_*`) or the
   fictional Acme Fruit Co. examples — never a real organization's names,
   identifiers, hostnames, share paths or in-house app names.
2. **Customer data stays in `customer/<name>/`.** Vendor binaries, session logs and
   troubleshooting evidence stay in its gitignored folders.
3. **Never write:** real user names or home paths (use `/Users/you`), employee or
   ticket IDs, serial numbers, license keys, internal hostnames or URLs, email
   addresses other than `@*.example`, or screenshots with any of these.
4. **Before any commit or hand-off**, run `bin/check-sanitized.sh` (or `--staged`)
   and `bin/check-doc-links.sh`. Read `.devagent/skills/sanitize-check.md` to
   interpret the findings. Never make a finding go away by weakening a pattern.
5. If you find sensitive data **already committed**, stop and tell the operator.
   Do not push; do not try to rewrite history on your own.
