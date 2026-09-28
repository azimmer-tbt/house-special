---
name: first-recipe-interview
description: Walk a newcomer through building their first recipe as an interview — one question at a time, running read-only inspection commands (codesign, pkgutil, spctl, the kit's inspect tools) and turning each result into a "here's what this found, agree?" card that settles one step of the decision tree. Use when someone says "help me build my first recipe", "walk me through this package", "I've been handed this software, what now?", "interview me", or is new and has one package to turn into a recipe.
---
# First Recipe Interview

## When to use

Someone who knows Unix but isn't a Mac admin has one piece of software and has been
asked to "build a recipe". They could read
[`docs/build-your-first-recipe.md`](../../docs/build-your-first-recipe.md) alone; this
skill is the same walkthrough, done *with* them. You ask, you run the looking-around
commands, you show what they found, and they agree or push back. Every answer lands
in a record that becomes the recipe's README.

**The guide is the script.** Read
[`docs/build-your-first-recipe.md`](../../docs/build-your-first-recipe.md) before the
first question. Its steps, figures and tables are what you're walking the person
through; this skill only adds how to run the conversation. When the two disagree,
the guide wins. Fix this skill.

Not for batches (use [`plan-of-attack`](plan-of-attack.md)) or for people who already
know which template they want (use
[`autopkg-recipe-development`](autopkg-recipe-development.md)).

## Inputs

- The software, or where it came from: a file in `customer/<name>/input/<App>/`, a
  download URL, or just a product name.
- The customer name (`customer/<name>/`); Acme if they're practising.
- **Suspicious Package** and **Apparency** installed (prerequisites, see
  [getting-started](../../docs/getting-started.md)). Check with
  `ls -d "/Applications/Suspicious Package.app" /Applications/Apparency.app`; if one
  is missing, ask them to install it before Step 2.
- Optional, and worth asking for: **prior art**. That means an existing recipe, a
  community recipe, or an old version of the package this recipe will replace.

## The gameplay loop

Each turn goes down one level of the decision tree (the guide's Figures 1–3):

1. **Pick the next open question** in the tree.
2. **Can a command answer it?** Run it (read-only) and show an *evidence card*:
   "Here's what codesign found. Agree?" If not, ask a *question card*.
3. **They agree, disagree or aren't sure.** Write the answer in the record.
4. **Does that settle a branch?** Show a *decision card* ("So this is Pattern
   4a. Agree?") and move down the tree.

Repeat until the tree ends in a template, then build, lint and run. Some steps are
settled by evidence (signature, file type, what an old package installed), some
only by the person (where it came from, what the org adds), and most by both.

## Ground rules

- **One question per message.** Offer the likely answers as choices; "not sure" is
  always allowed. A "not sure" is parked in the record as an open question for the
  reviewer, not guessed.
- **Evidence beats memory.** Where a command can settle a step, run it and show the
  result rather than asking the person to recall.
- **Inspect, never execute.** Everything you run is read-only. Never install the
  package, run its scripts or launch the app. No `sudo`: when a step needs it
  (`bin/pkg-reverse.sh`), give the person the command to run themselves.
- **Work in a scratch folder**, `"${TMPDIR:-/tmp}/first-recipe-<App>"`. Mount DMGs
  with `-nobrowse -readonly` and detach them when done. Nothing from `input/` or
  the scratch folder is ever committed.
- **The person decides.** If they disagree with a card, don't argue: record both
  their view and the evidence, and flag it for review.
- Point to the guide section for the "why" (one link per card), rather than
  explaining at length.

## The three kinds of card

Every message you send in the interview is one of these.

**Question**: when only the person knows.
```text
Step 1 of 4: where did it come from?
How did you get this file?
  a) Downloaded it from the vendor's website
  b) From a GitHub releases page
  c) Someone emailed it / it was on a share / it's behind a login
  d) It's an old in-house package, nobody has the sources
  e) Not sure
```

**Evidence**: after running a command. Show the facts that matter (not the raw
dump), say what they mean for the recipe, and ask.
```text
Here's what the signature check found:

  Signed by   Developer ID Installer: Example Vendor Inc (ABCDE12345)
  Team ID     ABCDE12345
  Notarized   yes (spctl: accepted, source=Notarized Developer ID)

What it means: the recipe can verify every future download against this
Team ID. The recipe checks it on every download, and the README records it.

Agree?  (yes / no / not sure)
```

**Decision**: when the answers so far settle a branch of the flowchart.
```text
So far: a signed vendor .pkg (flat, one component), emailed by the vendor.
That makes this Pattern 4a: copy the vendor's package as-is (Figure 1).
Agree?  (yes / no / not sure)
```

## Steps

Follow the guide's steps in order. Start with Step 0, then settle each question
with a card before moving on.

### 0. Set up

Ask the app name and customer. Create the scratch folder and the record (see
**Outputs**). If they have the file, make sure it's in
`customer/<name>/input/<App>/` (gitignored).

### 0b. Prior art

Ask: **"Has anyone packaged this before?"** Then check the three places it could be.
Whatever you find gets *reviewed*, not copied blindly.

| Prior art | How to find it | Review with |
|---|---|---|
| A recipe already in the customer's repo | `ls customer/<name>/output/recipes/*/ \| grep -i <App>`, and the catalogue CSV | Is it lint-clean? Does its README say why it looks the way it does? Maybe the job is a fix, not a new recipe ([`docs/updating-existing-recipes.md`](../../docs/updating-existing-recipes.md)) |
| A community AutoPkg recipe | `autopkg search <App>` (read-only; searches github.com/autopkg) | The community recipe audit, [Standards §6.10.2](../../reference/recipe-standards.md): vendor download, signature check, same Team ID, no hidden payload. If it passes, adopt it the §6.10.3 way (copy, don't override) |
| An old package the org deployed | Ask: **"Do you have an old version of this package?"** | Explode it (*The old package*, below). It answers much of Steps 3 and 4 in advance |

Evidence card for each hit ("There's a community recipe in `<author>-recipes`. It
downloads from the vendor and checks the signature. Want to audit it before we
build our own?").

### 1. Where did it come from? (guide Step 1, Figure 1)

Question card first ("How did you get this file?"), then back it with evidence
where you can:

| If they say… | Run | Settles |
|---|---|---|
| They have the `.app` | `/usr/libexec/PlistBuddy -c 'Print :SUFeedURL' "<App>.app/Contents/Info.plist"` | A URL means **Pattern 1** (Sparkle), whatever else they said |
| A web link | Look at it: `github.com/<owner>/<repo>/releases` means **2**; `…/latest` or `fwlink` means **3b** or **5**; a version in the URL means **3c** | Pattern 2, 3 or 5 |
| It's a `.pkg` of unclear origin | `bin/analyze-package.sh <file>.pkg --customer <name>` | Vendor vs in-house (**6**) |
| Emailed, on a share, or behind a login | (nothing to run) | **Pattern 4** |

### 2. What kind of file is it? (guide Step 2)

```bash
file <file>
pkgutil --expand <file>.pkg "$SCRATCH/x" && ls "$SCRATCH/x"   # Distribution at the top → 4b, else 4a
bin/inspect-dmg.sh <file>.dmg
bin/inspect-archive.sh <file>.zip
bin/inspect-app.sh <App>.app
```

Evidence card: what the file really is, and what's inside. For a vendor drop
(Pattern 4), follow with a decision card for the letter.

**The signature check.** Every recipe needs this, whatever the pattern.

```bash
# .pkg
pkgutil --check-signature <file>.pkg
spctl -a -vv -t install <file>.pkg
# .app (mount a DMG read-only first)
codesign -dvv "<App>.app" 2>&1 | grep -E '^(Identifier|Authority|TeamIdentifier)'
codesign -dr - "<App>.app"
spctl -a -vv "<App>.app"
```

Evidence card, with the exact values the recipe needs: the three authority lines
(`.pkg`) or the designated requirement (`.app`), the Team ID, and whether it's
notarized. For ad-hoc or unsigned results, use the guide's Step 2 table and say
plainly that it needs a reviewer's eye.

**Second opinion.** After the evidence card, ask the person to open the same file in
[Suspicious Package](https://www.mothersruin.com/software/SuspiciousPackage/)
(`.pkg`: `open -a "Suspicious Package" <file>.pkg`) or
[Apparency](https://www.mothersruin.com/software/Apparency/) (`.app`) and tell you
whether the signer, Team ID and notarization match what you showed. Record it
("agrees with Suspicious Package: yes"). If they don't match, stop and find out why
before going on: one of the two is wrong, and it may be our script.

### 3. Do we add anything? (guide Step 3, Figures 2 and 3)

- Question card: "Does anything else go with this: a license file, a config file,
  something that starts at login?"
- If there's an old package, show what it installed beyond the app (evidence card:
  "The old package also installed these 3 files, which aren't part of the vendor's
  app. Are they ours?").
- For each extra, a decision card from Figure 3. **Sealed vendor `.pkg` (1a, 2a, 3a,
  4a, 4b, 5)?** Then slicing is required. **Rebuilt app?** Then slicing is
  preferred. Name the slice type (6a/6b/6c/6d) and its install order ("installs
  after `<Org>_<App>.pkg`").
- A license key is a secret: it goes in the vendor cache, never in git.

### 4. Are there install scripts? (guide Step 4)

```bash
find "$SCRATCH/x" -path '*Scripts*' -type f            # from the expanded package
```

For each script: show it to the person, then an evidence card summarising what it
changes, anything hard-coded (versions, users, servers, paths), and whether it acts
on a user (then use [`postinstall-as-user`](postinstall-as-user.md)). Ask: "Keep it,
fix it, or drop it?" Any script that's kept must pass
`shellcheck -S warning <script>` and `bash -n <script>`.

### 5–7. Write, run, hand over (guide Steps 5–7)

- Decision card: the template or example to start from (guide Step 5 table). Copy it
  into `customer/<name>/output/recipes/<Vendor>/<App>/`.
- Fill in the values from the record. Show each file before writing it: they should
  see where every value came from.
- Run the checks and the build, and show the results as evidence cards:
  ```bash
  bin/scan-placeholders.sh --repo customer/<name>/output <App>
  bin/recipe-linter.sh --repo customer/<name>/output --pair-check
  autopkg run -v --search-dir customer/<name>/output/recipes \
    customer/<name>/output/recipes/<Vendor>/<App>/<App>.pkg.recipe.yaml < /dev/null
  ```
  (`< /dev/null` makes an interactive AutoPkg prompt fail rather than hang.)
- **Optional: the equivalence audit** ([Standards §6.10.2](../../reference/recipe-standards.md)).
  Offer it with a question card ("We can check the build against the old package / the
  vendor's own download. It takes a few minutes and catches wrong-vendor and
  wrong-version builds. Do it now? yes / skip"). If they skip, record "skipped" and why.
  If yes, one evidence card per check, in this order:
  1. **Signature:** Team ID of the prior art and of the build, side by side. Any
     difference is a stop, not a question.
  2. **Contents:** `bin/pkg-compare.sh --old-pkg <old> --new-pkg <built>`. Show files
     only in the old package as a list ("These look like things your org added. Each
     one needs a slice. Agree?"), and files only in the build that sit outside the
     `.app` ("I don't know what these are yet. Worth a look?").
  3. **Version:** both versions and the build's `LSMinimumSystemVersion` against
     `fleet_min_macos` from `config/org.yaml`. Same major line passes. A jump gets its
     own card: "The old package is 14.2; this build is 2027.2.1, and it needs macOS 15
     while your fleet starts at 14. Is that intended, and does your license cover
     2027? If not, we pin the recipe to the 14.x line."
  With no prior art, use mode B: ask them to download the vendor's file by hand and
  compare signature and version with the cached download; the install comparison needs
  test Macs, so give them the steps rather than running them.
- Draft `README.md` from the record, including the open questions and the audit
  result. Stop there for sign-off ([rule 11](../rules/11-per-package-signoff.md)).

## The old package

The most useful thing a newcomer can bring. It shows what the org actually
deployed: every file, owner and script.

```bash
pkgutil --expand old.pkg "$SCRATCH/old"
ls "$SCRATCH/old"                                            # Distribution? component pkgs?
find "$SCRATCH/old" -name Bom -exec lsbom -p MUGf {} \;      # every path, owner, mode
find "$SCRATCH/old" -path '*Scripts*' -type f                # scripts to review (Step 4)
```

If the old version is installed on a Mac they can check, the receipts tell the same
story: `pkgutil --pkgs | grep -i <vendor>`, then `pkgutil --files <package-id>`.

Evidence card: "The old package installs the app, plus these files, plus these
scripts." Keep the expanded copy: `bin/pkg-compare.sh` compares it with the new
build in Step 6.

## Outputs

- The **record**, kept as you go:
  `customer/<name>/sessions/session-NNN-first-recipe-<App>.md`
  ([rule 07](../rules/07-sessions.md)). One line per settled card:
  ```markdown
  | Step | Question | Answer | Evidence | Agreed |
  |---|---|---|---|---|
  | 2 | Signature | Developer ID Installer, ABCDE12345, notarized | pkgutil --check-signature, spctl | yes |
  ```
  Then **Open questions** (every "not sure" and disagreement), and **Pattern**
  (final, with the one-line reason).
- The recipe folder, lint-clean, with a README drafted from the record.

## Verify

- Every step of the guide has at least one card, and every card in the record has
  an answer or is listed under Open questions.
- The pattern in the record matches the `Comment:` in both recipes.
- Lint passes; `autopkg run` result recorded (success, or the error and what's next).

## Pitfalls

- **Asking what a command could answer.** "Is it signed?" is a command, not a
  question.
- **Several questions in one message.** Newcomers answer the first and skip the rest.
- **Raw output.** Show the three lines that matter, not 40 lines of `codesign`.
- **`codesign` on a `.pkg`.** Wrong tool; use `pkgutil --check-signature`
  (methodology lesson 5).
- **Trusting the file name.** Run `file` on it: a ".pkg" may be a zip, and a
  ".dmg" may hold a `.pkg` rather than an app.
- **Leaving DMGs mounted.** Always `hdiutil detach` what you attached.
