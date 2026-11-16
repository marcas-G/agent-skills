#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fractal —— 递归式需求驱动系统工程的状态机内核.

唯一真相：项目侧 docs/SE/fractal-state.json
分工：skills 管方法论（人读），本脚本管状态与纪律（机读）。
fail-open：hook 入口任何异常都静默放行，绝不阻塞用户项目；
           只有「明确判定违规」才拦截。
"""
import argparse
import datetime
import json
import os
import re
import sys

PHASES = ["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]
PHASE_DOCS = {
    "P0": "P0-problem.md",
    "P1": "P1-stakeholders.md",
    "P2": "P2-requirements.md",
    "P3": "P3-logical.md",
    "P4": "P4-architecture.md",
    "P5": "P5-detail.md",
    "P6": "P6-implementation.md",
    "P7": "P7-verification.md",
    "P8": "P8-validation.md",
}
DOC_TO_PHASE = {v: k for k, v in PHASE_DOCS.items()}
SE_DIR = "docs/SE"
STATE_FILE = os.path.join(SE_DIR, "fractal-state.json")

RULES = {1: "阶段闸门", 2: "递归闸门", 3: "孤儿目录"}

PHASE_DISCIPLINE = {
    "P0": "Rule 1 No Leap 不跳步：Problem→Requirement→Logical→Architecture→Trade-off→Design，禁止从「需要X」直跳「方案Y」。",
    "P1": "Rule 2 No Orphan 无孤儿：每条需求必须能回引真实场景/干系人关切，追不到就删。",
    "P2": "Rule 2 No Orphan 无孤儿：写不出 Criterion 的 REQ 不是需求，是愿望。",
    "P3": "Rule 3 Single Ownership 唯一主责：每项逻辑责任在 P4 将有且只有一个主要承担者。",
    "P4": "Rule 3 Single Ownership 唯一主责：LF×E 每行一个主承担者；关键状态有唯一权威拥有者。",
    "P5": "Rule 4 No Hidden Design 无隐藏设计：不变量、故障语义、恢复判据都要显式成文。",
    "P6": "Rule 4 No Hidden Design 无隐藏设计：写代码时做的设计决策必须回写 ADR，藏在代码里的不算存在。",
    "P7": "Rule 5 Evidence over Claim 证据高于宣称：REQ→判据→证据→PASS/FAIL，「应该没问题」不是证据。",
    "P8": "Rule 5 Evidence over Claim 证据高于宣称：引 P0 原文核对，不许凭记忆粉饰。",
}

OVERVIEW_TEMPLATE = """# SE 文档索引（fractal）

> 同一套问题结构，在任何层级通用。One question structure, every level.

## 使用规则

1. **新开发必须挂 REQ**——不在 P2 需求台账上的工作不做。
2. **差距驱动待办**——工作来源只有 /fractal-gap 的差距清单；新差距先回 P2 登记 REQ。

## 五条纪律（冲突裁决：进度 vs 纪律 → 纪律赢）

1. **No Leap 不跳步**：Problem → Requirement → Logical → Architecture → Trade-off → Design，禁止从「需要 X」直跳「方案 Y」。
2. **No Orphan 无孤儿**：任何 REQ/逻辑功能/元素/接口/验证用例必须能回答「我为什么存在」，追不到就删。
3. **Single Ownership 唯一主责**：任何逻辑责任、关键状态、共享资源，有且只有一个主要承担者。
4. **No Hidden Design 无隐藏设计**：实现中的设计决策必须升格为显式 ADR 回写文档，藏在实现里的决策不算存在。
5. **Evidence over Claim 证据高于宣称**：完成判定必须给证据链 REQ→判据→证据→PASS/FAIL。

## SoI 索引（fractal.py 维护）

