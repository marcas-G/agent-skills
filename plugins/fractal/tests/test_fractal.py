import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import fractal


class TmpBase(unittest.TestCase):
    """每个测试在自己声明的临时目录里跑（fractal.py 以 cwd 为项目根）。"""

    def setUp(self):
        self._old = os.getcwd()
        self.td = tempfile.TemporaryDirectory()
        os.chdir(self.td.name)

    def tearDown(self):
        os.chdir(self._old)
        self.td.cleanup()

    def run_cmd(self, *a):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                rc = fractal.main(list(a)) or 0
            except SystemExit as e:  # argparse 对未知子命令会 sys.exit(2)
                rc = e.code or 0
        return rc, out.getvalue(), err.getvalue()


class TestStart(TmpBase):
    def test_start_creates_state_dir_overview_and_focus(self):
        rc, out, _ = self.run_cmd("start", "alpha")
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isdir("docs/SE/alpha"))
        self.assertTrue(os.path.isfile("docs/SE/fractal-state.json"))
        self.assertTrue(os.path.isfile("docs/SE/00-overview.md"))
        st = fractal.load_state(os.getcwd())
        self.assertEqual(st["focus"], "alpha")
        self.assertIsNone(st["sois"]["alpha"]["parent"])
        self.assertIn("alpha", out)

    def test_start_rejects_bad_name(self):
        rc, _, err = self.run_cmd("start", "a b/c")
        self.assertEqual(rc, 1)
        self.assertIn("名称", err)

    def test_start_rejects_duplicate(self):
        self.run_cmd("start", "alpha")
        rc, _, err = self.run_cmd("start", "alpha")
        self.assertEqual(rc, 1)
        self.assertIn("已存在", err)

    def test_start_child_requires_registered_promote(self):
        self.run_cmd("start", "alpha")
        rc, _, err = self.run_cmd("start", "beta", "--parent", "alpha", "--element", "E1")
        self.assertEqual(rc, 1)
        self.assertIn("递归判断", err)


class TestStatus(TmpBase):
    def test_status_before_init_fails(self):
        rc, _, err = self.run_cmd("status")
        self.assertEqual(rc, 1)

    def test_status_reports_current_phase(self):
        self.run_cmd("start", "alpha")
        self.run_cmd("gate-pass", "alpha", "P0")
        rc, out, _ = self.run_cmd("status")
        self.assertEqual(rc, 0)
        self.assertIn("alpha", out)
        self.assertIn("P1", out)  # P0 过闸后当前阶段是 P1


class TestGates(TmpBase):
    def setUp(self):
        super().setUp()
        self.run_cmd("start", "alpha")

    def test_gate_pass_in_order(self):
        self.assertEqual(self.run_cmd("gate-pass", "alpha", "P0")[0], 0)
        self.assertEqual(self.run_cmd("gate-pass", "alpha", "P1")[0], 0)
        st = fractal.load_state(os.getcwd())["sois"]["alpha"]["phases"]
        self.assertEqual(st["P0"]["status"], "passed")
        self.assertEqual(st["P0"]["doc"], "P0-problem.md")

    def test_gate_pass_blocks_leap(self):
        rc, _, err = self.run_cmd("gate-pass", "alpha", "P3")
        self.assertEqual(rc, 1)
        self.assertIn("宁停勿跳", err)

    def test_gate_pass_p5_requires_recursion(self):
        for ph in ["P0", "P1", "P2", "P3", "P4"]:
            self.run_cmd("gate-pass", "alpha", ph)
        rc, _, err = self.run_cmd("gate-pass", "alpha", "P5")
        self.assertEqual(rc, 1)
        self.assertIn("递归", err)

    def test_waive_requires_reason_and_records(self):
        rc, _, err = self.run_cmd("waive", "alpha", "P0")
        self.assertEqual(rc, 1)
        self.assertIn("--reason", err)
        self.assertEqual(self.run_cmd("waive", "alpha", "P0", "--reason", "演示缺环境")[0], 0)
        st = fractal.load_state(os.getcwd())["sois"]["alpha"]["phases"]["P0"]
        self.assertEqual(st["status"], "waived")
        self.assertEqual(st["reason"], "演示缺环境")

    def test_waived_counts_as_open_for_next(self):
        self.run_cmd("waive", "alpha", "P0", "--reason", "r")
        self.assertEqual(self.run_cmd("gate-pass", "alpha", "P1")[0], 0)

    def test_gate_pass_idempotent(self):
        self.run_cmd("gate-pass", "alpha", "P0")
        self.assertEqual(self.run_cmd("gate-pass", "alpha", "P0")[0], 0)


