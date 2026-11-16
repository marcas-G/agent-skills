#!/usr/bin/env python3
"""E-6 变异执行器（P5 契约）。

不变量：
  I1 score 只由实际执行结果计算，绝不估计/外推
  I2 时间预算尽 → 已完成批次照报 + pending 显式，禁止以部分冒充全部
  I3 变异体不改测试文件；每变异体在独立副本上跑
"""
import ast
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

DEFAULT_BATCH = 30          # 每次运行变异体上限（可续）
DEFAULT_BUDGET = 300        # 秒


# ------------------------------------------------------- AST 变异算子（Python）

class Mutator(ast.NodeTransformer):
    OPS = [
        (ast.Lt, ast.LtE), (ast.LtE, ast.Lt),
        (ast.Gt, ast.GtE), (ast.GtE, ast.Gt),
        (ast.Eq, ast.NotEq), (ast.NotEq, ast.Eq),
        (ast.Is, ast.IsNot), (ast.IsNot, ast.Is),
    ]

    def __init__(self, doc_ids, target):
        self.doc_ids = doc_ids   # docstring 节点 id 集（等价变异，剔除）
        self.target = target     # 只变异第 target 个可变点（0-based）
        self.seen = 0
        self.applied = None

    def visit_Compare(self, node):
        node = self.generic_visit(node)
        for i, op in enumerate(node.ops):
            for src, dst in self.OPS:
                if isinstance(op, src):
                    if self.seen == self.target:
                        node.ops[i] = dst()
                        self.applied = (node.lineno, f"{src.__name__}->{dst.__name__}")
                    self.seen += 1
                    return node
        return node

    def visit_Constant(self, node):
        if id(node) in self.doc_ids:
            return node
        if isinstance(node.value, int) and not isinstance(node.value, bool):
            if self.seen == self.target:
                node.value += 1
                self.applied = (node.lineno, f"int->{node.value}")
            self.seen += 1
        elif isinstance(node.value, str) and node.value:
            if self.seen == self.target:
                node.value += "MUT"
                self.applied = (node.lineno, "string+MUT")
            self.seen += 1
        return node


def collect_docstrings(tree):
    """docstring = Module/FunctionDef/ClassDef body 首个字符串 Expr——变异它无行为影响。"""
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and \
               isinstance(body[0].value, ast.Constant) and \
               isinstance(body[0].value.value, str):
                ids.add(id(body[0].value))
    return ids


def count_mutables(tree, doc_ids):
    m = Mutator(doc_ids, -1)  # target=-1：只计数不应用
    m.visit(tree)
    return m.seen


def gen_mutants(src_path, source):
    """逐个 yield (mutated_source, desc)：第 k 轮变异第 k 个可变点（全面轮转）。

    每轮重新 parse——deepcopy 会使 id() 失效（docstring 剔除依赖节点 id）。
    """
    try:
        tree = ast.parse(source)
        doc_ids = collect_docstrings(tree)
        total = count_mutables(tree, doc_ids)
    except SyntaxError:
        return
    for target in range(total):
        tree_k = ast.parse(source)          # 新对象 → 新 id，重收集
        doc_ids_k = collect_docstrings(tree_k)
        m = Mutator(doc_ids_k, target)
        new = m.visit(tree_k)
        if not m.applied:
            continue
        try:
            out = ast.unparse(new)
        except Exception:
            continue
        yield out, f"L{m.applied[0]} {m.applied[1]}"


def run_tests(root, lang, timeout):
    if lang == "python":
        import shutil
        py = "pytest" if shutil.which("pytest") else sys.executable
        cmd = ([py] if py == "pytest" else [sys.executable, "-m", "pytest"]) + \
              ["-x", "-q", "--no-header", "-p", "no:cacheprovider"]
    elif lang == "go":
        cmd = ["go", "test", "./..."]
    else:
        cmd = ["npx", "jest", "--silent"]
    try:
        r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        # 业界惯例：timeout = killed（变异诱发死循环/挂起，视为被检出）
        return False
    except Exception:
        return False


def compile_ok(source):
    try:
        ast.parse(source)
        return True
    except SyntaxError:
        return False


