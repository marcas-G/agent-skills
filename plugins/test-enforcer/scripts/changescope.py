#!/usr/bin/env python3
"""E-3 变更范围识别器（P5 契约）。

不变量：
  I1 files 每个条目真实存在于磁盘或 VCS 记录——永不虚构
  I2 无 VCS 时 mode=full 且 vcs=none 显式标注（REQ-DRV-1）
"""
import json
import os
import subprocess
import sys

# 源文件后缀（非测试文件）——测试文件本身不计入被测范围
SRC_EXT = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb", ".php"}
TEST_MARKERS = ("test_", "_test.go", ".test.js", ".test.ts", ".spec.js", ".spec.ts",
                "_spec.rb", "Test")


def git(root, *args):
    return subprocess.run(
        ["git", "-C", root, *args], capture_output=True, text=True, timeout=60
    )


def is_test_file(path):
    base = os.path.basename(path)
    return (base.startswith("test_") or base.endswith(("_test.go", ".test.js",
            ".test.ts", ".spec.js", ".spec.ts", "_spec.rb")))


def find_base(root):
    for cand in ("main", "master", "trunk", "develop"):
        r = git(root, "rev-parse", "--verify", f"origin/{cand}")
        if r.returncode == 0:
            return f"origin/{cand}", cand
        r = git(root, "rev-parse", "--verify", cand)
        if r.returncode == 0:
            return cand, cand
    return None, None


def list_all_sources(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "node_modules", ".venv", "venv",
                                    "__pycache__", "dist", "build", ".test-enforcer")]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root)
            if os.path.splitext(fn)[1] in SRC_EXT and not is_test_file(rel):
                out.append(rel)
    return sorted(out)


def main():
    root = os.getcwd()
    args = sys.argv[1:]
    force_full = "--all" in args
    explicit = None
    for i, a in enumerate(args):
        if a == "--root" and i + 1 < len(args):
            root = os.path.abspath(args[i + 1])
        if a == "--files" and i + 1 < len(args):
            explicit = [x for x in args[i + 1].split(",") if x]

    result = {"root": root, "vcs": "none", "base_ref": None,
              "mode": "full", "files": [], "code_units": []}

    try:
        r = git(root, "rev-parse", "--is-inside-work-tree")
        in_repo = r.returncode == 0 and r.stdout.strip() == "true"
    except Exception:
        in_repo = False

    if explicit:
        # C2 补测流：显式指定范围
        result["mode"] = "explicit"
        result["files"] = [f for f in explicit if os.path.exists(os.path.join(root, f))]
        result["code_units"] = result["files"]
        print(json.dumps(result, ensure_ascii=False))
        return

    if force_full or not in_repo:
        result["vcs"] = "git" if in_repo else "none"
        result["files"] = list_all_sources(root)
        result["code_units"] = result["files"]
        if not in_repo:
            result["note"] = "no VCS: incremental gating unavailable, full mode (REQ-DRV-1)"
        print(json.dumps(result, ensure_ascii=False))
        return

    result["vcs"] = "git"
    base, base_name = find_base(root)
    if not base:
        result["files"] = list_all_sources(root)
        result["note"] = "no base branch found, full mode"
        result["code_units"] = result["files"]
        print(json.dumps(result, ensure_ascii=False))
        return

    result["base_ref"] = base_name
    r = git(root, "diff", "--name-only", f"{base}...HEAD")
    changed = [x for x in r.stdout.splitlines() if x.strip()] if r.returncode == 0 else []
    # 未提交变更也计入（工作树 vs base 的真实增量）
    r2 = git(root, "diff", "--name-only", base)
    working = [x for x in r2.stdout.splitlines() if x.strip()] if r2.returncode == 0 else []
    r3 = git(root, "ls-files", "--others", "--exclude-standard")
    untracked = [x for x in r3.stdout.splitlines() if x.strip()] if r3.returncode == 0 else []

    seen, files = set(), []
    for f in changed + working + untracked:
        if f in seen:
            continue
        seen.add(f)
        if os.path.splitext(f)[1] not in SRC_EXT or is_test_file(f):
            continue
        if os.path.exists(os.path.join(root, f)):  # 不变量 I1：真实存在（删除的变更跳过）
            files.append(f)

    result["mode"] = "incremental" if files else "incremental-empty"
    result["files"] = sorted(files)
    result["code_units"] = result["files"]
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
