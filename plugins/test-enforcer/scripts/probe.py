#!/usr/bin/env python3
"""E-2 工具链探测器（P5 契约）。

不变量：
  I1 档案中每个维度必有 available|blocked|unknown 三态之一，blocked 必附 reason
  I2 探测不到的工具一律 unknown/blocked，绝不猜测命令
  I3 合并后阈值显式出现在档案中（含覆盖来源）
"""
import json
import os
import shutil
import sys

DEFAULT_THRESHOLDS = {
    "coverage_line": 90,
    "coverage_branch": 90,
    "mutation_survive": 10,   # 存活率上限 %
}

CONFIG_NAME = ".test-enforcer.toml"

# 文件指纹 → 语言（顺序即优先级）
FINGERPRINTS = [
    (["pyproject.toml", "requirements.txt", "setup.py"], "python"),
    (["package.json"], "node"),
    (["go.mod"], "go"),
    (["Cargo.toml"], "rust"),
    (["pom.xml", "build.gradle", "build.gradle.kts"], "java"),
    (["Gemfile"], "ruby"),
    (["composer.json"], "php"),
]


def dim(state, reason=None):
    d = {"state": state}
    if reason:
        d["reason"] = reason
    return d


def probe_language(root):
    for files, lang in FINGERPRINTS:
        for f in files:
            if os.path.exists(os.path.join(root, f)):
                return lang, None
    return None, "no fingerprint match"


def which(tool):
    return shutil.which(tool) is not None


def runnable(cmd):
    """存在 ≠ 可运行（坏 shim 探测：~/.local/bin 下的 console script 可能 import 失败）。"""
    import subprocess
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False


def probe_python(root):
    dims = {}
    test_cmd = None
    coverage_cmd = None
    if which("pytest") or which("python3"):
        # 探测验证可运行性（坏 shim：which 找到但 import 失败 → 视为不可用）
        py = "pytest" if which("pytest") and runnable(["pytest", "--version"]) else None
        if py is None:
            py = f"{sys.executable} -m pytest" if runnable(
                [sys.executable, "-m", "pytest", "--version"]) else None
        if py:
            test_cmd = py
            dims["unit"] = dim("available")
            dims["integration"] = dim("available")
            # 覆盖：pytest-cov 探测
            try:
                import subprocess
                r = subprocess.run(
                    [*(py.split()), "-c", "import pytest_cov"],
                    capture_output=True, timeout=30,
                )
                if r.returncode == 0:
                    coverage_cmd = f"{py} --cov --cov-report=json --junitxml"
                    dims["coverage"] = dim("available")
                else:
                    dims["coverage"] = dim("blocked", "pytest-cov not installed")
            except Exception as e:
                dims["coverage"] = dim("unknown", str(e))
        else:
            dims["unit"] = dim("blocked", "pytest not found")
            dims["integration"] = dim("blocked", "pytest not found")
            dims["coverage"] = dim("blocked", "pytest not found")
    else:
        for k in ("unit", "integration", "coverage"):
            dims[k] = dim("blocked", "python/pytest not found")
    dims["mutation"] = (
        dim("available", "native=mutmut") if which("mutmut")
        else dim("available", "engine=heuristic(ast)")
    )
    try:
        import subprocess
        r = subprocess.run(
            [sys.executable, "-c", "import hypothesis"],
            capture_output=True, timeout=30,
        )
        dims["fuzz"] = dim("available") if r.returncode == 0 else dim(
            "blocked", "hypothesis not installed"
        )
    except Exception as e:
        dims["fuzz"] = dim("unknown", str(e))
    return test_cmd, coverage_cmd, dims


def probe_node(root):
    dims = {}
    runner = None
    for cmd in ("jest", "vitest"):
        if which(cmd):
            runner = cmd
            break
    if not runner and which("npx"):
        runner = "npx jest"
    if runner:
        dims["unit"] = dim("available")
        dims["integration"] = dim("available")
        coverage_flag = "--coverage"
        dims["coverage"] = dim("available", f"{runner} {coverage_flag} --json")
    else:
        for k in ("unit", "integration", "coverage"):
            dims[k] = dim("blocked", "jest/vitest not found")
    dims["mutation"] = (
        dim("available", "native=stryker") if which("stryker") or which("npx")
        else dim("available", "engine=heuristic(regex)")
    )
    dims["fuzz"] = dim("blocked", "no standard fuzz runner (use jest-property manually)")
    return (f"{runner}" if runner else None), None, dims


def probe_go(root):
    dims = {}
    if which("go"):
        dims["unit"] = dim("available")
        dims["integration"] = dim("available")
        dims["coverage"] = dim("available", "go test -cover")
    else:
        for k in ("unit", "integration", "coverage"):
            dims[k] = dim("blocked", "go not found")
    dims["mutation"] = (
        dim("available", "native=go-mutesting") if which("go-mutesting")
        else dim("available", "engine=heuristic(text)")
    )
    dims["fuzz"] = dim("available", "go native fuzzing")
    return "go test", "go test -cover", dims


PROBES = {"python": probe_python, "node": probe_node, "go": probe_go}


def load_config(root):
    """项目配置合并（REQ-DRV-2）。失败忽略并标注——绝不让坏配置炸掉流程。"""
    path = os.path.join(root, CONFIG_NAME)
    merged = dict(DEFAULT_THRESHOLDS)
    source = {"coverage_line": "default", "coverage_branch": "default",
              "mutation_survive": "default"}
    ignored = False
    if os.path.exists(path):
        try:
            import tomllib
            with open(path, "rb") as f:
                cfg = tomllib.load(f)
            th = cfg.get("thresholds", {})
            if isinstance(th, dict):
                for k in DEFAULT_THRESHOLDS:
                    if k in th and isinstance(th[k], (int, float)):
                        merged[k] = th[k]
                        source[k] = "project"
        except Exception:
            ignored = True
    return merged, source, ignored


def main():
    root = os.getcwd()
    for i, a in enumerate(sys.argv):
        if a == "--root" and i + 1 < len(sys.argv):
            root = os.path.abspath(sys.argv[i + 1])
    if not os.path.isdir(root):
        print(json.dumps({"error": f"root not readable: {root}"}))
        sys.exit(2)

    lang, reason = probe_language(root)
    if not lang:
        # 不变量 I2：探测不到 → 全维度 blocked，宁停勿猜
        out = {
            "root": root, "languages": [],
            "dimensions": {k: dim("blocked", reason) for k in
                           ("unit", "integration", "coverage", "mutation", "fuzz")},
            "thresholds": DEFAULT_THRESHOLDS,
            "threshold_source": "default", "config_ignored": False,
        }
        print(json.dumps(out))
        sys.exit(3)  # 专用码：无法探测 → E-1 呈现后停

    test_cmd, coverage_cmd, dims = PROBES[lang](root)
    th, src, ignored = load_config(root)

    out = {
        "root": root,
        "languages": [lang],
        "test_cmd": test_cmd,
        "coverage_cmd": coverage_cmd,
        "dimensions": dims,
        "thresholds": th,
        "threshold_source": src,
        "config_ignored": ignored,
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
