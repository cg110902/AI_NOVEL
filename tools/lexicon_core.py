# -*- coding: utf-8 -*-
"""
Universal Novel Studio - Lexicon Core (lexicon_core.py)
词表类别中心：泛化类别的种子源 + 逐书成长回路。

设计动机（反「穷举固化」）：
  开放语义类（骤变副词/口癖/伤情词/交易动词…）成员无穷，枚举永远不全、且跨题材刚性。
  核心契约：**词表不是规则，是记忆**。
    - 判据（definition，自然语言）才是规则本身，供操作 LLM 与人消费；
    - 种子（seeds）只是召回锚点，供确定性 Python 消费，"表外≠合法，表内触发怀疑"；
    - 漏报由无监督候选发现兜底（novel_utils.find_lexicon_candidates）；
    - 每本书通过 00_meta/lexicon.json 长出自己的词表（grown 带出处，exemptions 豁免）。

封闭集合（伏枪状态、schema 字段）与准封闭类（量词、资源单位）**不归本模块管**——
枚举即正确，泛化它们才是过度工程。

加载与合并链（与 config_core 优先级一致）：
  内置种子  →  题材档案 extras（genre_profile.json 的 genre_key 字段）  →  工作区 lexicon.json

用法：
    from lexicon_core import effective_terms, category_ids
    words = effective_terms("sudden_shift", workspace_dir)

    python tools/lexicon_core.py --list            # 查看全部类别卡
    python tools/lexicon_core.py --list sudden_shift
    python tools/lexicon_core.py --check -w novel_workspace
"""

import sys
import json
import copy
import logging
import argparse
from pathlib import Path

logger = logging.getLogger("novel_studio.lexicon_core")

LEXICON_SCHEMA = "novel-studio.lexicon/v1"
LEXICON_FILENAME = "lexicon.json"  # 位于 <workspace>/00_meta/


