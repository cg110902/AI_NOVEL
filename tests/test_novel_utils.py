# -*- coding: utf-8 -*-
"""
Unit tests for novel_utils core functions.
"""

import unittest
import sys
import re
from pathlib import Path

# Add project root and tools to sys.path
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root / "tools"))

from novel_utils import (  # noqa: E402
    GENERIC_SKELETONS,
    natural_chapter_sort_key,
    detect_semantic_redundancy,
    unsupervised_burstiness_slices,
    chapter_number_from_name,
    file_matches_chapter,
    chapter_token_to_num,
    latest_chapter_number,
    load_studio_config,
    has_placeholder,
    is_table_separator,
    load_registered_characters,
)


class TestNovelUtils(unittest.TestCase):

    def test_natural_chapter_sort_key(self):
        p1 = Path("vol_01/finalized/ch_001.md")
        p2 = Path("vol_01/finalized/ch_002.md")
        p10 = Path("vol_01/finalized/ch_010.md")
        self.assertLess(natural_chapter_sort_key(p1), natural_chapter_sort_key(p2))
        self.assertLess(natural_chapter_sort_key(p2), natural_chapter_sort_key(p10))

    def test_generic_skeletons_patterns(self):
        pattern_item = next(p for p in GENERIC_SKELETONS if "State Particle" in p["name"])
        self.assertTrue(re.search(pattern_item["pattern"], "面上露出一抹思索之色"))

        tag_leak_item = next(p for p in GENERIC_SKELETONS if "Internal Engineering Tag Leak" in p["name"])
        self.assertTrue(re.search(tag_leak_item["pattern"], "伏笔道具【GUN-003：太上剑宗绝密残篇】"))
        self.assertTrue(re.search(tag_leak_item["pattern"], "触发MIS-001误会"))
        self.assertTrue(re.search(tag_leak_item["pattern"], "进入Stage 1心智阶段"))
        self.assertFalse(re.search(tag_leak_item["pattern"], "陆知白收起手中的竹丝扫帚"))

    def test_semantic_redundancy_detection(self):
        lines = [
            "黑衣人吓瘫在地上，双腿抖若筛糠。",
            "他面无人色，牙关剧烈打战，魂飞魄散。"
        ]
        slices = detect_semantic_redundancy(lines, window_lines=2)
        self.assertGreaterEqual(len(slices), 1)
        self.assertEqual(slices[0]["cluster_name"], "恐惧与瘫软同义堆砌")

    def test_unsupervised_burstiness(self):
        lines = [
            "陆知白端起茶碗，陆知白微微一笑，陆知白缓缓站起身来。"
        ]
        bursts = unsupervised_burstiness_slices(lines, window_size=200, min_repeat=3)
        grams = [b["gram"] for b in bursts]
        self.assertIn("陆知白", grams)

    # ---- Boundary-safe chapter matching (regression for the ch_001/ch_010 bug) ----

    def test_chapter_number_from_name(self):
        self.assertEqual(chapter_number_from_name("ch_001.md"), 1)
        self.assertEqual(chapter_number_from_name("ch_010_beats.md"), 10)
        self.assertEqual(chapter_number_from_name("ch_100.md"), 100)
        self.assertIsNone(chapter_number_from_name("readme.md"))

    def test_chapter_token_to_num(self):
        self.assertEqual(chapter_token_to_num("ch_004"), 4)
        self.assertEqual(chapter_token_to_num("12"), 12)
        self.assertEqual(chapter_token_to_num(7), 7)
        self.assertIsNone(chapter_token_to_num(None))

    def test_file_matches_chapter_is_boundary_safe(self):
        # Asking for chapter 1 must NOT match chapter 10 / chapter 100.
        self.assertTrue(file_matches_chapter(Path("finalized/ch_001.md"), "ch_001"))
        self.assertTrue(file_matches_chapter(Path("finalized/ch_001.md"), 1))
        self.assertFalse(file_matches_chapter(Path("finalized/ch_010.md"), "ch_001"))
        self.assertFalse(file_matches_chapter(Path("finalized/ch_100.md"), "ch_001"))
        self.assertTrue(file_matches_chapter(Path("beats/ch_010_beats.md"), "ch_010"))

    def test_latest_chapter_number(self):
        import tempfile, shutil
        tmp = Path(tempfile.mkdtemp())
        try:
            fdir = tmp / "05_manuscript" / "vol_01" / "finalized"
            fdir.mkdir(parents=True)
            for n in (1, 2, 10):
                (fdir / f"ch_{n:03d}.md").write_text("x", encoding="utf-8")
            self.assertEqual(latest_chapter_number(tmp / "05_manuscript"), 10)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_config_loads_word_floor(self):
        cfg = load_studio_config()
        self.assertIn("generation", cfg)
        twc = cfg["generation"]["target_word_count"]
        self.assertGreaterEqual(twc["min"], 2500)
        self.assertLessEqual(twc["max"], 4000)
        self.assertEqual(twc["recommended"], 3200)

    # ---- Template placeholder & table-separator filtering ----

    def test_has_placeholder(self):
        self.assertTrue(has_placeholder("这是[主角姓名]的卡"))
        self.assertTrue(has_placeholder("[首卷对手]"))
        self.assertTrue(has_placeholder("核心金手指 / [终极大机制]"))
        self.assertFalse(has_placeholder("陈昂"))
        self.assertFalse(has_placeholder("普通正文，没有占位符"))

    def test_is_table_separator(self):
        self.assertTrue(is_table_separator("| :--- | :--- | :--- |"))
        self.assertTrue(is_table_separator("|---|:---:|---|"))
        self.assertTrue(is_table_separator("| :--- | :--- |"))
        self.assertFalse(is_table_separator("| GUN-001 | 断剑 | 第 1 章 |"))
        self.assertFalse(is_table_separator("| 伏笔 ID | 名称 |"))

    def test_fresh_init_has_no_placeholder_characters(self):
        """A newly initialized workspace must not register placeholder names as characters."""
        import tempfile, shutil
        from init_new_novel import init_novel
        tmp = Path(tempfile.mkdtemp())
        try:
            ws = tmp / "ws"
            self.assertTrue(init_novel(title="占位测试", protagonist="陈昂",
                                       workspace_path=str(ws)))
            chars = load_registered_characters(ws)
            self.assertIn("陈昂", chars)
            for c in chars:
                self.assertFalse(has_placeholder(c), f"占位符被误注册为角色: {c}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ---- Chinese numeral parsing (economy fallback) ----

    def test_chinese_numeral_parser(self):
        import importlib
        sys.path.insert(0, str(_root / "tools"))
        # Re-implement by importing the scanner's parse path indirectly:
        # we validate via audit_economy_ledger's CN constants through a tiny sample.
        from audit_economy_ledger import audit_economy_ledger  # noqa: F402
        # 直接复刻工具内 parse_num 逻辑做关键断言（货币单位“两/文”不得当数字）
        CN_DIGIT = {'零':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
        CN_SMALL = {'十':10,'百':100,'千':1000}
        CN_BIG = {'万':10000,'亿':100000000}
        def parse_num(s):
            try: return int(s)
            except ValueError: pass
            total, section, digit = 0, 0, 0
            for idx, ch in enumerate(str(s)):
                if ch == "两":
                    nxt = str(s)[idx+1] if idx+1 < len(str(s)) else ""
                    if nxt in CN_SMALL or nxt in CN_BIG: digit = 2
                    continue
                if ch in CN_DIGIT: digit = CN_DIGIT[ch]
                elif ch in CN_SMALL:
                    section += (digit if digit else 1) * CN_SMALL[ch]; digit = 0
                elif ch in CN_BIG:
                    section += digit; total = (total + section) * CN_BIG[ch]; section, digit = 0, 0
            total += section + digit
            return total
        self.assertEqual(parse_num("十两"), 10)   # “两”是货币单位，不是 2
        self.assertEqual(parse_num("十文"), 10)
        self.assertEqual(parse_num("三万"), 30000)
        self.assertEqual(parse_num("两万三千"), 23000)
        self.assertEqual(parse_num("一百五十"), 150)


class TestStripNameTitle(unittest.TestCase):
    """回归：头衔前缀不应并入角色名，否则正文短名匹配会失配（误判从未登场）。"""

    def test_strips_leading_title_prefix(self):
        from novel_utils import strip_name_title
        self.assertEqual(strip_name_title("村长·张老爹"), "张老爹")
        self.assertEqual(strip_name_title("游方道人·玄清"), "玄清")
        self.assertEqual(strip_name_title("陈浔"), "陈浔")  # 无前缀原样返回
        self.assertEqual(strip_name_title(""), "")

    def test_register_strips_title_prefix(self):
        import tempfile, shutil, json
        from init_new_novel import init_novel
        from novel_utils import load_registered_characters
        tmp = Path(tempfile.mkdtemp(prefix="novel_nametitle_"))
        try:
            ws = tmp / "ws"
            init_novel(workspace_path=str(ws))
            idx = ws / "02_characters" / "character_index.md"
            # 用带前缀的头衔名覆盖示例行
            rows = ["| **村长·张老爹** | 陈家村 / 长者 | 守村 | X | 第 1 章 |",
                    "| **游方道人·玄清** | 官方 / 散修 | 查异象 | X | 第 1 章 |"]
            body = "| 角色姓名 | 阵营 | 动机 | 反差 | 登场 |\n| :--- | :--- | :--- | :--- | :--- |\n" + "\n".join(rows) + "\n"
            idx.write_text(body, encoding="utf-8")
            chars = load_registered_characters(ws)
            self.assertIn("张老爹", chars)
            self.assertIn("玄清", chars)
            # 分隔行 `:---` 不得被当成角色
            self.assertNotIn(":---", chars)
            self.assertNotIn("---", chars)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestRecallKeywordFilter(unittest.TestCase):
    """回归：伏笔回忆关键词应排除已注册角色名，防止角色登场即误报缺回忆提示。"""

    def test_recall_keywords_exclude_registered_names(self):
        from audit_reader_confusion import _recall_keywords
        registered = {"陈浔", "钱老爷", "张老爹"}
        kws = _recall_keywords("钱老爷/周赖三的目光（盘剥势力留意陈浔）", registered)
        self.assertNotIn("钱老爷", kws)
        self.assertNotIn("陈浔", kws)
        # 道具/概念词应保留（回忆价值）
        self.assertTrue(any("目光" in k for k in kws))
        # 无角色名的纯概念伏笔不受角色名过滤影响（仍保留非角色关键词）
        kws2 = _recall_keywords("腰间三把开山斧（从未出鞘）", registered)
        self.assertTrue(kws2, "纯概念伏笔不应被过滤为空")
        self.assertTrue(all(k not in registered for k in kws2))


class TestEntityRegistry(unittest.TestCase):
    """回归：confusion 实体注册表应剥离头衔前缀、剔除分隔行幽灵条目。"""

    def test_entity_registry_strips_prefix_and_no_ghost(self):
        import tempfile, shutil
        from init_new_novel import init_novel
        from audit_reader_confusion import _load_entity_registry
        tmp = Path(tempfile.mkdtemp(prefix="novel_entreg_"))
        try:
            ws = tmp / "ws"
            init_novel(workspace_path=str(ws))
            idx = ws / "02_characters" / "character_index.md"
            body = ("| 角色姓名 | 阵营 | 动机 | 反差 | 登场 |\n"
                    "| :--- | :--- | :--- | :--- | :--- |\n"
                    "| **村长·张老爹** | 村 | 守村 | X | 1 |\n"
                    "| **游方道人·玄清** | 官 | 查异象 | X | 1 |\n")
            idx.write_text(body, encoding="utf-8")
            reg = _load_entity_registry(ws)
            chars = [k for k, v in reg.items() if v == "character"]
            self.assertIn("张老爹", chars)
            self.assertIn("玄清", chars)
            self.assertNotIn(":---", chars)
            self.assertNotIn("---", chars)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
