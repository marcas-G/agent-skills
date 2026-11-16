---
description: 推进当前 SoI 的下一阶段（先验收上阶段 Exit Gate，不放过关；支持显式弃权）
argument-hint: [soi-name 可选，默认 focus]
---

推进 fractal 流程的下一步。

## 执行步骤

1. **定位**：运行 `python3 <脚本路径> status [soi]`（无参用 focus；输出当前阶段与上一阶段闸门状态）。
2. **先验收上一阶段**：调用上一阶段的 Skill（`fractal-p0-problem` … `fractal-p8-validation`），逐条过它的 Exit Gate checklist：
   - 全过 → `python3 <脚本路径> gate-pass <soi> <上阶段>`（若尚未登记）
   - 有缺口 → 列出缺口请用户三选：**A** 补齐再推进 / **B** 修改上阶段文档后重验 / **C** 显式弃权 `python3 <脚本路径> waive <soi> <phase> --reason "..."`（记录在案，树上显示 ⚠）
3. **执行下一阶段**：调用对应 Skill 协作完成问答 → 写入 `docs/SE/<soi>/<该阶段文档名>`（写入会被 hook 校验，未过闸会被拦——这是正常的，说明第 2 步没做完）→ 全部勾选该阶段 Exit Gate。
4. **特殊跳转**：
   - **P4 完成 → 强制递归判断**：调用 Skill `fractal-recursion-check` 逐元素判定，逐条登记 `python3 <脚本路径> register-child <soi> <元素> --verdict leaf|promote --note "依据"`；有 promote → 提示用户 `/fractal-start --parent <soi> --element <元素>`（父级停在 P4→P5 之间，子 SoI 完成后回来）。
   - P3 产生派生需求 → 回写 P2 台账后再进 P4。
   - P7 出现 FAIL/BLOCKED 且用户选择带伤前进 → `waive` 记录风险声明后进 P8。
5. 提示下一步（可直接引用 `status` 输出）。

## 阶段序列

P0 → P1 → P2 → P3 → P4 →【强制 fractal-recursion-check】→ 全叶子: P5 → P6 → P7 → P8；有提升: 子 SoI 重走 P0

## 底线

任何阶段答不出核心问题 = 停在那里，宁停勿跳（Rule 1 No Leap）。
