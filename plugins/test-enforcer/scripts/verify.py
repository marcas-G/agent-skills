#!/usr/bin/env python3
"""E-5 独立验证器（P5 契约）。

不变量：
  I1 绝不采信传入的任何口头/转述结果——一切数字来自本进程执行工具的原始输出
  I2 解析失败 → 维度 unknown，绝不为 unknown 给通过
  I3 纯确定性：同输入同输出（无网络、无时间依赖）
"""
import ast
import json
import os
import re
import subprocess
import sys

TOOL_TIMEOUT_DEFAULT = 600  # 秒；单维超时隔离（REQ-DRV-4）


# ---------------------------------------------------------------- 假测试扫描

class FakeTestScanner:
    """R1 无断言 / R2 恒真 / R3 吞异常 / R4 断言 mock / R5 顺序依赖。

    Python 走真 AST；JS/TS 走正则降级并标 engine=regex。
    """

    def __init__(self, root):
        self.root = root
        self.findings = []

    def scan(self, test_files):
        for tf in test_files:
            ext = os.path.splitext(tf)[1]
            path = os.path.join(self.root, tf)
            try:
                with open(path, encoding="utf-8") as f:
                    src = f.read()
            except Exception as e:
                self.findings.append({"file": tf, "line": 0, "rule": "unreadable",
                                      "snippet": str(e), "engine": "io"})
                continue
            if ext == ".py":
                self._scan_python(tf, src)
            elif ext in (".js", ".ts", ".jsx", ".tsx"):
                self._scan_js(tf, src)
        return self.findings

    # ---- Python AST ----
    def _is_test_fn(self, node, is_class_member):
        return isinstance(node, ast.FunctionDef) and (
            node.name.startswith("test") or (is_class_member and node.name.startswith("test"))
        )

    def _count_asserts(self, body):
        n = 0
        for node in body:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assert):
                    n += 1
                elif isinstance(sub, ast.Call):
                    fn = sub.func
                    name = ""
                    if isinstance(fn, ast.Attribute):
                        name = fn.attr
                    elif isinstance(fn, ast.Name):
                        name = fn.id
                    if name.startswith(("assert", "fail")) or name == "raises":
                        n += 1
        return n

    def _is_tautology(self, test):
        if isinstance(test, ast.Constant) and isinstance(test.value, bool):
            return True
        # assert x == x / x is x
        if isinstance(test, ast.Compare) and len(test.ops) == 1 and \
           len(test.comparators) == 1:
            l, r = test.left, test.comparators[0]
            same = lambda n: isinstance(n, ast.Name)
            if same(l) and same(r) and l.id == r.id:
                return True
            if isinstance(l, ast.Constant) and isinstance(r, ast.Constant) and l.value == r.value:
                return True
        return False

    def _scan_python(self, tf, src):
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            self.findings.append({"file": tf, "line": e.lineno or 0,
                                  "rule": "syntax-error", "snippet": str(e),
                                  "engine": "ast"})
            return
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if self._is_test_fn(item, True):
                        self._check_py_fn(tf, item, class_ctx=node.name)
            elif self._is_test_fn(node, False):
                self._check_py_fn(tf, node)

    def _check_py_fn(self, tf, fn, class_ctx=None):
        loc = f"{class_ctx}." if class_ctx else ""
        if self._count_asserts(fn.body) == 0:
            self.findings.append({
                "file": tf, "line": fn.lineno, "rule": "R1-no-assert",
                "snippet": f"def {loc}{fn.name}(): no assert/expect found",
                "engine": "ast"})
        # 恒真 / 吞异常逐语句查
        for node in ast.walk(ast.Module(body=fn.body, type_ignores=[])):
            if isinstance(node, ast.Assert) and self._is_tautology(node.test):
                self.findings.append({
                    "file": tf, "line": node.lineno, "rule": "R2-tautology",
                    "snippet": ast.dump(node.test)[:80], "engine": "ast"})
            if isinstance(node, ast.ExceptHandler):
                useful = any(
                    isinstance(s, (ast.Raise,)) or
                    (isinstance(s, ast.Expr) and isinstance(s.value, ast.Call))
                    for s in node.body
                ) or self._count_asserts(node.body) > 0
                if not useful:
                    self.findings.append({
                        "file": tf, "line": node.lineno, "rule": "R3-swallow",
                        "snippet": "except ...: pass (no re-raise/assert)",
                        "engine": "ast"})
            # R4 断言 mock：断言子树中出现 mock 调用返回值
            if isinstance(node, ast.Assert):
                for sub in ast.walk(node.test):
                    if isinstance(sub, ast.Attribute) and \
                       re.match(r"mock\S*", sub.attr or ""):
                        self.findings.append({
                            "file": tf, "line": node.lineno,
                            "rule": "R4-assert-mock-suspect",
                            "snippet": ast.dump(node.test)[:80],
                            "engine": "ast-heuristic"})

    # ---- JS/TS 正则降级 ----
    JS_TEST_RE = re.compile(
        r"(?:it|test)\s*\(\s*['\"].*?['\"]\s*,\s*(?:async\s*)?\(\s*\)\s*=>", re.S)

    def _scan_js(self, tf, src):
        for m in self.JS_TEST_RE.finditer(src):
            start = m.end()
            # 从 => 后找第一个 { 起配对；初始 depth=0，首个 { 计 1，配对归 0 即测试体结束
            depth, i, started = 0, start, False
            while i < len(src):
                c = src[i]
                if c == "{":
                    depth += 1
                    started = True
                elif c == "}":
                    depth -= 1
                    if started and depth == 0:
                        break
                i += 1
            body = src[start:i]
            line = src[:m.start()].count("\n") + 1
            if not re.search(r"\bexpect\s*\(|\bassert\s*\(", body):
                self.findings.append({
                    "file": tf, "line": line, "rule": "R1-no-assert",
                    "snippet": src[m.start():m.start() + 60].replace("\n", " "),
                    "engine": "regex"})
            if re.search(r"expect\s*\(\s*(?:true|1)\s*\)", body):
                self.findings.append({
                    "file": tf, "line": line, "rule": "R2-tautology",
                    "snippet": "expect(true)", "engine": "regex"})
            if re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", body):
                self.findings.append({
                    "file": tf, "line": line, "rule": "R3-swallow",
                    "snippet": "catch(e){}", "engine": "regex"})


