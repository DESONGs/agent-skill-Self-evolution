# Agent Skill Platform 实施路线图

日期：2026-04-02  
状态：updated on 2026-04-08, roadmap with current implementation snapshot  
目标：把任务2产出的分层设计转换成真实开发顺序、团队分工和阶段性交付标准

## 1. 路线图目标

这份路线图回答三个现实问题：

1. 应该先做什么，后做什么
2. 每层开发怎么拆组，怎么并行
3. 每一阶段“做到什么程度才算可上线”

这份路线图默认系统会落成五个工程面：

- Skill Package Contracts
- Environment Kernel & Runtime
- Registry / Search / Governance
- Skill Factory
- Skill Lab

## 2. 总原则

### 2.1 先协议，后实现

必须先冻结三类协议，再做大规模编码：

1. skill package 协议
2. runtime <-> registry 接口协议
3. candidate <-> lab <-> registry promotion 协议

如果不先冻协议，后续一定会出现：

- package 结构反复变
- registry 存的数据不够 runtime 用
- runtime 回传的数据不足以做 ranking / promotion

### 2.2 先运行闭环，后自进化闭环

不要一开始就做“自我生成 skill”。工程上正确顺序是：

1. skill 可以被发布
2. skill 可以被检索
3. skill 可以被安全执行
4. skill 可以被反馈计量
5. candidate skill 才有意义

### 2.3 先 latest published 路径，后复杂分支

第一阶段只保 latest published 的主链路。

先不扩：

- 多环境 rollout
- 灰度百分比
- 多 registry 源
- 复杂在线学习排序

## 3. 推荐阶段

### 当前实现快照

先说明口径：

- 本文仍然是“路线图”，用于说明阶段顺序和拆组方式。
- 当前 merged repo 的真实代码状态，请优先看 [../plan/v0.5e-implementation-status.md](/Users/chenge/Desktop/skills-gp-%20research/agent-skill-platform/docs/plan/v0.5e-implementation-status.md)。
- 下文中引用 `skillhub / AgentSkillOS / loomiai-autoresearch` 的段落，更多是在说明来源与阶段来源，不应直接等价为当前仓内唯一实现位置。

截至 2026-04-03，Phase 1 中 registry / search / governance 的主链路已经在 `skillhub/server` 落地，具体包括：

- publish / review / promotion / scan / governance / download 主链路
- `skill_action / skill_environment_profile / skill_eval_suite / skill_bundle_artifact`
- `skill_run_feedback / skill_score_snapshot / skill_candidate / skill_promotion_decision`
- latest published only search projection 与 additive search response fields
- public / internal distribution API 分轨
- internal feedback / candidate / governance signal API

代码对齐文档见：

- [03-registry-search-governance.md](/Users/chenge/Desktop/skills-gp-%20research/docs/engineering/03-registry-search-governance.md)

因此当前路线图应理解为：

- Phase 1 的 registry / search / governance 已从“设计中”进入“持续收尾与联调”
- Phase 2 之后的 runtime / factory / lab 不再只是规划项；在 merged repo 中，v0.5 的 `find_skill / execute_skill / runtime dispatcher / backend lineage / factory facade` 已完成一轮可运行收口
- 后续继续推进时，应把本文当作阶段路线图，把 `v0.5e` 当作当前实现状态

## Phase 0：接口冻结与骨架搭建

目标：

- 冻结跨层协议
- 定下目录与仓结构
- 确定主模型与包结构

输出：

- skill package schema v1
- action contract schema v1
- runtime install bundle schema v1
- run feedback schema v1
- promotion submission schema v1

建议工期：

- 1 到 2 周

团队拆分：

- A 组：package contracts
- B 组：runtime/registry interface
- C 组：candidate/lab/promotion interface

Definition of Done：

- 每个 schema 都有文档和示例
- 每个 schema 都有 validator
- 每个 schema 都有 mock payload

## Phase 1：Skill Package 与 Registry 主链路

目标：

- skill 能以新协议被发布、索引、下载

重点工作：