| SoI | 父级 | 当前阶段 |
|---|---|---|
"""


class FractalError(Exception):
    pass


def die(msg):
    raise FractalError(msg)


def today():
    return datetime.date.today().isoformat()


def load_state(root):
    p = os.path.join(root, STATE_FILE)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError) as e:
        raise FractalError(f"fractal-state.json 无法解析（{e}）。修复：python3 scripts/fractal.py reconcile")
    if not isinstance(state, dict) or not isinstance(state.get("sois"), dict):
        raise FractalError("fractal-state.json 缺 sois 字典。修复：python3 scripts/fractal.py reconcile")
    return state


def save_state(root, state):
    p = os.path.join(root, STATE_FILE)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def new_state():
    return {"version": 1, "plugin": "fractal", "focus": None, "sois": {}}


def phase_status(soi, ph):
    return ((soi.get("phases") or {}).get(ph) or {}).get("status")


def passed_or_waived(soi, ph):
    return phase_status(soi, ph) in ("passed", "waived")


def current_phase(soi):
    for ph in PHASES:
        if not passed_or_waived(soi, ph):
            return ph
    return None


def ensure_overview(root, state):
    path = os.path.join(root, SE_DIR, "00-overview.md")
    if not os.path.isfile(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(OVERVIEW_TEMPLATE)
    rows = ["| SoI | 父级 | 当前阶段 |", "|---|---|---|"]
    for name in sorted(state["sois"]):
        soi = state["sois"][name]
        cur = current_phase(soi) or "完成"
        rows.append(f"| {name} | {soi.get('parent') or 'top'} | {cur} |")
    idx = "## SoI 索引（fractal.py 维护）\n\n" + "\n".join(rows) + "\n"
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    text = re.sub(r"## SoI 索引[\s\S]*$", idx, text)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def cmd_start(args):
    root = os.getcwd()
    state = load_state(root) or new_state()
    parent = args.parent
    if parent:
        if parent not in state["sois"]:
            die(f"父级 SoI 未登记：{parent}（先 /fractal-start {parent}）")
        rec = state["sois"][parent].get("recursion") or {}
        if args.element not in rec:
            die(f"{parent} 的递归判断中没有元素 {args.element}（先 register-child）")
        if rec[args.element].get("verdict") != "promote":
            die(f"元素 {args.element} 判定不是 promote，不能建子 SoI")
    name = args.name or (f"{parent}--{args.element}" if parent else None)
    if not name:
        die("缺少 SoI 名称：fractal.py start <name>")
    if (not re.fullmatch(r"[^\s/]+", name) or name.startswith(".")
            or name in (os.path.basename(STATE_FILE), "00-overview.md")):
        die("SoI 名称不合法（不能含空白或 /、不能以 . 开头、不能占用 fractal-state.json / 00-overview.md）")
    if name in state["sois"]:
        die(f"SoI 已存在：{name}")
    state["sois"][name] = {
        "parent": parent,
        "element": args.element if parent else None,
        "created": today(),
        "phases": {},
        "recursion": {},
    }
    os.makedirs(os.path.join(root, SE_DIR, name), exist_ok=True)
    if parent:
        state["sois"][parent]["recursion"][args.element]["child"] = name
    state["focus"] = name
    save_state(root, state)
    ensure_overview(root, state)
    print(f"SoI 已建立：{name}（父级：{parent or 'top'}）→ 从 P0 开始，用 /fractal-next 推进")
    return 0


def cmd_status(args):
    root = os.getcwd()
    state = load_state(root)
    if not state or not state.get("sois"):
        die("尚未初始化：先 /fractal-start <name>（或 fractal.py start <name>）")
    name = args.soi or state.get("focus")
    if not name:
        die("state 无 focus：请用 fractal.py status <soi-name>")
    soi = state["sois"].get(name)
    if soi is None:
        die(f"SoI 未登记：{name}")
    print(f"SoI：{name}（父级：{soi.get('parent') or 'top'}）")
    cur = current_phase(soi)
    print(f"当前阶段：{cur or '全部完成'}")
    if cur:
        i = PHASES.index(cur)
        if i > 0:
            prev = PHASES[i - 1]
            print(f"上一阶段 {prev}：{phase_status(soi, prev) or '未开始'}")
        print(f"下一步：完成 {cur}（Skill fractal-{cur.lower()}-*），过闸后 /fractal-next")
        if PHASES.index(cur) >= PHASES.index("P5") and not (soi.get("recursion") or {}):
            print("注意：递归判断未登记——P4 后必须先执行 fractal-recursion-check + register-child")
    else:
        print("下一步：/fractal-gap 看差距，或 /fractal-tree 看全树")
    return 0


def _require_order(state, name, ph):
    soi = state["sois"].get(name)
    if soi is None:
        die(f"SoI 未登记：{name}")
    i = PHASES.index(ph)
    if i > 0 and not passed_or_waived(soi, PHASES[i - 1]):
        prev = PHASES[i - 1]
        die(
            f"{name} 的 {prev} 状态为「{phase_status(soi, prev) or '未开始'}」，"
            f"不能对 {ph} 操作（宁停勿跳）。确要跳过请显式弃权：waive {name} {prev} --reason \"...\""
        )


def cmd_gate_pass(args):
    root = os.getcwd()
    state = load_state(root)
    if not state:
        die("尚未初始化：先 start")
    if args.phase not in PHASES:
        die(f"非法阶段：{args.phase}（P0-P8）")
    _require_order(state, args.soi, args.phase)
    soi = state["sois"][args.soi]
    if PHASES.index(args.phase) >= PHASES.index("P5") and not (soi.get("recursion") or {}):
        die(f"{args.soi} 未登记递归判断，不能过 P5 闸（先 register-child）")
    soi.setdefault("phases", {})[args.phase] = {
        "status": "passed", "doc": PHASE_DOCS[args.phase], "date": today(),
    }
    state["focus"] = args.soi
    save_state(root, state)
    ensure_overview(root, state)
    nxt = PHASES[PHASES.index(args.phase) + 1] if args.phase != "P8" else None
    print(f"{args.soi} {args.phase} 过闸已登记。" + (f"下一阶段 {nxt}。" if nxt else " 全部阶段完成。"))
    return 0


def cmd_waive(args):
    root = os.getcwd()
    state = load_state(root)
    if not state:
        die("尚未初始化：先 start")
    if args.phase not in PHASES:
        die(f"非法阶段：{args.phase}（P0-P8）")
    if not args.reason or not args.reason.strip():
        die("弃权必须给 --reason（记录在案，树上显示 ⚠）")
    _require_order(state, args.soi, args.phase)
    state["sois"][args.soi].setdefault("phases", {})[args.phase] = {
        "status": "waived", "doc": PHASE_DOCS[args.phase], "date": today(),
        "reason": args.reason.strip(),
    }
    state["focus"] = args.soi
    save_state(root, state)
    ensure_overview(root, state)
    print(f"{args.soi} {args.phase} 已弃权（⚠）：{args.reason.strip()}")
    return 0


def cmd_register_child(args):
    root = os.getcwd()
    state = load_state(root)
    if not state:
        die("尚未初始化：先 start")
    soi = state["sois"].get(args.soi)
    if soi is None:
        die(f"SoI 未登记：{args.soi}")
    if args.verdict not in ("leaf", "promote"):
        die("--verdict 只能是 leaf 或 promote")
    if not passed_or_waived(soi, "P4"):
        die("P4 未过闸/弃权，不能登记递归判断（先完成 P4）")
    entry = {"verdict": args.verdict, "note": args.note or "", "child": None}
    soi.setdefault("recursion", {})[args.element] = entry
    state["focus"] = args.soi
    save_state(root, state)
    if args.verdict == "promote":
        print(f"{args.soi} 的 {args.element} → 提升为新 SoI（建议名 {args.soi}--{args.element}）。"
              f"执行：/fractal-start --parent {args.soi} --element {args.element}")
    else:
        print(f"{args.soi} 的 {args.element} → 叶子，直接进 P5 详细设计。")
    return 0


def render_tree(state, with_stuck=True):
    sois = state["sois"]
    lines = []

    def mark(soi, ph):
        st = phase_status(soi, ph)
        if st == "passed":
            return f"{ph}✓"
        if st == "waived":
            return f"{ph}⚠"
        return f"{ph}·"

    def walk(name, prefix, is_last):
        soi = sois[name]
        badges = " ".join(mark(soi, ph) for ph in PHASES)
        branch = "└── " if is_last else "├── "
        lines.append((prefix + branch + name if prefix else name) + f"  [{badges}]")
        kids = sorted(n for n, s in sois.items() if s.get("parent") == name)
        for i, k in enumerate(kids):
            walk(k, prefix + ("    " if is_last else "│   "), i == len(kids) - 1)

    roots = sorted(n for n, s in sois.items() if not s.get("parent"))
    for i, r in enumerate(roots):
        walk(r, "", i == len(roots) - 1)

    if with_stuck:
        lines.append("")
        lines.append("卡点（下一步动作）：")
        for name in sorted(sois):
            cur = current_phase(sois[name])
            lines.append(f"  {name} → " + (f"/fractal-next 进 {cur}" if cur else "全部阶段完成"))
    return lines


def cmd_tree(args):
    root = os.getcwd()
    state = load_state(root)
    if not state or not state.get("sois"):
        die("尚未初始化：先 /fractal-start")
    print("\n".join(render_tree(state)))
    print("\n图例：✓ 过闸  ⚠ 弃权（有记录）  · 未开始")
    return 0


def validate_write(root, relpath):
    """返回 None=放行，或 (rule_no, reason) 拒绝。只管状态转移，不管内容。"""
    rel = os.path.normpath(relpath).replace(os.sep, "/")
    if not rel.startswith(SE_DIR + "/"):
        return None
    state = load_state(root)
    if not state:
        return None
    parts = rel.split("/")
    fname = parts[-1]
    if len(parts) < 4:
        return None  # docs/SE/ 直下的文件（state/overview/其他）放行
    soi_dir = parts[2]
    ph = DOC_TO_PHASE.get(fname)
    if ph is None:
        return None  # 非 P 文档（笔记等）放行
    soi = state["sois"].get(soi_dir)
    if soi is None:
        return (3, f"目录 {soi_dir}/ 未在 fractal-state.json 登记。"
                  f"先 /fractal-start 建 SoI（子 SoI 需父级先 register-child --verdict promote），再写阶段文档。")
    i = PHASES.index(ph)
    if i > 0 and not passed_or_waived(soi, PHASES[i - 1]):
        prev = PHASES[i - 1]
        st = phase_status(soi, prev) or "未开始"
        return (1, f"{soi_dir} 的 {prev} 状态为「{st}」，不能写 {fname}（宁停勿跳）。"
                  f"解除：/fractal-next 过 {prev} 闸，或显式弃权 "
                  f"python3 scripts/fractal.py waive {soi_dir} {prev} --reason \"...\"")
    if i >= PHASES.index("P5") and not (soi.get("recursion") or {}):
        return (2, f"{soi_dir} 未登记递归判断（P4 后必须逐元素判定叶子/提升）。"
                  f"解除：Skill fractal-recursion-check + register-child")
    return None


def cmd_check_write(args):
    try:
        rel = os.path.relpath(os.path.abspath(args.path), os.getcwd())
    except Exception:
        print("ALLOW")
        return 0
    if rel.split(os.sep)[0] == "..":
        print("ALLOW")
        return 0
    v = validate_write(os.getcwd(), rel)
    if v is None:
        print("ALLOW")
        return 0
    rule, reason = v
    print(f"BLOCKED [规则{rule}·{RULES[rule]}] {reason}")
    return 2


def cmd_hook_pretoolwrite(args):
    """PreToolUse 入口：读 stdin JSON，违规输出 decision:block（exit 0），其余一律放行。"""
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path") or ""
    if not path:
        return 0
    try:
        rel = os.path.relpath(os.path.abspath(path), os.getcwd())
    except Exception:
        return 0
    if rel.split(os.sep)[0] == "..":
        return 0
    v = validate_write(os.getcwd(), rel)
    if v:
        rule, reason = v
        print(json.dumps({
            "decision": "block",
            "hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny"},
            "reason": f"[fractal 规则{rule}·{RULES[rule]}] {reason}",
        }, ensure_ascii=False))
    return 0


def infer_phase_status(path):
    """Exit Gate checklist：有未勾=in-progress，全勾=passed，无 checklist=unknown。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return "unknown"
    m = re.search(r"## Exit Gate[\s\S]*$", text)
    if not m:
        return "unknown"
    section = m.group(0)
    if re.search(r"- \[ \]", section):
        return "in-progress"
    if re.search(r"- \[x\]", section, re.I):
        return "passed"
    return "unknown"


