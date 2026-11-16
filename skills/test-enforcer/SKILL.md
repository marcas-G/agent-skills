---
name: test-enforcer
description: Evidence-based software testing workflow with layered tests, coverage, mutation checks, false-test detection and explicit blocked status. Use for strict test audits, validating deliveries, or finding tests that only pass superficially.
---

# Test Enforcer — portable guidance

The full native Claude Code plugin contains deterministic test scripts, a test-writer agent and a Stop hook. It lives in `plugins/test-enforcer/` or optionally in the installed skill's `_plugin/`.

**Non-negotiable:** the agent must not fabricate verification evidence. Only actual test-tool outputs count. A test passing is not evidence that the product meets its original requirements.

1. Detect the language, test runner and scope of changed code; report unsupported combinations as BLOCKED.
2. Specify tests for normal behavior, edge cases, and failures; avoid assertions against constants, mocks without behavior checks and swallowed exceptions.
3. Execute the repository's actual tests with captured logs. Report test cases, command, environment, exit code and any skipped dimensions.
4. Collect coverage from the real coverage instrument, not from estimation.
5. When tools permit, perform mutation testing and inspect survivors; report sample size and incomplete batches.
6. Record precise evidence and unresolved gaps; any waiver requires an explicit reason.
7. Mark delivery verified only if agreed checks truly passed. Otherwise report FAIL or BLOCKED.

If installed with `_plugin/` support, the bundled `scripts/` may be run manually after checking their CLI options and project prerequisites. **Automatic Stop interception and delegated test-writer behavior are Claude Code-specific** and are not installed by the portable skill. Use `test-enforcer@agent-skills` in Claude Code for these integrations.
