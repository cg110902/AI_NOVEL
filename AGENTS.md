# Universal Novel Studio 执行法典

> 本文件是所有 Agent 的强制入口。完整资料索引见 [`agents/RESOURCE_MAP.md`](agents/RESOURCE_MAP.md)。本文件保留硬规则；Stage 细节、角色操作和专题文学规范按需读取，不要求启动时全部加载。

## 1. 开局协议

```bash
python studio.py hello --json
```

然后按任务读取 `agents/RESOURCE_MAP.md` 对应的 workflow Stage、角色 Skill 或专题 rule。需要项目事实时使用 `status`、`pack`、`doctor`、`radar`；只有命令参数不确定时才运行 `help --json`。

## 2. 权威优先级

`AGENTS.md` 硬性不变量 > 本书 `novel_workspace/00_meta/project_bible.md` > `genre_profile.json` > `agents/rules/novel_workflow.md` 工程 SOP > 当前角色 Skill > 专题 rules > `README.md`。

文学规则分为：T0 不变量、T1 默认、T2 参考、T3 可裁决覆盖。覆盖默认规则时，记录在项目圣经、导演记录或章节注记中。

## 3. 运行时绝对禁令

1. 不读取或编辑 `studio.py`、`tools/*.py`、`tests/*.py`；工具只通过 `python studio.py <command>` 调用。
2. 不直接手写 `04_timeline_and_state/*.json`。状态变更必须写入 `state_inbox/ch_xxx.json`，再运行 `sync`。
3. 不编辑自动生成的状态 Markdown（`current_state.md`、`timeline.md` 等）。
4. 定稿必须通过 `python studio.py lint ch_xxx`，未豁免的 BLOCK 不得交付。
5. 正文不得泄露 GUN-/MIS-/Stage/占位符等工程标记。
6. 不直接修改 `05_manuscript/**/finalized/`；修改必须回到 raw draft 后重新审校。
7. 不删除 `state_inbox/processed/`、`state_inbox/failed/` 或 `snapshots/` 审计资料。

## 4. 五条创作不变量

- 限制视角不越界。
- 信息差前后一致。
- 角色行为有真实动机。
- 设定、时间线、道具权属和因果一致。
- 长期状态变化必须有触发、过程和可感知代价；默认模板服从本书基调与场景心流。

## 5. 长线与状态护栏

以下是跨章节创作必须记住的工程摘要；完整解释和题材覆盖见专题 rules，不需要每次启动全文重读。

- **能力阶梯**：每卷默认跨越不超过 1 个大层级或 2～3 个小阶梯；单章暴涨或跨级必须有充分铺垫、过程、代价，并登记例外。悬疑中的能力阶梯是认知与证据链，都市可对应资源/人脉，科幻可对应技术/异能评级。
- **核心竞争力**：每本书原则上只有一个核心竞争力（系统、特殊能力、信息差、技术或规则利用等），必须有真实限制、使用代价和成长曲线，不能无脑碾压。
- **经济闭环**：有经济体系的题材以普通人的基本消费为购买力锚点，稀缺资源必须有流动消耗闭环；账本余额由引擎从流水重算，AI 只提交事实流水。`genre_profile.economy_required: false` 的题材可跳过经济台账。
- **伏笔闭环**：每个伏笔必须回收，或明确登记为长线；使用 `schedule` 检查回唤、引爆和沉睡窗口，禁止无记录挖坑或互相冲突。
- **状态幂等**：状态变更走 `state_inbox/ch_xxx.json` → `sync`；重复提交不得重复记账，失败提案留在 `failed/` 供修复，不猜测冲突事实。

## 6. Agent 协作与交付边界

- 审校官必须使用物理隔离上下文，避免继承主笔判断；完成后按配置回收临时 Agent。
- Agent 之间通过 beats、raw draft、finalized、state proposal 等文件交接，不直接共享未审计的隐式记忆。
- 正文质量问题必须回到 raw draft，重新审校后覆盖 finalized；同步官只能提交提案，确定性引擎负责合并、校验和快照。
- Python 工具提供结构、统计和证据；角色动机、节奏、文风、伏笔是否此刻回收等语义裁决由 LLM/导演完成。

## 7. 五阶段总图

