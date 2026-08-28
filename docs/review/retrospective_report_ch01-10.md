# 第一卷·第 1~10 章全面复盘问题报告

> 复盘范围：`agents/`（rules + skills + RESOURCE_MAP）、`AGENTS.md`、`docs/tool-contracts.md`、`docs/tool-baseline.md`、`templates/`、以及 `novel_workspace/` 全部状态 JSON/MD、正文（raw_drafts + finalized）、细纲（beats）、提案收件箱（processed/failed）。
> 依据：通读工程 + 实操回顾 ch_001~ch_010（每章走 pack→beats→draft→lint→sync 全链路，10 章全部 Stage 0–4 完成、`doctor` HEALTHY、10 套快照 `ch_00X_done`）。
> 结论分级：🔴 P0 建议优先处理 ｜ 🟠 P1 择机处理 ｜ 🟡 P2 优化/可选。

---

## 一、10 章流程有无问题、漏洞

### 整体结论
流程**主干健康、无断裂**。10 章全部走通五阶段，`doctor` 0 错 0 警；正式提案 10 份全部移入 `processed/`、2 份失败提案按协议留档 `failed/`（语义正确、仅格式错，属预期审计行为）；正文无工程标记泄漏；状态机与正文事实一致。真正的问题集中在**工具可观测性噪音**与**少量字段/文档错配**，而非流程本身。

### 漏洞清单

**🔴 L1｜`character_growth_arcs.json` 的 `strategy` 字段累积串接、失去可读性**
- 证据：`04_timeline_and_state/character_growth_arcs.json` 中陈浔的 `strategy` 已把 10 章策略以「；」逐章追加成一段超长文本（约 10 个"本章维持阶段2…允许暂不位移"）。
- 定性：**同步机制是追加而非回滚/压缩**。每章 `sync` 都在旧 strategy 后拼接新段，字段从"当前策略"退化为"10 章流水账"，任何人（含后续 pack/记忆读取）都难一眼读出"当前心智策略是什么"。随章推进必然无限膨胀，属工程级隐患。
- 建议：见「五-5.1」。

**🔴 L2｜`draft` 在场判定按"提及"而非"登台"**
- 证据：`draft ch_008`/`ch_010` 均把"钱老爷"列为在场实体，但钱老爷只出现在周赖三转述中、未实际出场；同步官复核时人工把他从 `current_state.present_characters` 移除（ch_010 当前 7 人无钱老爷）。
- 定性：`draft` 用对白关键词匹配判断"在场"，把"被提及"误判为"登场"。每次都要同步官人工纠偏，属于工具语义与剧本语义（"登台"）不一致。

**🟠 L3｜`lint` 机械误报无法清零**
- 证据：ch_010 因主角名"陈浔"、反派"钱老爷"作伏笔关键词，凡正文出现该词即报「缺回忆提示」WARNING（L11/L81），为 SUGGEST 级 waive 不阻断，但导致"零告警验收"在纯机械层面不可能达成。
- 定性：以**角色本名**作伏笔关键词时，正文必然高频命中，关键词机制失效；真实读者遗忘风险与文本词频被混为一谈。

**🟠 L4｜无跨章自动化事实一致性核对**
- 证据：事实守门仅靠 Stage 3 人工三轮审计，工程层无"某人 ch5 受伤→ch6 完好""道具 ch4 在甲地→ch6 在乙地"的程序比对（`facts`/`memory`/`radar` 均未提供跨章事实锁定断言）。
- 定性：10 章靠人盯能守住，但 50+ 章后单点遗漏概率上升。

**🟡 L5｜`character_index.md` 的分隔行被 pack 误读为角色条目**
- 证据：`02_characters/character_index.md` 的 markdown 表头分隔行 `| :--- | :--- |…` 被工具当成名字为空的角色，pack 报 `【:--- (:---)】已连续 9 章未出场`，污染可观测性（并非真的废条目）。
- 定性：markdown 表格解析未跳过分隔行；"掉线预警"出现幽灵实体，长期会掩盖真实掉线。

