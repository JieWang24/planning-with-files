# planning-with-files — Claude Code 插件（官方功能 + 会话模型定制）

> 分支 `claude`：[官方 planning-with-files](https://github.com/OthmanAdi/planning-with-files) 的 **Claude Code 插件** + 本地定制。
> 用持久化 Markdown（`task_plan.md` / `findings.md` / `progress.md`）作为 AI 的"磁盘工作记忆"；hooks 只把**绑定到当前会话的计划**注入上下文。

## 安装（二选一，勿同时用）

**路线 A · 插件（推荐）** —— 克隆后在 Claude Code 会话里：
```
/plugin marketplace add /绝对路径/到/planning-with-files
/plugin install planning-with-files@planning-with-files
```

**路线 B · 脚本全局安装**：
```bash
git clone git@github.com:JieWang24/planning-with-files.git
cd planning-with-files && git checkout claude
./install.sh        # 装进 ~/.claude：技能 + 命令 + 可靠 hooks（幂等、合并式）
```
装完**新开会话**。完整步骤/验证/故障排查见 **[docs/claude-setup.md](docs/claude-setup.md)**；设计与变更见 **[docs/claude-session-model.md](docs/claude-session-model.md)**。

## 会话模型（2.44.0-claude.0）

- **每个会话只处理绑定到它的计划**：`.planning/sessions/<session-id>.active_plan`。未绑定会话不注入任何计划内容；项目 `.planning/.active_plan` 只是"最近创建的计划"，永远不作为会话计划。
- **绑定方式**：`init-session.sh --plan-dir "<任务名>"`（新建并绑定）、`/plan-attach <PLAN_ID>`（续做已有计划）、resume/fork 自动继承、`/clear` 自动交接。
- **低噪音**：计划变化才注入全文，否则两行指针；无每命令提醒；subagent 不提醒；压缩后自动重注入。
- **进度同步**：Stop 默认 `sync`——本轮有改动却没更新计划文件时，以非错误反馈请求记一条进度；`continue` 模式可恢复"未完成就继续"。
- **临时任务**：提问含 `临时任务`，本会话 planning 钩子静默到下次正常提问。
- **按计划过滤的 catchup**、会话感知的 `/status` `/plan-attest` `/plan-goal` `/plan-loop`。

## 来自官方（保留）

- 插件包装 `.claude-plugin/`、斜杠命令 `/plan` `/start` `/status` `/plan-attest` `/plan-goal` `/plan-loop` `/plan-zh`（本 fork 新增 `/plan-attach`）
- 计划存证/防篡改（SHA-256，`[PLAN TAMPERED]`）、安全框定（`===BEGIN/END PLAN DATA===`）、Turn-loop 集成（`/goal` `/loop`）
- 英文技能 + 简体中文技能、`scripts/`、`templates/`

## 关键移植决策

官方把 hooks 写在 `SKILL.md` frontmatter，但 Claude Code 缺陷 [#17688](https://github.com/anthropics/claude-code/issues/17688) 导致插件内 frontmatter 钩子触发不稳定。本分支用**可靠的 `hooks/hooks.json`** 调用纯 Python 适配器实现全部 hook 行为。

## 仓库结构

| 路径 | 说明 |
|------|------|
| `.claude-plugin/` | 插件清单（plugin.json / marketplace.json） |
| `commands/` | 斜杠命令（含 `/plan-attach`、`/plan-zh`） |
| `hooks/` | ★ `hooks.json` + Python 适配器与各 hook 入口 |
| `scripts/` | `init-session.sh`、`session-plan.sh`、`session-lib.sh`、存证/检查/catchup 等（`skills/*/scripts/` 为同步副本） |
| `skills/planning-with-files[/-zh]` | 英文 / 中文技能 |
| `templates/` | 计划模板、`loop.md` |
| `tools/` | `smoke_test_session_model.py`、`planning-hooks-debug.py` |
| `install.sh` | 路线 B 全局安装器 |

## 与 Codex 版的关系

本地同时维护 Codex 版（`~/.codex/...`，`main` 分支）与 Claude 版。两端共享 `.planning/` 的**磁盘格式**（计划目录、`sessions/<id>.active_plan` + `.attached`），但各自按宿主能力实现行为；Claude 端的有意差异见 [docs/claude-session-model.md §2.6](docs/claude-session-model.md)。
