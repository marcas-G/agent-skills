# refactor-agent

梳理式重构 agent（Claude Code plugin）。核心观点：**重构不是表面整理，是梳理**——需求梳理 → 功能梳理 → 混乱识别 → 分批解耦改造。开发到哪乱到哪，随时来一轮，不用攒到大爆炸。

## 安装

放入 `~/.claude/plugins/` 或经 marketplace 安装后重启 Claude Code。

## 使用

| 命令 | 用途 |
|---|---|
| `/refactor [范围]` | 发起一轮重构（全库/模块/文件） |
| `/refactor-status` | 查进度 + 会话内混乱信号检测 |
| `/refactor-resume` | 中断后恢复现场 |

## 机制（一句话版）

- **四个决策点人工把关**：①意图对齐 ②范围圈定 ③批次放行 ④行为例外审批——AI 分析与执行，人拍板。
- **每批一提交、独立可回退**：测试失败自动 revert 该批，已确认批次不受牵连。
- **无测试自动降级**：只做安全类重构（显式清单）+ 人工验证清单加密确认。
- **中断可恢复**：事件日志为真相源，state 可重放重建；决策等待中快照带问题+选项，恢复直接重问。
- **SE 联动（可选）**：项目有 fractal docs/SE 时，梳理结论自动落档；没有则独立运行。

## 目录

```
commands/    3 个入口（refactor / status / resume = 协调器状态机）
skills/      6 个认知技能（survey/align/diagnose/plan/transform/sync）
scripts/     refactor.py 确定性核心（探察/日志/批次git/验证）
```

设计文档见宿主仓库 `docs/SE/refactor-agent/`（P0-P8 全程留痕）。
