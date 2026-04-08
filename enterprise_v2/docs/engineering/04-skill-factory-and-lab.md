# Skill Factory And Lab

日期：2026-04-02

本文是任务2的落地设计稿，目标不是再解释“为什么要做 skill factory / skill lab”，而是把它拆成可以直接开工的工程边界、目录结构、数据模型、调度链路、评测门禁和晋升路径。

本文只使用两类一手证据：

- `yao-meta-skill`：技能如何被生产、包装、评测、治理、导出
- `loomiai-autoresearch`：受控研究 runtime、pack/project 结构、MCP/CLI 生命周期、artifact 落盘

对应的代码和文档路径，后文会逐层引用。

## 0. 设计结论

如果把这条线真正做成工程，最稳的落地方式不是“生成一个大而全的自动 skill 工厂”，而是把系统拆成两层：

1. `Skill Factory`
   - 输入 workflow、transcript、failure、SOP、已有 skill 片段
   - 输出 candidate skill package
   - 负责“生成什么 skill、边界是什么、怎么命名、怎么声明 action”

2. `Skill Lab`
   - 输入 candidate skill package
   - 在受控 runtime 里执行评测、回归、扫描、包装、晋升
   - 负责“这个 skill 是否能上线、是否可复用、是否能被 registry 接收”

这两层之间的交界不是 prompt，而是一个标准化 candidate artifact。

## 1. 参考仓库的可复用边界

### 1.1 `yao-meta-skill` 适合复用的部分

`yao-meta-skill` 的价值不是“它有一套 skill 文档”，而是它已经把 skill 当成一个工程资产在运作。

可以直接复用的模块：

- `SKILL.md` 的触发优先、轻入口原则
- `manifest.json` 的治理字段和成熟度字段
- `agents/interface.yaml` 的中立兼容元数据
- `references/` 作为长文档、方法论、边界说明承载区
- `scripts/` 作为确定性 gate、打包、评测、报告生成的执行层
- `evals/` 作为固定评测集和 holdout 集
- `reports/` 作为迭代证据、质量证据、晋升证据

关键文件：

- [yao-meta-skill/SKILL.md](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/SKILL.md)
- [yao-meta-skill/manifest.json](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/manifest.json)
- [yao-meta-skill/agents/interface.yaml](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/agents/interface.yaml)
- [yao-meta-skill/references/skill-engineering-method.md](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/references/skill-engineering-method.md)
- [yao-meta-skill/scripts/trigger_eval.py](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/scripts/trigger_eval.py)
- [yao-meta-skill/scripts/run_eval_suite.py](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/scripts/run_eval_suite.py)
- [yao-meta-skill/scripts/resource_boundary_check.py](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/scripts/resource_boundary_check.py)
- [yao-meta-skill/scripts/governance_check.py](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/scripts/governance_check.py)
- [yao-meta-skill/scripts/cross_packager.py](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/scripts/cross_packager.py)
- [yao-meta-skill/scripts/promotion_checker.py](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/scripts/promotion_checker.py)
- [yao-meta-skill/scripts/create_iteration_snapshot.py](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/scripts/create_iteration_snapshot.py)

它提供的最重要的工程方法是：

- 先写触发面，再扩正文
- 先校验边界，再扩包体
- 先跑 holdout，再谈晋升
- 先有证据，再允许 library/governed 化

### 1.2 `loomiai-autoresearch` 适合复用的部分

`loomiai-autoresearch` 的核心价值是它已经把“可控研究 runtime”做出来了，而且不是纯代码实验，而是 CLI + MCP 双入口。

可以直接复用的模块：

- pack manifest 和 research spec schema
- project scaffold
- run lifecycle 和状态机
- artifact index 和写盘工具
- MCP server / job store / cancel / continue / status / read-artifact 这条链路
- gate policy 和 mutation policy 的控制回路

关键文件：

- [loomiai-autoresearch/README.md](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/README.md)
- [loomiai-autoresearch/docs/runtime-architecture.md](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/docs/runtime-architecture.md)
- [loomiai-autoresearch/src/autoresearch_agent/core/packs/schema.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/packs/schema.py)
- [loomiai-autoresearch/src/autoresearch_agent/core/packs/project.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/packs/project.py)
- [loomiai-autoresearch/src/autoresearch_agent/core/runtime/spec.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/runtime/spec.py)
- [loomiai-autoresearch/src/autoresearch_agent/core/runtime/manager.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/runtime/manager.py)
- [loomiai-autoresearch/src/autoresearch_agent/core/runtime/lifecycle.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/runtime/lifecycle.py)
- [loomiai-autoresearch/src/autoresearch_agent/core/artifacts/manifest.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/artifacts/manifest.py)
- [loomiai-autoresearch/src/autoresearch_agent/core/artifacts/writers.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/artifacts/writers.py)
- [loomiai-autoresearch/src/autoresearch_agent/mcp/server.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/mcp/server.py)
- [loomiai-autoresearch/src/autoresearch_agent/mcp/job_store.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/mcp/job_store.py)
- [loomiai-autoresearch/src/autoresearch_agent/core/search/gate_policy.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/search/gate_policy.py)
- [loomiai-autoresearch/src/autoresearch_agent/core/search/mutation_policy.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/search/mutation_policy.py)
- [loomiai-autoresearch/src/autoresearch_agent/core/strategy.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/strategy.py)
- [loomiai-autoresearch/tests/test_runtime_flow.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/tests/test_runtime_flow.py)
- [loomiai-autoresearch/tests/test_project_scaffold.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/tests/test_project_scaffold.py)