# ---------------------------------------------------------------------------
# 内置类别卡注册表（Single Source of Truth）
# kind: "density" = 密度检测类（命中多才有罪，单个词无罪）
#       "hint"    = 线索召回类（命中=摘证据给 LLM 复核，命中≠问题）
# genre_key: 可选；题材档案里叠加该字段的 extras（沿用已有数据，不迁移不重复）
# ---------------------------------------------------------------------------
BUILTIN_CATEGORIES = {
    "sudden_shift": {
        "name": "骤变状语",
        "kind": "density",
        "genre_key": None,
        "definition": (
            "表示事件瞬间发生、毫无铺垫的状语/副词。判据：在句中可替换为「突然」且句意基本不变。"
            "检测目标是密度（惊讶感通胀=铺垫不足），单个词本身无罪；"
            "「突然想起」类回忆引导与蓄势后的爆发属合理用法。"
        ),
        "seeds": ["突然", "骤然", "忽然", "猛然", "陡然"],
    },
    "ai_tics": {
        "name": "AI腔口癖",
        "kind": "density",
        "genre_key": "extra_ticks",
        "definition": (
            "AI 生成文本中高频、信息量低、整句删掉后叙事无损的脸谱化表达。"
            "判据：删除后不损失任何情节信息/情绪增量，或可替换为更具体的动作、生理反应、环境细节。"
            "检测基线是本书文风指纹（quality_radar），密度显著高于本书基线才提示；"
            "符合角色既有声纹的口癖应登记豁免而非修改。"
        ),
        "seeds": ["笑了笑", "似笑非笑", "嘴角微勾", "嘴角上扬", "勾起一抹", "微微一笑",
                  "淡淡地说", "缓缓开口", "深吸一口气", "瞳孔骤缩", "眸", "勾起唇角", "戏谑",
                  "玩味", "不动声色", "意味深长", "不约而同", "空气仿佛凝固", "时间仿佛静止"],
    },
    "cliffhanger_signal": {
        "name": "断章钩子信号词",
        "kind": "density",
        "genre_key": "cliffhanger_keywords",
        "definition": (
            "章末段落中预示突变、悬念、迫近威胁的信号词。判据：读者读到会产生「接下来会怎样」的期待。"
            "它标记的是钩子「存在」而非罪名；章末缺失时才提醒补钩子；"
            "quiet_close 题材（治愈系等）章末安静收尾属合理，豁免强钩子要求。"
        ),
        "seeds": ["脚步声", "突如其来", "敲门声", "传讯", "杀气", "暗流", "异动", "死寂",
                  "冷笑", "破空声", "警钟", "急促", "变故", "暴涨", "入局", "急报",
                  "波澜", "落子", "风暴", "警报", "震动", "轰鸣", "碎裂", "崩塌",
                  "沉默", "对峙", "逼近", "降临", "觉醒", "逆转", "真相", "秘密"],
    },
    "oppressive_mood": {
        "name": "压抑氛围词",
        "kind": "density",
        "genre_key": None,
        "definition": (
            "渲染沉重、阴森、绝望氛围的形容词/短语。判据：直接「告诉」读者氛围压抑，而非「展示」成因。"
            "dark_preferred 题材（悬疑/恐怖/克苏鲁）整体豁免密度提醒；"
            "绝境/葬礼等场景的局部压抑属场景心流，不算问题。"
        ),
        "seeds": ["死寂", "阴冷", "森然", "逼仄", "沉郁", "如坠冰窟", "暗黑", "森冷",
                  "死气沉沉", "压抑", "窒息", "彻骨", "冰冷死寂", "绝望", "阴沉", "灰败"],
    },
    "income_verbs": {
        "name": "收入动词",
        "kind": "hint",
        "genre_key": None,
        "definition": (
            "表示账本主体获得可计量资源的动词。判据：宾语是资源（货币/点数/物资），"
            "且语句能回答「获得了多少」。用于 economy_ledger 流水预提取，命中≠问题。"
        ),
        "seeds": ["收到", "赚", "挣", "分润", "分得", "赏了", "赏赐", "起获", "搜出", "缴获",
                  "卖了", "卖出", "所得", "入账", "进账", "赔偿", "获得", "获了", "得到", "赢",
                  "奖励", "奖了", "赚到"],
    },
    "expense_verbs": {
        "name": "支出动词",
        "kind": "hint",
        "genre_key": None,
        "definition": (
            "表示账本主体失去可计量资源的动词。判据：宾语是资源，且语句能回答「花掉了多少」。"
            "用于 economy_ledger 流水预提取，命中≠问题。"
        ),
        "seeds": ["花了", "花费", "花钱", "买下", "购得", "买", "付了", "付出",
                  "赔了", "还债", "还了", "交了", "缴纳", "花去", "支出", "掏出"],
    },
    "injury_signals": {
        "name": "伤势信号词",
        "kind": "hint",
        "genre_key": None,
        "definition": (
            "提示角色身体受损的词。判据：指向具体身体损伤/机能衰退。"
            "用途是给同步官摘录伤势证据行（injury_clues），命中≠问题；"
            "角色专属伤势名词（如「寒毒」）由本书 lexicon 成长收录。"
        ),
        "seeds": ["伤", "血", "吐血", "骨折", "毒", "反噬", "虚脱", "剧痛", "负荷", "过载",
                  "撕裂", "包扎", "止血", "暗疾", "力竭", "脱力", "昏迷", "擦伤"],
    },
    "deal_signals": {
        "name": "交易协议信号词",
        "kind": "hint",
        "genre_key": None,
        "definition": (
            "提示角色间达成协议/承诺/结盟/担保的词。判据：构成对后续剧情有约束力的约定。"
            "用途是给同步官摘录协议证据行（deal_clues），命中≠问题。"
        ),
        "seeds": ["协议", "契约", "答应", "承诺", "分账", "做庄", "联手", "结盟",
                  "凭据", "凭证", "合同", "发誓", "保证", "担保", "授权"],
    },
    "action_hints": {
        "name": "推进动作信号词",
        "kind": "hint",
        "genre_key": None,
        "definition": (
            "提示句子属于「推进/动作」而非静态描写的信号词。判据：该句因这个动作/决定"
            "而让剧情向前走了一步。用于黄金配比门的粗分类统计，"
            "单句误分类影响 <1%，无需穷举；本书高频特色动作（如「推演」「注入灵力」）"
            "可成长收录以提高配比精度。"
        ),
        "seeds": ["冲", "抓", "夺", "砍", "刺", "踢", "打", "躲", "闪", "跑", "追", "逃",
                  "转身", "推开", "抓住", "出手", "击中", "倒下", "站起", "掏出", "塞",
                  "决定", "交易", "谈", "问", "说", "道", "喊", "答", "发现", "得知", "突破"],
    },
    "describe_hints": {
        "name": "静态描写信号词",
        "kind": "hint",
        "genre_key": None,
        "definition": (
            "提示句子属于「静态描写」（环境/景物/外貌）的信号词。判据：句子在定格画面"
            "而非推进事件。用于黄金配比门的粗分类统计；本书高频意象词"
            "（如「机甲」「阵法」「稻田」）可成长收录。"
        ),
        "seeds": ["天空", "阳光", "月光", "夜色", "街道", "建筑", "墙壁", "地面", "风", "雨",
                  "云", "树", "花", "草", "山", "河", "海", "光", "影", "颜色", "穿着", "面容",
                  "身材", "房间", "陈设", "空气", "温度", "声音", "气味", "灰尘", "锈迹", "废墟"],
    },
    "gun_hint_signals": {
        "name": "伏笔信号词",
        "kind": "hint",
        "genre_key": None,
        "definition": (
            "提示可能埋设新伏笔（秘密/身世/信物/异常…）的词。判据：指向尚未回收、"
            "值得后续兑现的信息。用途是候选召回（candidate_gun_clues），"
            "是否真是伏笔由同步官语义判断，命中≠问题。"
        ),
        "seeds": ["秘密", "身世", "谜团", "古怪", "诡异", "来历不明", "神秘", "暗藏",
                  "隐患", "伏笔", "不简单", "另有", "隐情", "信物", "钥匙", "地图", "账册", "账本"],
    },
}