**🟡 L6｜`novel-state-syncer` 技能文件缺失**
- 证据：`AGENTS.md`（Stage 4 必读表）与 `agents/RESOURCE_MAP.md`（第 32 行）均引用 `agents/skills/novel-state-syncer`，但 `agents/skills/` 下只有 beats-builder / chapter-drafter / continuity-guard / director 四个 SKILL.md，无 novel-state-syncer。
- 定性：Stage 4「同步官」的操作协议文件缺席，靠 `novel_workflow.md` Stage 4 + tool-contracts 兜底执行（本次 10 章实际是靠它们完成的）。属**文档/资源索引与资产不一致**，新 Agent 照索引加载会扑空。

**🟡 L7｜读者视角"丝滑"无自动化断言**
- 证据：`lint` 的读者懵逼段输出仅标题/机械检测，未见"一路丝滑"的成句结论；是否"丝滑"完全依赖人工判断。
- 定性：可接受（语义本就难自动化），但应明确为「人工验收项」，不要误以为 lint 过了就等于读者体验过关。

---

## 二、冗余 / 死板 / 过度设计 / 忽略设计

**🟠 O1｜经济台账当前空转（启用但无流水，非删减，待审视）**
- 证据：`genre_profile.economy_required=true`，但 `economy_ledger.json` 10 章仅 ch_001 一条 `opening_balance delta 0`，无任何真实交易。
- 定性：题材是「山村生活流 + 藏拙苟活」，前 10 章几乎不触发金钱/点数变动。**不是设计错误**（玄幻经济引擎该启用），但属"启用而未用"——建议要么让经济引擎在后续发挥（租子/灵物买卖/坊市交易），要么在 `project_bible.md` 登记"本书经济线弱化"，避免空转的台账成为负担。

**🟠 O2｜对白配比系统性超出题材基线（未记豁免）**
- 证据：`genre_profile.ratio_baseline.dialogue=[25,45]`，而 ch_009 对白 55.9%、ch_010 48.5%，均超上限；`lint` 未作 BLOCK 阻断。
- 定性：本书靠对话推进（生活流特色），系统性偏高未必是病；但既超基线又未在任何登记文件说明，属「忽略设计」——应在 `project_bible.md`/导演记录登记"本书对白偏重、配比基线放宽"，否则后续质量遥测会一直误报。

**🟡 O3｜growth_arcs strategy 冗余**（同 L1，此处归因）
- 追加式字段设计，10 段串接为冗余。

**🟡 O4｜伏笔 target 扎堆第 19 章**
- 证据：`chekhov_guns.json` 中 GUN-CH001-002、CH002-001、CH006-001、CH009-001 四支全部 `target_ch=第19章`，开山斧单独到 25、来源线为 None 长线。
- 定性：4 支齐刷刷回唤同一章，短线压力集中；第 12 章前**无引爆型事件**，中段（11~18）节奏依赖压力累积，有拖沓风险。建议部分 GUN 的 target 拉开（如 16/19/22），形成错峰兑现（brainhole「大线并行、错峰兑现」）。

**🟡 O5｜timeline 前段标签偏粗**
- 证据：`timeline.json` 中 ch_002/003/004 连续标记"次日清晨至夜 / 次日 / 次日"，时间轴以"数十年后的初秋"大刻度兜底。
- 定性：不构成矛盾（与"数日/初秋"自由时间轴兼容，ch_009 有"探脉第七日"倒计时锚点），但逐日标签偏粗，50+ 章后容易把"次日"叠出矛盾。建议细纲阶段显式编号日期（如"初秋·第 2 日"）。

**🟡 O6｜快照全量复制，成本线性上升**
- 证据：10 套 × 约 12 文件全量镜像 `04_timeline_and_state`（`snapshots/20260828_*_ch_00X_done/`）。
- 定性：现阶段可接受；卷末可考虑增量/归档旧快照，避免长期膨胀。

**🟡 O7｜单点能力字段长串**
- 证据：`current_state.abilities` 把长生系统被动+生活技能+市井手腕揉成一段超长描述。
- 定性：可读性差，建议拆子字段（系统被动 / 常规 / 人脉手腕）或转角色卡维护。

---

## 三、工具使用是否合理、流程是否需合理化

