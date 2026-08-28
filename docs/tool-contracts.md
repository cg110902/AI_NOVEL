# Universal Novel Studio 工具契约 

> 本文件是 CLI 工具的公共行为契约，不替代命令的机器可读帮助。未标注“已实测”的行为均为设计约定或待验证项；不得把推测当成实现事实。

## 1. 工具边界

Python 工具负责结构、文件、状态合并、编号、账本重算、快照、统计和可重复校验；不负责裁决“是否好看”、角色动机是否成立、伏笔是否应该此刻回收、某个重复是否具有文学意图等问题。后者由 LLM 审校官或导演 Agent 判断。

工具输出的质量发现采用五级标签：

- `BLOCK`：确定性工程错误或已确认的严重事实错误，可阻断交付。
- `REVIEW`：疑似问题，必须由 LLM/人类复核，但不应仅凭统计自动改写。
- `SUGGEST`：优化建议，不阻断交付。
- `INFO`：统计或上下文信息。
- `WAIVED`：已登记、可追溯的合理例外。

质量等级与进程退出码分离：退出码表达命令执行结果，不能把所有文学 `WARNING` 当作进程失败。

## 2. 统一 CLI 协议

### 2.0 公共 Python 入口

`tool_runner.py` 是可选的薄封装：`run(args, workspace=..., timeout=...)` 以无 shell 插值的子进程调用 `python studio.py`，返回 `ToolResult`（保留 returncode/stdout/stderr，并提供 `ok` 与 JSON 解码）。它只调用公开 CLI，不导入 `tools/*`、不调用 LLM、不直接读写状态 SSOT；调用者仍须遵守本契约的退出码、JSON stdout 与副作用约定。参数错误在本地抛出 `ValueError`，超时/启动异常按 Python subprocess 异常处理。


### 2.1 质量发现格式

质量命令若返回结构化发现，推荐使用以下最小字段；当前 CLI 是否已全部输出这些字段，以黑盒基线为准，不得臆造：

```json
{
  "id": "voice-012",
  "level": "REVIEW",
  "message": "局部句式密度偏高",
  "evidence": "ch_012 第 4 段；近 300 字内出现 3 次",
  "location": "ch_012:paragraph:4",
  "detector": "quality.distill",
  "confidence": 0.82
}
```

`REVIEW` 必须保留证据位置；`WAIVED` 必须附 `waiver_ref`、理由和批准者。发现等级缺失时按 `REVIEW` 处理，不得自动升级为 `BLOCK`。汇总时只有未豁免 `BLOCK` 阻断交付；`REVIEW` 进入 LLM/人工清单，`SUGGEST`、`INFO` 不阻断。


- 默认读取项目根目录下的 `novel_workspace`；支持 `-w/--workspace` 指定隔离工作区。
- `--json` 命令的标准输出应为单一、可解析的 JSON；诊断信息写入 stderr 或 JSON 内的结构化字段，不混入 JSON 文本。
- 成功命令返回零；参数、前置条件、配置、schema、冲突、锁、IO、质量和内部错误返回非零。除已由黑盒观察确认的参数解析码外，本期不臆造具体数值。
- `stdout` 用于结果和机器输出，`stderr` 用于参数/运行诊断；文档未规定的具体字段均视为不稳定。

## 3. 错误分类与恢复

| 分类 | 典型情形 | 可重试 | 归档 failed/ | 默认处理 |
|---|---|---:|---:|---|
| `USAGE` | 未知命令、缺参数、非法 flag | 否，先修参数 | 否 | 调用 `--help` |
| `CONFIG` | 配置或题材档案无效 | 修复配置后 | 否 | 人工/导演确认 |
| `INPUT` | 章节号、文件内容无法解析 | 修复输入后 | 否 | LLM 不得猜测事实 |
| `PRECONDITION` | 工作区、稿件、快照不存在 | 补齐前置条件后 | 否 | 按导览下一步 |
| `SCHEMA` | 提案结构不合法 | 是 | 是（提案） | 修复提案 |
| `CONFLICT` | 账本、道具、时间线冲突 | 仅事实确认后 | 是（提案） | 同步官复核 |
| `LOCK` | 并发锁或锁超时 | 是 | 否 | 等待后重试 |
| `IO` | 读写、移动、快照失败 | 视原因 | 否 | 保留现场并人工处理 |
| `QUALITY` | 确定性门禁 BLOCK | 修复稿件后 | 否 | 回到 raw draft 重审 |
| `INTERNAL` | 未预期异常 | 否 | 否 | 保留日志、暂停流水线 |

## 4. 副作用模型

- `READ_ONLY`：只读工作区，重复调用应不改变状态。
- `WRITE_WORKSPACE`：生成或更新工作区产物。
- `MOVE_ARCHIVE`：在 `state_inbox/processed/` 与 `failed/` 间归档提案。
- `SNAPSHOT`：创建或更新快照。
- `DESTRUCTIVE`：清空稿件或恢复旧状态。
- `FORCE`：明确覆盖或重置已有资产。

命令应在执行前检查前置条件；涉及多个 SSOT 文件的写入应具有原子性或失败可恢复语义。未被黑盒验证的原子性在基线中标为待验证。

## 5. 幂等模型

- **幂等**：同一输入重复执行，状态等价且不会重复记账。
- **重复安全但输出可能不同**：状态不被重复破坏，但时间戳或报告可能变化。
- **非幂等/破坏性**：重复执行会覆盖、清空或改变状态，必须明确提示。
- **待验证**：文档未承诺，不能假设安全。

