# Claude 端会话模型（2.44.0-claude.0）：分析、设计与变更清单

> 适用：`claude` 分支（Claude Code 插件）。Codex 端（`~/.codex/...`、`main` 分支）**不在本次改动范围**。
> 原则：不追求与 Codex 逐行一致；Claude Code 有更合适的原生能力时，按 Claude 的方式设计；两端共享的**磁盘格式**保持兼容。

---

## 1. 问题复盘（2.43.0-claude.6）

### 1.1 最严重：未绑定会话跟错任务

| 环节 | Codex 端 | Claude 端（旧） |
|---|---|---|
| 门控 | 有 `sessions/` 时只认本会话 `.attached` | 默认直接放行 |
| 取计划 | 只认 `sessions/<sid>.active_plan` | 会话绑定 → `.active_plan` → 最新目录 → 根目录 `task_plan.md` |
| 渲染 | 仅已绑定时调用 | 未绑定时 `PLAN_ID` 为空，`resolve-plan-dir.sh` 回退到 `.active_plan` |
| 建计划时绑定 | `init-session.sh` 原子写入 | 脚本不绑定，PostToolUse 事后按 `.active_plan` 补绑 |

本机 47 份 Claude 转录（EarlyStop / DepthGraph / FusionCorrect / AUGUR / TCOT）实测：
- `RESOLVED via project default` 注入 **313 次**，`BOUND` 仅 6 处；
- Stop 以 "Task incomplete" 催促续跑 **47 次**（几乎都是未绑定会话、别人的计划）；
- 每次 Bash 前 / Write·Edit·Bash 后的提醒约 2.5k / 4.4k 处；
- 启动时跨会话 catchup 37 次，最多带入 266 条无关消息。

### 1.2 其他问题
1. PostToolUse 只要命令文本含 `init-session.sh` 就绑到 `.active_plan`：`cat`/`grep` 脚本或脚本失败都会误绑；绑定不写 `.attached`。
2. session_id 用 `turn_id` 兜底、未清洗。
3. **Claude 特有生命周期未处理**：resume/fork 可能换新 session_id（转录中可见旧 id）；`/clear` 必换新 id；SessionStart 未匹配 `compact`；subagent 也收提醒。
4. PreCompact 输出的 `additionalContext` 被 Claude Code 丢弃（文档：PreCompact 丢弃 systemMessage，且不支持 additionalContext），转录里从未出现。
5. Stop 用 `decision: block`（界面显示为 hook 错误）强制续跑，干扰对话式使用。
6. `/status` 读根目录 `task_plan.md`；`/plan-goal`、`/plan-loop`、`/plan-attest`、`attest-plan.sh`、`check-complete.sh` 走 `.active_plan` 回退链（可能给别人的计划存证）。
7. 没有"让本会话续做某个已有计划"的入口；`set-active-plan.sh` 只改项目指针。
8. 中文技能的脚本是旧 legacy 版本（建根目录 `task_plan.md`）；`/plan-zh` 调用了不存在的技能名；SKILL-zh 明文写着"未绑定会话仍拿到项目活动计划"。
9. 插件根 `session-catchup.py` 是"扫描所有会话"的旧版，且不按计划过滤。
10. `~/.claude/CLAUDE.md` 没有与 Codex AGENTS.md 对应的 planning 使用规则。

---

## 2. 设计

### 2.1 核心契约
- 会话只看到 `.planning/sessions/<session_id>.active_plan` 指向的计划（+ `.attached`，与 Codex 相同格式，两端可共用同一项目的 `.planning/`）。
- `.planning/.active_plan` 只表示"最近创建的计划"，hooks 从不把它当作会话计划（仅在 init 补绑时做前后对比）。
- 查找绑定时从 cwd 向上逐级查找——以 session_id 为键，因此不会串到父项目里别的会话的计划。
- 项目完全没有 `.planning/` 且根目录有 `task_plan.md` 时，保留 legacy 注入（无歧义）。

### 2.2 session_id
- hooks：payload `session_id`（文档字段）→ transcript 文件名 UUID → `PWF_SESSION_ID` / `CLAUDE_CODE_SESSION_ID`；不使用 turn 级 id；统一清洗。
- 脚本：`PWF_SESSION_ID`（SessionStart 通过官方 `CLAUDE_ENV_FILE` 导出）→ `CLAUDE_CODE_SESSION_ID`（Bash 环境实测存在，未写入文档，作为次选）。

### 2.3 绑定来源
| 来源 | 机制 |
|---|---|
| 新建 | `init-session.sh --plan-dir` 原子写绑定，并打印 `PLAN_ROOT=` / `PLAN_ID=` |
| 兜底 | PostToolUse 解析 Bash `tool_response.stdout` 的 `PLAN_ID=` 行（读脚本源码不会产生行首 `PLAN_ID=`，天然防误绑）；解析不到时才用 PreToolUse 快照的 `.active_plan` 前后对比 |
| 续做 | `session-plan.sh attach <PLAN_ID>` / `/plan-attach`（不改 `.active_plan`，附带按计划过滤的 catchup） |
| resume / fork | SessionStart 扫描 transcript 中出现过的旧 sessionId，继承最近一个有绑定的；若 transcript 尚未写入，首个 UserPromptSubmit 再试一次 |
| /clear | SessionEnd(reason=clear) 写交接记录（插件数据目录，带 Claude 进程号与时间戳）→ SessionStart(source=clear) 消费并绑定新 session_id，附带 catchup；若 SessionStart 先于 SessionEnd 触发，首个 UserPromptSubmit 再消费一次 |

