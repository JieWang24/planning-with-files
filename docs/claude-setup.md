# planning-with-files · Claude Code 配置教程（本地定制版）

本分支（`claude`）是 [planning-with-files](https://github.com/OthmanAdi/planning-with-files) 技能针对 **Claude Code** 的移植版本，并在官方功能之上加入了本地定制逻辑。本文档保证你在**任意新机器**上都能按步骤完整复现这套配置，不出纰漏。

---

## 1. 这是什么

planning-with-files 让 AI 像 Manus 一样，把"工作记忆"持久化到磁盘上的 Markdown 文件里：

| 文件 | 作用 |
|------|------|
| `task_plan.md` | 阶段（phases）、目标、决策、错误记录 |
| `findings.md`  | 研究发现、技术决策 |
| `progress.md`  | 会话日志、测试结果 |

复杂任务（≥5 次工具调用 / 多步研究 / 工程搭建）开始前先建计划文件，之后通过 **hooks** 在每次提问、每次工具调用、停止时自动把计划内容重新注入上下文，从而对抗长对话中的"目标遗忘"。

---

## 2. 与官方版本的差异（本地定制功能）★

这是本仓库的核心价值，迁移/复现时务必理解：

### 2.1 每会话独立绑定计划（per-session plan binding）
- 每个会话绑定到自己的计划：`.planning/sessions/<session-id>.active_plan`。
- 解析顺序由 `hooks/resolve-plan-dir.sh` 决定：`$PLAN_ID` 环境变量 → `.planning/.active_plan` → 最新的计划目录。
- 这样**同一个仓库里并行的多个会话不会互相串计划**。

### 2.2 自动绑定规则（auto-bind）
- 只有通过脚本创建计划才算数：`scripts/init-session.sh "标题"`。
- 当某个会话运行了 `init-session.sh`，`post_tool_use.py` 会自动把**当前会话**重新绑定到项目最新的活动计划，并提示 `Session plan bound to: <plan-id>`。
- 新会话**不会**自动继承项目的 `.active_plan`——必须显式绑定（运行创建脚本），或它已有自己的 `<session-id>.active_plan`。

### 2.3 临时任务抑制（temporary-task suppression）★
- 当用户的提问里包含关键词 **`临时任务`** 时，`user_prompt_submit.py` 会写入 `.planning/sessions/<session-id>.temporary-off` 标记，并让**该会话的所有 planning hooks 全部静默**（不注入计划、不在停止时拦截）。
- 下一条**正常**提问会自动清除该标记，恢复计划上下文；`Stop` 时若仍处于临时模式也会清除标记且不拦截。
- 用途：你只想让 AI 做一件一次性的小事，不希望它被当前的长计划"绑架"。
- 关键词在 `hooks/planning_hook_adapter.py` 的 `TEMPORARY_TASK_KEYWORDS` 中定义，可自行增改。

### 2.4 激活门控（attachment gating）
`hooks/planning_hook_adapter.py::is_session_attached` 决定一个会话是否接收计划上下文，优先级：
1. 临时任务标记存在 → **关闭**。
2. 环境变量 `PWF_HOOKS`：`on`/`off`。
3. 项目文件 `.planning/.hooks_mode`：
   - `on` → 始终开启（与具体会话无关）★ 本地默认用这个
   - `off` → 始终关闭
   - `session` → 仅当存在 `.planning/sessions/<session-id>.attached` 哨兵时开启
4. 兼容老项目：若没有 `.planning/sessions/` 目录 → 默认开启。

### 2.5 Claude 输出契约适配（移植关键点）
Codex 用 `{"systemMessage": ...}` 注入上下文；但在 Claude Code 里 `systemMessage` 只是给用户看的提示，**不会回灌给模型**。因此移植时改用 Claude 的 `hookSpecificOutput.additionalContext`（见 `planning_hook_adapter.py::emit_context`）。`Stop` 拦截仍用 `{"decision":"block","reason":...}`（两端一致）。

### 2.6 codex-scholar KB 提醒（沿用）
`hooks/post-tool-use.sh` 在每次 Bash 工具调用后附带一句 `[codex-scholar]` 提醒：KB 编辑应先把项目自有的想法/规格写进 `Designs/`。这是科研知识库工作流的约定，按需保留或删除。

---

## 3. 架构与文件布局

### 仓库结构（本分支）
```
.
├── README.md
├── install.sh                       # 一键安装器（全局 + 项目注册）
├── docs/claude-setup.md             # 本教程
├── skills/planning-with-files/      # → 安装到 ~/.claude/skills/planning-with-files/
│   ├── SKILL.md                     #   （已去掉 Codex 的 hooks: frontmatter）
│   ├── scripts/                     #   init-session / resolve-plan-dir / set-active-plan / attest-plan / check-complete / session-catchup（含 .ps1）
│   ├── templates/                   #   task_plan / findings / progress 模板
│   └── references/                  #   reference.md / examples.md
├── hooks/                           # → 安装到 ~/.claude/hooks/
│   ├── planning_hook_adapter.py     #   共享逻辑（会话绑定、临时抑制、门控、emit_context）
│   ├── session_start.py             #   SessionStart：跑 catchup + 注入计划
│   ├── user_prompt_submit.py        #   UserPromptSubmit：临时任务检测 + 注入计划
│   ├── pre_tool_use.py              #   PreToolUse：占位（仅识别建计划命令）
│   ├── post_tool_use.py             #   PostToolUse：自动绑定 + 进度提醒
│   ├── stop.py                      #   Stop：计划未完成则拦截续跑
│   ├── permission_request.py        #   PermissionRequest：审批前提醒看计划
│   └── *.sh                         #   渲染计划内容的 shell 脚本
└── project-template/.claude/settings.json   # 每个项目的 hooks 注册模板
```

### 运行时布局（安装后）
| 位置 | 内容 |
|------|------|
| `~/.claude/skills/planning-with-files/` | 技能本体（模板/脚本/参考） |
| `~/.claude/hooks/` | hook 适配器（全局，所有项目共用） |
| `<项目>/.claude/settings.json` | 该项目的 hooks 注册（指向全局 hooks，带项目本地回退） |
| `<项目>/.planning/` | 真正的计划数据：`.active_plan`、`.hooks_mode`、`sessions/`、`<plan-id>/` |

> Claude Code 的 hooks 写在 `settings.json` 里（**不是**像 Codex 那样写在 SKILL.md 的 frontmatter）。

### hook 注册命令的设计
模板里的命令形如：
```sh
python3 .claude/hooks/<name>.py 2>/dev/null || python3 "$HOME/.claude/hooks/<name>.py" 2>/dev/null || true
```
先找**项目本地** `.claude/hooks/`，找不到再回退到**全局** `~/.claude/hooks/`。我们只装全局，所以走回退；但保留本地优先，便于个别项目覆盖。

---

## 4. 前置要求

- **Claude Code** 已安装并可用。
- **python3** 在 PATH 中（hook 适配器是 Python，无第三方依赖）。
- macOS / Linux 自带 `sh`、`git`。（仓库里也带了 `.ps1`，Windows 可用 PowerShell。）

---

## 5. 安装步骤

### 5.1 拉取仓库并切到 claude 分支
```bash
git clone git@github.com:JieWang24/planning-with-files.git
cd planning-with-files
git checkout claude
```

### 5.2 全局安装（技能 + hooks）
```bash
./install.sh
```
这会把 `skills/planning-with-files` 复制到 `~/.claude/skills/`，把 `hooks/*` 复制到 `~/.claude/hooks/`，并设好可执行位。已存在的旧技能会自动备份为 `*.bak.<时间戳>`。

### 5.3 为某个项目启用 planning hooks
```bash
# 全局安装 + 注册项目（默认写 .planning/.hooks_mode=on）
./install.sh --project /path/to/your/project

# 已经装过全局，只想再注册一个项目
./install.sh --no-global --project /path/to/another/project

# 一次注册多个
./install.sh --project /path/A --project /path/B
```
`--mode` 控制门控写法：`on`（默认，始终开启）/ `session`（按会话哨兵）/ `off` / `skip`（只注册 hooks，不动 `.hooks_mode`）。

> `install.sh` 的项目注册是**幂等**的，且会**合并**而非覆盖：它只会替换自己之前写入的 planning hook 条目，保留你 `settings.json` 里其它 hooks 和 `env` 等设置。

### 5.4 首次进入项目：批准 hooks ★
Claude Code 出于安全，会在检测到项目 `.claude/settings.json` 里有新的/变更的 hooks 时**弹出审批提示**。第一次在该项目启动会话时**接受这些 hooks** 即可，否则不会执行。

### 手动注册（不想用 install.sh 时）
把 `project-template/.claude/settings.json` 的 `hooks` 内容合并进 `<项目>/.claude/settings.json`，再执行：
```bash
mkdir -p <项目>/.planning && echo on > <项目>/.planning/.hooks_mode
```

---

## 6. 验证安装（smoke test）

在一个**临时目录**里跑一遍完整链路（不污染真实项目）：
```bash
T=/tmp/pwf-verify; rm -rf "$T"; mkdir -p "$T"; SID=verify-sid
bash ~/.claude/skills/planning-with-files/scripts/init-session.sh "Verify" >/dev/null
# 上一行在当前目录建计划；改到 $T 下执行：
( cd "$T" && bash ~/.claude/skills/planning-with-files/scripts/init-session.sh "Verify" >/dev/null )
echo on > "$T/.planning/.hooks_mode"

# 自动绑定
printf '{"session_id":"%s","cwd":"%s","tool_name":"Bash","tool_input":{"command":"init-session.sh x"}}' "$SID" "$T" \
  | python3 ~/.claude/hooks/post_tool_use.py
# 注入计划（应输出 hookSpecificOutput / additionalContext）
printf '{"session_id":"%s","cwd":"%s","prompt":"go"}' "$SID" "$T" \
  | python3 ~/.claude/hooks/user_prompt_submit.py | head -c 200; echo
# 临时任务抑制（应无输出，且生成 temporary-off）
printf '{"session_id":"%s","cwd":"%s","prompt":"临时任务：看个报错"}' "$SID" "$T" \
  | python3 ~/.claude/hooks/user_prompt_submit.py
ls "$T/.planning/sessions/$SID.temporary-off" && echo "temp-off OK"
# Stop 拦截（计划未完成应返回 decision:block）
printf '{"session_id":"%s","cwd":"%s","stop_hook_active":false}' "$SID" "$T" \
  | python3 ~/.claude/hooks/stop.py
rm -rf "$T"
```
预期：自动绑定打印 `Session plan bound to: ...`；提问注入打印计划内容；临时任务无输出并生成 `temporary-off`；Stop 返回 `{"decision": "block", ...}`。

---

## 7. 日常使用

- **建计划**：让 AI / 或自己运行
  `~/.claude/skills/planning-with-files/scripts/init-session.sh "任务标题"`
  会生成 `.planning/<日期>-<slug>/{task_plan,findings,progress}.md` 并把它设为活动计划。
- **继续已有计划**：用解析器而不是直接读 `.active_plan`：
  `PLAN_DIR="$(sh ~/.claude/hooks/resolve-plan-dir.sh)"`
- **切换活动计划**：`scripts/set-active-plan.sh <plan-id>`（或 `export PLAN_ID=<plan-id>` 只钉住当前终端）。
- **临时插队**：提问里带 `临时任务` 三个字，本轮不受计划约束。
- **锁定计划防篡改**：`scripts/attest-plan.sh`（记录 SHA-256），`--show` / `--clear`。
- **检查完成度**：`scripts/check-complete.sh .planning/<plan-id>/task_plan.md`。

---

## 8. 配置项参考

| 开关 | 位置 | 取值 | 作用 |
|------|------|------|------|
| `.hooks_mode` | `<项目>/.planning/.hooks_mode` | `on` / `off` / `session` | 项目级门控默认值 |
| `PWF_HOOKS` | 环境变量 | `on` / `off` | 临时覆盖门控（优先于 `.hooks_mode`） |
| `PLAN_ID` | 环境变量 | `<plan-id>` | 钉住当前终端/会话用哪个计划 |
| `临时任务` | 提问文本 | 关键词 | 本会话静默 planning hooks 直到下次正常提问 |
| 关键词集合 | `hooks/planning_hook_adapter.py` `TEMPORARY_TASK_KEYWORDS` | 元组 | 自定义触发抑制的关键词 |

---

## 9. 故障排查

| 现象 | 原因 / 处理 |
|------|------------|
| 提问/启动时没有注入计划 | ① 没批准 hooks（重进项目接受）；② 该会话未绑定计划——跑一次 `init-session.sh`；③ `.hooks_mode` 是 `off`；④ 处于临时任务模式（发一条正常提问清除）。 |
| Stop 时一直被拦着续跑 | 这是设计：计划未完成会拦截。把 `task_plan.md` 里阶段状态改成 `complete`，或发 `临时任务`，或把 `.hooks_mode` 设 `off`。 |
| `python3: command not found` | hooks 静默失败（命令末尾有 `|| true`，不会阻断会话），但功能不生效——装好 python3。 |
| 多个会话串计划 | 确认 `.planning/sessions/<session-id>.active_plan` 各自存在；新会话需各自绑定。 |
| 改了 hooks 不生效 | hooks 在会话开始时加载；新开会话或重进项目。 |
| 想全局关闭 | `export PWF_HOOKS=off`，或把项目 `.hooks_mode` 设 `off`。 |

---

## 10. 卸载

```bash
rm -rf ~/.claude/skills/planning-with-files
rm -f  ~/.claude/hooks/{planning_hook_adapter,session_start,user_prompt_submit,pre_tool_use,post_tool_use,stop,permission_request}.py
rm -f  ~/.claude/hooks/{session-start,user-prompt-submit,post-tool-use,pre-tool-use,stop,resolve-plan-dir}.sh
# 再从各项目的 .claude/settings.json 删除 planning 相关 hooks 条目即可
```

---

## 11. 与 Codex 版本的关系

本地同时维护 Codex 版（`~/.codex/skills/planning-with-files` + `~/.codex/hooks/`，在各项目 `.codex/hooks.json` 注册）和 Claude 版。两者**业务逻辑共享**，仅"输入解析 + 输出契约"不同：

| 维度 | Codex | Claude Code |
|------|-------|-------------|
| hooks 注册 | 项目 `.codex/hooks.json` | 项目 `.claude/settings.json` |
| 注入上下文 | `{"systemMessage": ...}` | `hookSpecificOutput.additionalContext` |
| Stop 拦截 | `{"decision":"block"}` | `{"decision":"block"}`（一致） |
| 会话 ID | 从 transcript 路径解析 | payload 直接给 `session_id` |

**改一端逻辑时记得同步另一端**，保持行为一致。
