# Skill Registry

这个独立目录当前没有继续内嵌 `skillhub` 的完整生产服务实现。

保留策略：

- registry 作为冻结边界存在
- 运行链路消费 `RuntimeInstallBundle`
- lab 链路输出 `PromotionSubmission`
- 具体生产级 publish/review/scan/search/download 仍建议后续按 `skillhub` 方向独立抽取

本目录里与 registry 直接相关的统一模型和入口：

- `../../src/agent_skill_platform/models.py`
- `../../src/agent_skill_platform/runtime.py`