def infer_recursion(path):
    rec = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return rec
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2 or not cells[0] or cells[0].startswith("-") or cells[0] == "元素":
            continue
        joined = "".join(cells)
        verdict = "leaf" if "叶子" in joined else ("promote" if "提升" in joined else None)
        if verdict:
            note = cells[2] if len(cells) > 2 else ""
            rec[cells[0]] = {"verdict": verdict, "note": note, "child": None}
    return rec


def cmd_reconcile(args):
    root = os.getcwd()
    se = os.path.join(root, SE_DIR)
    problems = []
    state = None
    if os.path.isfile(os.path.join(root, STATE_FILE)):
        try:
            state = load_state(root)
        except Exception as e:
            problems.append(f"state.json 损坏（{e}），将从文档反推重建")
    if state is None:
        state = new_state()
        if os.path.isdir(se):
            for d in sorted(os.listdir(se)):
                dp = os.path.join(se, d)
                if d.startswith(".") or not os.path.isdir(dp):
                    continue
                soi = {"parent": None, "element": None, "created": None, "phases": {}, "recursion": {}}
                for ph, doc in PHASE_DOCS.items():
                    fp = os.path.join(dp, doc)
                    if os.path.isfile(fp):
                        soi["phases"][ph] = {"status": infer_phase_status(fp), "doc": doc, "date": None}
                soi["recursion"] = infer_recursion(os.path.join(dp, "P4-architecture.md"))
                state["sois"][d] = soi
            names = list(state["sois"])
            for n in names:
                for m in names:
                    if n != m and n.startswith(m + "--"):
                        state["sois"][n]["parent"] = m
                        state["sois"][n]["element"] = n[len(m) + 2:]
        state["focus"] = None
        save_state(root, state)
        problems.append("state 已重建；unknown 状态/字段请人工确认（gate-pass 或 waive 落实）")
        flat = [f for f in PHASE_DOCS.values() if os.path.isfile(os.path.join(se, f))]
        for f in flat:
            problems.append(f"检测到 v0.1 平铺文档 docs/SE/{f}——v0.2 不支持该布局，请移入 SoI 子目录或删除")
    # 对账
    for name, soi in sorted(state["sois"].items()):
        dp = os.path.join(se, name)
        if not os.path.isdir(dp):
            problems.append(f"{name}：state 有登记但目录缺失")
        for ph, info in (soi.get("phases") or {}).items():
            if info.get("status") in ("passed", "waived"):
                fp = os.path.join(dp, info.get("doc") or PHASE_DOCS[ph])
                if not os.path.isfile(fp):
                    problems.append(f"{name}：{ph} 标记 {info['status']} 但文档缺失 {info.get('doc')}")
    if os.path.isdir(se):
        for d in sorted(os.listdir(se)):
            if d.startswith(".") or not os.path.isdir(os.path.join(se, d)) or d in state["sois"]:
                continue
            problems.append(f"目录 {d}/ 未在 state 登记——/fractal-start 登记，或父级 register-child 后再建目录")
    if problems:
        print("漂移报告：")
        for x in problems:
            print(f"  - {x}")
    else:
        print("一致：state 与文档无漂移。")
    return 0


