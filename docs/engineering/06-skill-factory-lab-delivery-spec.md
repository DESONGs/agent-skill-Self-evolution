# Skill Factory / Skill Lab 交付规格

更新日期：2026-04-03

说明：

- 本文仍然描述 Factory / Lab 的目标交付规格，也就是“应该做成什么样”。
- 与当前代码实现对齐的落地口径，维护在 [07-skill-factory-lab-implementation-sync.md](/Users/chenge/Desktop/skills-gp-%20research/docs/engineering/07-skill-factory-lab-implementation-sync.md)。
- 如果本文与当前代码现状有差异，联调和开发排障时先以 `07` 文档记录的“当前实现行为”为准，再回到本文判断是否要继续补齐。

## 0. 范围与非目标

本文只定义 `Skill Factory / Skill Lab` 的工程闭环，覆盖：

- candidate skill 生成
- lab project 脚手架
- eval / regression / safety / governance pipeline
- promotion submission gate
- CLI / MCP 的 job lifecycle 接口面

本文明确不做两件事：

- 不设计主 runtime 的执行模式、agent 执行编排、底层 evaluator 内核
- 不设计 registry 内部表结构、索引结构、存储模型

## 1. 设计依据

以下路径是本设计的唯一依据，后文的复用和改造判断都只建立在这些真实文件之上：

- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/04-skill-factory-and-lab.md`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/README.md`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/SKILL.md`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/manifest.json`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/agents/interface.yaml`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/references/skill-engineering-method.md`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/trigger_eval.py`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/run_eval_suite.py`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/governance_check.py`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/resource_boundary_check.py`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/promotion_checker.py`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/create_iteration_snapshot.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/docs/runtime-architecture.md`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/packs/schema.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/packs/project.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/runtime/spec.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/runtime/manager.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/search/iteration_engine.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/mcp/server.py`

这些材料给出的约束很明确：

- `yao-meta-skill` 已经证明了“轻入口 + references/scripts/evals/reports + governance/promotion”的 skill 工程方法是可行的。
- `loomiai-autoresearch` 已经证明了“`research.yaml` + 单一 editable target + artifacts + submit/poll MCP”这条运行骨架是可复用的。
- 因此 Factory / Lab 的最省改法不是重做一套系统，而是把 skill 研究对象塞进现有 pack/project/spec/lifecycle 壳子里。

## 2. 核心工程决策

1. canonical candidate 只保留一个真源文件：`workspace/candidate.yaml`。
2. Factory 只负责 `ingest -> normalize -> materialize -> handoff`，不直接发布。
3. Lab 只负责 `mutate candidate spec -> materialize package -> gate -> produce submission bundle`。
4. generated skill package 永远是 `candidate.yaml` 的派生产物，不允许直接把生成包当 editable target。
5. downstream registry 只接收 submission bundle，不要求 Lab 感知 registry 内部存储细节。

## 3. Candidate Skill 数据模型

### 3.1 canonical 文件

Candidate 的 canonical 物理形式固定为：

- `workspace/candidate.yaml`

理由：

- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/docs/runtime-architecture.md` 已经把 `search.editable_targets[0]` 定义成运行时唯一受控变更面。
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/packs/schema.py` 和 `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/runtime/spec.py` 都默认围绕单 editable target 工作。
- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/04-skill-factory-and-lab.md` 已经给出 candidate spec 驱动 materialization 的方向。

### 3.2 schema

建议 schema 版本固定为 `skill.candidate.v1`，字段拆成 8 个 section：

| section | 作用 | 归属 |
| --- | --- | --- |
| `candidate` | candidate 身份、状态、来源类型 | factory / lab |
| `sources` | 原始材料引用和归一化摘要 | factory |
| `qualification` | 为什么值得成为 skill | factory |
| `skill` | trigger、boundary、workflow、output contract | factory |
| `actions` | 动作契约与入口 | factory |
| `package` | 生成包布局和兼容目标 | factory |
| `governance` | owner / maturity / cadence / trust | lab |
| `lab` | mutation axes、baselines、gate profile、metrics | lab |
| `promotion` | promotion state、submission mode、evidence refs | lab |

建议最小字段如下：

