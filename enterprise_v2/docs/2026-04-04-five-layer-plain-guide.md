# 五层工程设计白话说明

日期：2026-04-04

这份文档是给“要快速看懂系统怎么跑”的人写的。

目标只有一个：把现有工程设计文档里最关键的几件事说清楚，而且尽量不用黑话。

先说一个容易混淆的点：

- 这里说的“五层”，是整个平台的五层工程拆分。
- 不是另一份文档里提到的“能力环境 / 执行环境 / 上下文环境 / 治理环境 / 演化环境”那组环境分层。

对应来源是 [docs/engineering/00-program-overview-and-reuse-map.md](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/docs/engineering/00-program-overview-and-reuse-map.md)。

## 1. 五层分别是什么

### 第一层：Skill 包层

这一层回答的是：

- 一个 skill 到底由哪些文件组成
- 哪些文件管说明，哪些文件管执行，哪些文件管评测

你可以把它理解成“skill 的标准包装盒”。

当前最小可运行包，至少要有这四个文件：

- `SKILL.md`
- `manifest.json`
- `actions.yaml`
- `agents/interface.yaml`

代码里是硬性要求，见：

- [src/orchestrator/runtime/install.py#L86](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/orchestrator/runtime/install.py#L86)
- [src/autoresearch_agent/core/skill_lab/pipeline.py#L16](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/autoresearch_agent/core/skill_lab/pipeline.py#L16)

一句话总结：

skill 不是一段 prompt，而是一个带说明、动作声明、兼容信息的目录包。

### 第二层：环境内核和运行时层

这一层回答的是：

- 这次任务该不该用 skill
- 该用哪些 skill
- 用什么执行模式
- skill 要拷贝到哪里再执行

你可以把它理解成“调度中心 + 临时工位”。

当前由两块代码负责：

- 环境判断：[src/environment/kernel.py](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/environment/kernel.py)
- 执行隔离：[src/orchestrator/runtime/run_context.py](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/orchestrator/runtime/run_context.py)

### 第三层：注册、搜索、治理层

这一层回答的是：

- skill 发布后放哪
- 怎么查到它
- 怎么记版本
- 怎么收执行反馈
- 怎么收晋升申请

你可以把它理解成“技能仓库 + 台账系统”。

当前主仓里是一个轻量实现，不是最终生产版，但主链路已经能跑通：

- [src/agent_skill_platform/registry/service.py](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/agent_skill_platform/registry/service.py)

### 第四层：Skill Factory 和 Skill Lab 层

这一层回答的是：

- 新 skill 怎么来
- 先生成什么，再验证什么
- 怎样决定能不能晋升

你可以把它理解成“新技能孵化器 + 实验室”。

当前主入口：

- [src/autoresearch_agent/core/skill_lab/pipeline.py](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/autoresearch_agent/core/skill_lab/pipeline.py)
- [src/autoresearch_agent/packs/skill_research/builders/materialize_candidate.py](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/autoresearch_agent/packs/skill_research/builders/materialize_candidate.py)

### 第五层：交付和落地层

这一层回答的是：

- 开发顺序怎么排
- 哪几条接口先冻结
- 先打通哪条链路

它更偏项目落地，不是运行时代码本身。

对应文档：

- [docs/engineering/05-implementation-roadmap.md](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/docs/engineering/05-implementation-roadmap.md)

## 2. skill 的最小单元到底是什么

从“给系统识别和执行”的角度看，最小单元不是整个目录，而是：

- 一个 `skill package`
- 里面声明的一个或多个 `action`

真正被执行时，最小执行单元是“某个 skill 里的某个 action”。

理由很直接：

1. `RuntimeInstallBundle` 先把整个 skill 当成一个安装包加载进来。
2. `ActionResolver` 再从 `actions.yaml` 里选出这次要跑的那个 action。
3. `Runner` 最终执行的是这个 action 对应的脚本、MCP 调用、指令或子代理动作。

代码证据：

- skill 包加载：[src/orchestrator/runtime/install.py#L60](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/orchestrator/runtime/install.py#L60)
- action 声明：[src/orchestrator/runtime/actions.py#L30](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/orchestrator/runtime/actions.py#L30)
- action 解析：[src/orchestrator/runtime/resolve.py#L156](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/orchestrator/runtime/resolve.py#L156)

所以白话说：

- “skill”是一个能力包
- “action”才是一次真正拿去执行的动作

## 3. skill 是怎么被调度执行的

当前主链路可以压成 6 步：

1. 用户任务先进入 workflow。
2. environment kernel 判断模式，并决定选哪些 skill。
3. run context 建一个隔离运行目录。
4. skill 被复制到这个隔离目录里。
5. action resolver 从 `actions.yaml` 里挑出要跑的 action。
6. runner 按 action 类型真正执行。

对应代码：

- workflow 入口：[src/workflow/service.py#L147](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/workflow/service.py#L147)
- 环境判断：[src/environment/kernel.py#L59](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/environment/kernel.py#L59)
- 隔离运行目录：[src/orchestrator/runtime/run_context.py#L54](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/orchestrator/runtime/run_context.py#L54)
- action 解析：[src/orchestrator/runtime/resolve.py#L170](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/orchestrator/runtime/resolve.py#L170)
- runner 执行：[src/orchestrator/runtime/runners.py#L245](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/orchestrator/runtime/runners.py#L245)

执行模式现在主要有三种：

- `no-skill`：不用 skill，直接跑
- `free-style`：选中 skill 后，由运行时自由调用
- `dag`：任务本身明显需要多步编排时走 DAG

环境内核的自动规则很简单：

- 没选到 skill，就走 `no-skill`
- 有 DAG 提示，就走 `dag`
- 否则走 `free-style`

见：

- [src/environment/kernel.py#L232](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/environment/kernel.py#L232)

## 4. skill 在什么环境里执行

当前不是在主仓里原地执行，而是在隔离目录里执行。

原因很朴素：

- 不想污染主工作区
- 不想让 CLI 顺着父目录乱发现别的环境
- 想把这次运行的日志、产物、反馈单独存下来

`RunContext` 里实际分了两块地方：

- `exec_dir`：临时执行目录，在系统临时目录下
- `run_dir`：持久目录，专门存日志、结果、反馈、产物索引

见：

- [src/orchestrator/runtime/run_context.py#L57](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/orchestrator/runtime/run_context.py#L57)

skill 被装进去以后，会挂到类似下面的位置：

- `exec_dir/.claude/skills/<skill_id>`

见：

- [src/orchestrator/runtime/install.py#L278](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/orchestrator/runtime/install.py#L278)
- [src/orchestrator/runtime/run_context.py#L288](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/orchestrator/runtime/run_context.py#L288)

运行时还会检查两类边界：

- sandbox 级别够不够
- 是否允许联网

见：

- [src/environment/kernel.py#L80](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/environment/kernel.py#L80)
- [src/orchestrator/runtime/resolve.py#L281](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/orchestrator/runtime/resolve.py#L281)

## 5. skill 和运行结果怎么存

### skill 本体怎么存

当前 registry 的轻量实现同时存三样东西：

- SQLite 里的技能和版本记录
- `storage/packages/` 下的展开包目录
- `storage/bundles/` 下的打包产物

见：

- [src/agent_skill_platform/registry/service.py#L35](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/agent_skill_platform/registry/service.py#L35)
- [src/agent_skill_platform/registry/service.py#L129](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/agent_skill_platform/registry/service.py#L129)

### 运行结果怎么存

每次运行都会单独落一个 run 目录，里面至少会有：

- `environment.json`
- `retrieval.json`
- `run_envelope.json`
- `result_envelope.json`
- `artifacts/`
- `feedback.json`

见：

- [src/workflow/service.py#L214](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/workflow/service.py#L214)
- [src/orchestrator/runtime/run_context.py#L81](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/orchestrator/runtime/run_context.py#L81)

### 反馈怎么存

反馈有两份：

- 本地 `feedback.json`
- `feedback_outbox/` 待投递文件

如果配置了反馈接口，还会异步发出去。

见：

- [src/orchestrator/runtime/feedback.py#L66](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/orchestrator/runtime/feedback.py#L66)

## 6. 怎么回测和评估

这里要分两条线说。

### 6.1 普通 runtime 线

普通 runtime 线主要做“执行”和“反馈”，不是 skill 孵化评测主场。

它会记录：

- 选了什么 skill
- 跑了什么 action
- 是否成功
- 产物有哪些
- 反馈是否送达

### 6.2 新 skill 的 lab 线

真正的“回测和评估”发生在 `skill_research` 这条 lab 线上。

当前流程是：

1. 读取 `workspace/candidate.yaml`
2. 把 candidate 物化成完整 skill 包
3. 跑 6 组评测
4. 汇总 gate
5. 生成 promotion 决策
6. 把结果写进 run artifacts

代码入口：

- [src/autoresearch_agent/core/skill_lab/pipeline.py#L285](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/autoresearch_agent/core/skill_lab/pipeline.py#L285)

当前 6 组评测是：

- trigger
- action
- boundary
- governance
- resource
- safety

见：

- [src/autoresearch_agent/core/skill_lab/pipeline.py#L23](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/autoresearch_agent/core/skill_lab/pipeline.py#L23)

最后会产出这些关键文件：

- `trigger_eval.json`
- `action_eval.json`
- `boundary_eval.json`
- `governance_eval.json`
- `resource_eval.json`
- `safety_eval.json`
- `gate_summary.json`
- `promotion_decision.json`
- `report.md`

见：

- [src/autoresearch_agent/core/skill_lab/pipeline.py#L189](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/autoresearch_agent/core/skill_lab/pipeline.py#L189)

白话说：

- 不是先发布再看效果
- 而是先在 lab 里把这包 skill 做完整检查，再决定能不能进下一步

## 7. 新 skill 是怎么生成的

当前代码不是“直接让 agent 写完整 skill 目录”，而是走两段式：

1. 先生成一个 `candidate.yaml`
2. 再由 materializer 把它展开成完整 skill 包

这个设计非常关键，因为它把“可编辑的东西”先收缩成一个单文件。

pack manifest 已经把唯一可编辑目标写死了：

- `workspace/candidate.yaml`

见：

- [src/autoresearch_agent/packs/skill_research/pack.yaml#L70](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/autoresearch_agent/packs/skill_research/pack.yaml#L70)

materializer 会根据 `candidate.yaml` 生成：

- `SKILL.md`
- `manifest.json`
- `actions.yaml`
- `agents/interface.yaml`
- `references/README.md`
- `evals/README.md`
- `reports/README.md`
- `scripts/*`

见：

- [src/autoresearch_agent/packs/skill_research/builders/materialize_candidate.py#L103](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/autoresearch_agent/packs/skill_research/builders/materialize_candidate.py#L103)

## 8. 新 skill 的生成路径是什么

当前主路径可以直接写成：

`workspace/candidate.yaml -> materialize_candidate() -> generated skill package -> evaluators -> promotion submission -> registry`

更细一点是：

1. `init-skill-lab` 建项目骨架
2. 人或 agent 修改 `workspace/candidate.yaml`
3. `validate` 临时生成 skill 包并先验一遍
4. `run-skill-lab` 在 run 目录里生成正式实验产物
5. `build_promotion_submission`
6. `registry.submit_promotion`

入口文件：

- lab API：[src/agent_skill_platform/lab/__init__.py](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/agent_skill_platform/lab/__init__.py)
- promotion 构建：[src/agent_skill_platform/models.py#L71](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/agent_skill_platform/models.py#L71)
- registry 入库：[src/agent_skill_platform/registry/service.py#L241](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/agent_skill_platform/registry/service.py#L241)

## 9. 具体 agent 现在改写什么文件

如果只看当前 `skill_research` 这条线，答案很明确：

- agent 真正应该改的是 `workspace/candidate.yaml`

不是下面这些：

- 不是直接手改 `SKILL.md`
- 不是直接手改 `manifest.json`
- 不是直接手改 `actions.yaml`
- 不是直接手改 `agents/interface.yaml`

因为这几个文件在当前链路里是“生成物”，不是主要编辑面。

证据：

- editable target 固定为 `workspace/candidate.yaml`：[src/autoresearch_agent/packs/skill_research/pack.yaml#L70](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/autoresearch_agent/packs/skill_research/pack.yaml#L70)
- pipeline 读取的也是这个文件：[src/autoresearch_agent/core/skill_lab/pipeline.py#L42](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/autoresearch_agent/core/skill_lab/pipeline.py#L42)

## 10. 现在实际走什么 loop

### 当前已经实现的 loop

现在已经落地的是这个 loop：

1. 写或修改 `workspace/candidate.yaml`
2. 物化成 skill 包
3. 跑各类 gate
4. 生成 `promotion_decision`
5. 产出 submission
6. 交给 registry 审核/接收

### 当前还没有实现成“自动多轮自改”的部分

这点要说清楚：

当前 `skill_research` pipeline 还不是一个自动多轮 agent 自我改写闭环。

现在代码里的 `iteration_history.json` 只有一次记录，写死是第 1 轮；也就是说，它现在更像“单轮实验 + 出报告”，不是“自动反复改 candidate 直到收敛”。

见：

- [src/autoresearch_agent/core/skill_lab/pipeline.py#L307](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/autoresearch_agent/core/skill_lab/pipeline.py#L307)

真正带自动多轮迭代的，是另一个 prediction market 示例线，不是 skill_research 主线：

- [src/autoresearch_agent/core/search/iteration_engine.py#L129](/Users/chenge/Desktop/skills-gp- research/agent-skill-platform/src/autoresearch_agent/core/search/iteration_engine.py#L129)

所以白话结论是：

- 现在 skill 生成链已经有“单轮生成 + 单轮评测 + 提交晋升”
- 但还没有做成“agent 自动多轮修改 `candidate.yaml` 直到 gate 通过”的完整闭环

## 11. 一页结论

如果只记住最重要的几句话，记这几句就够了：

1. 五层里，真正和你这次问题最相关的是第 1、2、3、4 层，分别是“skill 怎么长、怎么调度跑、怎么存、怎么孵化”。
2. 运行时真正执行的最小单元不是整个 skill，而是 skill 里的一个 action。
3. skill 不在主仓原地跑，而是在隔离出来的临时执行目录里跑，结果再写回 run 目录。
4. 新 skill 现在不是直接改整包文件，而是先改 `workspace/candidate.yaml`，再自动展开成完整 skill 包。
5. 当前 lab 已经能做单轮评测和晋升申请，但还没做到自动多轮自改闭环。