GAP_STATES = ("PASS", "FAIL", "BLOCKED", "PARTIAL")


def parse_p7(path):
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s.startswith("|"):
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not cells or not cells[0] or cells[0].startswith("-") or cells[0].upper() == "REQ":
                continue
            st = None
            for c in cells:
                if c.upper() in GAP_STATES:
                    st = c.upper()
                    break
            if st:
                rows.append((cells[0], st))
    return rows


def cmd_gap(args):
    root = os.getcwd()
    se = os.path.join(root, SE_DIR)
    found, unparsed = [], []
    if os.path.isdir(se):
        for d in sorted(os.listdir(se)):
            fp = os.path.join(se, d, "P7-verification.md")
            if not os.path.isfile(fp):
                continue
            try:
                rows = parse_p7(fp)
            except OSError:
                rows = []
            if rows:
                found.extend((d, r, st) for r, st in rows)
            else:
                unparsed.append(d)
    if not found and not unparsed:
        print("没有可汇总的 P7 证据矩阵。")
        return 0
    print(f"全局差距（截至 {today()}）")
    by = {}
    for d, r, st in found:
        by.setdefault(st, []).append(f"{r}({d})")
    for st in ("FAIL", "BLOCKED", "PARTIAL", "PASS"):
        if st in by:
            print(f"  {st:<8} {len(by[st])} 条：{' / '.join(by[st])}")
    for d in unparsed:
        print(f"  ⚠ {d}/P7-verification.md 表格无法解析——请按固定五列表格（REQ|方法|判据|证据|状态）改写，或手工汇总")
    print()
    print("建议消差顺序（差距驱动，非想到什么做什么）：跨 SoI 阻塞 > 单 SoI 核心使命 > 边缘。")
    print("底线：新工作不在这张表上，先回 P2 登记 REQ（或被拒绝）。")
    return 0


