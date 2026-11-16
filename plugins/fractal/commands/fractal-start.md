---
description: 为新系统/子系统（SoI）立项——初始化状态与文档骨架，从 P0 开始
argument-hint: [soi-name 可选；子 SoI 在父级 register-child 之后自动命名]
---

为新的 System-of-Interest 启动 fractal 流程。

## 执行步骤

1. 初始化：运行状态脚本 `python3 <脚本路径> start <name>`（脚本路径见会话启动时的「fractal 已就绪」行；子 SoI 用 `start --parent <父soi> --element <元素>`，名称可省略自动取 `<父>--<元素>`）。脚本会登记 state、建目录、生成/更新 `docs/SE/00-overview.md`、设 focus。
2. 若是子 SoI：读取父级 `docs/SE/<父>/P4-architecture.md` 中该元素的职责与接口合约**原文**，作为本 SoI P1/P2 的硬边界输入（引用原文，不重述）。
3. 调用 Skill `fractal-p0-problem`，协作完成 P0 五问（可先基于上下文起草，再请用户逐问确认——**用户确认才算过**）。
4. 全部勾选 Exit Gate 自查后写入 `docs/SE/<soi>/P0-problem.md`，运行 `python3 <脚本路径> gate-pass <soi> P0`。
5. 提示用户：下一步 `/fractal-next` 进 P1。

## 注意

- 全程遵守五条纪律（速查在 `docs/SE/00-overview.md`，会话启动时注入当阶段最相关一条）。
