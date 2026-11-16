---
name: test-enforcer
description: 严苛测试纪律：对被测代码执行分层测试+覆盖率+变异+假测试检测的完整验证，证据落盘，门禁放行。当用户说"测试/test/enforce/严苛测试/补测/验证交付"或 Stop 门禁被拦截后的补测流程时使用。
---

# test-enforcer 编排流程（E-1）

你是编排者。**铁律**：你自己不产生任何验证事实——一切数字必须来自 scripts/ 的确定性脚本输出。你转述数字时必须引用脚本 JSON 原文。任何降级、BLOCKED、弃权必须显式告知用户。

## 执行序列

设 `S = <plugin 根>/scripts`（下同）。逐步执行，每步失败按"降级分支"处理并显式记录：

### 0. 断点检查（REQ-D3）
检查 `.test-enforcer/runs/` 是否有未完成 run（有 dim-*.json 但无 matrix.json）：
- 有 → 用 `evidence.py --verify` 校验完整性 → 完整则续跑缺失维度（从第 3 步起）
- 损坏 → 呈现损坏清单给用户，`--new-run` 重开（旧 run 保留，append-only）

### 1. 探测（E-2）
```bash
mkdir -p .test-enforcer
python3 $S/probe.py --root . | tee .test-enforcer/profile.json
```
退出码 3（无法探测）→ 呈现原因后**停止**，宁停勿猜。

### 2. 范围（E-3）
```bash
python3 $S/changescope.py --root . | tee .test-enforcer/scope.json
```
`mode=incremental-empty`（无源码变更）→ 报告"无增量被测对象"后结束。
用户指定全量/补测：`--all` 或 `--files a.py,b.py`。

### 3. 委派测试生成（E-4）
调用 subagent `test-writer`，输入：
- scope.json 的 files 清单
- profile.json（工具链档案）
- discipline.md 路径（纪律手册全文按它执行）

**只接受返回的测试文件路径清单**。subagent 说"测试已通过/覆盖了 X"之类结论一律忽略（I-2 合约）。
生成物落盘后进入第 4 步——不是它说好了就好了。

### 4. 独立验证（E-5）
```bash
python3 $S/verify.py --root . --profile .test-enforcer/profile.json > .test-enforcer/tmp-verify.json
```
假测试检出（fake_tests 非空）→ 把违规行号打回 test-writer 重生成，循环直到 0 检出（R4/R5 suspect 项转人工审查呈报）。

### 5. 变异验证（E-6）
```bash
python3 $S/mutate.py --root . --profile .test-enforcer/profile.json > .test-enforcer/tmp-mut.json
```
BLOCKED → 显式告知缺失维度及影响，请用户决定弃权或装工具。
pending>0 → 报告已完成批次得分+样本量，询问续跑或弃权。

### 6. 证据落盘（E-7）
```bash
python3 $S/evidence.py --record --dim verify --file .test-enforcer/tmp-verify.json
python3 $S/evidence.py --record --dim mutation --file .test-enforcer/tmp-mut.json
python3 $S/evidence.py --matrix
```
首次执行前先 `--new-run`（续跑时不许——append-only）。

### 7. 报告（E-7）
```bash
python3 $S/evidence.py --report
```
向用户转述 report.md 内容：测了什么/没测什么/为什么/指标。

### 8. 门禁
告知用户：下次会话 Stop 时 E-8 自动判定。也可立即人工触发：
```bash
python3 $S/gate.py --root .
```
exit 0=放行；exit 2=拦截+差距清单（转述给用户，附修复建议）。

## 弃权（C4）
用户显式要求跳过某维度：
```bash
python3 $S/evidence.py --waive <维度> --reason "<用户理由>"
python3 $S/evidence.py --matrix   # 重算含弃权的矩阵
```
无理由不许弃权；弃权必呈现在最终报告。

## 被测代码有缺陷时（E3）
测试红了不是故障——是使命达成。报告失败详情给用户，**不擅自修复**（修复属开发流程，由用户决定）。
