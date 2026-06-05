# planning-with-files — Claude Code 定制版

> 分支 `claude`：[planning-with-files](https://github.com/OthmanAdi/planning-with-files) 技能的 **Claude Code** 移植版 + 本地定制功能。
> 用持久化 Markdown 文件（`task_plan.md` / `findings.md` / `progress.md`）作为 AI 的"磁盘工作记忆"，并通过 hooks 在提问 / 工具调用 / 停止时自动重注入计划上下文。

## 快速开始

```bash
git clone git@github.com:JieWang24/planning-with-files.git
cd planning-with-files && git checkout claude

# 全局安装技能 + hooks，并为某个项目启用
./install.sh --project /path/to/your/project
```
首次在该项目启动 Claude Code 会话时，**批准弹出的 hooks**（安全门控）即可。

完整步骤、原理、验证、故障排查见 **[docs/claude-setup.md](docs/claude-setup.md)**。

## 本地定制功能（相对官方版）

- **每会话独立绑定计划**：`.planning/sessions/<session-id>.active_plan`，并行会话互不串计划。
- **自动绑定**：运行 `scripts/init-session.sh` 时自动把当前会话绑定到新计划。
- **临时任务抑制**：提问含关键词 `临时任务` 时，本会话所有 planning hooks 静默，直到下次正常提问。
- **门控开关**：`.planning/.hooks_mode`（`on`/`off`/`session`）或环境变量 `PWF_HOOKS`。
- **Claude 输出契约适配**：用 `hookSpecificOutput.additionalContext` 注入上下文（Codex 用的 `systemMessage` 在 Claude 不回灌给模型）。

## 目录

| 路径 | 安装目标 | 说明 |
|------|----------|------|
| `skills/planning-with-files/` | `~/.claude/skills/planning-with-files/` | 技能本体：SKILL.md、scripts、templates、references |
| `hooks/` | `~/.claude/hooks/` | hook 适配器（Python）+ 渲染脚本（shell） |
| `project-template/.claude/settings.json` | `<项目>/.claude/settings.json` | 每个项目的 hooks 注册模板 |
| `install.sh` | — | 一键安装器（全局 + 项目注册，幂等、合并式） |

## 同步说明

本地同时维护 Codex 版（`.codex/`）与 Claude 版（`.claude/`），业务逻辑共享，仅输入解析/输出契约不同。**改一端逻辑请同步另一端。**
