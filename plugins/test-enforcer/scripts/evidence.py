#!/usr/bin/env python3
"""E-7 证据管理器（P5 契约）。

不变量：
  I1 append-only：已写入记录不可改写（重跑=新时间戳目录）
  I2 matrix.json 只能由 dim-*.json 派生
  I3 checksum 校验失败 → --verify 返回损坏清单
"""
import glob
import hashlib
import json
import os
import sys
import time

EVIDENCE_DIR = ".test-enforcer"

DIMS = ["verify", "mutation"]  # 记录型维度（probe/scope 是输入档案，不入矩阵判定核心）


def evidence_root(root):
    return os.path.join(root, EVIDENCE_DIR, "runs")


def latest_run(root):
    runs = sorted(glob.glob(os.path.join(evidence_root(root), "*")))
    return runs[-1] if runs else None


def new_run(root):
    ts = time.strftime("%Y%m%d-%H%M%S")
    d = os.path.join(evidence_root(root), ts)
    os.makedirs(d, exist_ok=True)
    return d


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def cmd_record(root, dim, file):
    run = latest_run(root) or new_run(root)
    with open(file) as f:
        payload = json.load(f)
    rec = {
        "dimension": dim,
        "status": payload.get("status") or payload.get("verdict_hint", "UNKNOWN"),
        "produced_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "tool": payload.get("tool") or payload.get("engine"),
        "payload": payload,
    }
    if dim == "verify":
        # 门禁关键事实提取（gate 直接消费）
        cov = payload.get("coverage", {})
        rec["facts"] = {
            "exec_status": payload.get("exec", {}).get("status"),
            "coverage_line": cov.get("line") if isinstance(cov.get("line"), (int, float)) else None,
            "coverage_branch": cov.get("branch") if isinstance(cov.get("branch"), (int, float)) else None,
            "fake_test_count": len(payload.get("fake_tests", [])),
        }
    if dim == "mutation":
        rec["facts"] = {
            "score_survived_pct": payload.get("score_survived_pct"),
            "mutants_total": payload.get("mutants_total"),
            "pending": payload.get("batches", {}).get("pending", 0),
        }
    out = os.path.join(run, f"dim-{dim}.json")
    if os.path.exists(out):
        # 不变量 I1：不改写——同名维度重记 → 拒绝，重跑开新 run
        print(json.dumps({"error": "append-only violation",
                          "detail": f"{out} exists; start a new run"}))
        sys.exit(4)
    with open(out, "w") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    with open(out + ".sha256", "w") as f:
        f.write(sha256_file(out) + "\n")
    print(json.dumps({"recorded": dim, "run": run, "status": rec["status"]}))


def cmd_matrix(root):
    run = latest_run(root)
    if not run:
        print(json.dumps({"error": "no runs"}))
        sys.exit(2)
    matrix = {"run": run, "dimensions": {}}
    for p in sorted(glob.glob(os.path.join(run, "dim-*.json"))):
        if p.endswith(".sha256"):
            continue
        with open(p) as f:
            rec = json.load(f)
        name = os.path.basename(p)[4:-5]
        matrix["dimensions"][name] = {
            "status": rec.get("status"), "facts": rec.get("facts", {}),
            "produced_at": rec.get("produced_at"), "tool": rec.get("tool"),
            "artifact": os.path.basename(p)}
    waivers = load_waivers(run)
    matrix["waivers"] = waivers
    with open(os.path.join(run, "matrix.json"), "w") as f:
        json.dump(matrix, f, ensure_ascii=False, indent=1)
    print(json.dumps(matrix, ensure_ascii=False))


def load_waivers(run):
    p = os.path.join(run, "waivers.json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return []


def cmd_waive(root, dim, reason):
    run = latest_run(root)
    if not run:
        print(json.dumps({"error": "no runs to waive against"}))
        sys.exit(2)
    w = load_waivers(run)
    w.append({"dimension": dim, "reason": reason,
              "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    with open(os.path.join(run, "waivers.json"), "w") as f:
        json.dump(w, f, ensure_ascii=False, indent=1)
    print(json.dumps({"waived": dim, "reason": reason}))


def cmd_verify(root):
    run = latest_run(root)
    if not run:
        print(json.dumps({"integrity": "FAIL", "reason": "no runs"}))
        sys.exit(1)
    corrupt = []
    for p in glob.glob(os.path.join(run, "dim-*.json")):
        sp = p + ".sha256"
        if not os.path.exists(sp):
            corrupt.append({"file": os.path.basename(p), "issue": "missing checksum"})
            continue
        with open(sp) as f:
            expect = f.read().strip()
        if sha256_file(p) != expect:
            corrupt.append({"file": os.path.basename(p), "issue": "checksum mismatch"})
    ok = not corrupt
    print(json.dumps({"integrity": "PASS" if ok else "FAIL", "run": run,
                      "corrupt": corrupt}))
    sys.exit(0 if ok else 1)


def cmd_report(root):
    run = latest_run(root)
    if not run:
        print(json.dumps({"error": "no runs"}))
        sys.exit(2)
    with open(os.path.join(run, "matrix.json")) as f:
        m = json.load(f)
    lines = ["# test-enforcer 证据报告", "", f"run: `{run}`", "",
             "| 维度 | 状态 | 关键事实 | 工具 |", "|---|---|---|---|"]
    for name, d in m.get("dimensions", {}).items():
        facts = "; ".join(f"{k}={v}" for k, v in (d.get("facts") or {}).items())
        lines.append(f"| {name} | {d.get('status')} | {facts} | {d.get('tool')} |")
    if m.get("waivers"):
        lines += ["", "## 弃权记录", ""]
        for w in m["waivers"]:
            lines.append(f"- **{w['dimension']}**：{w['reason']}（{w['at']}）")
    lines += ["", "## 没测什么/为什么", "",
              "- 见各维度 payload 中 unknown/blocked 的 reason 字段",
              "- mutation pending>0 表示分批未完，score 仅覆盖已完成批次"]
    p = os.path.join(run, "report.md")
    with open(p, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps({"report": p}))


def cmd_newrun(root):
    print(json.dumps({"run": new_run(root)}))


def main():
    root = os.getcwd()
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--root" and i + 1 < len(args):
            root = os.path.abspath(args[i + 1])
    if "--new-run" in args:
        cmd_newrun(root); return
    if "--record" in args:
        dim = args[args.index("--dim") + 1] if "--dim" in args else None
        file = args[args.index("--file") + 1] if "--file" in args else None
        if not (dim and file):
            print(json.dumps({"error": "--record needs --dim and --file"})); sys.exit(2)
        cmd_record(root, dim, file); return
    if "--matrix" in args:
        cmd_matrix(root); return
    if "--verify" in args and "--waive" not in args:
        cmd_verify(root); return
    if "--waive" in args:
        dim = args[args.index("--waive") + 1]
        reason = args[args.index("--reason") + 1] if "--reason" in args else "unspecified"
        cmd_waive(root, dim, reason); return
    if "--report" in args:
        cmd_report(root); return
    print(json.dumps({"error": "no command",
                      "usage": "--new-run | --record --dim D --file F | --matrix | "
                               "--verify | --waive D --reason R | --report"}))
    sys.exit(2)


if __name__ == "__main__":
    main()