```yaml
schema_version: skill.candidate.v1

candidate:
  id: cand_20260402_001
  slug: github-pr-review
  title: GitHub PR Review
  source_kind: workflow
  created_at: 2026-04-02
  status: normalized
  editable_target: workspace/candidate.yaml

sources:
  refs:
    - kind: workflow
      ref_id: workflow://gh-pr-review/001
      title: "PR review weekly workflow"
      evidence_path: workspace/sources/workflow-gh-pr-review-001.json
  normalized_summary:
    recurring_job: "Review GitHub PRs and triage CI failures with bounded actions"
    outputs:
      - review summary
      - issue list
      - follow-up suggestions
    exclusions:
      - merge approval
      - arbitrary repo write access

qualification:
  should_be_skill: true
  reasons:
    - recurring_workflow
    - routing_risk
    - governance_matters
  target_user: engineering productivity team
  problem_statement: "PR review and CI triage are repeated and easy to misroute"

skill:
  name: GitHub PR Review
  description: Review PRs and triage CI issues with explicit boundaries and reusable checks.
  trigger_description: Use when asked to review a PR, inspect a diff, summarize review issues, or triage CI failures for a PR.
  anti_triggers:
    - explain GitHub basics
    - translate a comment only
    - brainstorm coding ideas without reviewing code
  boundary:
    owns:
      - PR review findings
      - CI triage summary
      - change recommendation drafting
    does_not_own:
      - merge approval
      - force-push execution
      - production hotfix operation
  workflow:
    inputs:
      - pr_url_or_repo_pr
      - optional_ci_context
    steps:
      - inspect diff
      - inspect comments and checks
      - produce findings
    outputs:
      - structured review
      - ci triage notes

actions:
  default_action: review_pr
  items:
    - id: review_pr
      kind: script
      entry: scripts/review_pr.py
      runtime: python3
      timeout_sec: 180
      sandbox: workspace-write
    - id: triage_ci
      kind: script
      entry: scripts/triage_ci.py
      runtime: python3
      timeout_sec: 180
      sandbox: workspace-write

package:
  target_platforms: [openai, claude, generic]
  include_references: true
  include_scripts: true
  include_evals: true
  include_reports: false
  layout_profile: standard_skill_package

governance:
  owner: platform-agent-team
  maturity_tier: production
  lifecycle_stage: library
  review_cadence: quarterly
  context_budget_tier: production
  risk_level: medium
  trust:
    source_tier: local
    remote_inline_execution: forbid
    remote_metadata_policy: allow-metadata-only

lab:
  pack_id: skill_research
  gate_profile: balanced
  mutation_axes:
    - trigger_description
    - anti_triggers
    - boundary
    - actions
    - eval_coverage
    - governance
  baseline_refs: []
  metrics: {}
  last_run_id: ""

promotion:
  state: draft
  mode: automatic_or_manual
  submission_bundle: ""
  published_skill_ref: ""
```

### 3.3 状态机

Candidate 状态机与 job 状态机必须分离。

Candidate 状态建议为：

- `created`
- `normalized`
- `lab_ready`
- `running`
- `evaluated`
- `gate_failed`
- `gate_passed`
- `promotion_pending`
- `submitted`
- `published`
- `rejected`

Job 状态沿用现有 submit/poll 语义，只在 run manifest 和 MCP status 上表达：

- `queued`
- `running`
- `finished`
- `failed`
- `cancel_requested`
- `cancelled`
- `continued`

## 4. Skill Factory 的输入来源

### 4.1 统一的 source envelope

Factory 必须先把所有来源归一化成 `source_ref`，再进入 candidate 生成链路。

建议统一结构：

```yaml
source_ref:
  kind: workflow | transcript | failure | recurring_composition
  ref_id: string
  title: string
  created_at: string
  owner: string
  raw_path: string
  normalized_path: string
  summary:
    recurring_job: string
    outputs: [string]
    exclusions: [string]
    evidence_tags: [string]
```

### 4.2 workflow

适用材料：

- SOP
- runbook
- repeated workflow note
- playbook

Factory 动作：

1. 抽取 recurring job、触发词、输出物、边界。
2. 生成 `qualification` 和 `skill.workflow`。
3. 生成初版 `trigger_description`、`anti_triggers`、`actions`。

产物：

- `workspace/sources/workflow-*.json`
- `workspace/candidate.yaml`

### 4.3 transcript

适用材料：