它提供的最重要的工程方法是：

- 单一 spec 驱动运行
- run-local artifact 目录
- status / continue / cancel / list_artifacts / read_artifact
- pack 负责领域逻辑，runtime 负责执行生命周期

## 2. 工程目标

本设计的目标不是“做一个能生成 skill 的 prompt 工具”，而是做一套可以被工程团队持续维护的能力生产线：

1. 把 workflow、transcript、failure、SOP、脑暴笔记，统一变成 candidate skill
2. 把 candidate skill 统一放进受控 skill lab
3. 把 skill lab 的实验结果变成可审核、可回放、可晋升的证据
4. 把通过门禁的 candidate 发布成 registry 资产
5. 把发布后的 skill 再喂回 runtime，形成下一轮复用

所以，任务2最终应该被落成下面四个角色：

- `skill factory`
- `skill lab`
- `registry/publish target`
- `runtime consumer`

## 3. Candidate Skill 的数据模型

### 3.1 Candidate 的最小定义

一个 candidate skill 不是一段 prompt，而是一个“待晋升能力包”的完整定义。

建议至少包含这些字段：

| 字段 | 含义 | 来源 |
|---|---|---|
| `candidate_id` | 候选实例 ID | 生成器 |
| `candidate_slug` | 人类可读 slug | 生成器 |
| `source_kind` | workflow / transcript / failure / composition / manual | factory |
| `source_refs` | 原始来源引用列表 | factory |
| `problem_statement` | 这个 skill 解决什么重复问题 | factory |
| `target_user` | 目标使用者 | factory |
| `skill_boundary` | 负责什么、不负责什么 | factory |
| `trigger_description` | frontmatter 触发描述 | factory |
| `anti_triggers` | 不应路由到这里的近邻请求 | factory |
| `default_action` | 默认 action id | factory |
| `actions` | 显式 action contract 列表 | factory |
| `governance` | owner / maturity / review cadence / trust | lab / registry |
| `pack_id` | 所属 pack | lab |
| `editable_target` | 唯一可变输入面 | lab |
| `lab_run_id` | 最近一次实验 run | lab |
| `metrics` | trigger / boundary / safety / portability / utility | lab |
| `promotion_state` | draft / lab_ready / gated / published / rejected | lab / registry |
| `published_skill_id` | 发布后 skill 主键 | registry |

### 3.2 推荐的 candidate 物理形式

为了尽量复用 `loomiai-autoresearch` 当前单 editable target 的运行模型，建议 candidate 的 canonical 表达先采用一个单文件 spec：

- `workspace/candidate.yaml`

这个文件作为“单一真源”，其他所有 skill package 文件都从它生成：

- `workspace/generated/<candidate_slug>/SKILL.md`
- `workspace/generated/<candidate_slug>/manifest.json`
- `workspace/generated/<candidate_slug>/actions.yaml`
- `workspace/generated/<candidate_slug>/agents/interface.yaml`
- `workspace/generated/<candidate_slug>/references/*`
- `workspace/generated/<candidate_slug>/scripts/*`
- `workspace/generated/<candidate_slug>/evals/*`

这样做的好处是：

- 可以直接复用当前 `research.yaml -> editable_targets[0] -> runtime` 的结构
- 先不强迫 runtime 支持多文件直接编辑
- 允许 candidate 先是一个结构化 spec，再被渲染成完整包

### 3.3 Candidate 状态机

建议状态机如下：

```text
created -> normalized -> lab_ready -> running -> evaluated
evaluated -> gate_passed -> promotion_pending -> published
evaluated -> gate_failed -> needs_revision
promotion_pending -> rejected
published -> superseded -> archived
```

这里要刻意把“实验状态”和“发布状态”分开：

- `running / evaluated / gate_passed` 属于 lab
- `promotion_pending / published / archived` 属于 registry

不要把两者揉成一个大状态机。

## 4. Skill Factory 的工程分解

### 4.1 工厂输入

Skill Factory 的输入不是一个抽象“需求”，而是几类具体可追踪的原材料：

- repeated workflow note
- chat transcript
- failed task log
- user SOP / playbook
- 已有 skill 的修复 diff
- 组合调用历史

每类输入都应该先标准化成 `source_ref`，再进入 candidate 生成链路。

### 4.2 工厂输出

工厂输出不是最终 skill，而是 candidate package 的草稿：