class TestRegisterChild(TmpBase):
    def setUp(self):
        super().setUp()
        self.run_cmd("start", "alpha")

    def test_requires_p4_done(self):
        rc, _, err = self.run_cmd("register-child", "alpha", "E1", "--verdict", "leaf")
        self.assertEqual(rc, 1)
        self.assertIn("P4", err)

    def test_leaf_and_promote(self):
        for ph in ["P0", "P1", "P2", "P3", "P4"]:
            self.run_cmd("gate-pass", "alpha", ph)
        self.assertEqual(self.run_cmd("register-child", "alpha", "E1", "--verdict", "leaf")[0], 0)
        rc, out, _ = self.run_cmd("register-child", "alpha", "E2", "--verdict", "promote", "--note", "③独立干系人")
        self.assertEqual(rc, 0)
        self.assertIn("alpha--E2", out)
        rec = fractal.load_state(os.getcwd())["sois"]["alpha"]["recursion"]
        self.assertEqual(rec["E1"]["verdict"], "leaf")
        self.assertEqual(rec["E2"]["verdict"], "promote")

    def test_child_start_backfills_name(self):
        for ph in ["P0", "P1", "P2", "P3", "P4"]:
            self.run_cmd("gate-pass", "alpha", ph)
        self.run_cmd("register-child", "alpha", "E2", "--verdict", "promote")
        rc, _, _ = self.run_cmd("start", "--parent", "alpha", "--element", "E2")
        self.assertEqual(rc, 0)
        rec = fractal.load_state(os.getcwd())["sois"]["alpha"]["recursion"]
        self.assertEqual(rec["E2"]["child"], "alpha--E2")


class TestTree(TmpBase):
    def test_tree_marks_and_stuck(self):
        self.run_cmd("start", "alpha")
        self.run_cmd("gate-pass", "alpha", "P0")
        for ph in ["P0", "P1", "P2", "P3", "P4"]:
            self.run_cmd("gate-pass", "alpha", ph)
        self.run_cmd("register-child", "alpha", "E2", "--verdict", "promote")
        self.run_cmd("start", "--parent", "alpha", "--element", "E2")
        self.run_cmd("waive", "alpha--E2", "P0", "--reason", "演示")
        rc, out, _ = self.run_cmd("tree")
        self.assertEqual(rc, 0)
        self.assertIn("alpha", out)
        self.assertIn("└──", out)
        self.assertIn("⚠", out)          # 弃权标记
        self.assertIn("✓", out)          # 过闸标记
        self.assertIn("卡点", out)        # 下一步动作
        self.assertIn("alpha--E2 → /fractal-next 进 P1", out)


