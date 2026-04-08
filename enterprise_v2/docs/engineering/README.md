# Agent Skill Platform 工程文档包

日期：2026-04-03

更新：2026-04-08。工程文档仍然保留设计与来源对齐价值，但当前 merged repo 的实现状态请优先参考 `docs/plan/v0.5e-implementation-status.md`。涉及 `skill_research` pack、lab pipeline、submission/export、CLI/MCP 联调时，请优先同时阅读 `06-skill-factory-lab-delivery-spec.md`、`07-skill-factory-lab-implementation-sync.md` 和 `v0.5e-implementation-status.md`。

这组文档用于把任务2直接转成后续开发输入。阅读顺序建议如下：

1. [00-program-overview-and-reuse-map.md](/Users/chenge/Desktop/skills-gp-%20research/docs/engineering/00-program-overview-and-reuse-map.md)
   - 先看总体分层、参考仓库复用映射、跨层接口
2. [../plan/v0.5e-implementation-status.md](/Users/chenge/Desktop/skills-gp-%20research/agent-skill-platform/docs/plan/v0.5e-implementation-status.md)
   - 当前 merged repo 已经落地并通过测试验证的实现状态
3. [02-skill-package-and-actions.md](/Users/chenge/Desktop/skills-gp-%20research/docs/engineering/02-skill-package-and-actions.md)
   - 定 skill 包结构与 `actions.yaml`
4. [03-registry-search-governance.md](/Users/chenge/Desktop/skills-gp-%20research/docs/engineering/03-registry-search-governance.md)
   - 定 registry、search、governance、publish/review/scan/download，并已对齐当前代码实现
5. [01-environment-kernel-and-runtime.md](/Users/chenge/Desktop/skills-gp-%20research/docs/engineering/01-environment-kernel-and-runtime.md)
   - 定 runtime、mode selection、run context、layering
6. [04-skill-factory-and-lab.md](/Users/chenge/Desktop/skills-gp-%20research/docs/engineering/04-skill-factory-and-lab.md)
   - 定 candidate、lab、eval、promotion gate
7. [05-implementation-roadmap.md](/Users/chenge/Desktop/skills-gp-%20research/docs/engineering/05-implementation-roadmap.md)
   - 定实施顺序、团队拆分、里程碑，并标注当前已落地阶段
8. [06-skill-factory-lab-delivery-spec.md](/Users/chenge/Desktop/skills-gp-%20research/docs/engineering/06-skill-factory-lab-delivery-spec.md)
   - Skill Factory / Skill Lab 的目标交付规格
9. [07-skill-factory-lab-implementation-sync.md](/Users/chenge/Desktop/skills-gp-%20research/docs/engineering/07-skill-factory-lab-implementation-sync.md)
   - 对齐当前 `loomiai-autoresearch` 代码落地状态、CLI/MCP 真实行为、run artifact 结构、测试回归结果，作为联调口径
10. [06-integration-freeze-and-delivery-plan.md](/Users/chenge/Desktop/skills-gp-%20research/docs/engineering/06-integration-freeze-and-delivery-plan.md)
   - 只做统一、裁剪、冻结、排期，作为跨团队联调口径

建议团队按下面工作流推进：

- Contracts 组先冻结 `SKILL.md / manifest.json / actions.yaml / interface.yaml`
- Registry 组在 `skillhub` 方向上扩模型与发布链路
- Runtime 组在 `AgentSkillOS` 方向上落环境内核与执行链路
- Factory/Lab 组在 `yao-meta-skill + loomiai-autoresearch` 方向上落 candidate 与实验链路
- Integration 组最后收口 install bundle、run feedback、promotion submission 三条接口

如果当前工作集中在 merged repo 的现状判断、`skill_research` pack、lab pipeline、submission/export 或 CLI/MCP 联调，请优先一起看：

- [../plan/v0.5e-implementation-status.md](/Users/chenge/Desktop/skills-gp-%20research/agent-skill-platform/docs/plan/v0.5e-implementation-status.md)
- [06-skill-factory-lab-delivery-spec.md](/Users/chenge/Desktop/skills-gp-%20research/docs/engineering/06-skill-factory-lab-delivery-spec.md)
- [07-skill-factory-lab-implementation-sync.md](/Users/chenge/Desktop/skills-gp-%20research/docs/engineering/07-skill-factory-lab-implementation-sync.md)

其中：

- `06` 回答“我们最终要交付什么”
- `07` 回答“当前代码已经实现到哪里、接口真实长什么样”

如果只做第一期，最低目标是：

- 新协议 skill 包可发布
- runtime 可从 registry 拉 bundle 并执行默认 action
- run feedback 可回流 registry

如果进入第二期，再接：

- candidate generation
- skill lab
- promotion / rollback / layered ranking
