# 词表成长协议

> **一句话**：词表不是规则，是记忆。**判据**（本文件+`lexicon` 命令内的自然语言定义）才是规则；
> 种子词只是召回锚点，漏报由无监督候选发现兜底，每本书通过 `00_meta/lexicon.json` 长出自己的词表。
> 本协议解决的老毛病：**穷举式词表既列举不全、又过于固化**（漏检"蓦地"、误伤历史题材的"老朽"）。
> **范式可迁移**：这套「判据 + 种子 + 统计 + 裁决 + 成长」同样适用于叙事结构的开放类别（成长轴、节奏波形、看点模型、章节功能等，见 `AGENTS.md` 规则分级约定）——核心都是**用判据代替穷举，用默认+边界+覆盖代替“必须/严禁”**。

---

## 1. 为什么不穷举（三分类铁律）

仓库里所有"词汇/类别列举"分三类，解法完全不同——**先分类，再动手**：

| 类 | 性质 | 例子 | 解法 |
|---|---|---|---|
| **A 封闭集合** | 系统自定义词汇 | 伏枪状态 Planted/Resolved、draft 字段名、schema 字段 | 枚举即正确，**禁止**"泛化"它 |
| **A′ 准封闭类** | 汉语近似有限的类 | 量词（一枚/一柄）、资源单位（灵石/信用点） | 枚举+补全即可 |
| **B 结构信号** | 不需懂词义即可检测 | 句式骨架正则（"X之色"）、n-gram 突发、对话占比 | 模式+统计 |
| **C 开放语义类** | 自然语言开放类，成员无穷 | 骤变副词、口癖、伤情词、收支动词 | **本协议**：判据+种子+统计+LLM 裁决+成长回路 |

对 C 类：**不追求零漏报**（不可达），追求"漏报可被发现 → 可被一键吸收"（可达）。

## 2. 类别卡速查（11 类）

运行 `python studio.py lexicon` 看实时完整判据与有效词表（种子+题材+本书成长−豁免）。

| id | 类别 | 型 | 消费方（命中后发生什么） |
|---|---|---|---|
| `sudden_shift` | 骤变状语 | 密度 | confusion：全章密度 ≥4 提示"铺垫不足" |
| `ai_tics` | AI腔口癖 | 密度 | quality_radar：每千字频次 vs 本书文风指纹基线 |
| `cliffhanger_signal` | 断章钩子信号词 | 密度 | lint：章末缺钩子时提醒（quiet_close 题材豁免） |
| `oppressive_mood` | 压抑氛围词 | 密度 | lint：密度超阈值提示（dark_preferred 题材整体豁免） |
| `income_verbs` / `expense_verbs` | 收/支动词 | 线索 | draft：预提取流水方向（命中≠问题） |
| `injury_signals` / `deal_signals` / `gun_hint_signals` | 伤势/协议/伏笔信号词 | 线索 | draft：摘证据行给同步官复核（命中≠问题） |
| `action_hints` / `describe_hints` | 推进/描写信号词 | 线索 | quality_radar：黄金配比门粗分类 |

**密度型**（density）：单个词无罪，密集才是问题；**线索型**（hint）：命中只是摘证据，永远不是问题。
语义聚类的成长（同义堆砌关键词）同样走 `lexicon.json` 的 `semantic_clusters` 段。

## 3. 成长 SOP（谁、何时、做什么）

```
lint / quality 报「🌱 词表成长候选」                 ← Python 无监督捞出“突发但未登记”的词（证据，不是删改命令）
   ↓
审校官/同步官 按类别卡判据裁决（LLM 语义判断，Python 不当裁判）
   ├─ 确认属于某类别 → 写入 00_meta/lexicon.json 对应 grown（带 by/ch/note）→ 下章起参与检测
   ├─ 属于误报噪音（专名/口头禅） → 不动，或在 exemptions 登记豁免
   └─ 不确定 → 留给作者裁决
   ↓
python studio.py lexicon check     ← 校验 schema + 零命中清退建议
```

**grown 条目格式**（`_` 开头的键是说明，工具忽略）：
```json
{"term": "蓦地", "by": "ai", "ch": 12, "note": "骤变状语，战斗章高频"}
```
纪律：① 每章回写 ≤8 词（防 LLM 幻觉膨胀）；② `by` 如实记 `ai`/`author`（可审计）；③ 纯字符串条目视为作者手写（宽容解析）。

**清退**：`lexicon check` 会列出"全部定稿 0 命中"的成长词；确认非趋势词即可删除。词表只增不减必然膨胀。

## 4. 豁免纪律（反"一刀切"）

- 误伤的正确解法是**登记豁免**，不是修改检测代码，也不是在正文里绕词；词表命中只提供证据，最终由 LLM/作者裁决。
- 豁免记 `exemptions`（该词退出本类别检测）：`{"term": "陡然", "by": "author", "note": "作者惯用"}`。
- 全局性豁免仍走原有机制：题材基调（tone_policy dark_preferred）豁免压抑词、quiet_close 豁免强钩子、combat_genre_only 过滤战斗套路——**场景级**豁免（如葬礼章允许压抑）由审校官裁决时直接放行并在定稿说明，不必入档。

## 5. 红线

1. **不给 Python 加语义模型**：jieba/embedding 只可作可选加速位，裁判永远是操作 LLM。
2. **不维护"大而全"静态词库**：新增题材只给 prior+少量种子；广度交给成长回路逐书积累。
3. **判据修订要评审**：类别卡 definition 是规则本体，改动=改规范，需同步本文件与 `lexicon` 命令展示（同一来源，勿手抄两份）。
4. **检测保持确定性**：同输入同输出；成长=显式编辑 `lexicon.json`，git diff 可见、可回滚。删除该文件即回退内置种子，零风险。

## 6. 数据与命令速查

- 成长文件：`<workspace>/00_meta/lexicon.json`（init 自动播种；`lexicon init` 可补种）
- 合并链：内置种子 → 题材档案 extras（`genre_profile.json` 的 extra_ticks/cliffhanger_keywords/semantic_clusters）→ 本书 grown − exemptions
- 命令：`lexicon`（类别卡）/ `lexicon list sudden_shift`（单类全量+来源）/ `lexicon check` / `lexicon init`；`--json` 机读
- 引擎：`tools/lexicon_core.py`（注册表与合并，唯一种子源）；`tools/novel_utils.py::find_lexicon_candidates`（无监督候选发现）
