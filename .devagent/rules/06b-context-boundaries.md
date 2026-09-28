# Context Boundaries

Keep context lean. Do **not** read these unless the operator asks, or a specific
question needs one specific file:

| Path | Why |
|------|-----|
| `reference/autopkg-wiki/` | Large third-party clone (the user's, gitignored). Look up one processor page for one question (`Processor-<Name>.md`); never read it for orientation. |
| `customer/*/sessions/` | Past session logs. Read only the current session's file. |
| `customer/*/troubleshooting/` | Raw evidence (logs, screenshots). Read the specific file you were pointed at. |
| `customer/*/input/` | Vendor binaries. Inspect with the `bin/inspect-*.sh` tools, don't read. |
| `dist/` | Build output of `bin/make-dist.sh`. |

Other customers' folders are out of scope unless the task is about them: work
for `customer/acme/` never needs `customer/<other>/`.
