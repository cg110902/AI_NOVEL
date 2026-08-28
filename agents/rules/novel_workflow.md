# 全题材 Stage 0-4 确定性工作流 SOP（全题材自适应版）

> **本文件是🔒 工程级 SOP（A 类）**：目录、命令、门禁、状态文件格式**保持刚性**，不要随意放宽。**“文学怎么写”的开放性见 `AGENTS.md` 规则分级约定与 `agents/rules/` 其他文档**；这里只约束“每一步做什么、产出什么、如何验收”。

> **通用化说明**：原「玄幻工作流 SOP」中的题材特定表述已通用化。所有 Stage 流程适用于全题材，字数/配比/基调由 `genre_profile.json` 控制。

---

## 工作模式：automatic / manual（Stage 编排总则）

### 查看与切换

```bash
python studio.py mode                # 查看当前模式（status/hello 也会显示）
python studio.py mode --set manual   # 切到手动；--set automatic 切回自动
python studio.py mode --json         # 机读输出（mode + source）
```

- 全局默认 `automatic`（`novel_config.yaml` 的 `workflow.mode`）。
- 书级覆盖写入 `<workspace>/00_meta/workflow_mode.json`，只影响当前工作区。
- 旧值 `autonomous_creation` 自动映射为 `automatic`，`director_review` 映射为 `manual`。
- 切换模式不删除稿件、提案、快照，不影响已合并状态。

### automatic（默认）：Stage 1–4 连续推进

用户确认设定后，Agent 不再逐步请示，按既定顺序连续执行：

```text
pack → beats（总策划自动选定 ABC 并记录理由）→ raw draft → 隔离审校
→ lint →（仅 CRITICAL 自动回炉，≤3 次）→ draft 提案 → 同步官复核 → sync → 交付终稿
```

每次自动选择追加记录到 `00_meta/director_log.md`（章节 / 阶段 / 选项 / 理由），供用户事后追溯。

**自动模式仍必须暂停（安全门，不得越过）**：

1. Stage 0 设定未与用户对齐；
2. `doctor` 报 ERROR；
3. lint CRITICAL 自愈重试耗尽（3 次）；
4. sync 失败、账本/时间线/道具/伏笔冲突；
5. 状态事实无法确定（不得猜测）；
6. 用户自然语言喊停（见下）。

暂停时报告原因与最近检查点，等待用户指令；不得自动覆盖或跳过。

### manual：逐步确认

在以下节点暂停等待用户确认后才继续：ABC 细纲走向选择、初稿是否进入审校、审校结果是否接受、状态提案是否批准、终稿交付。其余步骤与 automatic 相同。

### 自然语言控制协议（两种模式均生效）

用户用自然语言下指令时，Agent 按下表映射为操作；文件安全、状态合并、门禁仍由确定性工具执行：

| 用户说 | Agent 动作 |
|---|---|
| 不满意 / 重写 / 重新生成 | 定位最近交付章节 → 回到 `raw_drafts` 重新起草 → 审校 → `lint` → 覆盖 `finalized` → 重新提案 → `sync`。**绝不直接改 finalized** |
| 只改某段/某章 | 局部重写指定范围，保留其余事实与状态 |
| 暂停 / 停下 | 停止自动推进，报告当前位置 |
| 继续 | 从最近合法检查点恢复 |
| 接受 / 可以 | 允许交付，进入下一章 |
| 驳回 | 视同"重写"，并记录驳回原因 |
| 切手动/自动 | `python studio.py mode --set manual|automatic` |

指令模糊时必须先澄清，automatic 模式也不得猜测执行。

**不变量**：automatic 改变的只是"不等人"，不豁免任何门禁与禁令——lint 仍必须 Exit 0，状态仍只能经提案 sync，`finalized` 仍不可直改。

---

## Stage 0：新书初始化 (New Book Initialization)

