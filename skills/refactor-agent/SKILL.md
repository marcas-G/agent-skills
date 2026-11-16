---
name: refactor-agent
description: Comprehension-first repository refactoring workflow. Use when asked to understand unfamiliar code, identify maintainability risks, plan safe incremental refactors, and preserve behavior with evidence. Portable guidance; native plugin implements state machine.
---

# Refactor Agent — portable workflow

The full Claude Code plugin is bundled at `plugins/refactor-agent/` (or this installed skill's optional `_plugin/`). This portable adapter does **not** register native `/refactor` commands or run any automatic guards.

1. **Survey** — trace program entry points and concrete behaviors to file/symbol evidence; unknown areas go to a blind-spot list instead of guesses.
2. **Align** — reconcile observed functionality with stakeholder intent and existing system-engineering documents. Obtain a human decision on important ambiguities.
3. **Diagnose** — locate coupling, responsibility drift, missing boundaries and dangerous behavior assumptions.
4. **Plan** — propose small batches with exact file scope, behavior-preservation claim, verification command and rollback approach; obtain scope approval.
5. **Transform** — only after approval, apply the smallest safe batch. Record a clean baseline or git checkpoint first; destructive operations require approval.
6. **Verify and rollback** — run independent checks, report failures verbatim; revert only the current batch if its agreed criteria fail.
7. **Synchronize** — update affected documentation within the authorized change scope; report residual risks and open decisions.

Preserve the native plugin's four human decision points (alignment, scope selection, batch authorization, behavior exception) as **actual user approvals**, not model guesses. Do not claim that a batch passed checks that were not run.

For Claude Code, install `refactor-agent@agent-skills` to obtain native commands and state tracking. Other agents should treat this as a workflow specification, not as an automatic git gate.