`apply/sync` 必须以提案章节和稳定操作标识实现重复安全；建议正式提案携带 `operation_id` 或 `idempotency_key`。当前未修改引擎 schema，因此该键属于兼容性建议，是否被引擎强制校验须以黑盒结果为准。

## 6. Python 与 LLM 职责矩阵

| 工作 | Python | LLM/导演 |
|---|---|---|
| 文件、JSON、编号、账本、快照 | 负责 | 不手写 SSOT |
| 字数、频率、比例、重复统计 | 测量并给证据 | 判断是否需要改 |
| 新实体、称谓、时间线疑似冲突 | 提供证据和置信度 | 判断是否为诡计、留白或错误 |
| 角色声音、节奏、感染力 | 不裁决 | 负责 |
| 高频词/句式候选 | 统计局部密度和跨章趋势 | 判断是否模板化或有意重复 |
| 例外与非典型章节 | 记录 | 批准并说明理由 |

## 7. 逐命令契约摘要

以下子命令以 `help --json` 为命令目录来源（数量以实时输出为准）；精确字段和未实测退出码不在此臆造。

| 命令 | 前置/输入 | 输出 | 副作用 | 幂等/恢复 |
|---|---|---|---|---|
| `hello` | 可选 workspace | 导览 | READ_ONLY | 幂等 |
| `status` | 已初始化 workspace | 状态摘要 | READ_ONLY | 幂等 |
| `help` | 无 | 命令地图 | READ_ONLY | 幂等 |
| `--version` | 无 | 版本号 | READ_ONLY | 幂等 |
| `init` | title/genre/protagonist | 脚手架 | WRITE_WORKSPACE；`--force` 为 FORCE | 普通重复应拒绝，force 非幂等 |
| `genre` | 题材查询或 workspace | profile/题材列表 | READ_ONLY | 幂等 |
| `mode` | workspace，可 `--set manual\|automatic` | 当前工作模式（书级覆盖存于 `00_meta/workflow_mode.json`） | `--set` 为 WRITE_WORKSPACE；查看 READ_ONLY | 幂等；非法值返回参数错误码 |
| `pack` | 章节、可选 budget | 创作语境 | READ_ONLY（细纲由 Agent 写入） | 幂等，缺失前置条件不写盘 |
| `schedule` | 章节 | 伏笔调度建议 | READ_ONLY | 幂等；建议由 LLM 决定是否采用 |
| `lint` | 定稿章节 | 门禁与质量报告 | READ_ONLY | 幂等；BLOCK 后回 raw draft |
| `confusion` | 定稿章节 | 阅读卡点候选 | READ_ONLY | 幂等；默认 REVIEW |
| `rx/prescribe` | 章节 | 微创处方 | READ_ONLY | 幂等；由 LLM 采纳 |
| `diff` | 初稿和定稿 | 对比报告 | READ_ONLY | 幂等 |
| `facts` | 定稿章节 | 事实候选 | READ_ONLY | 幂等；LLM 复核 |
| `draft` | 定稿章节 | 状态提案骨架 | WRITE_WORKSPACE（`.draft.json`） | 重复覆盖行为待验证 |
| `apply` | 收件箱提案，可 dry-run | 合并报告 | WRITE_WORKSPACE；MOVE_ARCHIVE；dry-run READ_ONLY | 正式应重复安全；待验证 |
| `sync` | 正式提案、章节 | 合并/校验/快照 | WRITE_WORKSPACE；MOVE_ARCHIVE；SNAPSHOT | 重复提案不重复记账；原子性待验证 |
| `memory` | spine/recall/repeat 与参数 | 记忆报告 | READ_ONLY | 幂等 |
| `quality` | stall/ratio/distill/all | 质量遥测 | READ_ONLY | 幂等；文学项不应 BLOCK |
| `radar` | 可选章节 | 聚合全维质量雷达（当前子工具数量以 `help --json`/实测为准） | READ_ONLY | 幂等；文学项不应 BLOCK；无定稿时 overall_status=NO_DATA、quality_checked=false |
| `snapshots` | workspace | 快照列表 | READ_ONLY | 幂等 |
| `snapshot` | 名称 | 快照 | SNAPSHOT | 同名策略待验证 |
| `rollback` | 快照名，可 clean-drafts | 恢复报告 | DESTRUCTIVE（可清理草稿） | 非幂等；不存在快照不得写盘 |
| `export` | workspace，可 txt | 全书导出；无定稿时返回前置条件错误 | 可能 WRITE_WORKSPACE，目标路径待验证 | 有定稿时确定性重建；无定稿返回非零 |
| `clean` | workspace | 清理报告 | DESTRUCTIVE；不应删审计快照 | 破坏性，二次执行行为待验证 |
| `lexicon` | action/category | 词表/检查 | 通常 READ_ONLY；成长回写需明确 | 语义判断交给 LLM |
| `test` | 无 | 测试报告 | 可能产生临时副作用 | 应可重复 |

## 8. 提案兼容约定

正式提案应满足：文件名 `ch_xxx.json` 与顶层 `chapter` 匹配；顶层 `review_status: "approved"`；不含草稿专属字段。建议增加：

```json
{
  "operation_id": "ch_012:state-sync:v1",
  "review_status": "approved",
  "reviewed_by": "novel-state-syncer"
}
```

`review_status` 是当前流程审计字段；未修改引擎前，不宣称 CLI 会强制它。未知字段应保持向后兼容，不能静默改变 SSOT 语义；schema 升级必须增加版本并提供迁移说明。

