---
name: optloop
description: Supervised iterative optimization workflow with candidate generation, isolated execution, objective measurements, rollback and evidence retention. Use for bounded optimization loops; full automation requires Docker and the native runtime.
---

# OptLoop — portable workflow adapter

OptLoop's complete supervisor and container runtime are bundled in `plugins/optloop/`, or optionally this skill's installed `_plugin/`. Merely invoking this SKILL.md does **not** start any background process, container or native Claude Code loop.

For a requested optimization task:

1. Define the objective, constraints, success metric, budget and stopping criteria.
2. Establish an immutable baseline and deterministic evaluation procedure.
3. Generate small, attributable candidates without altering the baseline.
4. Run candidates in isolated workspaces or containers **only with user authorization and actual tool access**.
5. Compare measured outcomes on the same evaluation protocol; retain failure logs and uncertainty.
6. Promote only an accepted candidate; otherwise roll back or stop.
7. Log iterations, artifacts, selection rationale and unresolved blockers.

**Full execution**: install `optloop@agent-skills` in Claude Code for supervisor commands, worker agents and Docker integration. Outside Claude Code, use the bundled CLI only when correctly installed and configured; any hooks, CLI sessions and worker lifecycle need explicit integration. Never assert optimization progress without observed runs.

Environment: bash, Python, Docker and a working/authenticated Claude CLI inside worker containers. Check the bundled plugin README before starting.