def main():
    root = os.getcwd()
    profile, batch, budget = None, DEFAULT_BATCH, DEFAULT_BUDGET
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--root" and i + 1 < len(args):
            root = os.path.abspath(args[i + 1])
        if a == "--profile" and i + 1 < len(args):
            with open(args[i + 1]) as f:
                profile = json.load(f)
        if a == "--batch-size" and i + 1 < len(args):
            batch = int(args[i + 1])
        if a == "--time-budget" and i + 1 < len(args):
            budget = int(args[i + 1])
    if not profile:
        print(json.dumps({"error": "--profile required"}))
        sys.exit(2)

    lang = (profile.get("languages") or [None])[0]
    mutdim = profile.get("dimensions", {}).get("mutation", {})
    if mutdim.get("state") == "blocked":
        print(json.dumps({"dimension": "mutation", "status": "BLOCKED",
                          "reason": mutdim.get("reason", "blocked")}))
        return

    # 被测源文件（变更范围内的）
    from verify import find_test_files  # noqa: 复用测试文件发现
    scope_file = os.path.join(root, ".test-enforcer", "scope.json")
    targets = []
    if os.path.exists(scope_file):
        try:
            with open(scope_file) as f:
                targets = json.load(f).get("files", [])
        except Exception:
            pass
    if not targets:
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in (".git", "node_modules", ".venv",
                                                "__pycache__", ".test-enforcer", "build")]
            for x in fn:
                rel = os.path.relpath(os.path.join(dp, x), root)
                if x.endswith(".py") and not (x.startswith("test_") or x == "conftest.py"):
                    targets.append(rel)

    if lang != "python":
        # 非内置支持语言：显式 BLOCKED 而非假跑（ADR-3 + 诚实性）
        print(json.dumps({"dimension": "mutation", "status": "BLOCKED",
                          "reason": f"heuristic engine not implemented for {lang}; "
                                    f"native tool required"}))
        return

    total = killed = survived = compile_failed = 0
    t0 = time.time()
    pending = 0
    mutant_log = []

    for rel in targets:
        src_path = os.path.join(root, rel)
        try:
            with open(src_path, encoding="utf-8") as f:
                source = f.read()
        except Exception:
            continue
        for mutated, desc in gen_mutants(rel, source):
            if total >= batch or (time.time() - t0) > budget:
                pending += 1
                continue
            if not compile_ok(mutated):
                compile_failed += 1  # 剔除出分母（P5 契约）
                continue
            # 独立副本上跑（不变量 I3）
            with tempfile.TemporaryDirectory() as td:
                tmp_root = td
                for item in os.listdir(root):
                    if item in (".git", ".test-enforcer", "__pycache__", ".venv",
                                "node_modules"):
                        continue
                    s = os.path.join(root, item)
                    d = os.path.join(tmp_root, item)
                    try:
                        if os.path.isdir(s):
                            shutil.copytree(s, d)
                        else:
                            shutil.copy2(s, d)
                    except Exception:
                        pass
                with open(os.path.join(tmp_root, rel), "w", encoding="utf-8") as f:
                    f.write(mutated)
                passed = run_tests(tmp_root, lang, 120)
            total += 1
            if passed:
                survived += 1
                mutant_log.append({"file": rel, "desc": desc, "outcome": "SURVIVED"})
            else:
                killed += 1
                mutant_log.append({"file": rel, "desc": desc, "outcome": "killed"})
            if (time.time() - t0) > budget:
                break
        if (time.time() - t0) > budget or total >= batch:
            break

    denom = total  # compile_failed 已剔除
    score = round(100 * survived / denom, 1) if denom else None
    out = {
        "dimension": "mutation",
        "engine": "heuristic(ast)",
        "mutants_total": denom,
        "killed": killed,
        "survived": survived,
        "compile_failed_excluded": compile_failed,
        "score_survived_pct": score,   # 越低越好；None=样本 0（显式，不估计）
        "batches": {"done": denom, "pending": pending},
        "time_budget_used_sec": round(time.time() - t0, 1),
        "survived_detail": [m for m in mutant_log if m["outcome"] == "SURVIVED"][:20],
        "status": "PASS" if (score is not None and
                             score <= profile.get("thresholds", {}).get(
                                 "mutation_survive", 10)) else
                  ("UNKNOWN" if score is None else "FAIL"),
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
