# Changelog

## 0.2.0 - 2026-09-14

- 更名 recursive-se → **fractal**（同一套问题结构，在任何层级通用）。
- 确定性内核：`docs/SE/fractal-state.json` 唯一真相 + `scripts/fractal.py` 状态机（start/status/gate-pass/waive/register-child/tree/reconcile/gap/check-write）。
- Hook 拦截：未过闸写下一阶段 / 未递归判断写 P5+ / 未登记建子目录——拦下并给解除路径；弃权记录在案（⚠）。
- SessionStart 注入：递归树 + focus + 下一步 + 当阶段最相关纪律（≤15 行；未初始化项目一行就绪提示）。
- 命令 5 → 4：`/fractal-start` `/fractal-next` `/fractal-tree` `/fractal-gap`（se-discipline 折叠为常驻注入）。
- Skills：重命名 fractal-*，Exit Gate 统一为 checklist，P5 文档合并为 P5-detail.md，英文触发词。
- 测试：状态机单测 + 全链路集成测试；reconcile 支持 v0.1 平铺布局检测与反推重建。
- fail-open：python3 缺失/脚本异常只提醒不拦截。

## 0.1.0 - 2026-09-09

- 初版：10 skills（P0-P8 + 递归判断）+ 5 命令，纯提示词 + 文件约定，状态落盘 docs/SE/。
