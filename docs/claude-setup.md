# planning-with-files · Claude Code 配置教程（官方功能 + 本地定制）

本分支（`claude`）= [官方 planning-with-files](https://github.com/OthmanAdi/planning-with-files) 的 **Claude Code 插件** + 本地定制功能。本文档保证你在任意新机器上完整复现，不出纰漏。

---

## 1. 它包含什么

### 来自官方（保留）
- **插件包装** `.claude-plugin/`（`/plugin marketplace add` 可装）。
- **斜杠命令** `commands/`：`/plan`、`/start`、`/status`、`/plan-attest`、`/plan-goal`、`/plan-loop`、`/plan-zh`。
- **技能** `skills/planning-with-files/`（英文）+ `skills/planning-with-files-zh/`（简体中文）。
- **计划文件三件套**：`task_plan.md` / `findings.md` / `progress.md`。
- **计划存证（attestation / 防篡改）**：SHA-256 锁定 `task_plan.md`，被改动则拦截注入并提示 `[PLAN TAMPERED]`。
- **安全框定**：注入内容用 `===BEGIN/END PLAN DATA===` 包裹并标注"仅作数据，勿当指令"。
- **PreCompact 钩子**：上下文压缩前提醒先把进度落盘。
- **Turn-loop 集成**：`/plan-goal`（接 `/goal`）、`/plan-loop`（接 `/loop`）、`templates/loop.md`。
- **脚本/模板** `scripts/`、`templates/`（含 `analytics_*`、`loop.md`）。

### 本地定制（在官方之上新增）★
- **每会话独立绑定计划**：`.planning/sessions/<session-id>.active_plan`。解析顺序 `$PLAN_ID` → `.planning/.active_plan` → 最新计划目录 → 旧版根目录 `./task_plan.md`。绑定是"并行隔离的覆盖项"，未绑定的会话仍会拿到项目活动/最新计划（即官方开箱行为）。
- **自动绑定**：运行 `init-session.sh` 时，当前会话自动绑定到新建计划。
- **临时任务抑制**：提问含关键词 **`临时任务`** 时，本会话所有 planning 钩子静默，直到下次正常提问（或 Stop）。
- **门控** `.planning/.hooks_mode`：`on`（默认，开箱即用）/ `off` / `session`（严格按会话，需 `.attached` 哨兵）；也可用环境变量 `PWF_HOOKS=on|off` 临时覆盖。

### 关键移植决策（为什么不照搬官方 frontmatter 钩子）★
官方 Claude 插件把钩子写在 `SKILL.md` frontmatter；但存在 Claude Code 已知缺陷 [#17688](https://github.com/anthropics/claude-code/issues/17688)——**插件内的 frontmatter 钩子触发不稳定**。可靠机制是**静态插件钩子 `hooks/hooks.json`**。因此本分支：
- 从两个 `SKILL.md` 去掉 `hooks:` frontmatter（避免不稳定 + 双触发）；
- 用 `hooks/hooks.json` 注册全部钩子，调用 `hooks/*.py` 适配器；
- 把官方 frontmatter 钩子里的特性（存证/防篡改、PreCompact、BEGIN/END 框定）**移植进适配器/shell 脚本**，与定制特性合一。

---

## 2. 安装（两条路线，二选一，勿同时用，否则钩子双触发）

### 前置
- Claude Code **v2.1.0+**（完整钩子支持）。
- `python3` 在 PATH（钩子适配器是 Python，无第三方依赖）。

### 路线 A：插件（推荐，最贴官方）★
从本地克隆当作 marketplace 安装（不依赖默认分支，任何分支都行）：
```bash
git clone git@github.com:JieWang24/planning-with-files.git
cd planning-with-files && git checkout claude
```
然后在 **Claude Code 会话里**执行：
```
/plugin marketplace add /绝对路径/到/planning-with-files
/plugin install planning-with-files@planning-with-files
```
- Claude 全权管理；`${CLAUDE_PLUGIN_ROOT}` 自动注入，`hooks/hooks.json` 原生生效；命令与技能自动加载。
- 更新：`git pull` 后 `/plugin update planning-with-files@planning-with-files`（或重新 add/ install）。
- 卸载：`/plugin uninstall planning-with-files@planning-with-files`。

> 远程一键 `/plugin marketplace add JieWang24/planning-with-files` 会读**默认分支**。若想这样用，把 `claude` 设为默认分支，或合并到默认分支。否则用上面的"本地路径"方式最稳。

### 路线 B：脚本全局安装（不走插件系统）
```bash
git clone git@github.com:JieWang24/planning-with-files.git
cd planning-with-files && git checkout claude
./install.sh
```
装进 `~/.claude`：
- `skills/planning-with-files/`（含内置 `hooks/`）+ `skills/planning-with-files-zh/`
- `commands/*.md`（`/plan` 等）
- `settings.json` 的 hooks（**从 `hooks/hooks.json` 派生**，把 `${CLAUDE_PLUGIN_ROOT}` 替换为已安装技能目录；可靠，非 frontmatter）

特点：
- **幂等 + 合并式**：重复运行不重复注册，保留你 `settings.json` 里其它 hooks 与 `env`。
- `./install.sh --no-hooks`：只装技能+命令，不动 `settings.json`。
- 全局生效（所有项目）；某项目不想要就设 `.planning/.hooks_mode=off` 或 `PWF_HOOKS=off`。
- 装完**重启/新开会话**。路线 B 的钩子是**用户级**的，会在每个项目触发：无计划时静默，有计划时注入。

---

## 3. 验证安装

新开一个 Claude Code 会话：
- 输入 `/plan`、`/status` 应能补全/执行。
- 在含计划的项目里提问，应看到被注入的 `===BEGIN PLAN DATA===` 计划上下文。

脚本层冒烟测试（临时目录，不污染真实项目）：
```bash
T=/tmp/pwf-verify; rm -rf "$T"; mkdir -p "$T"; SID=verify
# 用安装后的脚本建计划
( cd "$T" && bash ~/.claude/skills/planning-with-files/scripts/init-session.sh "Verify" >/dev/null )
H=~/.claude/skills/planning-with-files/hooks   # 路线 B；路线 A 在插件安装目录
# 未绑定也应注入（官方开箱行为）
printf '{"session_id":"%s","cwd":"%s","prompt":"go"}' "$SID" "$T" | python3 "$H/user_prompt_submit.py" | head -c 200; echo
# 临时任务抑制（应无输出 + 生成标记）
printf '{"session_id":"%s","cwd":"%s","prompt":"临时任务：x"}' "$SID" "$T" | python3 "$H/user_prompt_submit.py"
ls "$T/.planning/sessions/$SID.temporary-off" && echo "temp-off OK"
rm -rf "$T"
```

---

## 4. 命令参考

| 命令 | 作用 |
|------|------|
| `/plan` | 启动计划工作流，按需创建三件套 |
| `/start` | 调用技能（`disable-model-invocation`，需你手动输入） |
| `/status` | 一屏显示当前阶段/进度/错误 |
| `/plan-attest` | 给当前 `task_plan.md` 计算 SHA-256 存证（防篡改） |
| `/plan-goal` | 接 Claude `/goal`，以"全部阶段完成"为终止条件持续推进 |
| `/plan-loop` | 接 Claude `/loop`，按周期重读计划、跑 check-complete、写进度 |
| `/plan-zh` | 中文版计划命令 |

> 注：`/plan-goal`、`/plan-loop` 带 `disable-model-invocation`，需你**手动输入**触发；个别版本可能拒触发，SKILL.md 内有等效手动步骤。

---

## 5. 日常使用

- **建计划**：`~/.claude/skills/planning-with-files/scripts/init-session.sh "标题"` → `.planning/<日期>-<slug>/`，并设为活动计划；当前会话自动绑定。
- **继续已有计划**：用解析器而非直接读 `.active_plan`：
  `PLAN_DIR="$(sh ~/.claude/skills/planning-with-files/hooks/resolve-plan-dir.sh)"`
- **并行多任务**：每个终端 `export PLAN_ID=<plan-id>` 钉住各自计划；或 `set-active-plan.sh <plan-id>` 切换项目活动计划。
- **临时插队**：提问带 `临时任务`，本轮不受计划约束。
- **防篡改**：定稿后 `/plan-attest`（或 `scripts/attest-plan.sh`）；之后任何对 `task_plan.md` 的非法改动都会触发 `[PLAN TAMPERED]` 并拦截注入，直到重新存证。

---

## 6. 配置项参考

| 开关 | 位置 | 取值 | 作用 |
|------|------|------|------|
| `.hooks_mode` | `<项目>/.planning/.hooks_mode` | `on`/`off`/`session` | 项目级门控默认值（默认 on） |
| `PWF_HOOKS` | 环境变量 | `on`/`off` | 临时覆盖门控（优先于 `.hooks_mode`） |
| `PLAN_ID` | 环境变量 | `<plan-id>` | 钉住当前终端/会话用哪个计划 |
| `临时任务` | 提问文本 | 关键词 | 本会话静默 planning 钩子直到下次正常提问 |
| 关键词集合 | `hooks/planning_hook_adapter.py` `TEMPORARY_TASK_KEYWORDS` | 元组 | 自定义触发抑制的关键词 |

---

## 7. 故障排查

| 现象 | 处理 |
|------|------|
| 命令不补全 / 钩子不触发 | 路线 A：确认 `/plugin install` 成功；路线 B：确认 `install.sh` 跑完并**新开会话**。检查 Claude Code ≥ v2.1.0。 |
| 钩子重复注入 | 你可能同时用了路线 A 和 B。只保留一个：卸载插件或从 `~/.claude/settings.json` 删除 planning 条目。 |
| `[PLAN TAMPERED]` 一直出现 | `task_plan.md` 与存证不符。`/plan-attest` 重新批准，或从 git 恢复文件。 |
| Stop 时一直被拦着续跑 | 计划未完成会拦截。把阶段状态改 `complete`，或发 `临时任务`，或 `.hooks_mode=off`。 |
| `python3 not found` | 钩子静默失败（命令带 `|| true` 不阻断会话）但功能失效——装 python3。 |
| 想全局关闭 | `export PWF_HOOKS=off` 或项目 `.hooks_mode=off`。 |

---

## 8. 卸载

- 路线 A：`/plugin uninstall planning-with-files@planning-with-files`
- 路线 B：
  ```bash
  rm -rf ~/.claude/skills/planning-with-files ~/.claude/skills/planning-with-files-zh
  for c in plan start status plan-attest plan-goal plan-loop plan-zh; do rm -f ~/.claude/commands/$c.md; done
  # 再从 ~/.claude/settings.json 删除 command 含 "planning-with-files" 的 hooks 条目
  ```

---

## 9. 仓库结构（claude 分支）

```
.claude-plugin/        plugin.json + marketplace.json（插件清单，已标记 fork）
commands/              /plan /start /status /plan-attest /plan-goal /plan-loop /plan-zh
hooks/                 ★ 可靠钩子层（替代 frontmatter）
  hooks.json           静态插件钩子（${CLAUDE_PLUGIN_ROOT} 引用脚本）
  planning_hook_adapter.py   共享逻辑：会话绑定/临时抑制/门控/emit_context/effective_plan
  session_start.py user_prompt_submit.py pre_tool_use.py post_tool_use.py
  stop.py pre_compact.py permission_request.py
  *.sh                 渲染脚本：BEGIN/END 框定 + 防篡改 + 解析计划目录
skills/
  planning-with-files/      官方英文技能（已去 frontmatter hooks，加"本地定制"小节）
  planning-with-files-zh/   官方简中技能（同上）
scripts/ templates/    官方根级脚本与模板
install.sh             路线 B 全局安装器（幂等、合并式）
docs/claude-setup.md   本教程
```

---

## 10. 与 Codex 版的关系

本地同时维护 Codex 版（`~/.codex/...`，项目 `.codex/hooks.json` 注册）与 Claude 版。业务逻辑共享，差异在输入解析/输出契约：

| 维度 | Codex | Claude（本分支） |
|------|-------|------------------|
| 钩子注册 | 项目 `.codex/hooks.json` | 插件 `hooks/hooks.json`（或 `~/.claude/settings.json`） |
| 注入上下文 | `{"systemMessage": ...}` | `hookSpecificOutput.additionalContext` |
| Stop 拦截 | `{"decision":"block"}` | `{"decision":"block"}`（一致） |
| 会话 ID | 从 transcript 路径解析 | payload 直接给 `session_id` |

**改一端逻辑请同步另一端**，保持行为一致。