### 工具使用合理性（总体）
合理。`pack`（装载上下文）/ `schedule`（伏笔调度）/ `lint`（门禁）/ `draft`+`sync`（提案化状态合并+快照）各司其职，符合 `tool-contracts.md` 的「Python 提供证据、LLM/导演做语义裁决」职责矩阵；`apply --dry-run`、`doctor`、`clean` 等边界行为已由 `tool-baseline.md` 黑盒留档。没有"用 LLM 手写 SSOT""绕过 lint""直改 finalized"等违规操作。

### 合理化建议
- **S1｜lint 关键词机制改造**（对应 L3）：排除主角/常规专名作为伏笔关键词，或把"缺回忆提示"对高频专名降级为建议级；避免 WAIVE 常态化。
- **S2｜draft 在场判定细分**（对应 L2）：区分 `登台`（有实际言行场景）与 `被提及`（仅转述/耳闻），后者进 `mentioned` 不占在场位；减少同步官人工纠偏。
- **S3｜growth strategy 改覆盖式**（对应 L1）：`strategy` 只保留"最近一次 + 自上次位移以来的累计"，历史策略归档到 `chapter_synopsis.json` 或独立按章字段，避免追加串接。
- **S4｜配比超基线登记豁免**（对应 O2）：`lint` 对 ratio 越界输出 REVIEW，由导演在 project_bible 登记"对白偏重"，之后遥测不再重复报警。
- **S5｜character_index 解析跳过分隔行**（对应 L5）：表格分隔行 `:---` 不解析为角色条目。
- **S6｜补 skills 缺口**（对应 L6）：补写 `agents/skills/novel-state-syncer/SKILL.md`，或把 RESOURCE_MAP/AGENTS.md 的引用改为指向 workflow Stage 4（二选一，保持一致）。
- **S7｜引入跨章事实抽查**（对应 L4）：阶段推进时用 `memory`/`facts` 对相邻章做一次"受伤/道具/时间"锁定比对，作为 Stage 4 的软性验收项。

---

## 四、其他问题

1. **工程可追溯性弱**：仓库无 git 历史、无 `test/` 目录（`tool-baseline.md` 明示不读 `tools/`、`studio.py`、`tests/` 源码），工具行为只能靠黑盒基线文档维护。若想长期维护，建议补核心命令的回归测试或至少把 baseline 保持为"文档真源"。
2. **`doctor`/`export`/`radar` 空工作区语义**：baseline H1~H7 已记录 `hello`/`status` 会创建目录、空工作区 `export`/`radar` 曾被误判成功——baseline 注明已修复（`export` 无定稿返回非零、`radar` 输出 `overall_status=NO_DATA`）。属「已修复的历史隐患」，建议后续定期复测防回归。
3. **章末钩子**：`ending_style=strong_hook`，ch_010 以"天边异光更亮 + 山坳冲突闷响"收尾，符合强钩子，无需改。
4. **伏笔纪律良好**：无"挖坑不填"，来源线明确标为长线，符合闭环承诺（T0）。
5. **心智成长控制得当**：陈浔 10 章始终"乐隐烟火"基线，每次位移都有触发+铺垫+暂不位移的显式声明，符合「不无因突变」；但 O4 说明到了该推高的时候，避免"反复积蓄、永不兑现"。

---

## 五、我的看法与完善修复方案

### 总体看法
这是一套**非常完整、SSOT 严谨、五阶段边界清晰**的自动创作管线：提案化状态变更、快照审计、双盲审校、门禁分层都远超普通"让 AI 写小说"的工程标准。10 章能无冲突跑通并维持正文干净，说明主流程设计成立。

问题不在"流程断了"，而在**两类小病**：① 工具可观测性噪音（L2/L3/L5 的误判与误报，消耗人工纠偏）；② 文档/资源与实现错配（L6 缺 skill）与字段设计的小冗余（L1/O1/O3）。这些都可低成本修复，且不改变现有协议。