1. 扩展 skill package 结构
   - 增加 `manifest.json`
   - 增加 `actions.yaml`
   - 保留 `SKILL.md`
   - 保留 `agents/interface.yaml`

2. 扩展 registry
   - 解析 `actions.yaml`
   - 新增 action / env profile / eval suite 元数据表
   - 保存 bundle zip 与对象文件

3. 固定 search projection
   - latest published only
   - label / ACL / visibility 生效

4. 固定 download API
   - 直接下载 bundle
   - 返回 runtime install bundle metadata

建议工期：

- 2 到 4 周

直接复用来源：

- `skillhub` 的 publish/review/download/search lifecycle
- `yao-meta-skill` 的 manifest/interface/validate/package contract

Definition of Done：

- 新协议 skill 包可以成功发布
- bundle 可以被下载
- registry 能返回 install-ready metadata
- search projection 能看到新字段

当前状态：

- registry / search / governance 这条线已基本达到上述 DoD，并新增了 internal distribution、internal feedback、candidate ingress、governance signal 能力。
- migration 实际文件以 `V39 / V40 / V41` 为准，不再使用早期草稿中的 `V42` 编号。

## Phase 2：Environment Kernel & Runtime 主链路

目标：

- registry 中的 skill 能被环境内核检索、装配、执行、记录结果

重点工作：

1. 抽出 Environment Kernel
   - task + env -> mode selection + skill selection

2. 保留双轴结构
   - manager axis：找 skill
   - orchestrator axis：跑 task

3. 引入 action resolver
   - 从 `actions.yaml` 决定 runner

4. 扩展 RunContext
   - skill hydrate
   - artifact standardization
   - result envelope

5. 回传 run feedback 到 registry

建议工期：

- 3 到 5 周

直接复用来源：

- `AgentSkillOS` 的 manager / orchestrator registry
- `RunContext`
- `workflow/service.py`
- active/dormant layering

Definition of Done：

- 能从 registry 拉一个 skill bundle
- 能在隔离环境执行默认 action
- 能写标准 artifact index
- 能回传 run feedback

当前状态：

- runtime 主执行链已经在 `AgentSkillOS` 代码内闭环，核心文件包括：
  - [AgentSkillOS/src/environment/models.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/environment/models.py)
  - [AgentSkillOS/src/environment/kernel.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/environment/kernel.py)
  - [AgentSkillOS/src/orchestrator/runtime/actions.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/actions.py)
  - [AgentSkillOS/src/orchestrator/runtime/install.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/install.py)
  - [AgentSkillOS/src/orchestrator/runtime/envelope.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/envelope.py)
  - [AgentSkillOS/src/orchestrator/runtime/resolve.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/resolve.py)
  - [AgentSkillOS/src/orchestrator/runtime/runners.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/runners.py)
  - [AgentSkillOS/src/orchestrator/runtime/feedback.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/feedback.py)
  - [AgentSkillOS/src/workflow/service.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/workflow/service.py)
  - [AgentSkillOS/src/orchestrator/freestyle/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/freestyle/engine.py)
  - [AgentSkillOS/src/orchestrator/dag/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/engine.py)
- 当前已经满足 runtime 侧的 Phase 2 DoD，但这里的 “回传 run feedback” 要按 producer 语义理解：
  - runtime 会写 `feedback.json` 和 `feedback_outbox/`
  - 若配置 `feedback_endpoint`，runtime 会以 Generic POST 发送 `RunFeedbackEnvelope`
  - registry 端对这些 feedback 的 ingestion、聚合、ranking 消费仍属于后续轨道
- runtime cap `max_sandbox / allow_network` 已完成从 `TaskRequest -> Environment Kernel -> ModeDecision -> ActionResolver` 的显式透传，不再是 engine 内的隐式局部开关

## Phase 3：Skill Factory

目标：

- 把 workflow / transcript / failure 转成 candidate skill package

重点工作：

1. 抽出 meta skill generation pipeline
2. 定义 candidate data model
3. 生成 candidate package 目录
4. 自动跑 package validator

建议工期：

- 2 到 4 周