```text
candidate/
  candidate.yaml
  generated/
    SKILL.md
    manifest.json
    actions.yaml
    agents/interface.yaml
    references/
    scripts/
    evals/
```

### 4.3 工厂核心步骤

建议生成链路分成五步：

1. `classify`
   - 判断这是不是应该被做成 skill
   - 复用 `yao-meta-skill` 的 non-skill decision 思路

2. `bound`
   - 固化 skill boundary
   - 写出 trigger、anti-trigger、输出契约

3. `compose`
   - 生成 `SKILL.md`、`actions.yaml`、`manifest.json`、`interface.yaml`
   - 从模板或已有 skill 片段拼装 references/scripts/evals

4. `package`
   - 生成可执行目录包和 zip bundle

5. `hand off`
   - 把 candidate 丢给 lab，不直接进 registry

### 4.4 工厂直接复用 `yao-meta-skill` 的方法

这里建议直接沿用 `yao-meta-skill` 的方法论，不要重写一套“skill 写作学”。

可以直接复用的思路：

- `SKILL.md` 只保留路由和最小执行骨架
- 长文档放 `references/`
- 确定性逻辑放 `scripts/`
- 可执行门禁放 `evals/`
- 工程证据放 `reports/`

对应文件：

- [yao-meta-skill/SKILL.md](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/SKILL.md)
- [yao-meta-skill/references/skill-engineering-method.md](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/references/skill-engineering-method.md)
- [yao-meta-skill/references/gate-selection.md](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/references/gate-selection.md)
- [yao-meta-skill/references/operating-modes.md](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/references/operating-modes.md)
- [yao-meta-skill/references/resource-boundaries.md](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/references/resource-boundaries.md)
- [yao-meta-skill/references/governance.md](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/references/governance.md)

### 4.5 工厂建议新增的元数据

`manifest.json` 不应该只是“项目名和版本”，而应该成为 skill 的治理主文件。

建议字段：

```json
{
  "name": "github-pr-review",
  "version": "1.0.0",
  "owner": "platform-agent-team",
  "status": "active",
  "maturity_tier": "production",
  "lifecycle_stage": "library",
  "review_cadence": "quarterly",
  "context_budget_tier": "production",
  "target_platforms": ["openai", "claude", "generic"],
  "factory_components": ["references", "scripts", "evals", "reports"],
  "risk_level": "medium",
  "source_type": "workflow",
  "source_refs": ["note://...", "trace://..."]
}
```

这部分可以直接复用 `yao-meta-skill/manifest.json` 的字段哲学：

- owner
- status
- maturity_tier
- lifecycle_stage
- review cadence
- target platforms

### 4.6 工厂输出的 skill package 目录

建议的 skill 目录结构如下：

```text
candidate-package/
├── SKILL.md
├── manifest.json
├── actions.yaml
├── agents/
│   └── interface.yaml
├── references/
├── scripts/
├── evals/
├── reports/
├── templates/
└── assets/
```

这个结构同时满足三件事：

- `yao-meta-skill` 的互操作风格
- `skillhub` 的包协议风格
- 未来 registry / runtime 的可执行性

## 5. Skill Package 的工程规范

### 5.1 `SKILL.md`

`SKILL.md` 只负责四件事：

- 触发面
- 工作边界
- 最小工作流
- 输出契约

不要把下面这些东西硬塞进 `SKILL.md`：

- 全部 evaluation 细节
- 全部 pack 元数据
- 全部脚本参数
- 全部平台适配差异

这点可以直接继承 `yao-meta-skill` 的原则：

- 先 route，再扩正文
- 让正文保持小而稳定

### 5.2 `actions.yaml`

建议新增 `actions.yaml` 作为 skill 的动作注册表。

原因非常简单：

- runtime 不能靠扫描 `scripts/` 猜执行入口
- agent 也不应该直接执行包内任意脚本
- action contract 必须显式、可验证、可审计

建议 schema：

```yaml
schema_version: actions.v1
actions:
  - id: run
    kind: script
    entry: scripts/run.py
    runtime: python3
    timeout_sec: 120
    sandbox: workspace-write
    input_schema:
      type: object
      required: [task]
    output_schema:
      type: object
      properties:
        summary:
          type: string
        artifacts:
          type: array
    side_effects:
      - writes_workspace
      - writes_reports

  - id: validate
    kind: script
    entry: scripts/validate.py
    runtime: python3
    timeout_sec: 30
    sandbox: read-only
```

### 5.3 `agents/interface.yaml`

`agents/interface.yaml` 作为中立兼容层，建议继续沿用 `yao-meta-skill` 的写法。

它应该负责：

- display_name
- short_description
- default_prompt
- canonical_format
- adapter targets
- execution context
- trust policy
- degradation strategy

对应参考：

- [yao-meta-skill/agents/interface.yaml](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/agents/interface.yaml)
- [yao-meta-skill/scripts/cross_packager.py](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/scripts/cross_packager.py)

### 5.4 `scripts/`