# ---------------------------------------------------------------- 执行与解析

def run_cmd(cmd, root, timeout, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(cmd, shell=isinstance(cmd, str), cwd=root,
                          capture_output=True, text=True, timeout=timeout, env=env)


def find_test_files(root, lang):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "node_modules", ".venv", "venv",
                                    "__pycache__", "dist", "build", ".test-enforcer")]
        for fn in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fn), root)
            if lang == "python" and (fn.startswith("test_") and fn.endswith(".py")
                                     or fn == "conftest.py"):
                out.append(rel)
            elif lang in ("node",) and re.search(r"\.(test|spec)\.(js|ts|jsx|tsx)$", fn):
                out.append(rel)
            elif lang == "go" and fn.endswith("_test.go"):
                out.append(rel)
    return sorted(out)


def pytest_cmd():
    """与 probe.py 的探测口径一致：优先 PATH 上的 pytest，回退 sys.executable -m pytest。"""
    import shutil
    if shutil.which("pytest"):
        return "pytest"
    return f"{sys.executable} -m pytest"


def parse_pytest(root):
    """pytest junitxml + coverage.json → 事实。解析不到 → None（不变量 I2）。"""
    out = {}
    junit = os.path.join(root, ".test-enforcer", "tmp-junit.xml")
    cov = os.path.join(root, "coverage.json")
    py = pytest_cmd()
    r = run_cmd(f"{py} -q --junitxml={junit}", root, TOOL_TIMEOUT_DEFAULT)
    out["exec"] = {"status": "pass" if r.returncode == 0 else "fail",
                   "raw_output_tail": (r.stdout + r.stderr)[-2000:],
                   "returncode": r.returncode}
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(junit)
        suite = tree.getroot().find("testsuite")
        if suite is None:
            suite = tree.getroot()
        total = int(suite.get("tests", 0) or 0)
        failed = int(suite.get("failures", 0) or 0) + int(suite.get("errors", 0) or 0)
        skipped = int(suite.get("skipped", 0) or 0)
        out["exec"].update({
            "passed": max(total - failed - skipped, 0),  # junit 无 passed 标准属性
            "failed": failed,
            "total": total})
    except Exception:
        out["exec"]["parse"] = "junit-failed(unknown)"
    if os.path.exists(cov):
        try:
            with open(cov) as f:
                cj = json.load(f)
            t = cj.get("totals", {})
            out["coverage"] = {
                "line": _num(t.get("percent_covered_display")),
                "covered_lines": t.get("covered_lines"),
                "num_statements": t.get("num_statements"),
                "branch": (round(100 * t.get("covered_branches", 0) / t["num_branches"], 1)
                           if t.get("num_branches") else None),
                "format": "coverage.py-json"}
        except Exception:
            out["coverage"] = {"state": "unknown", "reason": "coverage.json unparseable"}
    else:
        # 尝试带 cov 重跑一次拿覆盖（--cov-branch：分支覆盖必须显式开启）
        r2 = run_cmd(f"{py} -q --cov=. --cov-branch "
                     f"--cov-report=json:{cov} --junitxml={junit}",
                     root, TOOL_TIMEOUT_DEFAULT)
        if os.path.exists(cov):
            return dict(out, **parse_cov_json(cov))
        out["coverage"] = {"state": "unknown", "reason": "pytest-cov unavailable"}
    return out


