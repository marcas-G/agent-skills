# agent-skills — 通用 Agent Skill 索引

统一发现、统一分类、分仓维护、按需安装。

**本仓库只维护能力目录与校验工具，不复制、移动或重写现有项目的 Skill 源码。** 源仓库是唯一维护源。

## 快速导航

| 类别 | 能力 | 来源仓库 | 调用入口 |
| --- | --- | --- | --- |
| 认知与探索 | [plain](https://github.com/marcas-G/plainkit/blob/main/skills/plain/SKILL.md) | [plainkit](https://github.com/marcas-G/plainkit) | `plain` |
| 认知与探索 | [termcard](https://github.com/marcas-G/plainkit/blob/main/skills/termcard/SKILL.md) | plainkit | `termcard` |
| 认知与探索 | [cross-domain-exploration](https://github.com/marcas-G/plainkit/blob/main/skills/cross-domain-exploration/SKILL.md) | plainkit | `cross-domain-exploration` |
| 需求 | `req-collect` | `req-collector`（私有） | `/req-collector:req` |
| 系统工程 | [fractal](https://github.com/marcas-G/fractal) | fractal | `/fractal-start` |
| 软件工程 | `refactor-agent` | `refactor-agent`（私有） | `/refactor` |
| 软件工程 | `test-enforcer` | `test-enforcer`（私有） | `/test-enforcer` |
| 自动化优化 | [optloop](https://github.com/marcas-G/optloop) | optloop | `/optloop:start-loop` |

**统计口径：8 个通用能力单元。** 不是将内部子技能、评测样本或生成产物逐个算作可独立使用的 Skill。私有源仓库需有相应访问权限，不因本目录公开而自动开放。

## 使用方式

1. 查看 [catalog.yaml](catalog.yaml) 的使用场景、源路径、入口、依赖与状态。
2. 从原仓库安装对应 Skill 或完整插件；不要只复制插件内部的某个 `SKILL.md`。
3. 根据原仓库 README 配置依赖、认证和运行环境。

> `indexed-not-executed` 表示已纳入目录但尚未作实际安装执行验证，**不代表已安装或运行通过**。

## 分类导航

- [认知与探索](categories/reasoning.md)：解释、术语拆解、开放式跨领域启发
- [需求](categories/requirements.md)：多轮访谈与需求整理
- [系统及软件工程](categories/engineering.md)：递归系统工程、重构、测试门禁
- [自动化](categories/automation.md)：隔离式持续优化循环

## 能力边界

- `plain` 的「领域桥」用于**理解陌生内容**；`cross-domain-exploration` 通过检索真实外领域线索**扩展问题空间**，不要求严格同构或立即验证。
- `termcard` 针对单个术语作深度解构，与 `plain` 的长段解释互补。
- `req-collect` 聚焦需求收集；`fractal` 提供从现实问题、需求和架构到验证的递归系统工程。
- `fractal` 的 P0–P8/递归检查、`refactor-agent` 六个内部 Skill、`optloop` 的控制与运行时技能均作为**完整插件**维护，不拆开迁移。

## 不纳入本目录的内容

- `factor-loop`、`stock`、`paperfactory`、`opencode`：项目局部或领域专用 Skill，保留原位，不修改。
- `skill-compiler`：生成结果和评测对照，不作为独立发布 Skill 计数。
- `greet`：场景专用工具，暂不纳入通用目录。

不因为某个项目内部 Skill 包含通用思想，就从项目抽走它；只有独立维护、真实可复用时才考虑新增能力。

## 本地校验与 CI

```bash
python3 -m pip install 'PyYAML>=6,<7'
python3 scripts/check_catalog.py
```

[GitHub Actions](.github/workflows/validate-catalog.yml) 在 push 与 PR 时执行结构校验：检查 YAML、唯一 ID、分类映射与源路径格式。**它不访问原仓库，也不执行安装测试。**

## 维护规则

1. `catalog.yaml` 是唯一机器可读注册源。一个能力一个条目；不按 `SKILL.md` 数量计数。
2. 原仓库维护原始代码、Hook、脚本和插件版本；目录不复制源码或个人状态。
3. 新增能力时核实独立性、用户入口、工具依赖、功能边界和访问权限。
4. 任何新增、合并或下线都只修改本索引；项目局部 Skill 保持原状。
5. 只有实际安装测试获得证据后，才能更新 `status`，不要根据文件存在就声明运行可用。

## 目录结构

```text
agent-skills/
├── README.md
├── catalog.yaml
├── categories/
│   ├── reasoning.md
│   ├── requirements.md
│   ├── engineering.md
│   └── automation.md
├── scripts/check_catalog.py
└── .github/workflows/validate-catalog.yml
```

首次盘点依据为 2026-11-12 的 21 仓库文件级清单；2026-11-16 已核查 8 个代表性源 Skill 文件。未覆盖其他分支、未推送文件或第三方仓库。