直接复用来源：

- `yao-meta-skill` 的 templates / validation / packaging / governance check

Definition of Done：

- 给定 workflow note，能生成 candidate package
- candidate package 满足 package schema
- candidate 进入 lab input queue

## Phase 4：Skill Lab

目标：

- candidate skill 能在受控 lab 中被评测、比较、晋升

重点工作：

1. 把 autoresearch 从 strategy research 改成 skill research
2. 扩大 editable targets
   - `SKILL.md`
   - `actions.yaml`
   - `references/*`
   - `scripts/*`
   - `evals/*`

3. 固定 lab pack
   - trigger pack
   - action pack
   - governance pack

4. 固定 artifact 目录与状态机

建议工期：

- 4 到 6 周

直接复用来源：

- `loomiai-autoresearch` 的 runtime spec、project scaffold、artifact writers、MCP lifecycle

Definition of Done：

- candidate 可进入 lab project
- lab 可输出 regression report、governance report、promotion recommendation
- promotion 结果可提交到 registry

## Phase 5：Promotion、Canary 与反馈驱动优化

目标：

- candidate 不只是发布，而是能受控进入生产和回滚

重点工作：

1. promotion request
2. approval / reject / rollback
3. canary scope
4. ranking feedback ingestion
5. dormant -> active 晋升

建议工期：

- 3 到 5 周

直接复用来源：

- `skillhub` 的 review / promotion / governance 思路
- `AgentSkillOS` 的 layering 思路

Definition of Done：

- 新 skill 可通过 promotion 进入 published
- 失败 skill 可回滚
- 反馈指标可反映到 ranking / active-dormant 分层

## 4. 工作流拆组建议

### Track A：Contracts & Package

职责：

- `SKILL.md` / `manifest.json` / `actions.yaml` / `interface.yaml`
- validators
- bundler / exporter

主要依赖：

- `yao-meta-skill`
- `skillhub/docs/07-skill-protocol.md`

### Track B：Registry & Governance

职责：

- publish/review/scan/search/download
- metadata store
- search projection
- promotion

主要依赖：

- `skillhub`

### Track C：Runtime & Environment Kernel

职责：

- manager/orchestrator
- run context
- action resolve
- feedback reporter

主要依赖：

- `AgentSkillOS`

当前实现补充：

- 已完成 `Environment Kernel` 合同、resolver / runner 主链、run envelope / result envelope、feedback reporter 和 engine 端 cap enforcement
- 已落地的 runtime policy 字段包括：
  - `feedback_endpoint`
  - `feedback_auth_token_env`
  - `feedback_timeout_sec`
  - `feedback_max_retries`
  - `max_sandbox`
  - `allow_network`
- 当前这一轨不再是“纯设计”，而是“可联调、可回归测试的实现态”

### Track D：Factory & Lab

职责：

- candidate generation
- lab runtime
- eval pipeline
- promotion gate evidence

主要依赖：

- `yao-meta-skill`
- `loomiai-autoresearch`

### Track E：Integration & Migration

职责：

- registry-runtime 对接
- package 迁移
- run feedback ingestion
- old skill repo migration

## 5. 每阶段的接口冻结顺序

建议顺序：

1. `actions.yaml` schema
2. registry install bundle response
3. runtime run feedback envelope
4. candidate package envelope
5. promotion submission envelope

理由：

- 1 和 2 决定运行链路
- 3 决定反馈和 ranking
- 4 和 5 决定自进化链路

## 6. 推荐的实施颗粒度

### 6.1 第一批必须实现的对象

- `SkillPackageValidatorV2`
- `ActionManifestParser`
- `RuntimeInstallBundle`
- `ActionResolver`
- `RunFeedbackReporter`
- `CandidateSkillRecord`
- `LabRunRecord`
- `PromotionSubmission`

当前状态：

- 下面这些 runtime 对象已经在 `AgentSkillOS` 主链实现：
  - `ActionManifestParser`
  - `RuntimeInstallBundle`
  - `ActionResolver`
  - `RunFeedbackReporter`
