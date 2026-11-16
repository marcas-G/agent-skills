# 工程 / Engineering

| Skill | Claude Code plugin | Portable behavior |
|---|---|---|
| [fractal](../skills/fractal/SKILL.md) | [fractal](../plugins/fractal) | P0–P8 workflow; no automatic gates outside Claude |
| [refactor-agent](../skills/refactor-agent/SKILL.md) | [refactor-agent](../plugins/refactor-agent) | Human-gated survey, diagnosis and batch refactoring |
| [test-enforcer](../skills/test-enforcer/SKILL.md) | [test-enforcer](../plugins/test-enforcer) | Evidence-first tests; no automatic Stop hook outside Claude |

完整插件：`/plugin install <name>@agent-skills`。Portable Skills 支持带 `_plugin/` 的运行资源，但不自动注册命令或 Hook。
