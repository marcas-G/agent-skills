#!/usr/bin/env python3
"""E-8 门禁（P5 契约）——宿主 Stop 事件挂载。

不变量：
  I1 fail-closed：崩溃/缺证据/损坏/无 run → 一律拦截（exit 2）
  I2 判定纯确定性：同矩阵同输出
  I3 永不由非 E-7 路径取证据
  I4 永不放行含 fake_tests 的 run
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVIDENCE = os.path.join(HERE, "evidence.py")


def block(msg):
    # Stop hook 语义：exit 2 + stderr → 宿主拦截并转达
    sys.stderr.write(f"[test-enforcer 门禁] 拦截：\n{msg}\n")
    sys.exit(2)


def allow(msg):
    sys.stderr.write(f"[test-enforcer 门禁] 放行：{msg}\n")
    sys.exit(0)


def gate(root):
    # 证据完整性（不变量 I3：只通过 E-7）
    r = subprocess.run([sys.executable, EVIDENCE, "--root", root, "--verify"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        block(f"证据完整性校验失败或无证据——拒绝放行。\n{r.stdout}\n"
              f"下一步：/test-enforcer 重跑验证")
    # 读矩阵
    import glob
    runs = sorted(glob.glob(os.path.join(root, ".test-enforcer", "runs", "*")))
    if not runs:
        block("无验证记录。下一步：/test-enforcer")
    matrix_path = os.path.join(runs[-1], "matrix.json")
    if not os.path.exists(matrix_path):
        block("缺少 matrix.json（验证流程未完成）。下一步：/test-enforcer")
    with open(matrix_path) as f:
        m = json.load(f)
    dims = m.get("dimensions", {})
    waivers = {w.get("dimension") for w in m.get("waivers", [])}

    fails = []
    # 覆盖率阈值判定（读 probe 档案中的阈值——若无则默认）
    th = {"coverage_line": 90, "coverage_branch": 90, "mutation_survive": 10}
    prof_path = os.path.join(root, ".test-enforcer", "profile.json")
    if os.path.exists(prof_path):
        try:
            with open(prof_path) as f:
                th.update(json.load(f).get("thresholds", {}))
        except Exception:
            pass

    v = dims.get("verify")
    if not v:
        fails.append("缺 verify 维度记录（未执行测试验证）")
    else:
        facts = v.get("facts", {})
        if facts.get("exec_status") != "pass":
            fails.append(f"测试执行未通过（exec={facts.get('exec_status')}）")
        if facts.get("fake_test_count"):
            fails.append(f"检出 {facts['fake_test_count']} 处假测试（R1-R3）——必须清除")
        cl, cb = facts.get("coverage_line"), facts.get("coverage_branch")
        if cl is None:
            fails.append("行覆盖率 unknown——unknown 不得放行（请检查覆盖工具）")
        elif cl < th["coverage_line"]:
            fails.append(f"行覆盖 {cl}% < {th['coverage_line']}%")
        if cb is None:
            # 分支 unknown：允许显式弃权，否则拦截
            if "coverage_branch" not in waivers:
                fails.append("分支覆盖率 unknown——需修复覆盖工具或显式弃权 "
                             "(--waive coverage_branch)")
        elif cb < th["coverage_branch"]:
            fails.append(f"分支覆盖 {cb}% < {th['coverage_branch']}%")

    mu = dims.get("mutation")
    if not mu:
        fails.append("缺 mutation 维度记录（未执行变异验证）")
    else:
        mf = mu.get("facts", {})
        sc = mf.get("score_survived_pct")
        if sc is None:
            fails.append("变异存活率无样本（样本 0 不估计）——扩大 batch 或显式弃权")
        elif sc > th["mutation_survive"]:
            fails.append(f"变异存活率 {sc}% > {th['mutation_survive']}%（测试杀不死变异体）")
        if mf.get("pending", 0) and "mutation_pending" not in waivers:
            fails.append(f"变异批次未完成（pending={mf['pending']}）——续跑或显式弃权")

    # 未记录的核心维度
    for d in ("verify", "mutation"):
        if d not in dims and d in waivers:
            pass  # 全弃权放行（C4 留痕）

    # 弃权只豁免显式点名维度的条目：精确匹配维度名
    waived = []
    for f in fails:
        if any(w in f or f.startswith(w) for w in waivers):
            waived.append(f)

    if fails:
        not_waived = [f for f in fails if f not in waived]
        if not_waived:
            block("\n".join(f"- {f}" for f in not_waived) +
                  "\n下一步：修复后 /test-enforcer，或显式弃权留痕")
    allow("全维度达标（或显式弃权留痕）。证据见 .test-enforcer/runs/")


def main():
    root = os.getcwd()
    # Stop hook 的 CWD 即项目根；stdin 的 session JSON 不用于判定（纯矩阵驱动）
    try:
        gate(root)
    except SystemExit:
        raise
    except Exception as e:
        # 不变量 I1：任何崩溃 → 拦截
        block(f"门禁内部错误（fail-closed）：{e}")


if __name__ == "__main__":
    main()
