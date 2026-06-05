# planning-with-files — Claude Code 插件（官方功能 + 本地定制）

> 分支 `claude`：[官方 planning-with-files](https://github.com/OthmanAdi/planning-with-files) 的 **Claude Code 插件** + 本地定制功能。
> 用持久化 Markdown（`task_plan.md` / `findings.md` / `progress.md`）作为 AI 的"磁盘工作记忆"，通过 hooks 在提问 / 工具调用 / 停止 / 压缩前自动重注入计划上下文。

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
装完**新开会话**。完整步骤/原理/验证/故障排查见 **[docs/claude-setup.md](docs/claude-setup.md)**。

## 来自官方（保留）

- 插件包装 `.claude-plugin/`、斜杠命令 `/plan` `/start` `/status` `/plan-attest` `/plan-goal` `/plan-loop` `/plan-zh`
- 计划存证/防篡改（SHA-256，`[PLAN TAMPERED]`）、安全框定（`===BEGIN/END PLAN DATA===`）、**PreCompact** 钩子、Turn-loop 集成（`/goal` `/loop`）
- 英文技能 + 简体中文技能、`scripts/`、`templates/`（含 `analytics_*`、`loop.md`）

## 本地定制（在官方之上新增）

- **每会话独立绑定计划**：`.planning/sessions/<session-id>.active_plan`，并行会话互不串计划（未绑定仍走官方开箱行为）。
- **自动绑定**：运行 `init-session.sh` 时当前会话自动绑定到新计划。
- **临时任务抑制**：提问含 `临时任务` 时本会话钩子静默，直到下次正常提问。
- **门控**：`.planning/.hooks_mode`（`on`/`off`/`session`）或 `PWF_HOOKS` 环境变量。

## 关键移植决策

官方把 hooks 写在 `SKILL.md` frontmatter，但 Claude Code 缺陷 [#17688](https://github.com/anthropics/claude-code/issues/17688) 导致插件内 frontmatter 钩子触发不稳定。本分支改用**可靠的 `hooks/hooks.json`**（静态插件钩子）调用 Python 适配器，并把官方 frontmatter 钩子里的特性（存证、PreCompact、安全框定）与定制特性一并融合进适配器。

## 仓库结构

| 路径 | 说明 |
|------|------|
| `.claude-plugin/` | 插件清单（plugin.json / marketplace.json，已标记 fork） |
| `commands/` | 斜杠命令（英文 + `/plan-zh`） |
| `hooks/` | ★ 可靠钩子层：`hooks.json` + Python 适配器 + 渲染脚本 |
| `skills/planning-with-files[/-zh]` | 官方技能（去 frontmatter hooks，加"本地定制"小节） |
| `scripts/` · `templates/` | 官方根级脚本与模板 |
| `install.sh` | 路线 B 全局安装器（幂等、合并式） |
| `docs/claude-setup.md` | 详细教程 |

## 同步说明

本地同时维护 Codex 版（`~/.codex/...`）与 Claude 版。逻辑共享，仅输入解析/输出契约不同。**改一端逻辑请同步另一端。**