- 对应代码：
  - [AgentSkillOS/src/orchestrator/runtime/actions.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/actions.py)
  - [AgentSkillOS/src/orchestrator/runtime/install.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/install.py)
  - [AgentSkillOS/src/orchestrator/runtime/resolve.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/resolve.py)
  - [AgentSkillOS/src/orchestrator/runtime/feedback.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/feedback.py)

### 6.2 第二批实现的对象

- `LayeringRefresher`
- `SuccessRateSnapshotJob`
- `GovernanceScoreSnapshotJob`
- `CandidateDiscoveryJob`

### 6.3 暂缓实现的对象

- 在线 LLM 推荐排序
- 自动百分比灰度
- 多 registry federation
- 个性化推荐

## 7. 迁移计划

### 7.1 旧 skill 迁移

分三类处理：

1. `SKILL.md only`
   - 补 `manifest.json`
   - 生成缺省 `actions.yaml`
   - 在当前 runtime 兼容实现里，未迁移 skill 也会被合成 synthetic default `instruction` action，而不会自动猜测脚本入口

2. `SKILL.md + scripts`
   - 补 action contract
   - 补 runtime profile

3. `complex governed skill`
   - 补 eval suite
   - 补 governance metadata

### 7.2 旧 runtime 迁移

如果已有类似 `AgentSkillOS` 的执行路径，建议先包一层 compatibility adapter：

- 旧 skill discovery 保留
- 新 registry install bundle 转译为旧执行输入
- 逐步替换为 action resolver

当前实现补充：

- `AgentSkillOS` runtime 已处于这个 compatibility adapter 阶段：
  - skill discovery 仍保留在 manager axis
  - runtime 执行已经切到 declared action + resolver
  - 旧 `SKILL.md` 包仍通过 compatibility adapter 继续运行

### 7.3 旧 registry 迁移

如果已有 `skillhub` 数据，优先做 additive migration：

- 增表，不破坏老表
- projection 重建
- download API 增强

## 8. 风险与对策

### 风险 1：协议过晚冻结

后果：

- runtime 与 registry 反复返工

对策：

- Phase 0 必须先出 schema + validator + sample

### 风险 2：让 runtime 承担 registry 责任

后果：

- 审查、治理、执行耦合在一起

对策：

- registry 只发布 install bundle
- runtime 只执行 install bundle

### 风险 3：candidate 直发生产

后果：

- 线上 skill 质量失控

对策：

- 强制 lab gate
- promotion request 必经审查

### 风险 4：大规模 skill 检索退化

后果：

- skill 越多，系统越慢

对策：

- active/dormant layering 第一阶段就纳入设计，不要等 1 万 skill 后再补

### 风险 5：artifact 不标准

后果：

- lab、replay、ranking、governance 全部失真

对策：

- 所有 runner 强制输出标准 envelope 和 artifact index

## 9. 推荐的里程碑检查点

### Milestone A：Package Ready

检查点：

- skill v2 package 可验证、可打包、可发布

### Milestone B：Runtime Ready

检查点：

- runtime 可从 registry 取 skill 并执行 action

### Milestone C：Feedback Ready

检查点：

- 执行反馈可进入 registry 并用于排序

### Milestone D：Factory Ready

检查点：

- workflow/failure 可生成 candidate package

### Milestone E：Lab Ready

检查点：

- candidate 可进入 lab，并可生成 promotion evidence

### Milestone F：Promotion Ready

检查点：

- approved candidate 可进入 production published

## 10. 最终建议

如果资源有限，最优顺序是：

1. 先做 package + registry
2. 再做 runtime
3. 再做 feedback
4. 最后做 factory + lab

原因很简单：

- 没有 package 和 registry，就没有可管理 skill
- 没有 runtime，就没有执行闭环
- 没有 feedback，就没有优化依据
- 没有前面三者，factory/lab 只能沦为空转研究系统

所以，任务2真正的实施顺序不是“先做最酷的自进化”，而是：

> 先把 skill 变成可被发布、可被执行、可被回传反馈的工业资产，再把生成与研究闭环接上去。
