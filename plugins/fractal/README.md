# fractal

> 同一套问题结构，在任何层级通用。
> One question structure, every level of your system.

**English summary**: fractal is a Claude Code plugin that turns recursive, requirements-driven systems engineering into an enforced workflow: Problem → Stakeholders → Requirements → Logical → Architecture → (recursion check) → Detail → Implementation → Verification → Validation. State lives in your repo (`docs/SE/`), and hooks enforce the gates: skipping a phase gets blocked, waivers get recorded. Chinese-first with English triggers.

## 它是什么

独立生产力插件，给"要建一个不止三五行代码的系统"的人——软件、硬件、流程、组织，任何可以递归分解的系统。

核心主张：**工程是递归树，不是单链条。** 地铁线是整体，牵引供电是它的部分；牵引供电对变电所又是整体。每个层级（SoI, System-of-Interest）面对同一套问题结构：

`问题 → 干系人 → 需求 → 逻辑 → 架构 →【递归判断：叶子做详设，复杂提升为新 SoI】→ 详设 → 实现 → 验证 → 确认`

与"提示词库"的区别：**纪律有牙齿**。状态机内核（`docs/SE/fractal-state.json` 是唯一真相）+ hook 拦截，跳步会被拦下并给解除路径；弃权必须显式并记录在案（树上 ⚠）。

## 安装

依赖：Claude Code + python3（macOS/Linux/WSL/Git-Bash）。

```bash
# 1) 把本仓库添加为 marketplace（https://github.com/marcas-G/fractal 换成 git 地址，本地路径也可以）
claude plugin marketplace add https://github.com/marcas-G/fractal

# 2) 安装（用户级，所有项目可用）
claude plugin install fractal@fractal
```

也可以在 Claude Code 里 `/plugin` → 浏览 marketplace → 安装 fractal。

装完**新开会话**即可使用（命令与技能在会话启动时加载）。

> 注意：直接 `git clone` 到 `~/.claude/plugins/` 的装法**不生效**——插件必须经 marketplace 注册。

## 5 分钟上手

1. `/fractal-start my-system` —— 回答 P0 五问（用户确认才算过）
2. `/fractal-next` —— 一路推进，每阶段先过上阶段 Exit Gate
3. P4 完成后逐元素递归判断：简单元素做 P5 详设；复杂的提升为新 SoI 重走 P0
4. `/fractal-tree` 看递归树与卡点；`/fractal-gap` 看差距、定下一步工作

## 它替你拦住什么

| 规则 | 拦截 | 解除 |
|---|---|---|
| 1 阶段闸门 | 上一阶段未过闸/弃权，写下一阶段文档 | `/fractal-next` 过闸，或 `waive` 显式弃权 |
| 2 递归闸门 | 未做递归判断就写 P5+ 文档 | `fractal-recursion-check` + `register-child` |
| 3 孤儿目录 | 在未登记的目录写 SoI 文档 | `/fractal-start` 正式登记 |

五条纪律（SessionStart 自动注入当阶段最相关一条，全文在 `docs/SE/00-overview.md`）：

1. **No Leap 不跳步** 2. **No Orphan 无孤儿** 3. **Single Ownership 唯一主责** 4. **No Hidden Design 无隐藏设计** 5. **Evidence over Claim 证据高于宣称**

冲突裁决：进度 vs 纪律 → 纪律赢。

## 方法论速览

| 阶段 | 唯一核心问题 | 产出 |
|---|---|---|
| P0 问题定义 | 现实世界有什么问题？为什么值得解决？ | Problem Statement + 边界 |
| P1 干系人 | 谁会怎样与系统交互？处于什么环境？ | 干系人表 + 边界 + 场景 C1/C2… |
| P2 需求 | 必须具备什么可验证的能力？ | REQ 台账（每条挂 Criterion） |
| P3 逻辑分解 | 逻辑上必须发生什么？ | LF 清单 + 时序 + 失败响应 |
| P4 架构 | 哪些元素承担哪些逻辑责任？ | LF×E 分配 + 接口合约 + ADR |
| —— | **递归判断**：每个元素——职责单一/接口闭合/无独立干系人/无独立问题，四条全满足是叶子进 P5，否则提升为新 SoI 重走 P0 | 判定表（双写 state） |
| P5 详设 | 叶子元素具体怎样工作？ | 接口五件套 + 不变量 + 故障语义 |
| P6 实现 | 产物是否忠实实现设计？ | 映射表 + 偏差清单 |
| P7 验证 | 有什么证据证明规格被正确实现？ | REQ×证据矩阵（PASS/FAIL/BLOCKED） |
| P8 确认 | 最初的问题真正解决了吗？ | P0 原文核对 + 最终判定 |

## 状态与文件

```
docs/SE/
├── 00-overview.md                    索引 + 使用规则 + 五条纪律（脚本生成）
├── fractal-state.json                ★ 唯一真相（SoI 树/阶段/闸门/弃权）
├── <soi-name>/                       每个 SoI 一套 P0-P8 文档
├── <soi-name>--<元素名>/              子 SoI——平铺兄弟目录（promote 时由脚本创建，
│                                     命名 <父>--<元素>；不要手工建嵌套子目录）
└── ...各 SoI 目录并列，父子关系只存在于 state 中
```

允许手工编辑 state（schema 见源码），`reconcile` 会校验并报告漂移。

## 降级

python3 不可用或脚本异常时：hook 只提醒不拦截（fail-open），命令按文档手工回退。工具坏，不阻塞你的项目。

## FAQ

**为什么不让我直接写代码？** Rule 1 No Leap：从"需要 X"直跳"方案 Y"是多数返工的根源。先过 P0-P2，很快的。

**我赶时间，能跳吗？** 能——显式弃权：`waive <soi> <phase> --reason "..."`。记录在案、树上 ⚠，不粉饰。

**v0.1（recursive-se）的旧文档怎么办？** 布局不兼容。装 v0.2 后跑 `python3 <脚本> reconcile`，按提示把旧文档移入 SoI 子目录重新登记。

**支持 Windows 吗？** 原生 Windows 不在当前范围；WSL / Git-Bash 可用。

## 方法论来源

《递归式需求驱动系统工程开发手册》——本插件是该方法论的执行器。