脚本层建议分四类：

- `run-*`
  - skill 的真实动作入口
- `validate-*`
  - package / action / boundary 校验
- `build-*`
  - package、adapter、bundle 构建
- `eval-*`
  - offline regression、holdout、judge、scan

不要把脚本目录变成没有边界的“工具杂货铺”。

### 5.5 `evals/`

`evals/` 建议至少包含四类数据：

- `trigger_cases`
- `boundary_cases`
- `holdout_cases`
- `safety_cases`

这些评测集的目标不是做模型 benchmark，而是保证：

- skill 是否会误触发
- skill 是否越界
- skill 是否能覆盖近邻请求
- skill 是否在安全边界内工作

### 5.6 `reports/`

`reports/` 不是装饰品，而是晋升证据。

建议包含：

- `candidate_registry.json`
- `iteration_ledger.md`
- `route_scorecard.json`
- `governance_score.json`
- `promotion_decisions.json`
- `portability_score.json`
- `context_budget.json`

这些概念在 `yao-meta-skill` 里已经形成了很明确的痕迹：

- [yao-meta-skill/reports/candidate_registry.json](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/reports/candidate_registry.json)
- [yao-meta-skill/reports/iteration_ledger.md](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/reports/iteration_ledger.md)
- [yao-meta-skill/reports/route_scorecard.md](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/reports/route_scorecard.md)
- [yao-meta-skill/reports/governance_score.json](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/reports/governance_score.json)
- [yao-meta-skill/reports/promotion_decisions.json](/Users/chenge/Desktop/skills-gp-%20research/yao-meta-skill/reports/promotion_decisions.json)

## 6. Skill Lab 的工程分解

### 6.1 Lab 的任务

Skill Lab 的职责是把 candidate skill 放进受控实验链路里，完成以下四件事：

1. 验证结构是否完整
2. 验证 trigger 是否稳定
3. 验证边界、安全、资源、兼容性
4. 验证 candidate 是否值得发布

### 6.2 Lab 项目的根目录结构

建议仍然沿用 `loomiai-autoresearch` 的项目约定，但把领域从 `prediction_market` 改为 `skill_research`。

推荐根目录结构：

```text
skill-lab-project/
├── research.yaml
├── datasets/
├── workspace/
│   ├── candidate.yaml
│   ├── baselines/
│   ├── generated/
│   └── published/
├── artifacts/
├── .autoresearch/
│   ├── runs/
│   ├── cache/
│   └── state/
└── packs/
    └── skill_research/
```

其中：

- `research.yaml` 继续作为 runtime 的中心 spec
- `workspace/candidate.yaml` 作为单一 editable target
- `workspace/generated/` 作为 package materialization 输出
- `artifacts/` 作为 run-local 产物
- `.autoresearch/` 继续承载状态、缓存、run 目录

### 6.3 Lab 里的 editable target 设计

`loomiai-autoresearch` 当前只支持单一 `editable_targets[0]`，而且默认是 `workspace/strategy.py`。

对 skill research，最推荐的第一版改法不是直接支持多文件编辑，而是：

- 把 editable target 改成一个 canonical spec 文件
- 由 spec 渲染出完整 skill package

也就是说：

```yaml
search:
  editable_targets:
    - workspace/candidate.yaml
```

这个做法最大化复用当前 runtime：

- 仍然是“一个可变面”
- 仍然可以由 `IterationEngine` 控制多轮 mutate / evaluate
- 只是 mutate 的对象从 `strategy.py` 的常量变成 `candidate.yaml` 的结构字段

### 6.4 `candidate.yaml` 推荐字段

建议 candidate spec 拆成下面这些 section：

```yaml
schema_version: skill.candidate.v1
candidate:
  id: "cand_20260402_001"
  slug: "github-pr-review"
  source_kind: "workflow"
  source_refs: ["trace://...", "note://..."]
  status: "draft"

skill:
  name: "GitHub PR Review"
  description: "Review PRs with bounded checks and CI triage."
  trigger_description: "Use when asked to review a PR, comment on a diff, or triage CI."
  anti_triggers:
    - "general explanation"
    - "translation only"
    - "brainstorm only"
  boundary:
    owns:
      - "PR review judgment"
      - "CI issue triage"
    does_not_own:
      - "merge approval"
      - "production hotfix execution"

actions:
  default_action: "review"
  items:
    - id: "review"
      kind: "script"
      entry: "scripts/review.py"
    - id: "triage"
      kind: "script"
      entry: "scripts/triage.py"

governance:
  owner: "platform-agent-team"
  maturity_tier: "production"
  review_cadence: "quarterly"
  visibility: "internal"

compatibility:
  targets: ["openai", "claude", "generic"]
  shell: "bash"
  runtime: "python3"
```

### 6.5 Lab pack 设计

`loomiai-autoresearch` 的 pack 设计已经很好地把领域逻辑下沉到 pack 层。

当前 pack 的关键参考：