- 对话 transcript
- 协作记录
- agent-human 调试记录

Factory 动作：

1. 提取重复出现的任务意图和用户期望输出。
2. 标记 near-neighbor requests，直接喂给 `anti_triggers`。
3. 提取高频 follow-up，生成 action seeds。

重点不是把 transcript 原文塞进 skill，而是把 transcript 变成：

- route evidence
- exclusions
- failure examples
- reusable action contract

### 4.4 failure

适用材料：

- failed task log
- eval 失败样本
- misroute 记录
- boundary breach 样本

Factory 动作：

1. 把 failure 变成 `evals/` 的初始反例。
2. 把 failure 原因映射到 `anti_triggers`、`boundary.does_not_own`、`safety_cases`。
3. 记录 `qualification.reasons` 中的 `routing_risk` 或 `safety_risk`。

failure 不是补充说明，而是 candidate 的一等输入。

### 4.5 recurring composition

适用材料：

- 多个 skill 的组合调用历史
- 一个 workflow 被稳定拆成若干动作的轨迹
- recurring chain 的 orchestration note

Factory 动作：

1. 判断是否应该做成单 skill，还是做成带多个 action 的 skill。
2. 抽取 action graph，生成 `actions.items`。
3. 如果组合里出现固定前置条件和后置产物，把它们写进 `skill.workflow`。

composition 输入的产物不是“再造一个大而全 skill”，而是：

- 合理的多 action 结构
- 明确的 default action
- 组合执行的 boundary 和 exclusions

## 5. Candidate Package 的生成结构

Factory 输出的 candidate package 必须至少 materialize 出以下结构：

```text
workspace/generated/<candidate_slug>/
├── SKILL.md
├── manifest.json
├── actions.yaml
├── agents/
│   └── interface.yaml
├── references/
├── scripts/
├── evals/
└── reports/
```

各文件职责如下：

| 文件/目录 | 职责 | 设计依据 |
| --- | --- | --- |
| `SKILL.md` | 触发面、边界、最小工作流、输出契约 | `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/SKILL.md` |
| `manifest.json` | owner / maturity / lifecycle / review cadence / target platforms | `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/manifest.json` |
| `actions.yaml` | 显式 action contract、入口、超时、sandbox、输入输出 schema | 本文新增 |
| `agents/interface.yaml` | 中立兼容层和 adapter target | `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/agents/interface.yaml` |
| `references/` | 长文档、方法、SOP、边界说明 | `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/SKILL.md` |
| `scripts/` | deterministic action / validate / build / eval 脚本 | `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/README.md` |
| `evals/` | trigger/boundary/holdout/safety 回归集 | `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/run_eval_suite.py` |
| `reports/` | candidate registry、scorecard、promotion evidence | `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/create_iteration_snapshot.py` |

`actions.yaml` 建议最小 schema：

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
  - id: validate
    kind: script
    entry: scripts/validate.py
    runtime: python3
    timeout_sec: 30
    sandbox: read-only
```

## 6. Skill Lab Project 目录与 project scaffold

### 6.1 项目目录

Lab project 推荐结构：

```text
skill-lab-project/
├── research.yaml
├── datasets/
│   ├── trigger/
│   │   ├── train/
│   │   ├── dev/
│   │   └── holdout/
│   ├── boundary/
│   ├── action/
│   ├── safety/
│   └── baselines/
├── workspace/
│   ├── candidate.yaml
│   ├── sources/
│   ├── generated/
│   ├── baselines/
│   └── submissions/
├── artifacts/
├── .autoresearch/
│   ├── runs/
│   ├── cache/
│   └── state/
└── packs/
    └── skill_research/
