# -*- coding: utf-8 -*-
"""
Smoke tests for the `studio.py hello` AI orientation command.

hello is the entry ritual for agents landing in this repo: it must
(1) degrade gracefully (exit 0) when no workspace exists, and
(2) report live project facts + reading prices when one does.
"""

import sys
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root / "tools"))

from init_new_novel import init_novel  # noqa: E402


class TestHelloCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="novel_hello_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _hello(self, *args):
        return subprocess.run(
            [sys.executable, str(_root / "studio.py"), "hello", *args],
            capture_output=True, text=True, encoding="utf-8", errors="ignore",
        )

    def test_hello_without_workspace_is_graceful(self):
        """No workspace yet → hello still exits 0 and points to `init` (Stage 0)."""
        r = self._hello("-w", str(self.tmp / "nonexistent"))
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("入口导览", r.stdout)
        self.assertIn("init", r.stdout)
        self.assertIn("禁读区", r.stdout)

    def test_hello_with_workspace_reports_facts_and_prices(self):
        """With an initialized workspace → hello reports the book and token prices."""
        ws = self.tmp / "ws"
        self.assertTrue(init_novel(title="导览测试", genre="悬疑", protagonist="林默",
                                   workspace_path=str(ws)))
        r = self._hello("-w", str(ws))
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("导览测试", r.stdout)
        self.assertIn("下一步", r.stdout)
        self.assertIn("tok", r.stdout)  # 阅读价目表存在
        # JSON 模式：可机读，包含阅读清单与禁读区
        rj = self._hello("-w", str(ws), "--json")
        self.assertEqual(rj.returncode, 0, msg=rj.stderr)
        import json
        data = json.loads(rj.stdout)
        self.assertIn("reading_list", data)
        self.assertIn("forbidden_zone", data)
        self.assertGreater(data["forbidden_zone"]["total_tokens"], 0)
        self.assertTrue(any(x["path"] == "AGENTS.md" for x in data["reading_list"]))


if __name__ == "__main__":
    unittest.main()
