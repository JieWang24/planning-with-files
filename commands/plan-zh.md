---
description: "启动 Manus 风格的文件规划。为复杂任务在 .planning/<id>/ 下创建会话独立的计划目录。"
---

调用 planning-with-files-zh:planning-with-files-zh 技能，并严格按照其指示执行。

请把计划创建为**独立的计划目录**，使本会话与其他会话/计划隔离——**不要**在项目根目录创建规划文件。

1. 为任务取一个简短 slug（如 "auth-refactor"、"data-pipeline"）。
2. 创建计划目录并把当前会话绑定到它：

   ```bash
   sh "${CLAUDE_PLUGIN_ROOT}/scripts/init-session.sh" --plan-dir "<任务名>"
   ```

   这会用模板创建 `.planning/<YYYY-MM-DD>-<slug>/{task_plan.md,findings.md,progress.md}`，并自动把当前会话绑定到它。
3. 解析出该目录，并**只在该目录内**工作：

   ```bash
   PLAN_DIR="$(sh "${CLAUDE_PLUGIN_ROOT}/scripts/resolve-plan-dir.sh")"
   ```

   读取/更新 `$PLAN_DIR/task_plan.md`、`$PLAN_DIR/findings.md`、`$PLAN_DIR/progress.md`。

**不要**创建或修改根目录的 `task_plan.md`，也**不要**读取 `.planning/.active_plan` 或其他计划目录——那些属于别的会话。

然后引导用户完成规划工作流。所有规划文件内容使用中文。
