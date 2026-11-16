#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""refactor-agent 确定性核心（E-2 探察器 / E-7 git 层 / E-8 执行层 / E-9 记录器）。

设计依据 docs/SE/refactor-agent/P5-detail.md，不变量编号沿用之：
  INV-2.x 探察幂等与规则判定 | INV-7.x git 单点/零未授权落盘 | INV-8.x 验证只读
  INV-9.x 事件日志为真相、原子写、快照含待决策、可重放重建。

约定：目标项目根 = 当前工作目录；机器态在 .refactor/，人读产物在 docs/refactor/。
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path.cwd()
STATE_DIR = ROOT / ".refactor"
EVENTS_FILE = STATE_DIR / "events.jsonl"
STATE_FILE = STATE_DIR / "state.json"
LOCK_FILE = STATE_DIR / ".lock"
BASELINE_DIR = STATE_DIR / "baselines"
REPORT_DIR = ROOT / "docs" / "refactor"

# 事件类型白名单（state 派生只认这些；类型外的载荷不校验细目，由协调 skill 把关）
EVENT_TYPES = {
    "round-start", "phase", "probe", "survey-done", "decision-pending", "decision",
    "findings", "plan", "batch-committed", "batch-verified", "batch-reverted",
    "signal-rejected", "sync", "note", "round-end",
}
TERMINAL_PHASES = {"done"}

SKIP_DIRS = {".git", ".refactor", "node_modules", "dist", "build", "target",
             ".venv", "venv", "__pycache__", ".idea", ".vscode", ".claude"}
TEXT_EXTS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".h", ".cpp", ".hpp", ".cc",
    ".go", ".rs", ".rb", ".php", ".cs", ".swift", ".kt", ".scala", ".sh", ".bash",
    ".sql", ".html", ".css", ".scss", ".vue", ".svelte", ".md", ".json", ".yaml",
    ".yml", ".toml", ".ini", ".cfg", ".xml",
}