| 阶段 | 当前 Agent 必读 | 主要命令 | 产出 |
|---|---|---|---|
| Stage 0 初始化 | workflow Stage 0 + `novel-director` | `init`、`genre`、`doctor` | 设定、人设、卷纲、初始状态 |
| Stage 1 细纲 | workflow Stage 1 + `novel-beats-builder` | `pack`、`schedule` | Beats 细纲 |
| Stage 2 起草 | workflow Stage 2 + `novel-chapter-drafter` | `pack`、`memory` | raw draft |
| Stage 3 审校 | workflow Stage 3 + `novel-continuity-guard` | `lint`、`confusion` | finalized 定稿 |
| Stage 4 同步 | workflow Stage 4 + `novel-state-syncer` | `facts`、`draft`、`sync` | 提案、JSON 状态、快照 |

各阶段必读与按需资料（可直接照此加载，勿跳过当前阶段的 workflow 与角色 Skill）：

| 阶段 | 必读 | 按需资料 |
|---|---|---|
| 初始化 | workflow Stage 0、`novel-director` | style、long_arc、brainhole、anti_ooc |
| 细纲推演 | workflow Stage 1、`novel-beats-builder` | brainhole、long_arc、anti_ooc |
| 正文起草 | workflow Stage 2、`novel-chapter-drafter` | style、anti_ooc、long_arc |
| 独立审校 | workflow Stage 3、`novel-continuity-guard` | style、anti_ooc、lexicon |
| 状态同步 | workflow Stage 4、`novel-state-syncer` | lexicon、long_arc |
| 体检/诊断 | 相关命令说明 | tool-contracts、baseline |

详细步骤和验收标准只以 `agents/rules/novel_workflow.md` 为准；按问题查资料的扩展索引见 `agents/RESOURCE_MAP.md`。

### 工作模式（manual / automatic）

- 默认 `automatic`：用户确认设定后 Stage 1–4 连续推进，只在安全门（doctor ERROR、lint 重试耗尽、sync 冲突、用户喊停等）暂停；自动选择记录到 `00_meta/director_log.md`。
- `manual`：在 ABC 选择、进审校、接受审校、提案批准、终稿交付各节点逐步确认。
- 查看与切换：`python studio.py mode [--set manual|automatic]`。
- 用户说“不满意/重写”时回到 raw_drafts 重做后重新过门禁，绝不直接改 finalized；“暂停/继续”控制自动推进；指令模糊先澄清。完整协议见 workflow SOP「工作模式」一节。
- automatic 只免除“等人”，不豁免任何门禁与禁令。

## 8. 资料与工作区边界

- `novel_workspace/` 是唯一生产 SSOT；状态 JSON 为机器真值，Markdown 是自动生成视图。
- `templates/` 只在初始化或模板维护时读取。
- `README.md` 面向人类，不作为创作规则依据。
- `docs/tool-contracts.md` 是 CLI 契约，`docs/tool-baseline.md` 是黑盒实测记录。

## 9. 质量门禁

- **CRITICAL（阻断交付）**：工程标记外泄、篇幅越界、严重读者懵逼、状态机/账本/道具不一致。
- **WARNING（不阻断但需关注）**：配比偏离、语义冗余、题材陈词、伏笔沉睡超期、角色掉线。
- 只有未豁免的 CRITICAL 阻断交付；文学建议由 LLM/导演裁决，不由单一统计自动判定。

## 10. 故障排查

| 现象 | 排查 | 处理 |
|---|---|---|
| lint 报工程标记外泄 | `lint ch_xxx` | 删除正文中 GUN-/MIS-/Stage 等标记 |
| sync 失败 | 查看 `state_inbox/failed/` | 按错误修正正式提案后重跑 `sync` |
| 题材档案不匹配 | `genre --genre "你的题材"` | 检查关键词，或手动调整题材档案 |
| 状态不一致 | `doctor` | 修复 ERROR，或 `rollback` 到最近快照 |
| 伏笔沉睡超期 | `schedule ch_xxx` | 按建议回唤或引爆 |
| 配比持续报警 | `genre` | 确认题材与配比基线 |
| 命令不存在/不确定 | `help --json` | 以命令目录为准 |

## 11. 文档索引

- 资料地图：`agents/RESOURCE_MAP.md`
- 完整工作流：`agents/rules/novel_workflow.md`
- 专题规则：`agents/rules/novel_*.md`
- 角色 Skill：`agents/skills/*/SKILL.md`
- 题材档案：`novel_workspace/00_meta/genre_profile.json`
- CLI 契约/基线：`docs/tool-contracts.md`、`docs/tool-baseline.md`