class TestCheckWrite(TmpBase):
    def setUp(self):
        super().setUp()
        self.run_cmd("start", "alpha")

    def check(self, path):
        return self.run_cmd("check-write", "--path", path)

    def test_non_se_path_allowed(self):
        self.assertEqual(self.check("src/main.py")[0], 0)

    def test_state_and_overview_allowed(self):
        self.assertEqual(self.check("docs/SE/fractal-state.json")[0], 0)
        self.assertEqual(self.check("docs/SE/00-overview.md")[0], 0)

    def test_non_phase_doc_allowed(self):
        self.assertEqual(self.check("docs/SE/alpha/notes.md")[0], 0)

    def test_rule1_phase_gate(self):
        rc, out, _ = self.check("docs/SE/alpha/P1-stakeholders.md")  # P0 未过
        self.assertEqual(rc, 2)
        self.assertIn("规则1", out)
        self.assertIn("宁停勿跳", out)
        self.run_cmd("gate-pass", "alpha", "P0")
        self.assertEqual(self.check("docs/SE/alpha/P1-stakeholders.md")[0], 0)

    def test_rule1_after_waive(self):
        self.run_cmd("waive", "alpha", "P0", "--reason", "r")
        self.assertEqual(self.check("docs/SE/alpha/P1-stakeholders.md")[0], 0)

    def test_rule1_prevents_far_jump(self):
        for ph in ["P0", "P1"]:
            self.run_cmd("gate-pass", "alpha", ph)
        rc, out, _ = self.check("docs/SE/alpha/P4-architecture.md")  # P2 未过
        self.assertEqual(rc, 2)

    def test_rule2_recursion_gate(self):
        for ph in ["P0", "P1", "P2", "P3", "P4"]:
            self.run_cmd("gate-pass", "alpha", ph)
        rc, out, _ = self.check("docs/SE/alpha/P5-detail.md")
        self.assertEqual(rc, 2)
        self.assertIn("规则2", out)
        self.run_cmd("register-child", "alpha", "E1", "--verdict", "leaf")
        self.assertEqual(self.check("docs/SE/alpha/P5-detail.md")[0], 0)

    def test_rule2_allows_early_phases_without_recursion(self):
        self.assertEqual(self.check("docs/SE/alpha/P0-problem.md")[0], 0)

    def test_rule3_orphan_dir(self):
        rc, out, _ = self.check("docs/SE/ghost/P0-problem.md")
        self.assertEqual(rc, 2)
        self.assertIn("规则3", out)

    def test_no_state_allows(self):
        os.remove("docs/SE/fractal-state.json")
        self.assertEqual(self.check("docs/SE/alpha/P8-validation.md")[0], 0)


class TestHookPreToolWrite(TmpBase):
    def hook(self, payload):
        import subprocess
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "fractal.py")
        return subprocess.run(
            [sys.executable, script, "hook-pretoolwrite"],
            input=payload, capture_output=True, text=True, cwd=os.getcwd(),
        )

    def test_block_decision_json(self):
        self.run_cmd("start", "alpha")
        td = os.getcwd()
        r = self.hook(json.dumps({"tool_input": {"file_path": os.path.join(td, "docs/SE/alpha/P3-logical.md")}}))
        self.assertEqual(r.returncode, 0)  # hook 永不非零退出（fail-open）
        data = json.loads(r.stdout)
        self.assertEqual(data["decision"], "block")
        self.assertIn("规则1", data["reason"])

    def test_outside_project_allowed(self):
        self.run_cmd("start", "alpha")
        r = self.hook(json.dumps({"tool_input": {"file_path": "/tmp/other/P0-problem.md"}}))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_malformed_stdin_allowed(self):
        self.run_cmd("start", "alpha")
        r = self.hook("not-json")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")