def cmd_hook_sessionstart(args):
    root = os.getcwd()
    script = os.path.abspath(__file__)
    se = os.path.join(root, SE_DIR)
    if not os.path.isdir(se):
        print(f"fractal 已就绪（未初始化）。/fractal-start <name> 立项；脚本：{script}")
        return 0
    try:
        state = load_state(root)
    except Exception:
        state = None
    if not state or not state.get("sois"):
        print(f"fractal：docs/SE 存在但无 state（v0.1 旧布局？）。运行 python3 {script} reconcile 登记。")
        return 0
    lines = render_tree(state, with_stuck=False)
    if len(lines) > 9:
        focus = state.get("focus")
        # 刻意子串匹配：保留 focus 及其首层子树；行数由 keep[:9] 硬上限兜底
        keep = [l for l in lines if (focus and focus in l) or not l.strip().startswith(("├", "└", "│"))]
        lines = keep[:9] + ["…（/fractal-tree 查看全树）"]
    print("【fractal】")
    print("\n".join(lines))
    focus = state.get("focus")
    if focus and focus in state["sois"]:
        soi = state["sois"][focus]
        cur = current_phase(soi)
        if cur:
            print(f"focus：{focus}，当前 {cur}，下一步 /fractal-next")
            print(f"纪律——{PHASE_DISCIPLINE[cur]}")
        else:
            print(f"focus：{focus}，全部阶段完成（/fractal-gap 看差距，/fractal-tree 看全树）")
    print("五条纪律速查：docs/SE/00-overview.md")
    return 0


