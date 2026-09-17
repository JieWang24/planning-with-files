---
description: "启动 Manus 风格的文件规划。在 .planning/<id>/ 下创建独立计划，并把【本会话】绑定到它。"
---

调用 planning-with-files:planning-with-files-zh 技能，并严格按照其指示执行。

每个 Claude Code 会话只处理绑定到它的那一个计划。项目里的 `.planning/.active_plan` 只表示"某个会话最近创建的计划"，**永远不是本会话的计划**。

1. 如果用户是要**续做已有计划**，先绑定再继续，不要新建：

   ```bash
   sh "${CLAUDE_PLUGIN_ROOT}/scripts/session-plan.sh" list
   sh "${CLAUDE_PLUGIN_ROOT}/scripts/session-plan.sh" attach <PLAN_ID>
   ```

2. 否则新建计划（任务名简短、可读，建议英文或拼音，便于生成目录名）：

   ```bash
   sh "${CLAUDE_PLUGIN_ROOT}/scripts/init-session.sh" --plan-dir "<任务名>"
   ```

   这会创建 `.planning/<YYYY-MM-DD>-<slug>/{task_plan.md,findings.md,progress.md}`，把本会话绑定到它，并打印 `PLAN_ID=<id>` 和三个 canonical 文件路径。
3. **只在该计划内**工作——只读写它打印出的三个文件；后续轮次钩子会注入同样的路径。

**不要**创建或修改根目录 `task_plan.md`，**不要**读取 `.planning/.active_plan` 或其他计划目录——那些属于别的会话。**不要自己跑 `resolve-plan-dir.sh`**；脚本需要本会话计划目录时用 `sh "${CLAUDE_PLUGIN_ROOT}/scripts/session-plan.sh" path`。

然后引导用户完成规划工作流。所有规划文件内容使用中文。