def _num(x):
    """'100'/100 → 100.0 float；不可转 → None（unknown 语义）。"""
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.rstrip("%"))
        except ValueError:
            return None
    return None


def parse_cov_json(cov):
    try:
        with open(cov) as f:
            cj = json.load(f)
        t = cj.get("totals", {})
        return {"coverage": {
            "line": _num(t.get("percent_covered_display")),
            "branch": (round(100 * t.get("covered_branches", 0) / t["num_branches"], 1)
                       if t.get("num_branches") else None),
            "format": "coverage.py-json"}}
    except Exception:
        return {"coverage": {"state": "unknown", "reason": "unparseable"}}


def parse_jest(root):
    out = {}
    r = run_cmd("npx jest --coverage --coverageReporters=json-summary --json", root,
                TOOL_TIMEOUT_DEFAULT)
    try:
        tail = r.stdout[r.stdout.find("{"):]
        j = json.loads(tail)
        out["exec"] = {"status": "pass" if j.get("success") else "fail",
                       "passed": j.get("numPassedTests"), "failed": j.get("numFailedTests"),
                       "returncode": r.returncode}
    except Exception:
        out["exec"] = {"status": "unknown", "raw_output_tail": r.stdout[-2000:]}
    covp = os.path.join(root, "coverage", "coverage-summary.json")
    if os.path.exists(covp):
        try:
            with open(covp) as f:
                cs = json.load(f)
            total = cs.get("total", {})
            out["coverage"] = {
                "line": total.get("lines", {}).get("pct"),
                "branch": total.get("branches", {}).get("pct"),
                "format": "jest-json-summary"}
        except Exception:
            out["coverage"] = {"state": "unknown"}
    else:
        out["coverage"] = {"state": "unknown", "reason": "coverage-summary.json missing"}
    return out


def parse_go(root):
    out = {}
    r = run_cmd("go test ./... -cover -json", root, TOOL_TIMEOUT_DEFAULT)
    line_cov, dec = None, "unknown"
    try:
        for ln in r.stdout.splitlines():
            try:
                ev = json.loads(ln)
            except Exception:
                continue
            o = ev.get("Output", "")
            m = re.search(r"coverage:\s*([\d.]+)%", o)
            if m:
                line_cov = max(float(m.group(1)), line_cov or 0)
        dec = "pass" if '"Action":"pass"' in r.stdout and '"Action":"fail"' not in r.stdout else "fail"
    except Exception:
        pass
    out["exec"] = {"status": dec, "raw_output_tail": r.stdout[-2000:]}
    out["coverage"] = {"line": line_cov, "branch": None,
                       "format": "go-test-json", "branch_note": "go branch coverage n/a → unknown"}
    return out


RUNNERS = {"python": parse_pytest, "node": parse_jest, "go": parse_go}


def main():
    root = os.getcwd()
    profile = None
    timeout = TOOL_TIMEOUT_DEFAULT
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--root" and i + 1 < len(args):
            root = os.path.abspath(args[i + 1])
        if a == "--profile" and i + 1 < len(args):
            with open(args[i + 1]) as f:
                profile = json.load(f)
        if a == "--timeout" and i + 1 < len(args):
            timeout = int(args[i + 1])
    if not profile:
        print(json.dumps({"error": "--profile required"}))
        sys.exit(2)

    lang = (profile.get("languages") or [None])[0]
    result = {"dimension": "verify", "language": lang, "tool": profile.get("test_cmd")}

    try:
        parsed = RUNNERS[lang](root)
    except subprocess.TimeoutExpired:
        parsed = {"exec": {"status": "timeout"},
                  "coverage": {"state": "unknown", "reason": "timeout (isolated)"}}
    except Exception as e:
        parsed = {"exec": {"status": "unknown", "reason": str(e)},
                  "coverage": {"state": "unknown"}}

    result.update(parsed)

    # 假测试扫描（独立于执行——执行挂了也照扫）
    test_files = find_test_files(root, lang)
    result["fake_tests"] = FakeTestScanner(root).scan(test_files)
    result["test_files_scanned"] = len(test_files)

    # verdict_hint 仅供 E-8 参考；unknown 永不映射为 ok（不变量 I2）
    def hint():
        ex = result.get("exec", {}).get("status")
        cov = result.get("coverage", {})
        if ex != "pass" or result["fake_tests"]:
            return "FAIL"
        if not isinstance(cov.get("line"), (int, float)):
            return "UNKNOWN"
        return "PASS"
    result["verdict_hint"] = hint()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
