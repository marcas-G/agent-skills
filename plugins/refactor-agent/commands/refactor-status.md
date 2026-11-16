---
description: 查看重构进度 + 会话内混乱信号检测（不发起重构）
---

查询当前状态与轻量信号检测（C2 场景）。

**脚本解析**：

```bash
RF="$(python3 -c "import os;print(os.environ.get('CLAUDE_PLUGIN_ROOT',''))")/scripts/refactor.py"
[ -f "$RF" ] || RF="$(ls -t ~/.claude/plugins/cache/*/refactor-agent/*/scripts/refactor.py 2>/dev/null | head -1)"
```

## 步骤

1. `python3 "$RF" state` → 呈现：轮次/阶段/批次进度（留存/回退/待执行）/待决策问题。
2. **仅当 phase ∈ idle/done**（无进行中轮次）：调用 Skill `refactor-diagnose` 的**信号模式**做轻量检测（只看增量上下文涉及的文件，不全库扫描）。
   - 有信号且同类信号拒绝计数 < 3 → 呈现建议：信号摘要 + 文件级证据 + 判断题「发起 /refactor / 忽略」。用户选忽略 → `log signal-rejected {"kind":"<四类之一>","evidence":"<文件>"}`。
   - 拒绝计数 ≥ 3 → 该类信号本静默期内不再提示（REQ-S2）。
3. phase 非 idle → 只报进度，不做信号检测，提示可用 `/refactor-resume` 继续。