- [loomiai-autoresearch/src/autoresearch_agent/packs/prediction_market/pack.yaml](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/packs/prediction_market/pack.yaml)
- [loomiai-autoresearch/src/autoresearch_agent/packs/prediction_market/templates/research.yaml](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/packs/prediction_market/templates/research.yaml)
- [loomiai-autoresearch/src/autoresearch_agent/packs/prediction_market/templates/strategy.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/packs/prediction_market/templates/strategy.py)

`skill_research` pack 应该继承同样的结构，只是 entrypoints 和 axes 完全换掉：

```json
{
  "schema_version": "pack.manifest.v1",
  "pack_id": "skill_research",
  "name": "Skill Research",
  "version": "0.1.0",
  "description": "Pack for generating and evaluating reusable agent skills.",
  "domain": "skill_research",
  "entry_profile": "default",
  "supported_formats": ["json", "yaml", "md", "zip"],
  "default_adapter": "canonical_skill_yaml",
  "default_objective": "maximize_publishability",
  "axes_catalog": {
    "trigger_precision": { "type": "float" },
    "boundary_quality": { "type": "float" },
    "action_contract_completeness": { "type": "float" },
    "eval_coverage": { "type": "float" },
    "security_score": { "type": "float" },
    "portability_score": { "type": "float" }
  },
  "editable_targets": ["workspace/candidate.yaml"],
  "entrypoints": {
    "candidate_template": "templates/candidate.yaml",
    "skill_template": "templates/SKILL.md",
    "package_builder": "builders/package.py",
    "trigger_evaluator": "evaluators/trigger.py",
    "boundary_evaluator": "evaluators/boundary.py",
    "governance_evaluator": "evaluators/governance.py"
  },
  "defaults": {
    "constraints": {
      "per_eval_token_budget": 150000,
      "eval_timeout_seconds": 900,
      "retention_hours": 168
    }
  },
  "security": {
    "allowed_env_refs": ["OPENAI_API_KEY", "OPENAI_BASE_URL"],
    "allowed_secret_refs": []
  },
  "compatibility": {
    "min_agent_version": "0.1.0"
  }
}
```

这个 pack 设计是从 `loomiai-autoresearch` 的现有 schema 直接演化来的，而不是重做一套机制。

对应 schema 参考：

- [loomiai-autoresearch/src/autoresearch_agent/core/packs/schema.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/packs/schema.py)

### 6.6 Lab artifacts 目录

`loomiai-autoresearch` 当前已经证明了 run-local artifact 目录是正确的工程方向。

现有 artifact 产物参考：

- `result.json`
- `summary.json`
- `iteration_history.json`
- `artifact_index.json`
- `best_strategy.py`
- `strategy.patch`
- `report.md`
- `dataset_profile.json`
- `dataset_snapshot.json`

对应实现参考：

- [loomiai-autoresearch/src/autoresearch_agent/core/runtime/manager.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/runtime/manager.py)
- [loomiai-autoresearch/src/autoresearch_agent/core/artifacts/manifest.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/artifacts/manifest.py)
- [loomiai-autoresearch/src/autoresearch_agent/core/artifacts/writers.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/artifacts/writers.py)
- [loomiai-autoresearch/tests/test_runtime_flow.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/tests/test_runtime_flow.py)

对 skill research，建议增加下面这些产物：

- `candidate.yaml`
- `generated_skill_package/`
- `candidate_package.zip`
- `trigger_eval.json`
- `boundary_eval.json`
- `governance_eval.json`
- `security_scan.json`
- `portability_eval.json`
- `promotion_decision.json`
- `candidate_patch.json`

其中：

- `artifact_index.json` 继续保留
- `best_strategy.py` 不再是核心产物，改成 `best_skill_package/`
- `strategy.patch` 不再是主补丁，改成结构化 `candidate_patch.json` 或 `package.diff`

### 6.7 实验状态机

建议 `RuntimeStatus` 从 strategy research 的：

- `created`
- `running`
- `finished`
- `failed`
- `continued`

演化成 skill research 的：

- `created`
- `normalized`
- `running`
- `evaluated`
- `gate_passed`
- `promotion_pending`
- `published`
- `failed`
- `continued`

`loomiai-autoresearch` 的当前 lifecycle 代码可以直接提供状态机骨架：

- [loomiai-autoresearch/src/autoresearch_agent/core/runtime/lifecycle.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/runtime/lifecycle.py)

## 7. Eval Pipeline

### 7.1 先说明：skill 的 eval 不等于 strategy 的 eval

`loomiai-autoresearch` 当前的评测对象是策略参数与策略函数，核心指标是：

- fitness
- pnl
- accuracy
- drawdown
- trade count

对应参考：

- [loomiai-autoresearch/src/autoresearch_agent/core/search/iteration_engine.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/search/iteration_engine.py)
- [loomiai-autoresearch/src/autoresearch_agent/core/search/gate_policy.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/search/gate_policy.py)
- [loomiai-autoresearch/src/autoresearch_agent/core/search/mutation_policy.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/core/search/mutation_policy.py)

