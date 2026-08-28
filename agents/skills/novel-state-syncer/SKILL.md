---
name: novel-state-syncer
description: >-
  通用小说状态同步官技能。在 Stage 4 将定稿章节的事实变化提炼为提案、复核草稿、
  提交正式提案并触发确定性引擎合并、校验与快照。适用场景：事实抽取、状态提案、
  心智台账/伏笔池/误会台账/时间线/复式账本更新、快照与审计归档。
---

# 通用小说状态同步官技能 (Universal Novel State Syncer)

本技能担任第 4 阶段（状态自同步）的**同步官**：把「定稿正文里发生了什么」翻译成
确定性引擎能安全合并的状态提案，遵守「Python 合并、LLM 只提交事实」的分工，绝不
绕过引擎手写 `04_timeline_and_state/*.json`。

> **【全题材自适应】**：金额/单位/成长轴/伏笔节奏由 `genre_profile.json` 与本书
> `project_bible.md` 控制；同步官只做事实登记与复核，不做文学裁决。角色「心智阶段」
> 以 `character_growth_arcs.json` 登记的本书成长轴为准。

---

## 一、 核心定位 (Role)

- 🎯 把正文事实无损登记进状态机：人物登场、心智位移、伏笔状态、误会发酵、道具权属、
  时间推进、金额/资源流水；
- 🧠 复核 `draft` 预扫描草稿，修正其关键词误判（如「被提及」≠「登场」）；
- 🔁 提交正式提案 → `sync` 合并、双台账校验、拍快照 → 归档到 `processed/`。

---

## 二、 刚性红线 (Invariants)

1. **不手写 SSOT**：状态变更必须经 `state_inbox/ch_xxx.json` 提案 → `sync`；
   `current_state.md`、`timeline.md` 等自动渲染视图不手改；
2. **不猜测事实**：数值、时间、道具权属、心智位移无法确定时标记 `ESCALATE`，绝不臆造；
3. **草稿永不合并**：`.draft.json` / 带 `_draft:true` 的提案绝不进入 `sync`；
4. **失败留档**：校验失败的提案留在 `state_inbox/failed/` 供修复，不删除、不静默丢弃；
5. **正文不直改**：状态冲突需要改正文时，回到 `raw_drafts` 重新起草，不直接改 `finalized`。

---

## 三、 四步执行流 (Deterministic SOP)

1. **生成提案骨架**：
   ```bash
   python studio.py draft ch_xxx --json
   ```
   工具预扫描定稿，预填：在场角色、候选资金流水 `transactions_draft`、伤势/协议/伏笔
   线索句、自动梗概、`_review_checklist`。
2. **复核草稿（同步官职责）**：
   - **在场角色**：`draft` 按「正文提及」匹配，会把仅被转述的角色误列为在场（如钱老爷
     只出现在周赖三口中）。对照正文区分「登台」与「被提及」，仅登台者进
     `present_characters`；
   - **资金流水**：逐条核对方向/金额/资源池/事由/对手方，确认后移入正式 `transactions[]`；
   - **心智台账**：`growth_arcs` 的 `strategy` 采用**覆盖式**（保留最新策略），历史自动
     归档到 `strategy_history`，**不要把多章策略用「；」手写拼进 strategy**；
   - **伏笔**：`guns` 提交状态变化（Planted→Reminded→Resolved）与 target 调整，不重复建 id；
   - **梗概**：润色为 2~3 句精炼梗概。
3. **另存正式提案**：写入 `state_inbox/ch_xxx.json`，顶层 `review_status: "approved"`，
   删除全部草稿专属字段（`_draft`/`_instructions`/`_review_checklist`/`_evidence_summary`/
   `transactions_draft` 及各 `*_clues` 候选字段）；文件名与 `chapter` 匹配。
4. **合并、校验、快照**：
   ```bash
   python studio.py sync ch_xxx
   ```
   成功 → 提案移入 `processed/`、快照封存 `ch_xxx_done`；失败 → 移入 `failed/`，读取
   错误信息修复后重跑；双台账/道具冲突等无法确定的事实不猜测，超 3 次暂停转人工。

---

## 四、 交付物 (Deliverables)

- 【事实突变声明与记忆更新摘要】：基于 `sync` 输出，列出状态机中「新增/位移/回唤」的实体、
  心智阶段、伏笔与流水；
- 【下一章情节引子】：据此给 Stage 1 的下一章准备衔接。

---

## 五、 常见陷阱 (Pitfalls)

- `draft` 的 `present_characters` 是「高置信提示」不是最终答案，登台/提及需人工复核；
- `economy_ledger` 由引擎从流水重算，只提交 `transactions[]` 流水（delta 正收负支 + 事由），
  严禁手填余额；
- 角色名可能带头衔前缀（「村长·张老爹」），正文以短名「张老爹」称呼；同步官登记时
  用工具已剥离前缀的规范名，勿重复建档；
- 操作需幂等：`sync` 对同一 `operation_id` 重复提交不重复记账。

---

*协议来源：`agents/rules/novel_workflow.md` Stage 4 + `docs/tool-contracts.md`。*
