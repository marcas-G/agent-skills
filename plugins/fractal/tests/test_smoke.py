import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "fractal.py")


def run(cwd, *a, stdin=None):
    return subprocess.run(
        [sys.executable, SCRIPT, *a], cwd=cwd,
        input=stdin, capture_output=True, text=True,
    )


class TestSmokeJourney(unittest.TestCase):
    def test_full_journey_with_block_and_waiver(self):
        with tempfile.TemporaryDirectory() as td:
            # 1) 立项 + P0-P4 过闸
            self.assertEqual(run(td, "start", "alpha").returncode, 0)
            for ph in ["P0", "P1", "P2", "P3", "P4"]:
                self.assertEqual(run(td, "gate-pass", "alpha", ph).returncode, 0, ph)

            # 2) 未做递归判断 → P5 文档被规则2拦
            r = run(td, "check-write", "--path", "docs/SE/alpha/P5-detail.md")
            self.assertEqual(r.returncode, 2)
            self.assertIn("规则2", r.stdout)

            # 3) 递归判断：1 叶子 1 提升 → P5 放行
            run(td, "register-child", "alpha", "E1", "--verdict", "leaf")
            run(td, "register-child", "alpha", "E2", "--verdict", "promote", "--note", "③独立干系人")
            r = run(td, "check-write", "--path", "docs/SE/alpha/P5-detail.md")
            self.assertEqual(r.returncode, 0)

            # 4) 子 SoI：P0 未过 → P1 文档被规则1拦；弃权后放行
            self.assertEqual(run(td, "start", "--parent", "alpha", "--element", "E2").returncode, 0)
            r = run(td, "check-write", "--path", "docs/SE/alpha--E2/P1-stakeholders.md")
            self.assertEqual(r.returncode, 2)
            self.assertIn("规则1", r.stdout)
            run(td, "waive", "alpha--E2", "P0", "--reason", "演示：先聚焦父级")
            r = run(td, "check-write", "--path", "docs/SE/alpha--E2/P1-stakeholders.md")
            self.assertEqual(r.returncode, 0)

            # 5) 孤儿目录 → 规则3
            r = run(td, "check-write", "--path", "docs/SE/ghost/P0-problem.md")
            self.assertEqual(r.returncode, 2)
            self.assertIn("规则3", r.stdout)

            # 6) hook：P5 未过闸写 P6 → decision block
            payload = json.dumps({
                "tool_name": "Write",
                "tool_input": {"file_path": os.path.join(td, "docs/SE/alpha/P6-implementation.md")},
            })
            r = run(td, "hook-pretoolwrite", stdin=payload)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(json.loads(r.stdout)["decision"], "block")

            # 7) 过 P5 闸后放行；tree 显示弃权 ⚠ 与卡点
            run(td, "gate-pass", "alpha", "P5")
            r = run(td, "hook-pretoolwrite", stdin=payload)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout.strip(), "")
            r = run(td, "tree")
            self.assertIn("⚠", r.stdout)
            self.assertIn("卡点", r.stdout)

            # 8) sessionstart 注入 ≤15 行且含 focus
            r = run(td, "hook-sessionstart")
            self.assertIn("【fractal】", r.stdout)
            self.assertLessEqual(len(r.stdout.strip().splitlines()), 15)

            # 9) reconcile 一致性（补齐文档避免误报：过闸但文档缺失也算漂移）
            for name, docs in [
                ("alpha", ["P0-problem.md", "P1-stakeholders.md", "P2-requirements.md",
                           "P3-logical.md", "P4-architecture.md", "P5-detail.md"]),
                ("alpha--E2", ["P0-problem.md"]),
            ]:
                for d in docs:
                    with open(os.path.join(td, "docs/SE", name, d), "w", encoding="utf-8") as f:
                        f.write(f"# {d}\n\n## Exit Gate 自查\n\n- [x] done\n")
            r = run(td, "reconcile")
            self.assertIn("一致", r.stdout)

            # 10) gap：无 P7 矩阵时优雅输出
            r = run(td, "gap")
            self.assertEqual(r.returncode, 0)
            self.assertIn("没有", r.stdout)


if __name__ == "__main__":
    unittest.main()