# ---------------------------------------------------------------------------
# 工作区 lexicon.json 读取与解析（宽松解析 + 优雅降级，模式对齐 genre_profile）
# ---------------------------------------------------------------------------
def lexicon_path(workspace) -> Path:
    ws = Path(workspace) if workspace else None
    return (ws / "00_meta" / LEXICON_FILENAME) if ws else Path(LEXICON_FILENAME)


def load_workspace_lexicon(workspace) -> dict:
    """加载 <workspace>/00_meta/lexicon.json。不存在或损坏返回 {}（绝不抛异常阻断检测）。"""
    p = lexicon_path(workspace)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("词表成长文件损坏，已忽略并回退内置种子: %s (%s)", p, e)
        return {}
    if not isinstance(data, dict):
        logger.warning("词表成长文件顶层不是对象，已忽略: %s", p)
        return {}
    return data


def _parse_entries(raw) -> list:
    """grown/exemptions 条目宽松解析：'词' 或 {'term': '词', ...} → 统一为 dict(term, by, ch, note)。"""
    out = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if isinstance(item, str):
            t = item.strip()
            if t:
                out.append({"term": t, "by": "author"})
        elif isinstance(item, dict):
            t = str(item.get("term", "")).strip()
            if t:
                out.append({
                    "term": t,
                    "by": str(item.get("by", "ai")),
                    "ch": item.get("ch"),
                    "note": item.get("note"),
                })
    return out


def _category_config(category_id: str, workspace):
    lex = load_workspace_lexicon(workspace)
    cats = lex.get("categories") or {}
    cfg = cats.get(category_id) or {}
    if not isinstance(cfg, dict):
        return {}, {}
    return _parse_entries(cfg.get("grown")), _parse_entries(cfg.get("exemptions"))


