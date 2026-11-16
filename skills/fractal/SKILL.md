---
name: fractal
description: Recursive systems-engineering workflow for defining problems, stakeholders, requirements, logical design, architecture, implementation, verification and validation. Use for complex systems and structured decomposition. Claude Code plugin offers enforced gates; portable skill is guidance-only.
---

# Fractal — portable systems-engineering workflow

This portable skill is the **guidance layer**, not the full Claude Code plugin. Do not claim that a gate, hook, registry or state-machine command ran unless it actually ran. The complete original plugin is bundled in `plugins/fractal/` in this repository and optionally under this skill's `_plugin/` when installed with the bundle installer.

Work through the following stages; keep artifacts and decisions traceable, and ask for approval before irreversible actions.

1. **P0 — Problem**: actual real-world problem, consequences, limitations of existing approaches, desired outcome, explicit scope. Do not replace outcome with a feature request.
2. **P1 — Stakeholders**: external actors, constraints, interactions and scenarios.
3. **P2 — Requirements**: requirements tied to testable acceptance criteria.
4. **P3 — Logical behavior**: responsibilities, sequence, failure responses, independent of implementation.
5. **P4 — Architecture**: allocate logical functions to components, define interfaces and architectural decisions.
6. **Recursion check**: for each complex element, decide whether it is a leaf or a new System-of-Interest requiring its own P0–P4.
7. **P5 — Detail**: precise interface/behavior design for leaves.
8. **P6 — Implementation**: reconcile implemented functionality against specifications.
9. **P7 — Verification**: evidence that implementation matches requirements.
10. **P8 — Validation**: evidence that the original stakeholder problem was resolved.

Maintain traceable documents under `docs/SE/` and distinguish unverified from verified claims. Do not advance a stage without required evidence or an explicit recorded waiver. Never state that this portable skill itself enforces gates.

**Native execution**: Claude Code users should install `fractal@agent-skills` for commands, state machine and hooks. Other agents can follow this workflow manually, and may use bundled Python runtime where their tool permissions allow; Claude-specific hooks do not automatically run.
