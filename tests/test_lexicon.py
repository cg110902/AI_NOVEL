# -*- coding: utf-8 -*-
"""
Lexicon 测试：泛化类别词表中心 + 逐书成长回路 + 无监督候选发现。

覆盖：注册表完整性 / 三层合并（种子+题材+成长−豁免）/ 校验（含模板 "_" 键忽略）/
候选发现（未登记词可被捞出，已知词不误报）/ 骤变检测吃到成长词 / init 播种 / CLI 退出码。
"""

import sys
import json
import shutil
import tempfile
import unittest
import subprocess
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root / "tools"))

import lexicon_core as LC  # noqa: E402
from novel_utils import (  # noqa: E402
    find_lexicon_candidates, get_tics, get_semantic_clusters,
)
from init_new_novel import init_novel  # noqa: E402


class LexiconCoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="lex_core_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _ws(self, name, payload=None):
        ws = self.tmp / name
        (ws / "00_meta").mkdir(parents=True, exist_ok=True)
        if payload is not None:
            (ws / "00_meta" / "lexicon.json").write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return ws

    def test_registry_complete(self):
        """11 类类别卡全部有种子与判据（判据是规则本体，必须有）。"""
        ids = LC.category_ids()
        self.assertIn("sudden_shift", ids)
        self.assertIn("ai_tics", ids)
        self.assertIn("gun_hint_signals", ids)
        for cid in ids:
            meta = LC.category_meta(cid)
            self.assertTrue(meta["seeds"], f"{cid} 无种子")
            self.assertGreater(len(meta["definition"]), 20, f"{cid} 判据过短")
            self.assertIn(meta["kind"], ("density", "hint"))

    def test_effective_merge_and_exemption(self):
        """grown 追加（dict 与纯字符串两种形态）、exemptions 移除、聚类成长生效。"""
        ws = self._ws("ws", {
            "schema": "novel-studio.lexicon/v1",
            "categories": {
                "sudden_shift": {
                    "grown": [{"term": "蓦地", "by": "ai", "ch": 3}, "猝然"],
                    "exemptions": [{"term": "陡然"}],
                }
            },
            "semantic_clusters": {"恐惧与瘫软同义堆砌": {"grown": ["魂不附体"], "exemptions": []}},
        })
        eff = LC.effective_terms("sudden_shift", ws)
        self.assertIn("蓦地", eff)
        self.assertIn("猝然", eff)   # 纯字符串条目 → by=author
        self.assertNotIn("陡然", eff)  # 豁免退出检测
        self.assertIn("突然", eff)    # 种子保留
        prov = LC.provenance_map("sudden_shift", ws)
        self.assertEqual(prov["蓦地"], "成长·ai·ch3")
        clusters = {c["cluster_name"]: c for c in get_semantic_clusters(ws)}
        self.assertIn("魂不附体", clusters["恐惧与瘫软同义堆砌"]["keywords"])

    def test_genre_extras_merged(self):
        """题材档案 extra_ticks 仍叠加进有效词表（保持兼容）。"""
        ws = self._ws("ws2")
        (ws / "00_meta" / "genre_profile.json").write_text(
            json.dumps({"extra_ticks": ["题材测试雷词"]}, ensure_ascii=False), encoding="utf-8")
        tics = get_tics(ws)
        self.assertIn("题材测试雷词", tics)
        self.assertIn("笑了笑", tics)

    def test_validate_reports_problems_and_ignores_readme_keys(self):
        """未知类别 id / 缺 term 字段报错；模板自带 "_" 示例键忽略。"""
        ws = self._ws("ws3", {"categories": {
            "badid": {"grown": []},
            "sudden_shift": {"grown": [{"no_term": 1}]},
        }})
        problems = LC.validate_lexicon(ws)
        self.assertTrue(any("未知类别" in p for p in problems))
        self.assertTrue(any("term" in p for p in problems))

        ws4 = self._ws("ws4")
        tpl = _root / "templates" / "00_meta" / "lexicon.template.json"
        (ws4 / "00_meta" / "lexicon.json").write_text(tpl.read_text(encoding="utf-8"), encoding="utf-8")
        self.assertFalse([p for p in LC.validate_lexicon(ws4) if p.startswith("❌")])

    def test_candidates_discovery(self):
        """漏报兜底：未登记词「蓦地」突发被捞为候选；已知词「突然」不误报。"""
        lines = [
            "他突然转身，警惕地看向门外。",
            "他蓦地回头，蓦地站起，蓦地拔剑，蓦地后撤，蓦地大喝。",
            "夜色沉静如水。",
        ]
        cands = find_lexicon_candidates(lines, workspace=self.tmp / "nonexistent")
        grams = [c["gram"] for c in cands]
        self.assertIn("蓦地", grams)
        self.assertNotIn("突然", grams)
        top = cands[0]
        self.assertEqual(top["count"], 5)
        self.assertTrue(top["context"])

    def test_sudden_detector_uses_growth(self):
        """audit_reader_confusion 的骤变密度检测消费成长词（端到端链路）。"""
        from audit_reader_confusion import detect_causal_gaps
        ws = self._ws("ws5", {"categories": {"sudden_shift": {"grown": ["噌地"]}}})
        text = "。".join(["他噌地跳开"] * 5)
        alerts = detect_causal_gaps(text, text.split("。"), ws)
        self.assertTrue(any(a.get("count") for a in alerts))

    def test_init_seeds_lexicon(self):
        """init 自动播种 00_meta/lexicon.json（成长文件随书诞生）。"""
        ws = self.tmp / "ws6"
        self.assertTrue(init_novel(title="词表播种", genre="武侠", protagonist="沈砚",
                                   workspace_path=str(ws)))
        lx = ws / "00_meta" / "lexicon.json"
        self.assertTrue(lx.exists())
        data = json.loads(lx.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "novel-studio.lexicon/v1")


class LexiconCLITest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="lex_cli_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _studio(self, *args):
        return subprocess.run(
            [sys.executable, str(_root / "studio.py"), "lexicon", *args],
            capture_output=True, text=True, encoding="utf-8", errors="ignore",
        )

    def test_list_check_init_exit_codes(self):
        r = self._studio("list", "-w", str(self.tmp))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("sudden_shift", r.stdout)
        self.assertIn("判据", r.stdout)

        # 未播种工作区：check 提示可 init，退出码 0（空置=回退种子，不是错误）
        self.assertEqual(self._studio("check", "-w", str(self.tmp)).returncode, 0)
        # init 播种 → 模板校验通过
        self.assertEqual(self._studio("init", "-w", str(self.tmp)).returncode, 0)
        self.assertEqual(self._studio("check", "-w", str(self.tmp)).returncode, 0)
        # 重复 init：幂等提示，不算错
        self.assertEqual(self._studio("init", "-w", str(self.tmp)).returncode, 0)

        # 坏文件（类别 id 手滑）→ check 退出码 1
        (self.tmp / "00_meta").mkdir(parents=True, exist_ok=True)
        (self.tmp / "00_meta" / "lexicon.json").write_text(
            '{"categories": {"typo_id": {}}}', encoding="utf-8")
        r5 = self._studio("check", "-w", str(self.tmp))
        self.assertEqual(r5.returncode, 1)
        self.assertIn("typo_id", r5.stdout)

    def test_single_category_listing(self):
        r = self._studio("list", "sudden_shift", "-w", str(self.tmp))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("蓦地" if False else "突然", r.stdout)
        self.assertIn("[种子]", r.stdout)
        r2 = self._studio("list", "no_such", "-w", str(self.tmp))
        self.assertEqual(r2.returncode, 2)
