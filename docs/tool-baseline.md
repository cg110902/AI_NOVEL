# 工具黑盒基线（第一期）

日期：2026-08-28  
契约版本：`docs/tool-contracts.md` v1  
方法：仅通过 `python studio.py` CLI、`help --json` 和公开文档观察；未读取 `tools/`、`studio.py`、`tests/` 源码。

## 观测约定

- `observed`：本轮命令实际观察到的行为。
- `expected`：文档或工具契约的预期。
- `unverified`：当前未能安全构造或尚未复测，不视为实现事实。
- 临时工作区位于系统临时目录，未触碰默认 `novel_workspace`。

## 首轮结果

| ID | 命令 | 观察到的结果 | 文件副作用 | 风险 |
|---|---|---|---|---|
| H1 | `hello --json -w <missing>` | exit 0；返回可解析 JSON；报告项目不存在/未命名状态 | 创建了目标目录（目录最初不存在） | 中：查询命令是否应创建目录需明确 |
| H2 | `status -w <missing>` | exit 0；返回空项目状态摘要 | 创建了目标目录（与 H1 共用目录） | 中：空目录与未初始化工作区语义混淆 |
| H3 | `doctor -w <empty>` | exit 1；列出缺少目录/资产 | 只读（除测试采集文件） | 低/正常：健康检查正确阻断 |
| H4 | `snapshots -w <empty>` | exit 0；报告暂无历史快照 | 只读 | 低/正常 |
| H5 | `export -w <empty>` | exit 0；输出“未找到 05_manuscript 目录”类错误提示 | 未观察到导出文件 | 高：错误提示与 exit 0 不一致，可能造成自动化假绿 |
| H6 | `radar -w <empty>` | exit 0；输出全维雷达报告 | 只读 | 中：空工作区仍报告成功，需区分“无数据”与“通过” |
| H7 | `pack ch_001 -w <empty>` | exit 0；输出上下文打包报告 | 第二轮未观察到业务文件写入；初始化后 `pack` 仍未写入细纲 | 高：未初始化/缺章节时成功，可能绕过 Stage 0；应明确为空上下文报告还是前置条件错误 |
| H8 | `bogus -w <empty>` | exit 2；argparse usage/error 写 stderr | 无工作区副作用 | 低/正常 |
| H9 | `pack --bogus ch_001 -w <empty>` | exit 2；参数错误写 stderr | 无工作区副作用 | 低/正常 |
| H10 | `pack abc -w <empty>` | exit 2；明确提示无法解析章节编号 | 无工作区副作用 | 低/正常 |
| M1 | `help --json` | 不接受 `-w`；误加 workspace 参数时 exit 2 | 无副作用 | 低：运行器须按命令能力传参 |
| M2 | `genre --list --json -w <empty>` | exit 0；返回可解析 JSON 数组，包含 17 个题材档案 | 只读（目录已存在） | 低/正常 |
| M3 | `init -t Test -g 通用 -p 主角 -w <empty>` | exit 0；生成完整脚手架与初始资产 | 创建完整工作区、状态 JSON/MD、模板和初始化 beats | 低/正常 |
| M4 | 重复 `init`（无 force） | exit 1；拒绝覆盖已有工作区 | 未观察到破坏性变化 | 低/正常 |
| M5 | 初始化后 `doctor/status/snapshots` | 均 exit 0；健康检查通过、状态可读、无快照列表 | 只读 | 低/正常 |
| M6 | 初始化后 `apply --dry-run` | exit 0；提示没有待处理提案 | 未观察到 SSOT/提案变化 | 低/正常 |
| M7 | `pack ch_001 --budget 0/1/-5` | 均 exit 0；生成语境报告；本轮未观察到业务写入 | READ_ONLY | 中：预算边界与负数语义仍需明确 |
| M8 | `rx` 与 `prescribe`（缺稿件） | 均 exit 1；稳定提示找不到待审稿件 | 无副作用 | 低/正常 |
| M9 | `clean`（初始化后） | exit 0；清理报告；状态/审计目录保留 | 保留 `processed/`、`failed/`、`snapshots/` | 低/正常 |

## 初步结论

### 已确认可靠

1. 参数解析错误返回非零（本轮观察为 exit 2），且错误写入 stderr。
2. 非法章节标识会被拒绝，不产生业务文件。
3. `doctor` 能在空目录发现结构缺失并返回非零。
4. `init` 首次生成的目录和状态资产完整；重复初始化默认拒绝。
5. `genre --list --json` 输出为独立可解析 JSON，包含 17 个档案。

### 需要第二轮确认的高风险项

1. `pack` 在未初始化工作区的 exit 0 和写入行为是否真实、是否属于设计的“自动生成首章细纲”，还是应视为前置条件绕过。
2. `export` 在缺少手稿时返回 exit 0 是否为稳定契约；若是，应改为非零或 JSON 中明确 `status=empty`，避免自动化误判。
3. `hello/status` 是否会创建工作区目录；若会，应记录为允许的初始化目录副作用，或改为只读。
4. `radar` 空工作区的 exit 0 是否代表“报告生成成功”而不是“质量通过”。
5. 字符编码在当前 Git Bash 输出中出现乱码；需在稳定 UTF-8 终端复测，不能暂时判定为工具数据损坏。

## 本轮复测补充（2026-08-28）

- 生产 `novel_workspace` 仍未初始化；`doctor` 返回非零并列出缺失核心资产，未自动修复。
- 空工作区 `export` 已修复：无定稿返回非零，不再以成功码掩盖缺失前置条件。
- 空工作区 `radar --json` 已修复：无定稿时 `overall_status=NO_DATA`、`data_status=no_finalized_manuscript`、`quality_checked=false`，不再把无数据误当作质量通过。
- 空工作区 `pack ch_001 --json` 未写入业务文件；调用方应把空上下文视为不可直接推演，而不是已完成 Stage 1。
- `python docs/generate_metrics.py --check` 通过；文档入口中的失效 `--bool` 与残留动态占位符已清理。

## 尚未验证

以下项目需要已初始化临时工作区和公开 CLI 可构造的最小输入：

- `apply --dry-run` 是否零写入（首轮比较被采集文件干扰；排除采集文件后未观察到业务状态变化，仍需哈希级复测）；
- 正式 `apply/sync` 重复执行是否重复安全；
- 失败提案是否移入 `failed/` 且不污染 SSOT；
- `snapshot` 同名策略及 `rollback` 恢复完整性；
- `clean` 是否保留 `processed/` 和 `snapshots/`；
- `draft --json` 是否不落盘及重复覆盖策略；
- `pack --budget` 的 0/负数/极小值边界；
- `rx/prescribe` 输出等价性；
- `memory`、`quality`、`radar` 的默认/显式章节语义；
- `export` 输出路径和覆盖策略；
- 并发锁、崩溃恢复、跨平台文件原子性。

## 第二期候选修复

按风险排序：

1. 明确所有命令的“空工作区”语义，禁止成功码掩盖缺失前置条件；
2. 复核 `pack` 是否应为纯只读工具，避免未初始化时写细纲；
3. 统一查询/导出命令的空数据退出语义；
4. 为 `apply/sync` 建立可重复的 operation/idempotency 黑盒用例；
5. 为每个质量发现补充 `BLOCK/REVIEW/SUGGEST/INFO/WAIVED` 分层，不把文学建议等同进程失败。