def cluster_growth(workspace) -> dict:
    """语义聚类的成长配置：{cluster_name: {"grown": [...], "exemptions": [...]}}。"""
    lex = load_workspace_lexicon(workspace)
    raw = lex.get("semantic_clusters") or {}
    out = {}
    if isinstance(raw, dict):
        for name, cfg in raw.items():
            cfg = cfg if isinstance(cfg, dict) else {}
            out[name] = {
                "grown": [e["term"] for e in _parse_entries(cfg.get("grown"))],
                "exemptions": [e["term"] for e in _parse_entries(cfg.get("exemptions"))],
            }
    return out


# ---------------------------------------------------------------------------
# 合成：种子 + 题材 extras + 本书成长 − 豁免
# ---------------------------------------------------------------------------
def _genre_extras(category_id: str, workspace) -> list:
    meta = BUILTIN_CATEGORIES[category_id]
    key = meta.get("genre_key")
    if not key:
        return []
    try:
        from genre_profile import resolve_genre_profile  # 惰性导入避免环
        prof = resolve_genre_profile(workspace)
    except Exception:
        logger.debug("题材档案解析失败，跳过题材叠加", exc_info=True)
        return []
    extra = prof.get(key) or []
    return [e for e in extra if isinstance(e, str) and e.strip()]


def effective_terms(category_id: str, workspace=None) -> list:
    """返回某类别参与检测的最终词表（去重保序）。"""
    if category_id not in BUILTIN_CATEGORIES:
        raise KeyError(f"未知词表类别: {category_id}（可用: {', '.join(BUILTIN_CATEGORIES)}）")
    terms = list(BUILTIN_CATEGORIES[category_id]["seeds"])
    terms.extend(_genre_extras(category_id, workspace))
    grown, exempt = _category_config(category_id, workspace)
    terms.extend(e["term"] for e in grown)
    exempt_set = {e["term"] for e in exempt}
    return [t for t in dict.fromkeys(terms) if t not in exempt_set]


def provenance_map(category_id: str, workspace=None) -> dict:
    """term → 来源标签（供 `lexicon list` 展示与审计）。"""
    if category_id not in BUILTIN_CATEGORIES:
        raise KeyError(f"未知词表类别: {category_id}")
    meta = BUILTIN_CATEGORIES[category_id]
    prov = {t: "种子" for t in meta["seeds"]}
    for t in _genre_extras(category_id, workspace):
        prov.setdefault(t, "题材")
    grown, exempt = _category_config(category_id, workspace)
    for e in grown:
        prov[e["term"]] = f"成长·{e.get('by', '?')}" + (f"·ch{e.get('ch')}" if e.get("ch") else "")
    for e in exempt:
        prov[e["term"]] = "⚠️豁免"
    return prov


def all_known_terms(workspace=None) -> set:
    """全部类别的有效词并集 + 聚类关键词（供候选发现过滤「已知词」）。"""
    known = set()
    for cid in BUILTIN_CATEGORIES:
        try:
            known.update(effective_terms(cid, workspace))
        except Exception:
            continue
    return known


def seeds_of(category_id: str) -> list:
    """返回某类别的内置种子（浅拷贝）。供旧常量做向后兼容别名。"""
    if category_id not in BUILTIN_CATEGORIES:
        raise KeyError(f"未知词表类别: {category_id}")
    return list(BUILTIN_CATEGORIES[category_id]["seeds"])


def category_ids() -> list:
    return list(BUILTIN_CATEGORIES)


def category_meta(category_id: str) -> dict:
    if category_id not in BUILTIN_CATEGORIES:
        raise KeyError(f"未知词表类别: {category_id}")
    m = copy.deepcopy(BUILTIN_CATEGORIES[category_id])
    m["id"] = category_id
    return m


