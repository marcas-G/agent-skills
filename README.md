# Agent Skills Marketplace

**中文** | [English](README.en.md)

一套可统一安装、跨 Agent 复用的通用技能集合。含 **8 个可发现的 Agent Skills** 和 **6 套完整 Claude Code 插件**，全部源码集中在本仓库，不再只是索引链接。

> 说明：Claude Code 的 Marketplace 提供完整命令、Hook 和运行时；其他 Agent 使用开放的 `SKILL.md` 目录及兼容安装器。跨 Agent 的“可发现/可调用”并不意味着自动继承 Claude Code 的强制门禁或后台进程。

## 能力一览

| Skill / 能力 | 用途 | Claude Code Marketplace 包 | 其他 Agent |
|---|---|---|---|
| [plain](skills/plain/SKILL.md) | 专业内容通俗解释、领域桥 | `plainkit` | 原生说明型 Skill |
| [termcard](skills/termcard/SKILL.md) | 五格术语解构 | `plainkit` | 原生说明型 Skill |
| [cross-domain-exploration](skills/cross-domain-exploration/SKILL.md) | 跨领域真实搜索、开放启发 | `plainkit` | 原生说明型 Skill |
| [req-collect](skills/req-collect/SKILL.md) | 多轮需求访谈和落档 | `req-collector` | Skill + references |
| [fractal](skills/fractal/SKILL.md) | 递归系统工程与阶段门禁 | `fractal` | 工作流适配；脚本可选 |
| [refactor-agent](skills/refactor-agent/SKILL.md) | 梳理式重构、逐批回滚 | `refactor-agent` | 工作流适配；脚本可选 |
| [test-enforcer](skills/test-enforcer/SKILL.md) | 严格测试、证据和变异验证 | `test-enforcer` | 工作流适配；脚本可选 |
| [optloop](skills/optloop/SKILL.md) | 隔离式持续优化循环 | `optloop` | 工作流适配；运行时可选 |

这些能力分为四类：[认知与探索](categories/reasoning.md)、[需求](categories/requirements.md)、[工程](categories/engineering.md)、[优化自动化](categories/automation.md)。

## 安装 A：Claude Code Marketplace（完整功能）

在 Claude Code 中运行：

```text
/plugin marketplace add marcas-G/agent-skills
/plugin install plainkit@agent-skills
/plugin install req-collector@agent-skills
/plugin install fractal@agent-skills
/plugin install refactor-agent@agent-skills
/plugin install test-enforcer@agent-skills
/plugin install optloop@agent-skills
```

只安装需要的插件即可，无须全部安装。Claude Code 可从仓库根目录的 [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) 发现六个插件。完整插件位于 `plugins/`，保留其 `skills/`、`commands/`、`hooks/`、`agents/`、`scripts/` 等依赖（以实际插件为准）。

- `plainkit` 一次提供三个认知 Skill。
- `fractal`、`test-enforcer` 的门禁依赖 Claude Code Hooks 和 Python。
- `optloop` 需要 bash、Python、Docker、容器内 Claude CLI 及可用认证。安装不等于启动。
- 原有插件的用户状态、密钥和环境依赖**不会**放进本仓库，也不会由安装过程自动配置。

## 安装 B：Codex / Cursor / OpenCode / Gemini CLI / GitHub Copilot

先将本仓库克隆到本地：

```bash
git clone https://github.com/marcas-G/agent-skills.git
cd agent-skills
```

然后使用 Python 3 标准库安装器（无额外 pip 依赖）：

```bash
# 通用目录 ~/.agents/skills；Codex、Cursor、OpenCode、Gemini CLI、Copilot 均能发现
python3 scripts/install.py --agent universal --scope user

# 或选择 Agent 的专用目录：codex / cursor / opencode / gemini / copilot / claude
python3 scripts/install.py --agent opencode --scope user
python3 scripts/install.py --agent cursor --scope project --target /path/to/your-project

# 按需安装，不覆盖已有技能
python3 scripts/install.py --agent codex --only plain termcard cross-domain-exploration

# 预览与更新
python3 scripts/install.py --agent universal --dry-run
python3 scripts/install.py --agent universal --force

# 不打包 4 个复杂 Skill 的原生脚本资源（仅保留流程说明）
python3 scripts/install.py --agent universal --no-runtime
```

Windows 可将 `python3` 替换为 `py -3` 或 `python`；安装器使用跨平台 Python 文件操作。默认用户级安装；`--scope project` 使用当前目录，`--target` 可指定目标项目或用户目录。

**兼容范围**：

| Agent | 用户级 Skill 目录 | 项目级 Skill 目录 |
|---|---|---|
| Codex | `~/.agents/skills/` | `.agents/skills/` |
| Cursor | `~/.cursor/skills/` | `.cursor/skills/` |
| OpenCode | `~/.config/opencode/skills/` | `.opencode/skills/` |
| Gemini CLI | `~/.gemini/skills/` | `.gemini/skills/` |
| GitHub Copilot CLI | `~/.copilot/skills/` | `.github/skills/` |
| Claude Code（Skill 模式） | `~/.claude/skills/` | `.claude/skills/` |

其他 Agent 建议优先使用 `universal`（`.agents/skills`）路径；Claude Code 要使用完整插件功能，请选择 Marketplace 安装而非 Skill 模式。详细情况见 [兼容性说明](docs/compatibility.md)。

## 目录结构

```text
agent-skills/
├── .claude-plugin/marketplace.json    # Claude Code Marketplace 注册表
├── plugins/                           # 六套原生插件完整运行包
│   ├── plainkit/
│   ├── req-collector/
│   ├── fractal/
│   ├── refactor-agent/
│   ├── test-enforcer/
│   └── optloop/
├── skills/                            # 八个跨 Agent SKILL.md 入口
│   ├── plain/  termcard/  cross-domain-exploration/
│   ├── req-collect/
│   └── fractal/  refactor-agent/  test-enforcer/  optloop/
├── scripts/install.py                 # 多 Agent 安装器
├── scripts/check_catalog.py           # 内容/Marketplace 校验
├── tests/                             # 安装器测试
├── catalog.yaml                       # 统一机器可读元数据
├── categories/                        # 分类导航
├── docs/compatibility.md              # 兼容与能力边界
├── SOURCES.md                         # 原始仓库、复制范围和许可证说明
├── README.md
└── README.en.md
```

## 核心区别：通用 Skill 与原生插件

`plain` 负责把专业内容解释清楚，`cross-domain-exploration` 负责主动向其他领域寻找值得借鉴的新视角；两者不是同一类任务。

`fractal`、`refactor-agent`、`test-enforcer`、`optloop` 在 Claude Code 中提供原生工作流。跨 Agent 安装会将这四个能力所需的插件文件复制到对应 Skill 的 `_plugin/`，方便在允许的环境中手动调用脚本，但**不会自动注入 Hook、注册 Claude 专用子代理或启动守护进程**。不要将文本纪律误报为实际强制检查。

## 验证与来源

```bash
python3 -m pip install "PyYAML>=6,<7"
python3 scripts/check_catalog.py
python3 -m unittest discover -s tests -v
```

CI 检查 Marketplace、8 个 Skill 的头部元数据、插件资产完整性和安装器行为。通过这些测试仅表示**结构与本地安装通过**，不表示各平台实机集成已全部跑通。

源码来源、是否私有、复制边界见 [SOURCES.md](SOURCES.md)。本仓库是统一发布源，原项目仓库不作修改；项目专属 Skill（如量化因子工作流和 paperfactory 内嵌技能）仍留在原项目。
