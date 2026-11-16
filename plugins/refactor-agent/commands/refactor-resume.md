---
description: 中断后恢复重构现场：重放快照，续跑或重问待决策问题
---

恢复现场（E2 场景，LF-13）。

**脚本解析**：

```bash
RF="$(python3 -c "import os;print(os.environ.get('CLAUDE_PLUGIN_ROOT',''))")/scripts/refactor.py"
[ -f "$RF" ] || RF="$(ls -t ~/.claude/plugins/cache/*/refactor-agent/*/scripts/refactor.py 2>/dev/null | head -1)"
```

## 步骤

1. `python3 "$RF" resume` → 读输出：
   - `recoverable=false` → 无可恢复现场，结束。
   - `git_clean=false` → 提示先处理工作区（重投运判据），判断题：仍恢复/中止。
   - `pending_decision` 非空 → **直接重问该决策**（问题+选项来自快照，不重算上游梳理——DRV-2），用户选择后 `log decision` 续跑。
2. 按 `state.phase` 回到 `/refactor` 流程对应步骤续跑：probing→1；surveying→4；diagnosing→6；planning→7；executing→8（跳过已 verified/reverted 批次）；reporting→10。
3. 恢复失败（事件日志不可重放）→ 明确告知现场不可恢复，判断题：废弃旧轮重新开始 / 人工检查 .refactor/。