### 执行步骤
1. **运行初始化命令**：
   ```bash
   python studio.py init --title "书名" --genre "题材描述" --protagonist "主角名"
   ```
   - 工具自动创建目录结构、拷贝模板、匹配题材档案（`genre_profile.json`）、生成初始状态机。
   - 题材匹配基于关键词（17 种内置题材），可运行 `python studio.py genre --genre "你的题材"` 预览匹配结果。
   - 已有手稿或细纲时，重开会中止；确需重开请追加 `--force`（会重置状态文件/未决提案/题材档案/词表成长文件/旧书快照），仅清空稿件用 `studio.py clean`。

2. **总策划 Agent 与用户互动对齐**（`agents/skills/novel-director`）：
   - 核心看点（2~3 个维度，详见 `novel_brainhole_and_pacing.md`）
   - 世界观设定（能力阶梯/经济体系/社会结构/地理）
   - 主角人设（性格/动机/能力/心智起点）
   - 核心配角与对手
   - 首卷大纲（主线/人际/暗线三线交织）
   - 开局具象死线（3 章内的破局危机）

3. **生成初始资产**：
   - `00_meta/project_bible.md`（项目圣经：核心法则/看点/基调）
   - `00_meta/genre_profile.json`（题材档案，自动匹配，可人工微调）
   - `01_world/world_rules.md`（能力阶梯/规则/经济锚点）、`factions.md`、`geography.md`
   - `02_characters/character_index.md` + 主角与首卷核心人物卡
   - `03_outlines/main_plot.md` + `vol_01_outline.md`
   - `04_timeline_and_state/`（初始 JSON 状态机/伏笔池/误会台账/心智台账/复式账本/时间线/提案收件箱；同名 `.md` 为自动渲染只读视图）

### 验收标准
- [ ] 目录结构完整
- [ ] 题材档案已匹配（`python studio.py genre` 确认）
- [ ] 项目圣经已写（核心看点/基调/能力阶梯）
- [ ] 主角卡已写（性格/动机/能力/心智起点 Stage 0）
- [ ] 首卷大纲已写（三线交织/卷末高潮）
- [ ] 初始状态机已生成（`current_state.json`/`economy_ledger.json`/`chekhov_guns.json` 等）

---

## Stage 1：单章细纲推演 (Chapter Beats Building)

### 执行步骤
1. **装载全量上下文**：
   ```bash
   python studio.py pack ch_xxx --json [--budget 8000]
   ```
   - 自动装载：本章 Beats 细纲（如有）、实时状态机、活跃伏笔池、上一章末尾余温、涉及角色的完整人物卡、题材档案导演指导。

2. **编剧 Agent 推演细纲**（`agents/skills/novel-beats-builder`）：
   - 提取 `high_priority_story_alerts`：临界伏笔揭露、掉线角色唤醒。
   - 提取 `foreshadow_schedule`：本章应引爆/回收/回唤的伏笔。
   - 提取 `synopsis_spine` 与 `cross_chapter_warnings`：避免重复场景。
   - 推演 3 个 ABC 走向选项，每个标明：4 维积木拼装、破局手段、角色心智演进、伏笔推进、全书闭环承诺。

3. **走向决断**：
   - `autonomous_creation` 模式下由总策划 Agent 自动选定最优选项，并在导演记录中写明选择理由；只有配置为导演介入模式时才暂停等待人类裁决。
   - 细纲写入 `03_outlines/vol_xx/beats/ch_xxx_beats.md`。

### 验收标准
- [ ] 上下文已装载（pack 输出无 ERROR）
- [ ] 3 个 ABC 走向已推演
- [ ] 走向已选定
- [ ] 细纲已写入 beats 目录
- [ ] 细纲包含：场景拆分/角色动作/对白要点/伏笔安排/章末钩子

---

## Stage 2：正文起草 (Chapter Drafting)

### 执行步骤
1. **装载上下文**（如未装载）：
   ```bash
   python studio.py pack ch_xxx
   ```