```

### 6.2 scaffold 改造点

`/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/packs/project.py` 当前会创建：

- `datasets`
- `workspace`
- `artifacts`
- `.autoresearch/runs`
- `.autoresearch/cache`
- `.autoresearch/state`
- `research.yaml`
- `workspace/strategy.py`

第一阶段改造要求：

1. 保留上述目录创建逻辑。
2. 把默认 editable file 从 `workspace/strategy.py` 替换成 `workspace/candidate.yaml`。
3. 新增 `workspace/generated`、`workspace/baselines`、`workspace/submissions`、`workspace/sources`。
4. 在 `datasets/` 下增加 `trigger/`、`boundary/`、`action/`、`safety/` 的 README 或空目录。
5. 在 `.autoresearch/state/pack_manifest.json` 中保存 `skill_research` pack manifest 的拷贝，沿用现有 manifest copy 习惯。

## 7. editable targets 如何从 strategy research 改造成 skill research

### 7.1 保留的契约

以下契约保持不变：

- `research.yaml` 仍然是 project spec 入口。
- `search.editable_targets[0]` 仍然是唯一受控变更面。
- `RuntimeManager` 仍然按 run 目录落盘 artifacts。
- `IterationEngine` 仍然驱动多轮 mutate / evaluate / select。

### 7.2 替换的对象

从：

- `workspace/strategy.py`
- 数值轴：`confidence_threshold / bet_sizing / max_bet_fraction / prompt_factors`
- objective：`maximize_pnl`

改成：

- `workspace/candidate.yaml`
- 结构轴：`trigger_description / anti_triggers / boundary / actions / eval_coverage / governance`
- objective：`maximize_publishability`

### 7.3 materialization flow

Lab 每一轮只允许改 `workspace/candidate.yaml`，之后执行：

1. `materialize_candidate(candidate.yaml) -> workspace/generated/<slug>/...`
2. `run_gate_suite(generated package)`
3. `write result/report/index artifacts`
4. `compare against baseline / previous candidate`
5. `select winner candidate spec`

这样做的好处：

- 不需要先做多文件 patch runtime。
- generated package 永远可重建。
- `candidate_patch.json` 可以稳定表达 spec 级变化。

## 8. Lab Pack 设计

### 8.1 physical pack

第一阶段只定义一个 runtime pack：

- `packs/skill_research/pack.yaml`

建议目录：

```text
packs/skill_research/
├── pack.yaml
├── templates/
│   ├── candidate.yaml
│   ├── SKILL.md.j2
│   ├── manifest.json.j2
│   ├── actions.yaml.j2
│   └── interface.yaml.j2
├── builders/
│   ├── materialize_candidate.py
│   └── export_submission_bundle.py
└── evaluators/
    ├── trigger_pack.py
    ├── action_pack.py
    ├── governance_pack.py
    ├── boundary_pack.py
    ├── resource_pack.py
    └── safety_pack.py