class TestReconcile(TmpBase):
    def test_clean_ok(self):
        self.run_cmd("start", "alpha")
        rc, out, _ = self.run_cmd("reconcile")
        self.assertEqual(rc, 0)
        self.assertIn("一致", out)

    def test_reports_passed_but_doc_missing(self):
        self.run_cmd("start", "alpha")
        self.run_cmd("gate-pass", "alpha", "P0")
        rc, out, _ = self.run_cmd("reconcile")
        self.assertIn("文档缺失", out)

    def test_reports_unregistered_dir(self):
        self.run_cmd("start", "alpha")
        os.makedirs("docs/SE/ghost", exist_ok=True)
        rc, out, _ = self.run_cmd("reconcile")
        self.assertIn("ghost", out)
        self.assertIn("未在 state 登记", out)

    def test_rebuild_from_docs(self):
        self.run_cmd("start", "alpha")
        os.makedirs("docs/SE/beta", exist_ok=True)
        with open("docs/SE/beta/P0-problem.md", "w", encoding="utf-8") as f:
            f.write("# P0\n\n## Exit Gate 自查\n\n- [x] 谁遇到问题\n- [x] 后果\n")
        with open("docs/SE/beta/P1-stakeholders.md", "w", encoding="utf-8") as f:
            f.write("# P1\n\n## Exit Gate 自查\n\n- [x] A\n- [ ] B\n")
        os.remove("docs/SE/fractal-state.json")
        rc, out, _ = self.run_cmd("reconcile")
        self.assertIn("重建", out)
        st = fractal.load_state(os.getcwd())["sois"]["beta"]["phases"]
        self.assertEqual(st["P0"]["status"], "passed")
        self.assertEqual(st["P1"]["status"], "in-progress")

    def test_rebuild_infers_recursion_and_parent(self):
        self.run_cmd("start", "alpha")
        os.makedirs("docs/SE/alpha--E2", exist_ok=True)
        with open("docs/SE/alpha--E2/P4-architecture.md", "w", encoding="utf-8") as f:
            f.write("| 元素 | 判定 | 依据 | 去向 |\n|---|---|---|---|\n| E2 | 提升SoI | ③ | 子目录 |\n")
        os.remove("docs/SE/fractal-state.json")
        self.run_cmd("reconcile")
        st = fractal.load_state(os.getcwd())["sois"]
        self.assertEqual(st["alpha--E2"]["parent"], "alpha")
        self.assertEqual(st["alpha--E2"]["recursion"]["E2"]["verdict"], "promote")

    def test_reports_v01_flat_layout(self):
        os.makedirs("docs/SE", exist_ok=True)
        with open("docs/SE/P0-problem.md", "w", encoding="utf-8") as f:
            f.write("# 旧世界\n\n## Exit Gate 自查\n\n- [x] x\n")
        rc, out, _ = self.run_cmd("reconcile")
        self.assertIn("v0.1", out)

    def test_unknown_status_blocks_gate_progression(self):
        """重建出的 unknown 不算过闸——闸门 fail-closed。"""
        self.run_cmd("start", "alpha")
        os.makedirs("docs/SE/beta", exist_ok=True)
        with open("docs/SE/beta/P0-problem.md", "w", encoding="utf-8") as f:
            f.write("# P0（无 checklist）\n")
        os.remove("docs/SE/fractal-state.json")
        self.run_cmd("reconcile")
        rc, _, err = self.run_cmd("gate-pass", "beta", "P1")
        self.assertEqual(rc, 1)  # P0 是 unknown，不能过 P1 闸


class TestGap(TmpBase):
    def _p7(self, soi, body):
        os.makedirs(f"docs/SE/{soi}", exist_ok=True)
        with open(f"docs/SE/{soi}/P7-verification.md", "w", encoding="utf-8") as f:
            f.write(body)

    def test_gap_summarizes(self):
        self.run_cmd("start", "alpha")
        self._p7("alpha", (
            "# P7\n\n| REQ | 方法 | 判据 | 证据 | 状态 |\n|---|---|---|---|---|\n"
            "| REQ-A1 | Test | t1 | e1 | PASS |\n"
            "| REQ-A2 | Test | t2 | e2 | FAIL |\n"
            "| REQ-A3 | Analysis | t3 | e3 | BLOCKED |\n"
        ))
        rc, out, _ = self.run_cmd("gap")
        self.assertEqual(rc, 0)
        self.assertIn("FAIL", out)
        self.assertIn("REQ-A2(alpha)", out)
        self.assertIn("差距驱动", out)

    def test_gap_degrades_on_bad_format(self):
        self.run_cmd("start", "alpha")
        self._p7("alpha", "# P7\n\n全部通过，无问题。\n")
        rc, out, _ = self.run_cmd("gap")
        self.assertEqual(rc, 0)
        self.assertIn("无法解析", out)

    def test_gap_empty(self):
        self.run_cmd("start", "alpha")
        rc, out, _ = self.run_cmd("gap")
        self.assertIn("没有", out)