2. **主笔 Agent 起草**（`agents/skills/novel-chapter-drafter`）：
   - 按细纲分场景精雕细琢。
   - 恪守 5 条通用铁律（限制视角/信息差/动机真实/因果一致/无工程标记）。
   - 文风/基调/配比由题材档案控制（`genre_profile.tone_policy` / `ratio_baseline` / `ending_style`）。
   - 字数目标按优先级解析：书级 `project_bible.md`/`director_notes` 覆盖 > `genre_profile.word_count` 题材默认 > `novel_config.yaml` 全局 fallback；最终 resolved `min/max` 是硬门禁，`recommended` 仅为软目标。当前通用 fallback 为 2500~4000 字，推荐 3200 字。
   - 角色行为符合角色卡与当前心智阶段。

3. **初稿归档**：
   - 写入 `05_manuscript/vol_xx/raw_drafts/ch_xxx_v1.md`。

### 验收标准
- [ ] 字数位于最终 resolved `word_count.min/max` 硬门禁内（无题材覆盖时 fallback 为 2500~4000，3200 仅为推荐值）
- [ ] 无工程标记（GUN-/MIS-/Stage/占位符）
- [ ] 限制视角未越界
- [ ] 角色行为符合心智阶段
- [ ] 细纲中的关键情节已落实
- [ ] 章末钩子符合 `genre_profile.ending_style`

---

## Stage 3：双轨独立审校 (Dual-Track Independent Editing)

### 执行步骤
1. **Sub-Agent 审校优先**：
   - 调用 `invoke_subagent` 启动审校官（`agents/skills/novel-continuity-guard`）。
   - 审校官在**物理隔离上下文**中运行（不继承主 Agent 上下文），确保双盲。
   - 审校官执行：语感重铸（按题材档案文风规范）、全能纠错（错别字/标点/穿帮/称谓不一致）、AI 味清除。
   - 审校官写入 `05_manuscript/vol_xx/finalized/ch_xxx.md`。

2. **本地自审校降级**（Sub-Agent 不可用时）：
   - 主 Agent 自审校，按 `novel-continuity-guard` 规范执行。

3. **门禁核验**：
   ```bash
   python studio.py lint ch_xxx
   ```
   - Exit Code 0 = 通过（含读者懵逼检测，CRITICAL 级阻断）。
   - 不通过 → 修复后重新审校 → 重新门禁。
   - 自愈流水线（`self_healing_pipeline: true`）自动打回重写，最多 `max_auto_retry_attempts: 3` 次。

### 验收标准
- [ ] Python 质量工具仅提供证据；LLM/导演完成语义裁决
- [ ] 审校已完成（finalized 目录有文件）
- [ ] `lint ch_xxx` Exit Code 0
- [ ] 仅 CRITICAL 触发回炉；WARNING 记录但不自动重写；每次尝试记录 `attempt n/3` 与失败原因，超过上限暂停转人工
- [ ] 正文问题必须回到 raw_drafts 重新审校，禁止直接修改 finalized
- [ ] 无 CRITICAL 级问题
- [ ] 字数仍达标（审校后字数可能变化）
- [ ] 无工程标记外泄

---

## Stage 4：状态自同步 (State Auto-Sync)

### 执行步骤
1. **生成提案骨架**：
   ```bash
   python studio.py draft ch_xxx
   ```
   - 0-Token 预扫描定稿，在 `state_inbox/ch_xxx.draft.json` 预填：
     - 本章在场角色（高置信）
     - 候选资金流水 `transactions_draft`（含收支方向/金额/资源池/证据句，标 `_needs_review`）
     - 伤势/协议/伏笔线索句
     - 自动梗概
     - `_review_checklist`