```

### 8.2 trigger pack

职责：

- 评估 `trigger_description`、`anti_triggers`、route confusion、holdout non-regression

直接复用的思路：

- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/trigger_eval.py`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/run_eval_suite.py`

第一阶段接口：

- 输入：`generated/SKILL.md`、`evals/trigger/*`
- 输出：`artifacts/trigger_eval.json`、`artifacts/route_scorecard.json`

### 8.3 action pack

职责：

- 校验 `actions.yaml`
- 校验 entry 文件存在
- 校验 timeout/sandbox/runtime/input_schema/output_schema
- 校验 package build/export 需要的动作契约完整度

第一阶段 action pack 不执行 runtime 内核，只做 contract validation 和 packaging readiness。

第一阶段接口：

- 输入：`generated/actions.yaml`、`generated/scripts/*`
- 输出：`artifacts/action_eval.json`、`artifacts/packaging_eval.json`

### 8.4 governance pack

职责：

- 校验 `manifest.json`、frontmatter、`agents/interface.yaml`
- 校验 owner / maturity / review cadence / status / lifecycle_stage
- 汇总 governance score 和 promotion readiness

直接复用的思路：

- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/governance_check.py`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/resource_boundary_check.py`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/promotion_checker.py`

第一阶段接口：

- 输入：`generated/manifest.json`、`generated/SKILL.md`、`generated/agents/interface.yaml`
- 输出：`artifacts/governance_eval.json`、`artifacts/resource_eval.json`、`artifacts/promotion_decision.json`

### 8.5 boundary / resource / safety pack

这三个 pack 第一阶段可以实现为 evaluator，而不是独立 runtime pack：

- `boundary_pack.py`
  - 检查 owns / does_not_own 是否与 boundary cases 一致
- `resource_pack.py`
  - 复用 context budget、quality density、目录引用检查
- `safety_pack.py`
  - 检查脚本白名单、危险扩展、未声明 side effect

## 9. artifact 目录、run status、result/report/index 设计

### 9.1 run 目录

沿用 `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/runtime/manager.py` 的 run-local 落盘方式，每个 run 都有独立目录。

建议 skill lab artifacts：

```text
<run_dir>/
├── run_manifest.json
├── run_spec.json
├── result.json
├── summary.json
└── artifacts/
    ├── candidate.yaml
    ├── candidate_patch.json
    ├── generated_skill_package/
    ├── candidate_package.zip
    ├── trigger_eval.json
    ├── route_scorecard.json
    ├── boundary_eval.json
    ├── action_eval.json
    ├── governance_eval.json
    ├── resource_eval.json
    ├── safety_eval.json
    ├── packaging_eval.json
    ├── gate_summary.json
    ├── promotion_decision.json
    ├── report.md
    └── artifact_index.json
```

### 9.2 run_manifest.json

保留现有 run manifest 骨架，只新增 skill lab 关心的字段：

- `candidate_id`
- `candidate_slug`
- `candidate_status`
- `gate_profile`
- `submission_ready`

### 9.3 result.json

`result.json` 作为机器可消费的最终结论：

```json
{
  "schema_version": "skill.lab.result.v1",
  "run_id": "run-20260402-001",
  "candidate_id": "cand_20260402_001",
  "status": "gate_passed",
  "best_candidate_ref": "artifacts/generated_skill_package",
  "metrics": {
    "trigger_precision": 1.0,
    "trigger_recall": 1.0,
    "boundary_quality": 0.95,
    "governance_score": 92,
    "resource_budget_ok": true,
    "packaging_ok": true
  },
  "promotion": {
    "decision": "promotion_pending",
    "mode": "manual",
    "reasons": ["script_actions_present"]
  }
}
```

### 9.4 summary.json

`summary.json` 保持轻量，只放轮询必须读到的字段：

- `run_id`
- `candidate_id`
- `status`
- `iteration_count`
- `gate_passed`
- `promotion_decision`
- `updated_at`

### 9.5 report.md

`report.md` 是人读摘要，必须至少包含：

- candidate 基本信息
- 关键 gate 结果
- regression 差异
- promotion 建议
- artifact 路径

### 9.6 artifact_index.json

继续沿用 artifact index 思路，但 skill lab 需要增加这几个字段：

- `artifact_role`
- `candidate_id`
- `gate_name`
- `content_type`
- `sha256`
- `size_bytes`

## 10. Eval / Regression / Safety / Governance Gate

### 10.1 gate 顺序

第一阶段 gate 顺序固定如下：

1. `structure gate`
2. `trigger gate`
3. `boundary gate`
4. `action gate`
5. `resource gate`
6. `governance gate`
7. `safety gate`
8. `packaging gate`
9. `promotion gate`

### 10.2 各 gate 的 pass 条件

| gate | pass 条件 | 直接依据 |
| --- | --- | --- |
| structure | `SKILL.md / manifest.json / actions.yaml / agents/interface.yaml` 存在且 schema 合法 | `/Users/chenge/Desktop/skills-gp- research/docs/engineering/04-skill-factory-and-lab.md` |
| trigger | train/dev/holdout 汇总后无新增误触发；near-neighbor 干净 | `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/run_eval_suite.py` |
| boundary | `owns / does_not_own` 与 boundary cases 一致 | 本文新增 |
| action | 所有 action entry 存在，contract 完整，sandbox/runtime 明确 | 本文新增 |
| resource | context budget 未超 tier；未引用空目录；`SKILL.md` 不过重 | `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/resource_boundary_check.py` |
| governance | manifest/frontmatter 对齐；owner/review cadence/status/maturity 合法；score 达标 | `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/governance_check.py` |
| safety | 没有未声明危险扩展和越界 side effect | 本文新增 |
| packaging | adapter 导出通过；bundle 结构白名单通过 | `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/README.md` |
| promotion | 前置 gate 全部通过，且 non-regression / evidence bundle 完整 | `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/promotion_checker.py` |

### 10.3 regression policy

第一阶段采用分层策略：

- `Scaffold`
  - 必过：structure、resource
  - 建议过：trigger
- `Production`
  - 必过：structure、trigger、resource、governance、packaging
- `Library`
  - 必过：Production 全部 + boundary + action
- `Governed`
  - 必过：Library 全部 + safety + human approval required

### 10.4 promotion policy

automatic promote 只允许同时满足：

- `trigger gate` 通过
- `boundary gate` 通过
- `action gate` 通过
- `resource gate` 通过
- `governance gate` 达到目标 maturity
- `safety gate` 通过
- `packaging gate` 通过
- candidate 未引入高风险脚本能力

否则统一进入：

- `promotion_pending`

## 11. MCP / CLI job lifecycle

### 11.1 复用原则

直接复用 `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/mcp/server.py` 的 submit + poll + cancel + artifact read 模式，不重新设计长任务生命周期。

### 11.2 CLI 接口

第一阶段 CLI 只需要下面这些命令：

- `skill-factory normalize-source --input <path> --kind <kind> --out workspace/sources/...`
- `skill-factory build-candidate --source-ref <path> --out workspace/candidate.yaml`
- `skill-factory materialize --candidate workspace/candidate.yaml --out workspace/generated/<slug>`
- `skill-lab init --project-root <path>`
- `skill-lab validate --project-root <path>`
- `skill-lab run --project-root <path>`
- `skill-lab continue --project-root <path> --run-id <run_id>`
- `skill-lab status --project-root <path> --run-id <run_id>`
- `skill-lab artifacts --project-root <path> --run-id <run_id>`
- `skill-lab read-artifact --project-root <path> --run-id <run_id> --artifact <path>`
- `skill-lab submit-promotion --project-root <path> --run-id <run_id>`

### 11.3 MCP 接口

第一阶段 MCP 工具面：

- `validate_project`
- `run_project`
- `continue_run`
- `cancel_run`
- `stop_run`
- `get_run_status`
- `list_artifacts`
- `read_artifact`
- `submit_promotion`

其中：

- `run_project` 的输入仍然是 `project_root` 和可选 `run_id`
- `get_run_status` 只返回 job 状态和关键 summary
- `list_artifacts` / `read_artifact` 继续读取 run-local artifacts
- `submit_promotion` 不直接发布，只生成 submission bundle 和 submission manifest

### 11.4 lifecycle

统一流程：

1. CLI 或 MCP 提交 `run_project`
2. 服务端返回 `run_id` 和 `queued/running`
3. 客户端轮询 `get_run_status`
4. 结束后调用 `list_artifacts`
5. 如需人工判断，读取 `promotion_decision.json`、`report.md`
6. 满足 gate 后调用 `submit_promotion`

## 12. candidate -> promotion submission 的流转

### 12.1 流转步骤

1. `ingest`
   - workflow / transcript / failure / recurring composition -> `workspace/sources/*.json`
2. `normalize`
   - 生成 `workspace/candidate.yaml`
3. `materialize`
   - 生成 `workspace/generated/<slug>/...`
4. `evaluate`
   - 生成全部 gate artifacts
5. `decide`
   - 生成 `promotion_decision.json`
6. `submit`
   - 导出 promotion submission bundle

### 12.2 submission bundle

Lab 交给 downstream registry 的 bundle 固定为：

```text
workspace/submissions/<candidate_slug>-<run_id>/
├── skill-package.zip
├── submission_manifest.json
├── promotion_decision.json
├── gate_summary.json
├── report.md
├── release_snapshot.json
└── artifact_index.json
```

其中 `submission_manifest.json` 建议字段：

- `schema_version`
- `candidate_id`
- `candidate_slug`
- `run_id`
- `package_path`
- `package_sha256`
- `promotion_decision`
- `gate_summary_path`
- `report_path`
- `submitted_at`

Lab 到此为止。registry 如何入库、建版本、建索引，不属于本文范围。

## 13. 哪些模块可直接复用，哪些必须改造

### 13.1 `yao-meta-skill`

| 模块 | 结论 | 说明 |
| --- | --- | --- |
| `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/README.md` | 直接复用方法论 | 直接复用“workflow/transcript/runbook -> skill package”的 authoring flow 和 packaging/test 习惯 |
| `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/SKILL.md` | 直接复用原则 | 复用轻入口、路由优先、references/scripts/reports 下沉原则 |
| `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/manifest.json` | 直接复用字段哲学 | owner、updated_at、status、maturity_tier、lifecycle_stage、context_budget_tier、review_cadence、target_platforms、factory_components 直接沿用 |
| `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/agents/interface.yaml` | 直接复用结构 | 兼容层字段和 trust/degradation 模型直接沿用 |
| `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/references/skill-engineering-method.md` | 直接复用方法 | qualification、boundary-first、trigger-first、risk-based gates、promotion policy 直接纳入 Factory/Lab 规则 |
| `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/trigger_eval.py` | 改语义复用 | 保留 semantic scoring、bucket/family stats/misfire 输出结构，输入从单 description 扩展到 candidate-generated package |
| `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/run_eval_suite.py` | 改语义复用 | 保留 train/dev/holdout 聚合框架和 family summary 输出 |
| `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/governance_check.py` | 改语义复用 | 保留 allowed status/maturity/review cadence、score_breakdown、manifest/frontmatter 校验 |
| `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/resource_boundary_check.py` | 改语义复用 | 保留 context budget、quality density、未声明目录检查，扫描对象从 skill package 扩展到 generated package |
| `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/promotion_checker.py` | 改语义复用 | 保留 gate aggregation 和 decision shell，替换当前 target-specific route/judge fields |
| `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/create_iteration_snapshot.py` | 改语义复用 | 保留 release snapshot 与 artifact 路径索引模式，改成 candidate/run 维度 |

### 13.2 `loomiai-autoresearch`

| 模块 | 结论 | 说明 |
| --- | --- | --- |
| `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/docs/runtime-architecture.md` | 直接复用运行边界 | 复用 `research.yaml`、单 editable target、artifact 落盘、MCP over stdio、submit/poll job model |
| `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/packs/schema.py` | 改语义复用 | `pack.manifest.v1`、`research.yaml.v1`、defaults merge、`editable_targets` 契约保留；默认 objective/search axis 改成 skill 语义 |
| `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/packs/project.py` | 改语义复用 | 保留 scaffold shell，默认文件从 `strategy.py` 换为 `candidate.yaml`，增加 lab 目录 |
| `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/runtime/spec.py` | 改语义复用 | 保留 spec normalize/validate 壳子，替换默认 pack、objective、editable target、output artifacts |
| `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/runtime/manager.py` | 改语义复用 | 保留 run/artifact/manifest/summary 写盘壳子，替换 strategy 加载、dataset profile、best_strategy 输出逻辑 |
| `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/search/iteration_engine.py` | 改语义复用 | 保留 iteration loop、history、best selection、gate policy 接口；替换 prediction-market evaluator 和 mutation axes |
| `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/mcp/server.py` | 直接复用工具面 | 保留 tool registry、job store、submit/poll/cancel/list/read artifact 流程，只补 `submit_promotion` 和 skill lab 描述 |

### 13.3 必须新增，不存在现成实现

第一阶段必须新增这些模块：

- `actions.yaml` schema 和 validator
- `candidate.yaml` schema 和 materializer
- `boundary_pack.py`
- `action_pack.py`
- `safety_pack.py`
- `submission_manifest.json` builder

## 14. 第一阶段 Lab backlog

### 14.1 shared contracts

| ID | 负责人 | 交付物 | 验收标准 |
| --- | --- | --- | --- |
| SH-01 | shared | `skill.candidate.v1` schema | 能校验 `workspace/candidate.yaml`，覆盖本文 section 3 所有字段 |
| SH-02 | shared | `actions.v1` schema | action entry/sandbox/runtime/input_schema/output_schema 均可校验 |
| SH-03 | shared | `skill.lab.result.v1` / `skill.lab.summary.v1` | MCP status 和 artifacts 可稳定消费 |

### 14.2 factory

| ID | 负责人 | 交付物 | 验收标准 |
| --- | --- | --- | --- |
| FAC-01 | factory | source normalizer | workflow/transcript/failure/recurring composition 都能生成 `source_ref` |
| FAC-02 | factory | candidate builder | 能从 `source_ref` 生成 `workspace/candidate.yaml` |
| FAC-03 | factory | package materializer | 能从 candidate materialize `SKILL.md / manifest.json / actions.yaml / agents/interface.yaml / references / scripts / evals` |
| FAC-04 | factory | baseline template set | 提供 `SKILL.md.j2 / manifest.json.j2 / actions.yaml.j2 / interface.yaml.j2 / candidate.yaml` 模板 |

### 14.3 lab

| ID | 负责人 | 交付物 | 验收标准 |
| --- | --- | --- | --- |
| LAB-01 | lab | `skill_research` pack manifest | 基于 `pack.manifest.v1` 可被 pack loader 识别 |
| LAB-02 | lab | project scaffold | `skill-lab init` 能生成 section 6 的目录 |
| LAB-03 | lab | trigger pack | 能输出 `trigger_eval.json`、`route_scorecard.json` |
| LAB-04 | lab | action pack | 能输出 `action_eval.json`、`packaging_eval.json` |
| LAB-05 | lab | governance/resource pack | 能输出 `governance_eval.json`、`resource_eval.json` |
| LAB-06 | lab | boundary pack | 能输出 `boundary_eval.json` |
| LAB-07 | lab | safety pack | 能输出 `safety_eval.json` |
| LAB-08 | lab | gate summary builder | 能输出 `gate_summary.json` 和最终 `promotion_decision.json` |
| LAB-09 | lab | artifact writer integration | `result.json / summary.json / artifact_index.json / report.md` 完整落盘 |
| LAB-10 | lab | promotion submission builder | 能导出 section 12.2 的 submission bundle |

### 14.4 MCP / CLI

| ID | 负责人 | 交付物 | 验收标准 |
| --- | --- | --- | --- |
| IF-01 | platform | `skill-lab run/continue/status/artifacts/read-artifact` CLI | submit/poll/cancel/read artifact 全链路可用 |
| IF-02 | platform | MCP tool mapping | `run_project/get_run_status/list_artifacts/read_artifact/submit_promotion` 全部返回结构化结果 |
| IF-03 | platform | job status projection | candidate status 与 job status 均可在 `summary.json` 和 MCP status 中读取 |

## 15. 第一阶段接口清单

### 15.1 文件接口

- `workspace/candidate.yaml`
- `workspace/generated/<candidate_slug>/SKILL.md`
- `workspace/generated/<candidate_slug>/manifest.json`
- `workspace/generated/<candidate_slug>/actions.yaml`
- `workspace/generated/<candidate_slug>/agents/interface.yaml`
- `artifacts/result.json`
- `artifacts/summary.json`
- `artifacts/gate_summary.json`
- `artifacts/promotion_decision.json`
- `workspace/submissions/<candidate_slug>-<run_id>/submission_manifest.json`

### 15.2 Python 接口

- `normalize_source(input_path, kind) -> source_ref`
- `build_candidate(source_ref) -> candidate_dict`
- `materialize_candidate(candidate_path, output_dir) -> generated_package_dir`
- `run_trigger_pack(package_dir, eval_dir) -> trigger_eval`
- `run_action_pack(package_dir) -> action_eval`
- `run_governance_pack(package_dir) -> governance_eval`
- `run_boundary_pack(package_dir, eval_dir) -> boundary_eval`
- `run_resource_pack(package_dir) -> resource_eval`
- `run_safety_pack(package_dir) -> safety_eval`
- `build_gate_summary(run_dir) -> gate_summary`
- `build_promotion_submission(run_dir) -> submission_dir`

### 15.3 CLI 接口

- `skill-factory normalize-source`
- `skill-factory build-candidate`
- `skill-factory materialize`
- `skill-lab init`
- `skill-lab validate`
- `skill-lab run`
- `skill-lab continue`
- `skill-lab status`
- `skill-lab artifacts`
- `skill-lab read-artifact`
- `skill-lab submit-promotion`

### 15.4 MCP 接口

- `validate_project`
- `run_project`
- `continue_run`
- `cancel_run`
- `stop_run`
- `get_run_status`
- `list_artifacts`
- `read_artifact`
- `submit_promotion`

## 16. 开工顺序

第一阶段推荐顺序：

1. 先落 `candidate.yaml` 和 `actions.yaml` 两个 contract。
2. 再落 materializer 和 `skill_research` pack。
3. 之后打通 trigger/action/governance 三个主 gate。
4. 然后把 result/report/index 和 submission bundle 打通。
5. 最后补 CLI/MCP 接口和 backlog 剩余 evaluator。

完成以上五步后，Factory / Lab 就具备工程闭环：

- Factory 可以把 workflow/transcript/failure/composition 变成 candidate
- Lab 可以把 candidate 变成可评估、可回归、可提交晋升的资产
- downstream registry 只需要接 submission bundle，而不必反向感知 Lab 内部实现