class TestHookSessionStart(TmpBase):
    def session(self):
        import subprocess
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "fractal.py")
        return subprocess.run(
            [sys.executable, script, "hook-sessionstart"],
            capture_output=True, text=True, cwd=os.getcwd(),
        )

    def test_uninitialized_one_liner(self):
        r = self.session()
        self.assertEqual(r.returncode, 0)
        self.assertIn("就绪", r.stdout)
        self.assertIn("fractal.py", r.stdout)  # 给出脚本绝对路径
        self.assertEqual(len(r.stdout.strip().splitlines()), 1)

    def test_initialized_compact_tree(self):
        self.run_cmd("start", "alpha")
        self.run_cmd("gate-pass", "alpha", "P0")
        r = self.session()
        self.assertEqual(r.returncode, 0)
        self.assertIn("【fractal】", r.stdout)
        self.assertIn("P1", r.stdout)              # 当前阶段
        self.assertIn("No Orphan", r.stdout)       # P1 对应纪律 Rule 2（PHASE_DISCIPLINE）
        self.assertLessEqual(len(r.stdout.strip().splitlines()), 15)

    def test_v01_layout_hint(self):
        os.makedirs("docs/SE", exist_ok=True)
        open("docs/SE/P0-problem.md", "w").close()
        r = self.session()
        self.assertIn("reconcile", r.stdout)


class TestRobustness(TmpBase):
    def test_invalid_json_state_clis_error_not_crash(self):
        self.run_cmd("start", "alpha")
        with open("docs/SE/fractal-state.json", "w", encoding="utf-8") as f:
            f.write("{not valid json")
        rc, _, err = self.run_cmd("status")
        self.assertEqual(rc, 1)
        self.assertIn("reconcile", err)
        rc2, _, err2 = self.run_cmd("check-write", "--path", "docs/SE/alpha/P1-stakeholders.md")
        self.assertEqual(rc2, 1)
        self.assertIn("reconcile", err2)

    def test_structurally_invalid_state_reconcile_selfheals(self):
        self.run_cmd("start", "alpha")
        with open("docs/SE/fractal-state.json", "w", encoding="utf-8") as f:
            f.write('{"foo": 1}')
        rc, out, _ = self.run_cmd("reconcile")
        self.assertEqual(rc, 0)
        self.assertIn("重建", out)
        st = fractal.load_state(os.getcwd())
        self.assertIn("alpha", st["sois"])

    def test_non_utf8_doc_does_not_crash(self):
        self.run_cmd("start", "alpha")
        os.makedirs("docs/SE/beta", exist_ok=True)
        with open("docs/SE/beta/P0-problem.md", "wb") as f:
            f.write(b"# \xff\xfe binary\n\n## Exit Gate\n\n- [x] x\n")
        os.remove("docs/SE/fractal-state.json")  # 强制走重建路径，真正读取二进制文档
        rc, out, _ = self.run_cmd("reconcile")
        self.assertEqual(rc, 0)
        st = fractal.load_state(os.getcwd())
        self.assertEqual(st["sois"]["beta"]["phases"]["P0"]["status"], "passed")  # errors=replace 下仍可推断

    def test_check_write_absolute_path_normalized(self):
        self.run_cmd("start", "alpha")
        td = os.getcwd()
        rc, out, _ = self.run_cmd("check-write", "--path", os.path.join(td, "docs/SE/alpha/P1-stakeholders.md"))
        self.assertEqual(rc, 2)  # 绝对路径与相对路径语义一致

    def test_reserved_soi_names_rejected(self):
        self.run_cmd("start", "alpha")
        for bad in ["fractal-state.json", "00-overview.md", "..", ".hidden"]:
            rc, _, err = self.run_cmd("start", bad)
            self.assertEqual(rc, 1, bad)
            self.assertIn("不合法", err)

    def test_sessionstart_truncates_many_sois(self):
        import subprocess
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "fractal.py")
        for i in range(12):
            self.run_cmd("start", f"s{i:02d}")
        r = subprocess.run([sys.executable, script, "hook-sessionstart"],
                           capture_output=True, text=True, cwd=os.getcwd())
        self.assertEqual(r.returncode, 0)
        lines = r.stdout.strip().splitlines()
        self.assertLessEqual(len(lines), 15)
        self.assertTrue(any("…" in l or "/fractal-tree" in l for l in lines))
