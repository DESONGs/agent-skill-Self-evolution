# 仓库定位与 README 修正计划

日期：2026-04-03  
状态：active  
范围：只修正仓库定位与 README 主叙事，不改代码，不回写其它设计稿

## 1. 原始系统目标

这个项目的原始目标不是构建单一 runtime、单一 registry，或单一 Python 工具仓，而是形成一个自我迭代的 Skill OS。

其系统级目标来自现有设计文档中的五层定义：

1. Skill Package Layer
2. Environment Kernel & Runtime Layer
3. Registry / Search / Governance Layer
4. Skill Factory & Skill Lab Layer
5. Program Delivery Layer

对应的完整闭环应当是：

`Task / Transcript / Failure -> Environment Kernel -> Registry Search -> Runtime Hydration -> Action Execution -> Feedback -> Skill Factory -> Candidate -> Skill Lab -> Promotion Gate -> Registry Publish -> Reuse`

因此，项目的顶层定义必须始终围绕“自我迭代 Skill OS”展开，而不是围绕一期最小运行闭环展开。

## 2. 当前仓现状

当前 `agent-skill-platform` 仓已经吸收并整合了多个来源项目的核心源码和工程边界：

- `AgentSkillOS`
  - environment kernel
  - manager / orchestrator
  - runtime 执行链
- `skillhub`
  - registry / search / governance 的系统角色和接口边界
- `yao-meta-skill`
  - skill package contract、authoring、validation、governance 思路
- `loomiai-autoresearch`
  - skill lab、research runtime、artifact lifecycle、MCP 相关能力

因为这些源码已经被迁入当前仓，并且仓内提供了统一 SDK / CLI，所以当前仓看起来像一个单仓 Python repo。这是当前实现形态，不应反向改写项目的顶层目标定义。

## 3. 偏离点清单

当前 README 的主要偏离点包括：

### 3.1 把系统写成“Python 单仓主干”

README 直接把仓库定义为一个“可持续开发的 Python 主干仓”，这会让读者误以为项目的本体是单仓实现，而不是多来源整合后的 Skill OS。

### 3.2 把 `skillhub` 弱化成仓内最小 registry 的替代

README 用仓内 FastAPI + SQLite registry implementation 承担了首页中的 registry 叙事，导致 `skillhub` 作为 registry/search/governance 来源的系统位置被弱化。

### 3.3 把自我迭代闭环弱化成一期四接口闭环

README 过度突出：

- `actions.yaml`
- `RuntimeInstallBundle`
- `RunFeedbackEnvelope`
- `PromotionSubmission`

这四条接口是一阶段收口接口，但不是 Skill OS 的全部目标。当前表述容易让读者误以为项目只剩“publish / run / feedback”。

### 3.4 把仓内 SDK / CLI 提升成首页主叙事

README 把 Python API / CLI 放到了过于靠前的位置，使首页重心从“系统目标与来源整合”漂移到“当前仓内怎么调用”。

## 4. 统一定位结论

本仓的正式定位统一为：

- `agent-skill-platform` 是新的统一主仓
- 它面向的是自我迭代 Skill OS 的完整目标
- 四个参考项目属于“已吸收整合的来源”
- 它们不应再在 README 首页中被写成当前仓外部并列运行边界

同时，必须明确：

- 当前仓已经吸收了大量核心源码
- 当前仓可以承载完整实现方向上的继续开发
- 当前仓内某些能力仍然只是当前落地状态，不等于所有生产级能力已经完成

也就是说：

- 本仓是主仓
- 不是工作台
- 不是参考壳
- 也不应被表述成“只是组合几个外部系统的胶水层”

## 5. README 修正原则

README 的修正必须遵守以下原则：

### 5.1 先写系统目标和来源整合

README 首页前部必须优先回答：

- 这个项目是什么
- 为什么它是 Skill OS
- 四个来源项目分别贡献了什么能力

### 5.2 再写当前仓已吸收的实现

README 应说明当前仓已经内聚了哪些源码与能力，但不能让“当前实现形态”盖过“系统顶层定义”。

### 5.3 最后再写仓内 SDK / CLI / smoke

SDK / CLI 是当前仓的开发便利层，应该保留，但必须后置，不能成为首页主叙事。

### 5.4 不把仓内最小 registry 写成系统本体定义

仓内 registry integration implementation 可以被描述为：

- 当前主仓内的已落地实现
- 当前用于 install bundle / feedback / promotion 主链路验证的实现

但不应被写成：

- 项目最终 registry 形态
- 对 `skillhub` 系统角色的替代定义

## 6. README 修正范围

本轮修正范围固定如下：

### 修改

- `agent-skill-platform/README.md`
- `agent-skill-platform/docs/engineering/08-repo-positioning-and-readme-correction-plan.md`

### 不修改

- `agent-skill-platform/docs/README.md`
- `agent-skill-platform/docs/engineering/README.md`
- `agent-skill-platform/docs/engineering/00-program-overview-and-reuse-map.md`
- `agent-skill-platform/docs/engineering/05-implementation-roadmap.md`
- `agent-skill-platform/docs/engineering/06-integration-freeze-and-delivery-plan.md`

本文件的目的不是回写设计稿，而是固定当前仓首页文档的正式定位口径，避免后续 README 再次偏到“单仓最小实现说明”。