def build_parser():
    ap = argparse.ArgumentParser(prog="fractal.py", description="fractal 状态机内核")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("start", help="建 SoI（state+目录+00-overview）")
    p.add_argument("name", nargs="?")
    p.add_argument("--parent")
    p.add_argument("--element")
    p.set_defaults(func=cmd_start)

    p = sub.add_parser("status", help="当前位置与下一步")
    p.add_argument("soi", nargs="?")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("gate-pass", help="登记过闸")
    p.add_argument("soi")
    p.add_argument("phase")
    p.set_defaults(func=cmd_gate_pass)

    p = sub.add_parser("waive", help="显式弃权（记录在案）")
    p.add_argument("soi")
    p.add_argument("phase")
    p.add_argument("--reason", default="")
    p.set_defaults(func=cmd_waive)

    p = sub.add_parser("register-child", help="登记递归判断结果")
    p.add_argument("soi")
    p.add_argument("element")
    p.add_argument("--verdict", required=True, choices=["leaf", "promote"])
    p.add_argument("--note", default="")
    p.set_defaults(func=cmd_register_child)

    p = sub.add_parser("tree", help="递归树与卡点")
    p.set_defaults(func=cmd_tree)

    p = sub.add_parser("check-write", help="校验一次 docs/SE 写入（0 放行 / 2 拒绝）")
    p.add_argument("--path", required=True)
    p.set_defaults(func=cmd_check_write)

    p = sub.add_parser("hook-pretoolwrite", help="PreToolUse hook 入口（stdin JSON）")
    p.set_defaults(func=cmd_hook_pretoolwrite)

    p = sub.add_parser("reconcile", help="state 与文档对账；损坏时反推重建")
    p.set_defaults(func=cmd_reconcile)

    p = sub.add_parser("gap", help="汇总全部 P7 矩阵 = 差距驱动路线图")
    p.set_defaults(func=cmd_gap)

    p = sub.add_parser("hook-sessionstart", help="SessionStart hook 入口")
    p.set_defaults(func=cmd_hook_sessionstart)

    # ---- Task 3-8 的子命令在此追加 ----
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 1
    if getattr(args, "cmd", "") in ("hook-pretoolwrite", "hook-sessionstart"):
        try:
            return args.func(args) or 0
        except Exception:
            return 0  # fail-open：hook 任何异常都不阻塞
    try:
        return args.func(args) or 0
    except FractalError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