DEFAULT_THRESHOLD = 10000
SIGNAL_SILENCE_ROUNDS = 3  # REQ-S2：同类信号被拒后静默轮数


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def die(msg, code=1):
    print(json.dumps({"error": msg}, ensure_ascii=False), file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------- E-9 记录器

class Journal:
    """事件追加 + 派生快照。INV-9.4：state.json 永远可由 events.jsonl 重放重建。"""

    def __init__(self):
        STATE_DIR.mkdir(exist_ok=True)
        EVENTS_FILE.touch(exist_ok=True)

    def _events(self):
        events = []
        for line in EVENTS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # 尾部残行（崩溃时半写）按截断处理，重放自愈
        return events

    def _derive(self, events):
        st = {
            "version": 0, "round": None, "phase": "idle", "scope": None,
            "decisions": [], "pending_decision": None, "batches": [],
            "rejected_signals": {}, "blindspots": [], "warnings": [],
            "last_probe": None, "updated_at": None, "history": [],
        }
        for ev in events:
            st["version"] = ev["seq"]
            st["updated_at"] = ev["ts"]
            t, p = ev["type"], ev.get("payload", {})
            if t == "round-start":
                st["round"] = p["round"]
                st["phase"] = "probing"
                st["scope"] = p.get("scope")
                st["batches"], st["decisions"] = [], []
            elif t == "phase":
                st["phase"] = p["name"]
            elif t == "probe":
                st["last_probe"] = p
            elif t == "survey-done":
                st["blindspots"] = p.get("blindspots", [])
            elif t == "decision-pending":
                # INV-9.2：决策等待中 ⟹ 快照含该决策问题+选项
                if "question" not in p or "options" not in p:
                    st["warnings"].append(
                        f"seq={ev['seq']} decision-pending 缺 question/options，已忽略")
                else:
                    st["pending_decision"] = p
            elif t == "decision":
                st["pending_decision"] = None
                st["decisions"].append(p)
            elif t == "plan":
                st["batches"] = [
                    {"id": b["id"], "files": b.get("files", []),
                     "risk": b.get("risk", "low"),
                     "exception_expected": b.get("exception_expected", False),
                     "status": "planned"}
                    for b in p.get("batches", [])
                ]
            elif t == "batch-committed":
                self._batch(st, p["batch"])["status"] = "committed"
            elif t == "batch-verified":
                self._batch(st, p["batch"])["status"] = (
                    "verified" if p.get("pass") else "reverted-pending")
            elif t == "batch-reverted":
                self._batch(st, p["batch"])["status"] = "reverted"
            elif t == "signal-rejected":
                k = p.get("kind", "?")
                st["rejected_signals"][k] = st["rejected_signals"].get(k, 0) + 1
            elif t == "round-end":
                st["phase"] = "done"
                st["history"].append(
                    {"round": st["round"], "status": p.get("status", "aborted")})
        return st

    @staticmethod
    def _batch(st, bid):
        for b in st["batches"]:
            if b["id"] == bid:
                return b
        raise ValueError(f"未知批次 {bid}（未在 plan 事件中登记）")

    def read_state(self):
        st = self._derive(self._events())
        return st

    def append(self, etype, payload):
        if etype not in EVENT_TYPES:
            die(f"未知事件类型 {etype}")
        # 写入前校验（防止坏事件污染日志，破坏 INV-9.4 可重放性）
        if etype == "decision-pending" and (
                "question" not in payload or "options" not in payload):
            die("decision-pending 缺 question/options（INV-9.2）")
        events = self._events()
        seq = (events[-1]["seq"] + 1) if events else 1
        ev = {"seq": seq, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "round": self.read_state().get("round"), "type": etype,
              "payload": payload}
        # 先追加事件（真相源），再原子刷新派生快照
        with open(EVENTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        self._rewrite_state()
        return ev

    def _rewrite_state(self):
        st = self._derive(self._events())
        # INV-9.3：原子写——临时文件 + rename，任一时刻文件可解析或不存在
        fd, tmp = tempfile.mkstemp(dir=STATE_DIR, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(st, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, STATE_FILE)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return st


def with_lock(fn):
    """串行化写操作；并发会话的写请求直接拒绝（P5 E-9 Q4）。"""
    import fcntl
    def wrapper(*a, **k):
        STATE_DIR.mkdir(exist_ok=True)
        with open(LOCK_FILE, "w") as lf:
            try:
                fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                die("另一进程持有 .refactor 写锁（已有会话在运行）")
            return fn(*a, **k)
    return wrapper


def get_journal():
    return Journal()


# ---------------------------------------------------------------- E-2 探察器

def cmd_probe(args):
    profile = {"root": str(ROOT)}
    langs, nfiles, nlines = {}, 0, 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if Path(dirpath).relative_to(ROOT).parts and \
                Path(dirpath).relative_to(ROOT).parts[0] in {"docs"}:
            continue  # 文档不计入代码规模
        for name in filenames:
            p = Path(dirpath) / name
            ext = p.suffix.lower()
            if ext not in TEXT_EXTS or p.stat().st_size > 1_000_000:
                continue
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    lines = sum(1 for _ in f)
            except OSError:
                continue
            nfiles += 1
            nlines += lines
            langs[ext] = langs.get(ext, 0) + lines
    profile["languages"] = dict(sorted(langs.items(), key=lambda x: -x[1])[:8])
    profile["files"] = nfiles
    profile["lines"] = nlines

    # 测试命令探测：逐项检查标记文件，不预设框架（INV-2.1 只陈述事实）
    def has(name):
        return (ROOT / name).exists()
    pkg = {}
    if has("package.json"):
        try:
            pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pkg = {}
    test_cmd = None
    py = "python" if shutil.which("python") else (
        "python3" if shutil.which("python3") else None)
    pytest_cmd = f"{py} -m pytest" if py else "pytest"
    if pkg.get("scripts", {}).get("test"):
        test_cmd = "npm test"
    elif has("Makefile") and "test:" in (ROOT / "Makefile").read_text(errors="ignore"):
        test_cmd = "make test"
    elif has("pytest.ini") or has("tox.ini"):
        test_cmd = pytest_cmd
    elif has("pyproject.toml") and "[tool.pytest" in (ROOT / "pyproject.toml").read_text(errors="ignore"):
        test_cmd = pytest_cmd
    elif has("go.mod"):
        test_cmd = "go test ./..."
    elif has("Cargo.toml"):
        test_cmd = "cargo test"
    elif has("pom.xml"):
        test_cmd = "mvn test"
    elif has("build.gradle") or has("build.gradle.kts"):
        test_cmd = "gradle test"
    profile["test_cmd"] = test_cmd

    profile["se_docs"] = (ROOT / "docs" / "SE").is_dir()

    git_ok, git_dirty = False, False
    r = run_git(["rev-parse", "--is-inside-work-tree"])
    if r and r.returncode == 0 and r.stdout.strip() == "true":
        s = run_git(["status", "--porcelain"])
        git_ok = s is not None and s.returncode == 0
        git_dirty = bool(s and s.stdout.strip())
    profile["git"] = {"available": git_ok, "dirty": git_dirty}

    # 模式判定：固定规则表取最严格（INV-2.1 零裁量；INV-2.2 幂等）
    threshold = int(os.environ.get("REFACTOR_SIZE_THRESHOLD", args.threshold))
    warnings = []
    if nlines > threshold:
        mode = "refused-fullrefactor"
    elif not git_ok:
        mode = "no-git"
    else:
        if not test_cmd:
            mode = "degraded"
            warnings.append("未探测到测试命令：降级模式（安全类重构+人工确认）")
        else:
            mode = "normal"
        if git_dirty:
            warnings.append("git 工作区不干净：建议先提交或暂存，批次提交将混入未预期变更")
    out({"profile": profile, "mode": mode, "threshold": threshold,
         "warnings": warnings,
         "advice": "分模块重构" if mode == "refused-fullrefactor" else ""})


def run_git(gargs, check=False):
    try:
        r = subprocess.run(["git"] + gargs, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if check and r.returncode != 0:
        return None
    return r


# ------------------------------------------------------------ E-9 轮次管理

@with_lock
def cmd_start(args):
    j = get_journal()
    st = j.read_state()
    if st["phase"] not in ["idle"] + list(TERMINAL_PHASES):
        die(f"已有进行中轮次 {st['round']}（phase={st['phase']}）。"
            f"请先 /refactor-resume 或结束本轮")
    round_id = args.round_id or time.strftime("r%Y%m%d-%H%M%S")
    ev = j.append("round-start", {"round": round_id, "scope": args.scope})
    out({"round": round_id, "seq": ev["seq"],
         "dir": str(REPORT_DIR / round_id), "state": j.read_state()})


@with_lock
def cmd_log(args):
    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError as e:
        die(f"payload 不是合法 JSON：{e}")
    j = get_journal()
    if args.type == "round-end":
        st = j.read_state()
        payload.setdefault("status", "aborted")
        payload.setdefault("summary", "")
    ev = j.append(args.type, payload)
    out({"ok": True, "seq": ev["seq"], "version": j.read_state()["version"]})


def cmd_state(_args):
    st = get_journal().read_state()
    if not STATE_FILE.exists():
        st = get_journal()._rewrite_state()
    out(st)


def cmd_resume(_args):
    j = get_journal()
    # state 损坏 → 从事件重放重建（INV-9.4 恢复路径）
    try:
        st = j.read_state()
    except (ValueError, KeyError) as e:
        die(f"事件日志无法重放（{e}）：现场不可恢复，建议重新梳理")
    st = j._rewrite_state()
    r = run_git(["status", "--porcelain"])
    git_clean = bool(r and r.returncode == 0 and not r.stdout.strip())
    out({"recoverable": st["phase"] not in (["idle"] + list(TERMINAL_PHASES)),
         "state": st, "git_clean": git_clean,
         "pending_decision": st["pending_decision"],
         "note": "重投运判据：state 可解析 + git 干净" if git_clean
                 else "git 不干净：先处理工作区再恢复"})


def cmd_report(_args):
    j = get_journal()
    st = j.read_state()
    if not st["round"]:
        die("没有可报告的轮次")
    rd = REPORT_DIR / st["round"]
    rd.mkdir(parents=True, exist_ok=True)
    committed = [b for b in st["batches"] if b["status"] in ("committed", "verified")]
    reverted = [b for b in st["batches"] if b["status"] == "reverted"]
    lines = [
        f"# 重构报告：{st['round']}", "",
        f"- 范围：{st['scope'] or '全库'}",
        f"- 状态：{st['phase']}",
        f"- 批次：{len(committed)} 留存 / {len(reverted)} 回退", "",
        "## 改了什么", "",
    ]
    for b in committed:
        lines.append(f"- 批次 {b['id']}（风险 {b['risk']}"
                     f"{'，含已审批例外' if b['exception_expected'] else ''}）：{', '.join(b['files'])}")
    lines += ["", "## 为什么改", ""]
    for d in st["decisions"]:
        lines.append(f"- 决策{d.get('id', '?')}「{d.get('question', '')}」→ {d.get('choice', '')}（{d.get('reason', '')}）")
    lines += ["", "## 遗留什么", ""]
    for b in reverted:
        lines.append(f"- 批次 {b['id']} 被回退（原因见 journal）")
    for z in st["blindspots"]:
        lines.append(f"- 盲区：{z}")
    if st["pending_decision"]:
        lines.append(f"- 未决决策：{st['pending_decision'].get('question', '?')}")
    lines += ["", "## 信号拒绝记录", ""]
    lines += [f"- {k}：{v} 次" for k, v in st["rejected_signals"].items()] or ["- 无"]
    (rd / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out({"report": str(rd / "report.md"), "note": "骨架已生成，叙述由协调器补全"})


# ------------------------------------------------------------- E-7 批次 git 层

def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@with_lock
def cmd_baseline(args):
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for f in args.files:
        p = ROOT / f
        if not p.exists():
            die(f"基线文件不存在：{f}")
        hashes[str(f)] = _sha256(p)
    bf = BASELINE_DIR / f"batch-{args.batch}.json"
    bf.write_text(json.dumps(hashes, ensure_ascii=False, indent=2), encoding="utf-8")
    out({"batch": args.batch, "files": len(hashes), "baseline": str(bf)})


def cmd_guard(args):
    """ADR-9：批次文件相对 git HEAD 无未提交变更才放行。

    原设计（计划时基线 hash 比对）在同轮多批次触碰重叠文件时必然假冲突
    ——前序批次的合法修改会让后序批次的基线过期。HEAD 对比永远新鲜：
    我们自己的批次已提交故不报警，外部未提交改动立即现形。
    """
    r = run_git(["status", "--porcelain", "--"] + args.files)
    if r is None or r.returncode != 0:
        die("git status 失败，无法执行哨兵检查")
    dirty = [line[3:].strip() for line in r.stdout.splitlines() if line.strip()]
    out({"batch": args.batch, "pass": not dirty, "dirty": dirty,
         "note": "" if not dirty else "冲突：文件存在未提交的外部改动，停止该文件（P3-E6）"})


@with_lock
def cmd_commit(args):
    st = get_journal().read_state()
    if args.batch not in {b["id"] for b in st["batches"]}:
        die(f"批次 {args.batch} 不在本轮计划（先经规划器+决策③）")
    files = args.files
    add = run_git(["add", "--"] + files)
    if not add or add.returncode != 0:
        die("git add 失败（文件路径有误？）")
    c = run_git(["commit", "-m", f"refactor(batch-{args.batch}): {args.message}"])
    if not c or c.returncode != 0:
        die(f"git commit 失败：{(c.stderr if c else '').strip()[:300]}——工作区保留，暂停人工处理")
    sha = run_git(["rev-parse", "HEAD"]).stdout.strip()
    j = get_journal()
    j.append("batch-committed", {"batch": args.batch, "files": files, "sha": sha})
    out({"batch": args.batch, "sha": sha,
         "note": "通知验证器（verify）；失败将按 INV-7 单点回退"})


@with_lock
def cmd_revert(args):
    r = run_git(["log", "--fixed-strings",
                 f"--grep=refactor(batch-{args.batch}):",
                 "-1", "--format=%H"])
    if not r or not r.stdout.strip():
        die(f"找不到批次 {args.batch} 的提交")
    sha = r.stdout.strip()
    c = run_git(["revert", "--no-edit", sha])
    if not c or c.returncode != 0:
        die("git revert 冲突：人工解决后继续（批次状态未变更）")
    get_journal().append("batch-reverted",
                         {"batch": args.batch, "reverted_sha": sha,
                          "reason": args.reason or "验证失败/人工指令"})
    out({"batch": args.batch, "reverted": sha})


# ------------------------------------------------------------- E-8 验证执行

def cmd_verify(args):
    if not args.cmd:
        die("缺测试命令（来自探察器画像或降级模式跳过）")
    try:
        r = subprocess.run(args.cmd, shell=True, capture_output=True,
                           text=True, timeout=args.timeout)
        passed, timed_out = r.returncode == 0, False
        tail = (r.stdout + r.stderr).strip().splitlines()[-20:]
        exit_code = r.returncode
    except subprocess.TimeoutExpired as e:
        passed, timed_out, exit_code = False, True, None
        tail = ((e.stdout or b"").decode(errors="ignore") if isinstance(e.stdout, bytes)
                else (e.stdout or "")).splitlines()[-20:]
        tail += ["[refactor] 测试超时，按失败处理（疑似环境问题）"]
    out({"pass": passed, "timed_out": timed_out, "exit_code": exit_code,
         "summary": tail,
         "note": "" if passed else "失败→触发回退（batch revert）；独立裁决，不复用改造器结论"})


@with_lock
def cmd_mark_verified(args):
    get_journal().append("batch-verified", {"batch": args.batch,
                                            "pass": args.passed,
                                            "summary": args.summary or ""})


def main():
    ap = argparse.ArgumentParser(prog="refactor.py",
                                 description="refactor-agent 确定性核心")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("probe", help="项目画像+模式判定（E-2）")
    p.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    p.set_defaults(fn=cmd_probe)

    p = sub.add_parser("start", help="开轮（E-9）")
    p.add_argument("--scope", default=None)
    p.add_argument("--round-id", default=None)
    p.set_defaults(fn=cmd_start)

    p = sub.add_parser("log", help="追加事件（E-9）")
    p.add_argument("type", choices=sorted(EVENT_TYPES))
    p.add_argument("payload", help="JSON")
    p.set_defaults(fn=cmd_log)

    p = sub.add_parser("state", help="读快照（E-9）")
    p.set_defaults(fn=cmd_state)

    p = sub.add_parser("resume", help="现场恢复（E-9）")
    p.set_defaults(fn=cmd_resume)

    p = sub.add_parser("report", help="报告骨架（E-9）")
    p.set_defaults(fn=cmd_report)

    p = sub.add_parser("baseline", help="批次基线采集（E-7 哨兵）")
    p.add_argument("batch")
    p.add_argument("files", nargs="+")
    p.set_defaults(fn=cmd_baseline)

    p = sub.add_parser("guard", help="冲突哨兵：批次文件 vs git HEAD（E-7，ADR-9）")
    p.add_argument("batch")
    p.add_argument("files", nargs="+")
    p.set_defaults(fn=cmd_guard)

    p = sub.add_parser("commit", help="批次提交（E-7 git 单点）")
    p.add_argument("batch")
    p.add_argument("message")
    p.add_argument("files", nargs="+")
    p.set_defaults(fn=cmd_commit)

    p = sub.add_parser("revert", help="批次回退（E-7 git 单点）")
    p.add_argument("batch")
    p.add_argument("--reason", default=None)
    p.set_defaults(fn=cmd_revert)

    p = sub.add_parser("verify", help="执行测试（E-8）")
    p.add_argument("--cmd", default=None)
    p.add_argument("--timeout", type=int, default=600)
    p.set_defaults(fn=cmd_verify)

    p = sub.add_parser("mark-verified", help="登记验证结果（E-8→E-9）")
    p.add_argument("batch")
    p.add_argument("--passed", action="store_true")
    p.add_argument("--summary", default="")
    p.set_defaults(fn=cmd_mark_verified)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
