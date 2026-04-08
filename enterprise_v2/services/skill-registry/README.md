# Skill Registry

这一层对应仓内最小可运行的 Python registry。

源码位置：

- `../../src/agent_skill_platform/registry/`

当前已实现能力：

- publish skill package / zip bundle
- resolve `RuntimeInstallBundle`
- ingest `RunFeedbackEnvelope`
- intake `PromotionSubmission`
- list/get published skills

技术栈：

- FastAPI
- SQLite
- local file storage