# ---------------------------------------------------------------------------
# 校验（`studio.py lexicon check` / 独立 CLI 共用）
# ---------------------------------------------------------------------------
def validate_lexicon(workspace) -> list:
    """校验工作区 lexicon.json，返回问题列表（空列表=通过）。错误级别带 ❌ 前缀。"""
    problems = []
    p = lexicon_path(workspace)
    if not p.exists():
        return [f"ℹ️ 尚无词表成长文件 {p}（可运行 `studio.py lexicon init` 生成，或保持空置回退内置种子）"]

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return [f"❌ JSON 解析失败: {e}"]

    if not isinstance(data, dict):
        return ["❌ 顶层必须是 JSON 对象"]
    schema = data.get("schema")
    if schema and schema != LEXICON_SCHEMA:
        problems.append(f"❌ schema 应为 {LEXICON_SCHEMA}，实际 {schema!r}")

    cats = data.get("categories", {})
    if not isinstance(cats, dict):
        problems.append("❌ categories 必须是对象（键=类别 id，值={grown, exemptions}）")
        cats = {}
    for cid, cfg in cats.items():
        if cid.startswith("_"):
            continue  # 说明性示例键（模板自带），忽略
        if cid not in BUILTIN_CATEGORIES:
            problems.append(f"❌ 未知类别 id「{cid}」（可用: {', '.join(BUILTIN_CATEGORIES)}）")
            continue
        if not isinstance(cfg, dict):
            problems.append(f"❌ categories.{cid} 必须是对象")
            continue
        for field in ("grown", "exemptions"):
            raw = cfg.get(field, [])
            if raw and not isinstance(raw, list):
                problems.append(f"❌ categories.{cid}.{field} 必须是列表")
                continue
            for item in raw or []:
                if isinstance(item, str):
                    if not item.strip():
                        problems.append(f"❌ categories.{cid}.{field} 存在空词条")
                    continue
                if isinstance(item, dict):
                    if not str(item.get("term", "")).strip():
                        problems.append(f"❌ categories.{cid}.{field} 条目缺少 term 字段")
                    continue
                problems.append(f"❌ categories.{cid}.{field} 条目必须是字符串或 {{term,...}} 对象: {item!r}")

    sc = data.get("semantic_clusters", {})
    if sc and not isinstance(sc, dict):
        problems.append("❌ semantic_clusters 必须是对象（键=聚类名，值={grown, exemptions}）")
    return problems