### 修复方案（按优先级）
- **P0-1｜修 growth strategy 追加机制**：改 `sync` 对 `strategy` 采用"覆盖最近一次"并附 `history` 归档，或约束提案中该字段为增量描述、由引擎合成为"当前基线 + 最近一段"。
- **P0-2｜补 novel-state-syncer SKILL.md**（或改引用），消除资源索引断层。
- **P1-1｜lint 排除主角/常规专名关键词**，减少常态 WAIVE。
- **P1-2｜draft 区分"登台/被提及"**。
- **P1-3｜project_bible 登记两处豁免**：对白配比放宽、经济线弱化（若维持现状）。
- **P1-4｜伏笔 target 错峰**：调整部分 GUN 的 `target_ch`，拉开 16/19/22。
- **P2-1｜character_index 解析跳过分隔行**。
- **P2-2｜timeline 细纲标显式日期**、快照卷末归档、能力字段拆子字段。

> 说明：P0/P1 均可在后续章节推进时顺带落地，无需回改已交付的 ch_001~010 正文（正文干净，避免动 finalized）。

---

## 六、通读工程 + 对比 novel_workspace 全部文件的结论

### 覆盖清单（全部实读）
- **流程/契约**：`AGENTS.md`（1~7 节）、`agents/rules/` 6 份（workflow / style / long_arc / brainhole / anti_ooc / lexicon）、`agents/RESOURCE_MAP.md`、`agents/skills/` 4 份 SKILL.md、`docs/tool-contracts.md`、`docs/tool-baseline.md`、`templates/` 全部模板。
- **workspace**：`00_meta/project_bible.md`、`genre_profile.json`、`workflow_mode.json`；`01_world/` 3 份；`02_characters/character_index.md` + profiles；`03_outlines/main_plot.md` + `vol_01_outline.md` + `vol_01/beats/ch_001~010`；`04_timeline_and_state/` 全部 JSON + MD + 10 套快照 + state_inbox(processed×10 / failed×2)；`05_manuscript/vol_01/raw_drafts/` + `finalized/ch_001~010` + `audit/ch_00X_review.md`（ch_009/010 实操全程产出）。

### 对比结论（正文 ↔ 状态机）
1. **一致**：每章 `current_state` 的 time/location/present_characters/abilities/assets/equipment 与 finalized 正文逐条吻合（以 ch_009/010 逐字核对）；道具权属（开山斧、旱烟杆、老牛）全程未错乱；时间线事件与章末钩子衔接一致。
2. **干净**：finalized 正文 0 处工程标记（GUN-/MIS-/Stage/占位符）；factions.md 等设定文件里的方括号为设定描述、非未填占位符。
3. **归档完整**：10 份正式提案移入 `processed/`，2 份失败提案（ch_001.2/1.3，格式错、语义对）留档 `failed/` 供审计，符合 tool-contracts 错误分类。
4. **配比/伏笔/心智**：详见 O2/O4 及五——均无正文冲突，属"基线口径"问题而非事实错误。

### 总体定级
**流程无阻断性问题**；建议在后续章节按 P0→P2 顺带消化「可观测性噪音 + 资源错配 + 少量登记缺失」，并将「读者丝滑」显式列为人工验收项。正文质量与状态一致性 10 章均达标。

---

---

## 七、修复落实清单（本次已落地，含代码/文档/数据三层）

> 用户本次授权对全部文件（含 `studio.py`/`tools/*.py`/`tests/*.py`）读写，故此前只能从数据侧规避的**工具源码层缺陷**已真正修复。状态为 ✅ 已修复 / ⚠️ 已登记（接受现状） / 🔲 留待后续。

