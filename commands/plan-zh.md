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

   这会用模板创建 `.planning/<YYYY-MM-DD>-<slug>/{task_plan.md,findings.md,progress.md}`，自动把当前会话绑定到它，并打印一行 `PLAN_ID=<id>`。记住这个 id。
3. **只在该计划内**工作——读取/更新 `.planning/<PLAN_ID>/task_plan.md`、`.planning/<PLAN_ID>/findings.md`、`.planning/<PLAN_ID>/progress.md`。

**不要**创建或修改根目录的 `task_plan.md`，也**不要**读取 `.planning/.active_plan` 或其他计划目录——那些属于别的会话。**不要自己跑 `resolve-plan-dir.sh`**——普通 shell 里它没有 `PLAN_ID`，会错误回退到 `.active_plan`（有多个计划时就读错）。后续轮次请直接用钩子注入的 canonical 计划文件路径。

然后引导用户完成规划工作流。所有规划文件内容使用中文。
