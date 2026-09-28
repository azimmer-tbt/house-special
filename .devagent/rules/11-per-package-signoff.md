# Per-Package Operator Sign-Off

AutoPkg recipe work involves many judgement calls: pattern selection, PKG_ID format, chown block design, signature verification approach. These are poor matches for LLM assist without a human in the loop.

## Rule

**Before moving from one per-package step to the next, present the findings and wait for operator sign-off.** Do not proceed to building, validating, or the next app until the operator explicitly approves.

This applies to every step in the per-package workflow:

1. ✅ Research completed — present findings → **wait for sign-off**
2. ✅ Recipe drafted — present for review → **wait for sign-off**
3. ✅ Recipe built — present results → **wait for sign-off** before next app
4. ✅ Recipe validated — present pkg-compare results → **wait for sign-off**

The operator may also signal that multiple steps can be batched ("do all three, then report"). Follow that signal when given, but default to single-step sign-off.