# ---------------------------------------------------------------------------
# 独立 CLI（studio.py 的 lexicon 子命令直接复用本模块函数）
# ---------------------------------------------------------------------------
def _cli():
    _tools_dir = Path(__file__).resolve().parent
    if str(_tools_dir) not in sys.path:
        sys.path.insert(0, str(_tools_dir))
    ap = argparse.ArgumentParser(description="词表类别中心：泛化类别种子 + 逐书成长回路")
    ap.add_argument("--list", nargs="?", const="__all__", default=None, metavar="CATEGORY",
                    help="列出全部类别卡或单个类别的有效词表（含来源）")
    ap.add_argument("--check", action="store_true", help="校验工作区 lexicon.json + 成长词清退建议")
    ap.add_argument("--init", action="store_true", help="播种工作区 00_meta/lexicon.json（模板来自 templates/）")
    ap.add_argument("--json", action="store_true", help="机读输出（--list 模式）")
    ap.add_argument("-w", "--workspace", default=None)
    args = ap.parse_args()

    from novel_utils import resolve_workspace, project_root
    ws = resolve_workspace(args.workspace)

    if args.init:
        tgt = ws / "00_meta" / LEXICON_FILENAME
        if tgt.exists():
            print(f"ℹ️ 已存在 {tgt}（如需重置请先手动删除，避免丢失本书成长记忆）")
            return
        src_tpl = project_root() / "templates" / "00_meta" / "lexicon.template.json"
        if not src_tpl.exists():
            print(f"❌ 模板缺失: {src_tpl}")
            sys.exit(1)
        tgt.parent.mkdir(parents=True, exist_ok=True)
        tgt.write_text(src_tpl.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"✅ 已播种词表成长文件: {tgt}")
        print("   成长协议: agents/rules/novel_lexicon.md | 校验: python studio.py lexicon check")
        return

    if args.check:
        problems = validate_lexicon(ws)
        for p_ in problems:
            print(p_)
        if any(p_.startswith("❌") for p_ in problems):
            sys.exit(1)
        if not problems or not problems[0].startswith("ℹ️"):
            print("✅ 词表成长文件校验通过")

        # 清退建议：成长词在全部定稿中 0 命中（防词表无限膨胀）
        lex = load_workspace_lexicon(ws)
        grown_all = []
        for cid, cfg in (lex.get("categories") or {}).items():
            if cid.startswith("_") or cid not in BUILTIN_CATEGORIES:
                continue
            for e in _parse_entries((cfg if isinstance(cfg, dict) else {}).get("grown", [])):
                grown_all.append((cid, e["term"]))
        if grown_all:
            try:
                from novel_utils import find_manuscript_files
                ms_dir = ws / "05_manuscript"
                corpus = ""
                for f in (find_manuscript_files(ms_dir) if ms_dir.exists() else []):
                    corpus += f.read_text(encoding="utf-8")
                zero = [(cid, t) for cid, t in grown_all if t not in corpus]
                if zero:
                    print("🧹 [清退建议] 以下成长词在全部定稿中 0 次出现，可考虑移除（防膨胀；确认是趋势词可保留）:")
                    for cid, t in zero:
                        print(f"   - 「{t}」({cid})")
                else:
                    print(f"🌱 成长词共 {len(grown_all)} 个，全部有命中记录")
            except Exception as e:
                logger.debug("清退扫描跳过: %s", e)
        return

    if args.list:
        if args.json:
            def _payload(cid):
                m = category_meta(cid)
                m["effective_terms"] = effective_terms(cid, ws)
                m["provenance"] = provenance_map(cid, ws)
                return m
            target = list(BUILTIN_CATEGORIES) if args.list == "__all__" else [args.list]
            for cid in target:
                if cid not in BUILTIN_CATEGORIES:
                    print(json.dumps({"error": f"未知类别 {cid}", "available": list(BUILTIN_CATEGORIES)},
                                     ensure_ascii=False))
                    sys.exit(2)
            print(json.dumps({cid: _payload(cid) for cid in target}, ensure_ascii=False, indent=2))
            return

        if args.list == "__all__":
            print(f"📚 词表类别卡（{len(BUILTIN_CATEGORIES)} 类，schema {LEXICON_SCHEMA}）")
            has_book = lexicon_path(ws).exists()
            print(f"   工作区: {ws} | 成长文件: {'✅ ' + str(lexicon_path(ws)) if has_book else '∅（回退内置种子+题材档案）'}\n")
            for cid, meta in BUILTIN_CATEGORIES.items():
                grown, exempt = _category_config(cid, ws)
                extras = _genre_extras(cid, ws)
                kind = "密度" if meta["kind"] == "density" else "线索"
                print(f" ▪ {cid}（{meta['name']}｜{kind}类）: 种子 {len(meta['seeds'])}"
                      f" + 题材 {len(extras)} + 成长 {len(grown)} − 豁免 {len(exempt)}"
                      f" = 有效 {len(effective_terms(cid, ws))}")
                print(f"   判据: {meta['definition']}")
            print("\n查看单类全量: python studio.py lexicon list sudden_shift | 协议: agents/rules/novel_lexicon.md")
        else:
            cid = args.list
            if cid not in BUILTIN_CATEGORIES:
                print(f"❌ 未知类别 {cid}；可用: {', '.join(BUILTIN_CATEGORIES)}")
                sys.exit(2)
            meta = BUILTIN_CATEGORIES[cid]
            print(f"📚 {cid}（{meta['name']}｜{'密度' if meta['kind'] == 'density' else '线索'}类）")
            print(f"判据: {meta['definition']}\n")
            prov = provenance_map(cid, ws)
            for t in effective_terms(cid, ws):
                print(f"   {t}  [{prov.get(t, '?')}]")
        return

    ap.print_help()


if __name__ == "__main__":
    _cli()
