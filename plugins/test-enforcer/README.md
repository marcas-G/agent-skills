# test-enforcer

Claude Code plugin——把 AI agent 的测试纪律强制到"直接交付"水平。

## 为什么

Agent 写测试天然走最低阻力路径：只测 happy path、假断言、覆盖率好看但什么都验证不了。
提示词管不住（软约束），人工审查审不完（会累），CI 覆盖率骗得过（空断言也刷覆盖）。

本 plugin 的答案：**LLM 只许生成测试文件，一切"测试通过了"的结论只能来自确定性脚本独立执行，
完成宣告被门禁拦截——agent 没有任何自报通道。**

## 组成

| 组件 | 职责 |
|---|---|
| `/test-enforcer` skill | 编排完整流程：探测→增量范围→委派生成→独立验证→证据落盘→报告 |
| `agents/test-writer.md` | 专职测试生成体：按纪律手册产出，唯一合法输出=测试文件路径 |
| `skills/test-enforcer/discipline.md` | 纪律手册：三类用例强制 / 专项清单 S1-S6 / 反模式禁令 8 条 |
| `scripts/probe.py` | 语言/工具链探测（宁停勿猜，探测不到=blocked 显式标注） |
| `scripts/changescope.py` | 增量范围识别（git diff） |
| `scripts/verify.py` | 独立验证：执行+junit/coverage 解析+AST 假测试扫描（R1 无断言/R2 恒真/R3 吞异常/R4 断言 mock） |
| `scripts/mutate.py` | 变异测试：AST 变异算子+独立副本+分批+预算，score 绝不估计 |
| `scripts/evidence.py` | append-only 证据包：checksum 校验、断点续跑、弃权留痕 |
| `hooks/` Stop 门禁 | fail-closed：崩溃/缺证据/unknown → 一律拦截 |

## 硬验收线（默认，`.test-enforcer.toml` 可覆盖）

- 行+分支覆盖 ≥ 90%
- 变异存活率 ≤ 10%（杀假覆盖的核心指标）
- 假测试 0 容忍（AST 检出即 FAIL）
- unknown 维度不放行；部分结果不冒充全部；弃权必须留痕

## 安装

```bash
git clone https://github.com/marcas-G/test-enforcer.git
# 放入你的 plugin 目录（marketplace 方式或本地引用），重启 Claude Code
```

被测项目根放 `.test-enforcer.toml` 可覆盖阈值：

```toml
[thresholds]
coverage_line = 85
mutation_survive = 15
```

## 语言支持

Python（全链：pytest/coverage/AST 变异/AST 假测试扫描）、JS/TS（jest/vitest + regex 扫描降级）、
Go/Rust/Java 等：探测在册，未接入组合显式 BLOCKED——绝不静默跳过。

## 边界（诚实声明）

- 测试严 ≠ 代码对：本 plugin 验证"测试是否配得上代码"，不验证需求本身正确
- 变异测试对大仓库有耗时成本（分批+预算可控）
- LLM 博弈是无止境的军备竞赛：AST 规则抓下限，变异测试兜底（骗得过 AST 的测试通常杀不死变异体）
