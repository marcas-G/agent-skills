# Agent Skills Marketplace

[简体中文](README.md) | **English**

A consolidated, installable collection of reusable Agent Skills: **8 portable Agent Skills** and **6 complete Claude Code plugins**, with their actual source files in this repository.

> Claude Code Marketplace installs native commands, hooks and plugin runtimes. Other assistants consume standardized `SKILL.md` directories with a cross-platform installer. Skill discovery does **not** imply that Claude-specific enforcement or background services work natively elsewhere.

## Included capabilities

| Skill | Purpose | Native Claude plugin | Portable delivery |
|---|---|---|---|
| [plain](skills/plain/SKILL.md) | Explain specialized content in familiar terms | `plainkit` | Instruction Skill |
| [termcard](skills/termcard/SKILL.md) | Unpack terminology into five structured questions | `plainkit` | Instruction Skill |
| [cross-domain-exploration](skills/cross-domain-exploration/SKILL.md) | Search other disciplines for unexpected, useful ideas | `plainkit` | Instruction Skill |
| [req-collect](skills/req-collect/SKILL.md) | Stateful requirements interviews | `req-collector` | Skill plus references |
| [fractal](skills/fractal/SKILL.md) | Recursive requirements-driven systems engineering | `fractal` | Workflow adapter, optional scripts |
| [refactor-agent](skills/refactor-agent/SKILL.md) | Comprehension-first, incremental refactoring | `refactor-agent` | Workflow adapter, optional scripts |
| [test-enforcer](skills/test-enforcer/SKILL.md) | Deterministic verification and mutation testing | `test-enforcer` | Workflow adapter, optional scripts |
| [optloop](skills/optloop/SKILL.md) | Isolated, evidence-based optimization loops | `optloop` | Workflow adapter, optional runtime |

Browse by category: [Reasoning](categories/reasoning.md) · [Requirements](categories/requirements.md) · [Engineering](categories/engineering.md) · [Automation](categories/automation.md).

## Option A — Claude Code Marketplace (full native plugins)

Inside Claude Code:

```text
/plugin marketplace add marcas-G/agent-skills
/plugin install plainkit@agent-skills
/plugin install req-collector@agent-skills
/plugin install fractal@agent-skills
/plugin install refactor-agent@agent-skills
/plugin install test-enforcer@agent-skills
/plugin install optloop@agent-skills
```

Install only the packages you need. The Marketplace index is [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json); executable plugin packages live under `plugins/`. The original commands, agents, scripts, hooks and skills are bundled together where required.

- `plainkit` provides three skills in one plugin.
- `fractal` and `test-enforcer` rely on Claude Code hooks and Python to enforce gates.
- `optloop` requires bash, Python, Docker, an authenticated Claude CLI inside workers and suitable permissions; installing it does not start the service.
- Local user state, credentials and secrets are not included.

## Option B — Codex, Cursor, OpenCode, Gemini CLI and GitHub Copilot

```bash
git clone https://github.com/marcas-G/agent-skills.git
cd agent-skills

# Shared ~/.agents/skills folder: recognized by Codex, Cursor, OpenCode, Gemini CLI and Copilot
python3 scripts/install.py --agent universal --scope user

# Agent-specific directory
python3 scripts/install.py --agent opencode --scope user

# Install into another project
python3 scripts/install.py --agent cursor --scope project --target /path/to/project

# Install only selected skills
python3 scripts/install.py --agent codex --only plain termcard cross-domain-exploration

# Preview, update or omit optional runtime payloads
python3 scripts/install.py --agent universal --dry-run
python3 scripts/install.py --agent universal --force
python3 scripts/install.py --agent universal --no-runtime
```

The installer uses the Python standard library, so no pip packages are needed for installation. On Windows, use `py -3` or `python` if `python3` is unavailable.

| Agent | User directory | Project directory |
|---|---|---|
| Codex | `~/.agents/skills/` | `.agents/skills/` |
| Cursor | `~/.cursor/skills/` | `.cursor/skills/` |
| OpenCode | `~/.config/opencode/skills/` | `.opencode/skills/` |
| Gemini CLI | `~/.gemini/skills/` | `.gemini/skills/` |
| GitHub Copilot CLI | `~/.copilot/skills/` | `.github/skills/` |
| Claude Code (portable skills) | `~/.claude/skills/` | `.claude/skills/` |

See the [compatibility matrix](docs/compatibility.md) for limits and official documentation. For Claude Code's **full plugin behavior**, use the Marketplace rather than the portable-skill installer.

## Repository structure

```text
agent-skills/
├── .claude-plugin/marketplace.json  # 6 Claude Code plugins
├── plugins/                         # full original plugin packages
│   ├── plainkit/ req-collector/ fractal/
│   └── refactor-agent/ test-enforcer/ optloop/
├── skills/                          # 8 standard, portable SKILL.md entries
├── scripts/install.py               # Python cross-agent installer
├── scripts/check_catalog.py         # structure/manifest validation
├── tests/                            # installer tests
├── catalog.yaml                     # machine-readable catalog
├── categories/                       # ability categories
├── docs/compatibility.md            # cross-agent support details
├── SOURCES.md                        # provenance / licensing notes
├── README.md                         # Chinese
└── README.en.md                      # English
```

## Portability and enforcement boundaries

The first four portable skills preserve their original instructions and supporting files. The four complex ones use **portable workflow adapters**. For these, the installer also bundles the related complete native plugin under each installed skill's `_plugin/` directory by default; use `--no-runtime` to omit it.

On non-Claude agents, hook-based enforcement, automatic command registration, native subagents and background worker lifecycle are **not automatically transferred**. You can invoke bundled scripts explicitly in an appropriate environment, but do not describe unexecuted checks as completed.

`plain` aims to **explain** the unfamiliar using familiar concepts; `cross-domain-exploration` aims to **expand** the possible solution space by actively searching other domains. They intentionally remain separate.

## Validation and source attribution

```bash
python3 -m pip install "PyYAML>=6,<7"
python3 scripts/check_catalog.py
python3 -m unittest discover -s tests -v
```

CI checks Marketplace metadata, the eight skill entries, bundled plugin assets and installer behavior. Passing these checks does **not** certify installation or native operation on every agent.

See [SOURCES.md](SOURCES.md) for original repositories, copied scope, public/private provenance and licensing. Project-specific skills are intentionally left in their original projects, unchanged.