### 2.4 各 hook 行为

| Hook | 未绑定 | 已绑定 |
|---|---|---|
| SessionStart startup | 项目有计划目录时给一条提示（不含计划内容，`PWF_UNBOUND_HINT=off` 可关） | 注入计划 |
| SessionStart resume/fork | 先尝试继承 | 注入计划 |
| SessionStart clear | 先尝试交接 | 注入计划 + catchup |
| SessionStart compact | 静默 | 重新注入 + "刚压缩，请重读" |
| UserPromptSubmit | `临时任务` 检测；否则静默 | 计划变化时注入全文，否则两行指针（指纹比较） |
| PreToolUse(Bash) | 拦截裸 `resolve-plan-dir.sh`；计划脚本前快照 | 同左；**无每命令提醒** |
| PostToolUse(Bash/Write/Edit/MultiEdit/NotebookEdit) | 计划脚本后绑定/解绑 | 同左；活动计数，一个窗口内提醒一次（仅主线程） |
| Stop | 静默 | `sync`（默认）：本轮有改动但未更新计划文件 → 一次非错误反馈请求记进度；`continue`：阶段未完成且无后台任务 → 继续；`off`；阶段数变化时给用户一行状态 |
| SessionEnd | 清临时任务标记 | reason=clear 时写交接 |
| PermissionRequest | 静默 | 给用户显示本会话计划与当前阶段（subagent 除外） |
| PreCompact | **移除**（输出被 Claude Code 丢弃，改由 SessionStart compact 承担） | |

### 2.5 状态存放
- 项目内（与 Codex 共享）：只有绑定文件 `sessions/<sid>.active_plan` / `.attached`、可选 `.hooks_mode` / `.stop_mode` / `.hooks_debug` 与调试日志。
- 插件数据目录（`$CLAUDE_PLUGIN_DATA/planning-state/`，仅当该变量指向本插件目录；否则及路线 B 为 `~/.claude/planning-with-files-state/`；`PWF_STATE_DIR` 可覆盖）：临时任务标记、活动计数、注入指纹、resume 重试标记、/clear 交接；30 天自动清理。

### 2.6 与 Codex 端的有意差异
| 维度 | Codex | Claude（本分支） | 原因 |
|---|---|---|---|
| 注入通道 | `systemMessage` | `hookSpecificOutput.additionalContext` | Claude 的 systemMessage 不进模型上下文 |
| 渲染实现 | Python 适配器 + shell 渲染脚本 | 纯 Python | 去掉 resolver 回退路径，便于指纹/分支控制 |
| 注入频率 | 每次提问全量 | 变化才全量，否则指针 | 注入内容会留在对话历史里，重复注入是噪音 |
| 每命令提醒 | 无 PreToolUse 提醒；PostToolUse(Bash) 提醒 | 都没有；改为活动窗口提醒 | 降噪 |
| Stop | `decision: block` 催续跑 | 默认 `sync` 非错误反馈；`continue` 可选 | Claude 支持 Stop additionalContext；续跑交给 `/plan-goal` |
| 生命周期 | thread id 稳定 | resume/fork 继承、/clear 交接、compact 重注入 | Claude 会换 session_id |
| 续做旧计划 | 无 | `session-plan.sh attach` / `/plan-attach` | 缺失能力 |
| catchup | 最近一个会话 | 同一计划上的会话 | 防串任务 |
| 临时任务标记 | 项目 `sessions/` | 插件数据目录 | 不污染共享目录 |

---

## 3. 变更清单（已实施）

- `hooks/`：重写适配器与全部入口；新增 `session_end.py`；删除 shell 渲染脚本、`resolve-plan-dir.sh` 副本与 `pre_compact.py`；`hooks.json` 更新 matcher 并注册 SessionEnd。
- `scripts/`：新增 `session-lib.sh`、`session-plan.sh`；`init-session.sh` 原子绑定 + `PLAN_ROOT`/`PLAN_ID` 输出 + 标题写入 + Claude 会话内默认目录模式；`attest-plan.sh` / `check-complete.sh` 按会话解析；`set-active-plan.sh` 增加提示；`session-catchup.py` 重写为按计划过滤。
- `skills/*/scripts/`：与 `scripts/` 完全同步（中文技能也不再使用旧脚本）。
- `commands/`：`/plan`、`/plan-zh`（修正技能名）、`/status`、`/plan-goal`、`/plan-loop`、`/plan-attest` 按会话解析；新增 `/plan-attach`。
- 文档：英/中 SKILL、README、`docs/claude-setup.md`、本文件；`templates/loop.md`。
- `install.sh`：清理旧事件中的本插件条目（如旧 PreCompact）。
- `tools/smoke_test_session_model.py`：21 组端到端场景（隔离 HOME 与插件数据目录）。
- 本地：插件缓存升级到 2.44.0-claude.0；`~/.claude/CLAUDE.md` 增加 planning 使用规则。

## 4. 验证
```bash
python3 tools/smoke_test_session_model.py
```
真实会话中可临时开启调试：`python3 tools/planning-hooks-debug.py on <project>`，查看 `.planning/debug/hook-events.jsonl`。