| 编号 | 问题 | 状态 | 修复方式 |
|---|---|---|---|
| L1 | `growth_arcs.strategy` 追加串接 | ✅ | `tools/state_store.py::merge_growth_arcs` 改**覆盖式**（保留最新）+ 新增 `strategy_history` 按章归档；存量数据已从 10 段压缩为最新单段、history 重建 10 段 |
| L3 | lint「缺回忆提示」误报（主角/反派名作关键词） | ✅ | `tools/audit_reader_confusion.py` 新增 `_recall_keywords`，排除等于已注册角色名的回忆关键词；ch_010 两处 WARNING 已清零 |
| L5 | `character_index` 分隔行被当幽灵角色 | ✅ | `tools/track_character_decay.py` 改用 `is_table_separator` 健壮过滤；`:---` 不再注册 |
| 新增 | 名字头衔前缀（"村长·张老爹"）导致全文失配 | ✅ | `tools/novel_utils.py` 新增 `strip_name_title`，`load_registered_characters`/`load_characters` 剥离前缀；张老爹/玄清从误报"连续10章未出场"修正为 ch_009 正常出场 |
| 新增 | 预算模式 `synopsis_spine` 被 story_bible 饿死裁成空串 | ✅ | `tools/package_context.py::_apply_budget` 强制保留最近一章梗概（防重复刚需），绝不返回空；同步修正与之矛盾的坏测试 `test_budget_mode_trims_and_reports` |
| L6 | `novel-state-syncer` SKILL 缺失 | ✅ | 新增 `agents/skills/novel-state-syncer/SKILL.md`（覆盖 Stage 4 提案/复核/合并/快照全流程，含新策略覆盖机制说明） |
| L7 | 读者"丝滑"无断言 | ✅ | lint 现于畅通时明确输出"读者视角一路丝滑"（随 L3 修复一并生效） |
| O1 | 经济台账空转 | ⚠️ 登记 | `project_bible.md` §5.1 登记"经济线弱化"豁免（启用但不强制前期流水） |
| O2 | 对白配比超基线 | ⚠️ 登记 | `project_bible.md` §5.1 登记对白上限放宽至 55~60% 豁免 |
| O4 | 伏笔 target 扎堆第 19 章 | ✅ | `chekhov_guns.json` 目标错峰：钱老爷目光→16、时代潮汐→19、灵植灵物→19、青云灵脉→22、开山斧→25 |
| L2 | `draft` 在场判定（提及 vs 登台） | ⚠️ 登记 | 属语义判断、难以确定性自动化；已在新 SKILL 中明示同步官须复核区分登台/被提及，沿用人工纠偏 |
| L4 | 无跨章事实自动核对 | 🔲 留待 | 仍靠人工三轮审校；后续可在 Stage 4 用 `memory`/`facts` 做软性抽查 |
| O5 | timeline 粗标签 | ⚠️ 登记 | "数十年后初秋"松散时间轴为苟王题材的刻意设定，不与 ch_009"探脉第七日"锚点冲突，暂不强制逐日编号 |
| O6 | 快照全量复制 | 🔲 留待 | 现 10 套可接受；卷末可考虑增量/归档 |
| O7 | `current_state.abilities` 长串 | 🔲 留待 | 纯展示优化，读作字符串功能正常，暂不改 schema |

**回归护栏**：为上述代码修复新增 5 个回归测试（`TestStripNameTitle`×2、`TestRecallKeywordFilter`×1、`TestEntityRegistry`×1、`test_growth_strategy_overwrites_with_history`×1）；全套测试由基线 116 升至 **121 全通过**，`doctor` HEALTHY，10 章 lint 全部畅通。

### 二轮全量扫描补充修复

1. **`audit_character_gestures.py` 自带角色解析副本同病**（幽灵 `:---` + 头衔前缀未剥离）→ 复用 `strip_name_title`/`is_table_separator`；`map_character_network` 确认"未发现掉线"。
2. **`audit_reader_confusion._load_entity_registry` 未剥头衔前缀** → 补 `strip_name_title`，"村长·张老爹"等不再作为带前缀实体入库。
3. **`failed/ch_001.2/1.3.json` 为损坏 JSON**（直引号未转义/冒号 operation_id）→ 修复为可解析并各加 `_note` 说明失败原因与"已被 processed 取代勿合并"（保留在 failed/ 审计）。
4. **chekhov 伏笔 target 错峰后 plan 叙述残留"第19章"** → 对齐为 16/22。

> 二轮扫描未发现流程断裂；`memory` 的跨章 ngram 命中为"角色签名动作重复"（老牛蹭鼻、陈浔吧嗒烟丝、熬粥等），属 REVIEW 级文学信号而非工程缺陷，由审校判断保留/变奏，不机械改正文。

---

*报告日期：2026-08-28 ｜ 作者：主笔 Agent（通读工程 + 实操 ch_001~010 + 修复落实）*