Skill research 的评测对象应该换成：

- trigger precision / recall
- boundary accuracy
- action contract completeness
- safety / scan verdict
- portability compatibility
- pack validity
- artifact completeness
- promotion readiness

### 7.2 建议的评测顺序

1. `structure gate`
   - 校验 `SKILL.md`、`manifest.json`、`actions.yaml`、`interface.yaml`
   - 校验目录和文件白名单
   - 校验 package 大小和文件数量

2. `trigger gate`
   - 校验触发描述是否把正确任务路由进来
   - 校验近邻请求是否不会误触发

3. `boundary gate`
   - 校验 skill 负责范围是否清晰
   - 校验 `SKILL.md` 是否把不该做的事排除掉

4. `resource gate`
   - 校验 context budget
   - 校验 `SKILL.md` 体积
   - 校验 references/scripts/assets 是否被合理声明

5. `governance gate`
   - 校验 owner / maturity / review cadence / status
   - 校验 manifest 与 frontmatter 一致性

6. `security gate`
   - 校验脚本是否超出边界
   - 校验包内文件和 action 是否有危险扩展

7. `packaging gate`
   - 校验是否能导出到目标平台
   - 校验 adapter 是否生成成功

8. `promotion gate`
   - 只有上述门禁都过，才允许 candidate 进入 registry

### 7.3 可以直接复用的 gate 思路

#### 来自 `yao-meta-skill`

- `trigger_eval.py`
- `run_eval_suite.py`
- `resource_boundary_check.py`
- `governance_check.py`
- `cross_packager.py`
- `promotion_checker.py`

这些脚本非常适合作为 skill research 的 gate 原型。

#### 来自 `loomiai-autoresearch`

- `gate_policy.py`
- `mutation_policy.py`
- `iteration_engine.py`
- `artifact manifest`

这些模块适合保留“控制回路”而不是直接复用指标本身。

### 7.4 建议的 skill eval 产物

每轮 lab run 至少输出：

- `iteration_history.json`
- `candidate_eval.json`
- `gate_summary.json`
- `safety_scan.json`
- `promotion_decision.json`
- `artifact_index.json`

如果 candidate 通过晋升，还应该输出：

- `published_package.zip`
- `published_manifest.json`
- `published_adapter/`
- `release_notes.md`

## 8. 自动晋升和半自动晋升

### 8.1 自动晋升条件

适合自动晋升的 candidate 必须同时满足：

- `trigger_eval` 没有明显误触发
- `boundary` 清晰
- `security scan` 通过
- `packaging` 通过
- `governance` 达到目标成熟度
- `artifact` 完整

对于低风险、强确定性的 skill，可以允许自动晋升。

### 8.2 半自动晋升条件

如果 candidate 属于以下情况，建议保留人工审批：

- 新增了脚本执行能力
- 包含外部 API 依赖
- 属于组织关键路径
- 属于高影响治理 skill
- 触发面容易和其他 skill 混淆

这种情况下，lab 仍然可以自动生成所有证据，但 `promotion_state` 只能到 `promotion_pending`，不能直接 `published`。

### 8.3 晋升决策建议

建议把晋升决策变成结构化文件：

```json
{
  "candidate_id": "cand_20260402_001",
  "decision": "promote",
  "mode": "automatic",
  "reasons": [
    "trigger gate passed",
    "boundary gate passed",
    "security gate passed",
    "packaging gate passed"
  ],
  "scores": {
    "trigger_precision": 1.0,
    "boundary_quality": 0.94,
    "security_score": 0.98,
    "portability_score": 0.96
  }
}
```

这个决策对象应该进入 `reports/` 并和 candidate 一起保留。

## 9. MCP / CLI Runtime

### 9.1 当前 runtime 可以直接复用什么

`loomiai-autoresearch` 已经把 CLI 和 MCP 的职责边界做得很好，skill research 可以直接继承：

- CLI 负责本地初始化、校验、运行、状态查询、读取 artifact
- MCP 负责给外部 agent 提供标准工具面
- run 状态持久化到 `.autoresearch/state/mcp_jobs/`
- long-running task 采用 submit + poll 模式

对应参考：

- [loomiai-autoresearch/src/autoresearch_agent/mcp/server.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/mcp/server.py)
- [loomiai-autoresearch/src/autoresearch_agent/mcp/job_store.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/mcp/job_store.py)
- [loomiai-autoresearch/README.md](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/README.md)

### 9.2 skill research 需要新增的命令 / 工具

建议在现有 runtime 之上新增这些入口：

CLI:

- `init-skill-candidate`
- `validate-skill-package`
- `run-skill-lab`
- `continue-skill-lab`
- `list-skill-artifacts`
- `read-skill-artifact`
- `promote-skill-candidate`
- `export-skill-package`

MCP:

- `validate_project`
- `run_project`
- `continue_run`
- `cancel_run`
- `stop_run`
- `get_run_status`
- `list_artifacts`
- `read_artifact`
- `promote_candidate`

