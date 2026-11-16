# Cross-agent compatibility matrix

Portable skills follow the `SKILL.md` directory convention, while the Claude Code Marketplace installs complete native plugins. These are **different installation methods**.

| Agent | User skill directory | Project skill directory | Mode |
|---|---|---|---|
| Claude Code | `~/.claude/skills` | `.claude/skills` | 8 portable skills; also 6 native Marketplace plugins |
| Codex | `~/.agents/skills` | `.agents/skills` | 8 portable skills |
| Cursor | `~/.cursor/skills` | `.cursor/skills` | 8 portable skills; `.agents/skills` also recognized |
| OpenCode | `~/.config/opencode/skills` | `.opencode/skills` | 8 portable skills; `.agents/skills` also recognized |
| Gemini CLI | `~/.gemini/skills` | `.gemini/skills` | 8 portable skills; `.agents/skills` also recognized |
| GitHub Copilot CLI | `~/.copilot/skills` | `.github/skills` | 8 portable skills; `.agents/skills` also recognized |

`python3 scripts/install.py --agent universal` puts portable skills at `~/.agents/skills`, suitable for Codex, Cursor, OpenCode, Gemini CLI and Copilot. For Claude Code's native plugin commands/hooks, install through the Marketplace instead. To install into project workspace, use `--scope project`, or add `--target /path/to/project`.

**Portable limitations:** Claude-specific hooks, commands, subagent registration and stateful enforcement do not automatically work in another agent. The installer includes runtime scripts in `_plugin/` for the four adapter skills unless `--no-runtime` is specified. Runtime existence does not imply execution or agent integration. OptLoop also requires Docker/Claude CLI credentials.

## Source documentation

- [Codex Agent Skills](https://learn.chatgpt.com/docs/build-skills)
- [Cursor Agent Skills](https://cursor.com/docs/skills)
- [OpenCode Skills](https://opencode.ai/docs/skills)
- [Gemini CLI Skills](https://geminicli.com/docs/cli/skills/)
- [GitHub Copilot Skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills)
- [Claude Code plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
