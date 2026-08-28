# -*- coding: utf-8 -*-
"""
Init → writing-support contract tests.

Guarantees the "Stage 0 初始化 → 资料支撑" chain:
  * init must NOT create clutter (.gitkeep in a gitignored workspace,
    per-book template copies under 02_characters/templates/);
  * pack must actually LOAD the Stage-0 support assets (story bible,
    world settings, volume outline) that init generates — the writing
    loop must see the settings, not just the lint tools.
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "tools"))

from init_new_novel import init_novel  # noqa: E402
from package_context import package_context_for_chapter  # noqa: E402


class InitSupportChainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="init_support_"))
        self.ws = self.tmp / "ws"
        self.assertTrue(init_novel(title="资料链测试", genre="悬疑", protagonist="林默",
                                   workspace_path=str(self.ws)))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_init_does_not_create_clutter(self):
        gitkeeps = list(self.ws.rglob(".gitkeep"))
        self.assertEqual(gitkeeps, [],
                         msg=f"gitignored 工作区不应生成 .gitkeep: {gitkeeps}")
        self.assertFalse((self.ws / "02_characters" / "templates").exists(),
                         msg="书内不应再复制人物卡模板（唯一母版在仓库 templates/）")

    def test_pack_loads_stage0_support_assets(self):
        pkg = package_context_for_chapter("ch_001", workspace_path=str(self.ws),
                                          as_json=True, print_output=False)
        self.assertTrue(pkg.get("story_bible", "").strip(),
                        msg="pack 必须装载项目圣经（Stage 0 资料支撑）")
        self.assertIn("世界规则", pkg.get("world_settings", ""),
                      msg="pack 必须装载 world_rules（世界观设定）")
        self.assertIn("全书主线", pkg.get("volume_outline", ""),
                      msg="pack 必须装载 main_plot（主线与卷纲）")

    def test_budget_keeps_bible_drops_outline_last(self):
        """Tiny budget: bible stays whole; big trimmable blocks may be dropped
        but must be reported in budget_report instead of vanishing silently."""
        pkg = package_context_for_chapter("ch_001", workspace_path=str(self.ws),
                                          as_json=True, print_output=False, budget=600)
        self.assertTrue(pkg.get("story_bible", "").strip(),
                        msg="项目圣经是不可裁核心，小预算也必须整块保留")
        sections = {s["section"]: s for s in pkg["budget_report"]["sections"]}
        for key in ("world_settings", "volume_outline"):
            self.assertIn(key, sections, msg=f"{key} 必须出现在预算报告中")
            self.assertTrue(pkg.get(key, "") or sections[key]["dropped_tokens"] > 0,
                            msg=f"{key} 被裁时必须如实记录")


if __name__ == "__main__":
    unittest.main()