### 9.3 runtime 结构怎么改最省

最省改法不是重写 server，而是把当前 runtime 抽象层换成 skill research pack：

- `research.yaml` 保持
- `RuntimeManager` 保持
- `MCP` job store 保持
- `artifact` 写盘保持
- `pack` 和 `editable target` 的语义换掉

也就是说：

- 当前 runtime 是“策略研究 runtime”
- 未来 runtime 变成“skill research runtime”
- 二者共用同一套生命周期框架

### 9.4 运行时需要彻底换掉的东西

下面这些不能原样照搬：

- `workspace/strategy.py`
- `best_strategy.py`
- `strategy.patch`
- `maximize_pnl`
- `confidence_threshold / bet_sizing / max_bet_fraction` 这一组数值轴

替代成：

- `workspace/candidate.yaml`
- `best_skill_package/`
- `candidate_patch.json` 或 `package.diff`
- `maximize_publishability`
- `trigger_precision / boundary_quality / security_score / portability_score / governance_score`

## 10. 直接可复用模块清单

### 10.1 可以直接复用，不需要先改架构

来自 `yao-meta-skill`：

- `SKILL.md` 的轻入口理念
- `manifest.json` 的治理元数据字段
- `agents/interface.yaml` 的兼容层
- `references/` 的方法文档区
- `scripts/` 的 gate / pack / report 习惯
- `evals/` 和 `reports/` 的质量证据分层

来自 `loomiai-autoresearch`：

- `core/spec/research_config.py` 的 spec 组织方式
- `core/runtime/manager.py` 的 run 生命周期
- `core/runtime/lifecycle.py` 的状态机
- `core/artifacts/writers.py` 的原子写盘
- `core/artifacts/manifest.py` 的 artifact index
- `mcp/server.py` 和 `mcp/job_store.py` 的 submit/poll/cancel/continue 模式

### 10.2 可以复用，但必须改语义

来自 `yao-meta-skill`：

- `trigger_eval.py` -> skill trigger routing eval
- `run_eval_suite.py` -> skill regression suite
- `resource_boundary_check.py` -> skill context / resource boundary gate
- `governance_check.py` -> skill governance gate
- `cross_packager.py` -> skill adapter exporter
- `promotion_checker.py` -> candidate promotion decision

来自 `loomiai-autoresearch`：

- `core/packs/schema.py` -> candidate spec + skill pack spec
- `core/packs/project.py` -> skill lab scaffold
- `core/search/gate_policy.py` -> candidate gate policy
- `core/search/mutation_policy.py` -> candidate mutation policy
- `core/strategy.py` -> package rendering + source patching
- `core/search/iteration_engine.py` -> candidate iteration loop

### 10.3 不适合直接复用，应该替换

这些模块的控制结构可以借鉴，但业务语义要换掉：

- `prediction_market` pack
- `strategy.py` 作为可编辑对象
- `pnl / accuracy / drawdown` 指标体系
- `best_strategy.py`
- `strategy.patch`

## 11. 从 strategy research 到 skill research 的改造清单

这一段是整个文档最重要的迁移说明。

### 11.1 editable target 的改造

当前：

- 单 editable target = `workspace/strategy.py`

建议：

- 单 editable target = `workspace/candidate.yaml`

原因：

- skill research 需要同时控制 `SKILL.md`、`manifest.json`、`actions.yaml`、`interface.yaml`
- 但 runtime 先保留单一变更面最稳
- 通过生成器把 spec materialize 成完整 package，能最大化复用现有 runtime

### 11.2 objective 的改造

当前 objective:

- maximize_pnl
- maximize_accuracy
- minimize_drawdown

建议 objective:

- maximize_publishability
- maximize_trigger_precision
- maximize_boundary_clarity
- minimize_security_risk
- maximize_portability

### 11.3 mutation 的改造

当前 mutation 改的是数值常量：

- confidence_threshold
- bet_sizing
- max_bet_fraction
- prompt_factors

建议 mutation 改成 skill 结构字段：

- trigger_description
- anti_triggers
- boundary scope
- action contract
- eval case set
- governance metadata

### 11.4 artifacts 的改造

当前 artifacts 是：

- `best_strategy.py`
- `strategy.patch`
- `report.md`
- `dataset_profile.json`
- `dataset_snapshot.json`

建议 skill research artifacts 是：

- `best_skill_package/`
- `candidate_patch.json`
- `report.md`
- `trigger_eval.json`
- `boundary_eval.json`
- `governance_eval.json`
- `security_scan.json`
- `artifact_index.json`

### 11.5 pack 的改造

当前 `prediction_market` pack 负责：

- data adapter
- evaluator
- strategy template
- research template

参考文件：