2. **同步官复核草稿**（`agents/skills/novel-state-syncer`）：
   - 核对每条 `transactions_draft`：金额/方向/资源池/事由/对手方。确认后移入正式 `transactions[]`。
   - 润色 `synopsis` 为 2~3 句精炼梗概。
   - 按 10+ 维度补全语义字段（时空/能力/资产/道具/人际/情报/心智/伏笔/格局/机制/开放式自定义）。
   - ⚠️ `.draft.json` 与带 `_draft:true` 的提案**绝不会被合并**。复核完成后**另存为正式** `state_inbox/ch_xxx.json`，设置顶层 `review_status: "approved"`（可附 `reviewed_by`/`reviewed_at`），并删除所有草稿专属字段：`_draft`/`_instructions`/`_review_checklist`/`_evidence_summary`/`synopsis_source_hint`/`transactions_draft` 及 `candidate_gun_clues`/`deal_clues`/`injury_clues` 等 `*_clues` 候选字段。

3. **一键合并、校验与快照**：
   ```bash
   python studio.py sync ch_xxx
   ```
   - 引擎自动完成：合并提案 → 复式记账 → 双台账校验 → 道具时空轨迹校验 → 打快照。
   - 成功：提案移入 `processed/`，快照封存 `ch_xxx_done`。
   - 失败：提案移入 `failed/`，打印原因；仅修复 `failed/` 中的正式提案后重跑。每章最多自动重试 3 次，双台账/道具冲突等无法确定的事实不得猜测，超限暂停转人工。

4. **交付**：
   - 【事实突变声明与记忆更新摘要】（基于 sync 输出）
   - 【下一章情节引子】

### 验收标准
- [ ] 提案骨架已生成（draft 输出无 ERROR）
- [ ] 草稿已复核并另存为正式提案，且顶层 `review_status` 为 `"approved"`（可附审核人和时间）
- [ ] 正式提案文件名与 `chapter` 匹配，且不含草稿专属字段
- [ ] `sync ch_xxx` 成功（提案移入 processed/）
- [ ] 双台账平衡（sync 输出无 ERROR）
- [ ] 道具时空轨迹一致
- [ ] 快照已封存
- [ ] 事实突变声明已交付

---

## 全流程状态流转图

```
Stage 0 (init) → 目录结构/题材档案/设定/人设/大纲/初始状态机
    ↓
Stage 1 (beats) → pack 上下文 → ABC 走向 → 选定 → beats 细纲
    ↓
Stage 2 (draft) → pack 上下文 → 主笔起草 → raw_drafts 初稿
    ↓
Stage 3 (edit) → Sub-Agent 审校(隔离) → finalized 定稿 → lint 门禁
    ↓ (门禁通过)
Stage 4 (sync) → draft 提案骨架 → 同步官复核 → 正式提案 → sync 合并 → 快照
    ↓
回到 Stage 1 (下一章)
```

---

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| 题材档案匹配错误 | 运行 `studio.py genre --genre "你的题材"` 预览，或手动编辑 `00_meta/genre_profile.json` 的 `id` 字段 |
| pack 输出太大 | 加 `--budget 8000` 限制 token 预算（**默认 0=全量不裁**）。裁剪按优先级：本章细纲与高优先级预警（到期伏笔/掉线角色）**绝不裁**，人物卡最先被裁，状态真值整块保留。被裁内容只是不进本次打包、原文件完好，`budget_report` 会逐项列明裁掉了什么并给出找回提示；不够就调高预算或去掉参数取全量 |
| lint 一直不通过 | 查看 CRITICAL 项，修复后重跑；自愈流水线最多重试 3 次 |
| sync 失败 | 查看 `state_inbox/failed/` 中的提案与错误信息，修正后重跑 `sync` |
| 状态不一致 | 运行 `studio.py doctor` 体检，或 `studio.py rollback <snapshot>` 回滚 |
| 想跳过某 Stage | 不建议。每个 Stage 有确定性目的，跳过会导致后续 Stage 数据缺失。 |

---

*本 SOP 为全题材自适应版本。所有字数/配比/基调参数由 `genre_profile.json` 控制，不同题材不同。运行 `python studio.py genre` 查看当前题材配置。*
