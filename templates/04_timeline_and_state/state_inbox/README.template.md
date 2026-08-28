# 状态变更提案投递箱 (State Inbox)

章节定稿后的标准流水线：
1. **0-LLM 骨架预填**：运行 `python studio.py draft ch_xxx` 预填 `ch_xxx.draft.json`（已填在场角色、候选流水、线索句与自动梗概）；
2. **LLM 语义复核**：`novel-state-syncer` 打开草稿逐项复核并补全语义字段，另存为正式 `ch_xxx.json`（删除 `_draft`/`_instructions`/`_review_checklist`/`_evidence_summary`/`transactions_draft` 等草稿专属字段）；
3. **确定性合并**：运行 `python studio.py apply`（或 `python studio.py sync ch_xxx` 自动包含合并）将变更合并进 6 大状态文件并重算余额。

> ⚠️ 注意：`*.draft.json` 与带 `_draft:true` 的提案绝不会被合并，只有复核后的正式 JSON 提案才会生效。
> ✅ 正式提案必须包含顶层 `review_status: "approved"`；`"draft"` 或缺失表示尚未完成同步官复核。可附 `reviewed_by`、`reviewed_at` 作为审计信息。当前字段是流程审计约定，是否强制由 CLI 校验以实际命令输出为准。
> 💡 格式参考：可查阅同目录下 `ch_sample.proposal.template.json` 获取完整结构范例。

## 提案 JSON 格式说明 (schema: novel-studio.state-mutation/v1)
- `operation_id`（建议）：稳定的章节级幂等键，例如 `ch_012:state-sync:v1`；重复提交不得重复记账。
- `review_status`：正式提案必须为 `approved`；`draft` 或缺失表示尚未复核。
- `current_state`：时空锚点、在场角色、境界、伤势、资产、局势（按字段差异更新）
- `guns`：伏笔 `plant` / `update` / `resolve` / `remind`（`remind` 一键回唤为 Reminded 状态；id 可省略，引擎自动按序编号；⚠️ `update`/`resolve`/`remind` 只能作用于台账中已存在的伏笔 id——第 1 章等首章提案通常只有 `plant`）
- `misunderstandings`：误会 `plant` / `update` / `resolve`（自动编号，同样只能 `update`/`resolve` 已存在的记录）
- `growth_arcs`：角色成长轨道更新；`stage` 为**自由文本**（可为 `Stage 2【信息做庄】`，也可为 `信任·戒备第3阶`／`认知线·4` 等本书自定义轨道，见 AGENTS.md 规则分级约定）
- `timeline`：编年史事件追加（幂等去重）
- `transactions`：复式账本流水（`delta` 正=收入负=支出，余额由流水自动重算）
- `synopsis`：（可选）本章 2~3 句精炼梗概 + `chapter_title`，登记进章节梗概脊柱（`chapter_synopsis.json`）

合并成功的提案自动归档移入 `processed/`，校验失败的移入 `failed/` 并输出错误原因。