- [loomiai-autoresearch/src/autoresearch_agent/packs/prediction_market/pack.yaml](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/packs/prediction_market/pack.yaml)
- [loomiai-autoresearch/src/autoresearch_agent/packs/prediction_market/templates/research.yaml](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/packs/prediction_market/templates/research.yaml)
- [loomiai-autoresearch/src/autoresearch_agent/packs/prediction_market/templates/strategy.py](/Users/chenge/Desktop/skills-gp-%20research/loomiai-autoresearch/src/autoresearch_agent/packs/prediction_market/templates/strategy.py)

`skill_research` pack 应该负责：

- candidate template
- package builder
- trigger evaluator
- boundary evaluator
- governance evaluator
- export adapter

## 12. candidate -> published 的闭环

建议把整个链路定义成六步：

1. `ingest`
   - 从 workflow / transcript / failure / SOP 收集输入

2. `normalize`
   - 生成 `candidate.yaml`
   - 填好 candidate 元数据、边界、动作、治理字段

3. `materialize`
   - 生成完整 skill package
   - 生成 `SKILL.md`、`manifest.json`、`actions.yaml`、`interface.yaml`、`references/`、`scripts/`、`evals/`

4. `evaluate`
   - 跑 trigger / boundary / resource / governance / security / packaging gates

5. `promote`
   - 自动或半自动生成 promotion decision
   - 通过则打包进 registry

6. `publish`
   - 将 package 送入 registry
   - 生成 published skill id 和版本 id

### 12.1 这个闭环里的责任分工

`skill factory` 负责：

- 1, 2, 3

`skill lab` 负责：

- 4, 5

`registry` 负责：

- 6

`runtime` 负责：

- 发布后消费 skill

### 12.2 和 downstream registry 的接口

candidate 通过 lab 之后，应该输出一个 registry-ready bundle：

- `published_bundle.zip`
- `published_manifest.json`
- `published_adapter/`
- `release_notes.md`

这个 bundle 的最低兼容目标，应至少满足：

- `SKILL.md`
- `manifest.json`
- `agents/interface.yaml`
- 目录结构白名单

这也是 `skillhub` 设计中已经被证明的方向。

## 13. 与 `skillhub` 的衔接方式

虽然本文重点不在 registry，但 candidate->published 最终要进入 registry，所以这里需要留一个明确接口。

对接时建议直接采用 `skillhub` 的资产观：

- `Skill` 是容器
- `SkillVersion` 是版本快照
- `SkillFile` 是文件索引
- `Tag` 是分发别名
- `Label` 是分类治理
- `Audit` 是安全审计

对应参考：

- [skillhub/docs/01-system-architecture.md](/Users/chenge/Desktop/skills-gp-%20research/skillhub/docs/01-system-architecture.md)
- [skillhub/docs/07-skill-protocol.md](/Users/chenge/Desktop/skills-gp-%20research/skillhub/docs/07-skill-protocol.md)
- [skillhub/docs/14-skill-lifecycle.md](/Users/chenge/Desktop/skills-gp-%20research/skillhub/docs/14-skill-lifecycle.md)
- [skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillPublishService.java](/Users/chenge/Desktop/skills-gp-%20research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillPublishService.java)
- [skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/security/SecurityScanService.java](/Users/chenge/Desktop/skills-gp-%20research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/security/SecurityScanService.java)
- [skillhub/server/skillhub-infra/src/main/java/com/iflytek/skillhub/infra/scanner/SkillScannerAdapter.java](/Users/chenge/Desktop/skills-gp-%20research/skillhub/server/skillhub-infra/src/main/java/com/iflytek/skillhub/infra/scanner/SkillScannerAdapter.java)

skill factory / lab 的职责不是替代 registry，而是给 registry 产出合格的包。

## 14. 推荐实施路线

### Phase 0: 只改 spec，不改 runtime 架构

- 新增 `skill_research` pack
- 把 editable target 改成 `workspace/candidate.yaml`
- 让 candidate spec 能 materialize 成 skill package

### Phase 1: 把 gate 和 artifact 打通

- 接入 trigger / boundary / governance / resource / packaging / security gates
- 让 lab 输出完整 artifact bundle

### Phase 2: 把 candidate 晋升接入 registry

- 生成 published bundle
- 对接 downstream registry
- 让 published 资产可下载、可搜索、可版本化

### Phase 3: 让 candidate 学会自举

- candidate 生成 candidate
- lab 评 candidate
- registry 收 candidate
- runtime 消费 candidate 的后继版本

## 15. 最小可开工清单

如果下一步真的要开工，我建议先做这 6 件事：

1. 定义 `candidate.yaml` schema
2. 定义 `skill_research` pack.yaml
3. 定义 `SKILL.md / manifest.json / actions.yaml / interface.yaml` 的最小模板
4. 定义 trigger / boundary / governance / packaging 四类 gate
5. 把 `loomiai-autoresearch` 的 runtime 改成 skill lab runtime
6. 把 `yao-meta-skill` 的评测脚本改成 skill research 的一等公民

这 6 件事做完，skill factory 和 skill lab 就不是概念，而是可持续迭代的工程系统。
