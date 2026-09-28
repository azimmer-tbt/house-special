---
name: sanitize-check
description: Scan for leaks (home paths, tickets, serials, sync folders, big files, installers, the fork's denylist) with bin/check-sanitized.sh, fix findings the right way, and check doc references with bin/check-doc-links.sh. Use when someone says "check for leaks", "is this safe to share", "sanitize before commit", "scan what's staged", "install the pre-commit hook", or "something confidential got committed".
---
# Sanitize Check

## When to use

Before every commit, before sharing any file from a customer workspace, and always
before contributing upstream. Upstream is public: it carries only Acme examples.

## Inputs

- The tree (default), paths under it, or the staged set.
- The local denylist `.leak-patterns` at the repo root — **gitignored on purpose**
  (a committed denylist leaks every name it lists). One ERE per line (`grep -E`),
  blank lines and `#` comments ignored. List: org names in every spelling, codes and
  prefixes (`YOURORG_`), the reverse-DNS prefix (`com\.yourorg\.`), internal domains
  and hostnames, employee/user-ID formats, in-house app and team names. Full example in
  [forking.md](../../docs/forking.md#the-denylist-leak-patterns).
- With a customer registry (`config/customers.yaml`), each customer's own
  `.leak-patterns` too: applied everywhere except that customer's folder, so a
  customer's names may appear only there.

## Steps

1. Scan:
   ```bash
   bin/check-sanitized.sh                          # whole toolkit tree
   bin/check-sanitized.sh --path docs --path .devagent/skills
   bin/check-sanitized.sh --staged                 # only what you're about to commit
   bin/check-sanitized.sh --customer widgets       # that customer's folder, inside the kit or not
   bin/check-sanitized.sh --all-customers          # each customer folder in turn, worst exit wins
   bin/check-sanitized.sh --install-hook           # pre-commit hook running --staged
   ```
   Other flags: `--patterns <file>`, `--allow <rel>` (exempt a file from the
   denylist only), `--max-kb <n>`, `--root <dir>`.
2. Fix each finding by its label (`file:line: [label] excerpt`):

   | Label | Means | Fix |
   |---|---|---|
   | `home-path` | `/Users/<name>` that isn't a placeholder | Use `/Users/you`, `~`, or `$HOME` |
   | `ticket` | CHG/RITM/INC/CTASK + 6+ digits | Remove it; keep the lesson, not the ticket |
   | `serial` | "Serial Number" + value | Remove or use an obviously fake value |
   | `onedrive` | a tenant sync-folder path | Generic path, e.g. `~/Documents/...` |
   | `large-file` | over `--max-kb` (1024) | Don't commit it; durable store + `files_to_copy.yaml` |
   | `binary` | `.pkg .mpkg .dmg .zip` outside `tests/fixtures` | Remove from the tree / unstage |
   | `denylist:N` | line N of the non-comment patterns in `.leak-patterns` | Replace with Acme placeholders: `com.acmefruit.*`, `Acme_`, `acmefruit.example`, `AcmeFruitCo` |
   | `customer:NAME:N` | line N of customer NAME's `.leak-patterns`, matched outside NAME's folder | Move it into NAME's folder, or replace with Acme placeholders |

   Raw evidence (logs, `autopkg -vvv` output, screenshots) moves to
   `customer/<name>/troubleshooting/` (gitignored) — distil the lesson into a README
   or [`reference/methodology.md`](../../reference/methodology.md) in generic words.
   A test fixture that must contain a matching string splits it so the source line
   doesn't match (e.g. `'One''Drive-'`, as the script itself does).
3. **Swap real apps for the sample set**, not for names you make up. Each public
   app is harmless alone; a list of them fingerprints the org that packaged them.
   Replace a real app with the sample from the same pattern slot or role
   ([`docs/patterns.md`](../../docs/patterns.md)): fictional first, a household
   name only when the point needs a recognisable real vendor, and no name at all
   for a war story ("the first recipe of that shape").

   | Kind | Samples |
   |---|---|
   | Fictional (Acme Fruit Co.) | Orchard Analytics (OrchardLabs; 4c) and its License slice (6c); Kiwi Capture (KiwiSoft; 4d, template); Pomelo Studio (PomeloSoftware; 7, template); AcmeSupport, Quarantine Helper, AcmeSupport-Legacy (6b); Acme Login Banner (6a); Acme Wallpaper, Audit-Control-Expiry (6c); Acme UninstallAgent (6d); Fruit Screensaver (Corkscrews; 2b + 6b slice); Fruta Starter Kit (2d) |
   | Real, open source | Moonlight, Raspberry Pi Imager, Pearcleaner, Orange Data Mining; dockutil, desktoppr, default-browser, Outset, swiftDialog, Nudge, icongrabber; Zettlr, Hammerspoon, draw.io |
   | Household commercial (examples only, never live recipes) | Firefox, Google Chrome, VS Code (3b); Microsoft Word (5); HP Printer Drivers, Xerox Drivers (4a/4b); Citrix Workspace, Cisco Secure Client (4b); Adobe Creative Cloud; Claude; Sophos Endpoint |

   | Role in a lesson | Use |
   |---|---|
   | Security, EDR or monitoring agent, or its daemon config | Sophos Endpoint |
   | VPN client with site config (4e) | Cisco Secure Client |
   | Installer that won't run under AutoPkg, snapshotted into a faux DMG; a snapshot holding several components, split into slices | Pomelo Studio |
   | Licensed app delivered by the vendor | Orchard Analytics |
   | License or config file slice | Orchard Analytics License |
   | Messy vendor file name | `Orchard Analytics 3.1 Installer.dmg` |

   Anything else gets generic words ("a VPN client", "an in-house tool"). Put the
   real names you removed in `.leak-patterns` so they can't come back.
4. Check references in the docs you touched:
   ```bash
   bin/check-doc-links.sh                    # every doc in the kit
   bin/check-doc-links.sh docs/patterns.md .devagent/skills/*.md
   ```
   Relative links resolve from the file's own directory; backticked paths starting
   with a top-level kit directory resolve from the repo root. Placeholders
   (`<name>`, `*`, `%VAR%`, `{{TOKEN}}`) and fenced code are skipped.
5. **If something already leaked into a commit:** don't push. Stop and tell the
   operator what, where and which commits; rewriting local history (amend, interactive
   rebase, or rebuilding the branch from `upstream/main`) is their call. If it was
   pushed, it is compromised: rotate secrets and treat the remote as exposed.

## Outputs

`clean: N file(s) scanned, M denylist pattern(s)` (exit 0), or sorted findings plus a
count (exit 1); 2 = usage error. `check-doc-links.sh`: exit 0 all resolve, 1 broken.

## Verify

Both tools exit 0 on the paths you changed, and `--staged` is clean right before
`git commit`. A new denylist pattern: whole tree stays clean, your own workspace
(`--path customer/<you>`) lights up.

## Pitfalls

- **Never "fix" a finding by weakening a pattern**, widening the placeholder list,
  `--allow`-ing the file, or deleting a line from `.leak-patterns`. Fix the content.
- In a work fork the hook blocks legitimate commits to `customer/<you>/`; install it
  only in a separate upstream-contribution clone, or run `--staged` by hand.
- The scanner skips `.git/`, every `.leak-patterns` file and `reference/autopkg-wiki/`, and only sees what it is
  pointed at — read the diff before pushing anyway.
- Never put real hostnames, user names, ticket numbers or license keys in fixtures
  or sample output ([CONTRIBUTING](../../CONTRIBUTING.md) rule 4).

## References

- [`docs/forking.md`](../../docs/forking.md) §5 (denylist, pre-commit hook, contributing back)
- [`docs/customer-contract.md`](../../docs/customer-contract.md) — what must never be committed
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md)
