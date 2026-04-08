# Skill Package And Actions

> 目标：把 `skill` 从“目录里的提示词”升级成“可发布、可安装、可调度、可校验、可导出、可回滚的能力包”。
>
> 本文只覆盖任务2的工程落地，不再讨论 task1 的环境哲学。

## 0. 这份文档要解决什么

这份文档回答 6 个工程问题：

1. `skill package` 的标准目录和文件职责是什么。
2. `SKILL.md`、`manifest.json`、`actions.yaml`、`agents/interface.yaml` 各自应该承载什么字段。
3. `references/`、`scripts/`、`evals/`、`tests/`、`adapters/`、`reports/` 应该如何分层。
4. 现有哪些仓库里的模块可以直接复用，哪些必须抽离重构，哪些应该新增。
5. 发布前校验、运行时校验、打包导出链路怎么串起来。
6. skill 安装缓存、bundle 结构、兼容 OpenSkills / Claude / skillhub 的边界在哪里。

---

## 1. 复用来源总览

先定结论：这件事不是从零做，而是把四个成熟原型拼成一个可落地体系。

| 来源仓库 | 主要可复用能力 | 角色定位 |
|---|---|---|
| `yao-meta-skill` | 触发面、治理、评测、包装导出、适配器合同 | skill authoring / packaging factory |
| `skillhub` | 包协议、目录约束、版本化 registry、发布/审核/扫描/下载/搜索 | skill registry / governance |
| `AgentSkillOS` | skill 发现、目录扫描、隔离 runtime、run context、执行模式 | skill runtime / scheduler |
| `loomiai-autoresearch` | `research.yaml` / pack/project scaffold / artifact model / MCP lifecycle | candidate lab / experiment runtime |

### 1.1 直接可复用的文件

这些文件不是“参考”，而是建议直接作为实现模板或规范源。

- [yao-meta-skill/SKILL.md](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/SKILL.md)
- [yao-meta-skill/manifest.json](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/manifest.json)
- [yao-meta-skill/agents/interface.yaml](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/agents/interface.yaml)
- [yao-meta-skill/references/packaging-contracts.md](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/references/packaging-contracts.md)
- [yao-meta-skill/scripts/cross_packager.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/cross_packager.py)
- [yao-meta-skill/scripts/governance_check.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/governance_check.py)
- [yao-meta-skill/scripts/resource_boundary_check.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/resource_boundary_check.py)
- [skillhub/docs/07-skill-protocol.md](/Users/chenge/Desktop/skills-gp- research/skillhub/docs/07-skill-protocol.md)
- [skillhub/docs/14-skill-lifecycle.md](/Users/chenge/Desktop/skills-gp- research/skillhub/docs/14-skill-lifecycle.md)
- [skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillPublishService.java](/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillPublishService.java)
- [skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/validation/SkillPackageValidator.java](/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/validation/SkillPackageValidator.java)
- [skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/metadata/SkillMetadataParser.java](/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/metadata/SkillMetadataParser.java)
- [skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/security/SecurityScanService.java](/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/security/SecurityScanService.java)
- [skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillDownloadService.java](/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillDownloadService.java)
- [skillhub/server/skillhub-infra/src/main/java/com/iflytek/skillhub/infra/scanner/SkillScannerAdapter.java](/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-infra/src/main/java/com/iflytek/skillhub/infra/scanner/SkillScannerAdapter.java)
- [AgentSkillOS/src/manager/tree/skill_scanner.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/skill_scanner.py)
- [AgentSkillOS/src/orchestrator/dag/skill_registry.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/skill_registry.py)
- [AgentSkillOS/src/orchestrator/runtime/run_context.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/run_context.py)
- [AgentSkillOS/src/orchestrator/base.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/base.py)
- [loomiai-autoresearch/src/autoresearch_agent/core/packs/schema.py](/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/packs/schema.py)
- [loomiai-autoresearch/src/autoresearch_agent/core/packs/project.py](/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/packs/project.py)
- [loomiai-autoresearch/src/autoresearch_agent/core/runtime/manager.py](/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/runtime/manager.py)
- [loomiai-autoresearch/docs/runtime-architecture.md](/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/docs/runtime-architecture.md)

---

## 2. 目标架构

建议把一个 skill package 视为 4 层对象，而不是一个目录：

| 层级 | 对象 | 说明 |
|---|---|---|
| Source layer | `SkillPackage` | git/文件系统中的源目录 |
| Metadata layer | `SkillUnit` | 可检索、可治理、可评分的逻辑单元 |
| Runtime layer | `SkillInstall` | 某次运行中被复制到隔离环境的实例 |
| Distribution layer | `SkillBundle` | 导出给不同平台/客户端的打包结果 |

这 4 层必须分开。

- `SkillPackage` 解决“怎么写”。
- `SkillUnit` 解决“这是什么能力”。
- `SkillInstall` 解决“这次怎么跑”。
- `SkillBundle` 解决“怎么发出去”。

### 2.1 当前仓库里已经有的雏形

- `AgentSkillOS` 已经把“发现”和“执行”分成两层，`SkillScanner` 只读 `SKILL.md`，`RunContext` 负责复制 skill 到隔离目录后执行。
- `skillhub` 已经把“注册、版本、文件、扫描、下载、治理”分层。
- `yao-meta-skill` 已经把“触发、治理、评测、包装、兼容导出”做成完整 pipeline。
- `loomiai-autoresearch` 已经把“项目、pack、runtime spec、artifact”做成受控研究 runtime。

我们要做的不是推翻，而是把这四个雏形合成一套 skill 工程规范。

---

## 3. 标准目录结构

建议标准 package 结构如下：

```text
my-skill/
├── SKILL.md
├── manifest.json
├── actions.yaml
├── agents/
│   └── interface.yaml
├── references/
├── scripts/
├── evals/
├── tests/
├── adapters/
├── reports/
└── assets/
```

### 3.1 各目录职责

| 目录 | 职责 | 允许放什么 |
|---|---|---|
| `SKILL.md` | 路由入口 | 触发条件、边界、操作主线、输出契约 |
| `manifest.json` | 治理与版本主文件 | owner、成熟度、生命周期、目标平台、风险等级 |
| `actions.yaml` | 动作契约主文件 | 可执行 action、runner、timeout、sandbox、输入输出 schema |
| `agents/interface.yaml` | 中立兼容元数据 | display name、default prompt、兼容性、退化策略 |
| `references/` | 长文档 | playbook、背景、决策依据、操作说明 |
| `scripts/` | 可执行逻辑 | validate、run、package、export、report |
| `evals/` | 评测与回归集 | trigger cases、holdout、goldens、promotion policy |
| `tests/` | 结构性测试 | schema、回归、packaging failure fixtures |
| `adapters/` | 平台适配物 | openai / claude / generic / internal targets |
| `reports/` | 质量证据 | eval suite、scorecard、promotion ledger、drift history |
| `assets/` | 静态资源 | 图片、示例文件、图标、模板素材 |

### 3.2 兼容边界

对外兼容只要求以下最小集合：

- `SKILL.md`
- `references/`
- `scripts/`
- `assets/`

这是 `skillhub/docs/07-skill-protocol.md` 的互操作边界。

平台内部增强建议再加：

- `manifest.json`
- `actions.yaml`
- `agents/interface.yaml`
- `evals/`
- `tests/`
- `reports/`
- `adapters/`

结论很明确：

- OpenSkills / Claude 兼容层只认 `SKILL.md` 及目录约定。
- skillhub registry 需要更多结构化字段，但这些字段不应该破坏互操作层。
- `actions.yaml` 是内部平台动作层，不属于现有 OpenSkills 必需项。

---

## 4. `SKILL.md` 规范

### 4.1 角色定位

`SKILL.md` 只做 4 件事：

1. 触发 routing。
2. 使用边界。
3. 高层执行流程。
4. 输出契约。

不要把它写成一个巨型手册。

`yao-meta-skill/SKILL.md` 已经给出很清晰的方向：保持入口轻，长文档下沉到 `references/`，可执行逻辑下沉到 `scripts/`，证据放到 `reports/`。

### 4.2 建议 frontmatter schema

建议最小字段如下：

```yaml
---
name: github-pr-review
description: Review GitHub pull requests, summarize risk, and produce actionable feedback.
version: 1.0.0
tags: [github, review, ci]
category: code-review
owner: platform-agent-team
status: active
---
```

#### 必需字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | string | kebab-case，唯一 slug |
| `description` | string | 一句话说明何时触发 |

#### 强烈建议字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `version` | string | skill source version |
| `tags` | array[string] | 便于检索和 label 初始化 |
| `category` | string | skill 家族类别 |
| `owner` | string | 责任人或团队 |
| `status` | string | `experimental` / `active` / `deprecated` |

#### 可选扩展字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `metadata` | object | 只放非兼容性字段 |
| `x-*` | any | 平台内部扩展，禁止影响互操作 |

### 4.3 body 约束

正文建议只保留：

- Router Rules
- Modes
- Compact Workflow
- Output Contract
- Reference Map

不要把下面这些东西塞进 `SKILL.md`：

- 复杂脚本参数说明
- 大段设计推理
- 长篇 eval 结果
- 平台适配细节

这些都应该下沉到 `references/`、`evals/`、`reports/`。

---

## 5. `manifest.json` 规范

### 5.1 角色定位

`manifest.json` 是内部治理主文件，不是互操作主文件。

它负责：

- 谁拥有这个 skill
- 这个 skill 处于什么成熟度
- 生命周期状态是什么
- 目标平台是什么
- 是否需要 review / scan / promotion

`yao-meta-skill/manifest.json` 已经证明这个文件非常适合承载治理语义。

### 5.2 建议 schema

```json
{
  "name": "github-pr-review",
  "version": "1.0.0",
  "owner": "platform-agent-team",
  "updated_at": "2026-04-02",
  "status": "active",
  "maturity_tier": "production",
  "lifecycle_stage": "library",
  "review_cadence": "quarterly",
  "target_platforms": ["openai", "claude", "generic"],
  "factory_components": ["references", "scripts", "evals", "reports"],
  "risk_level": "medium",
  "default_runtime_profile": "python311-safe"
}
```

### 5.3 字段级建议

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | string | 必须和 `SKILL.md.name` 一致 |
| `version` | string | 包版本 |
| `owner` | string | 团队或人 |
| `updated_at` | date | `YYYY-MM-DD` |
| `status` | string | `experimental` / `active` / `deprecated` |
| `maturity_tier` | string | `scaffold` / `production` / `library` / `governed` |
| `lifecycle_stage` | string | `library` / `candidate` / `published` / `archived` |
| `review_cadence` | string | `monthly` / `quarterly` / `semiannual` / `annual` / `per-release` |
| `target_platforms` | array[string] | 适配目标 |
| `factory_components` | array[string] | `references` / `scripts` / `evals` / `reports` 等 |
| `risk_level` | string | `low` / `medium` / `high` |
| `default_runtime_profile` | string | 运行时配置名 |

### 5.4 校验规则

- `name` 必须和 `SKILL.md` frontmatter 同步。
- `updated_at` 必须是日期，不允许随便写时间戳。
- `maturity_tier` 需要和评测/治理证据相匹配。
- `status=deprecated` 时应附带 `deprecation_note`。

这套治理校验可以直接参考 `yao-meta-skill/scripts/governance_check.py` 的实现思路。

---

## 6. `agents/interface.yaml` 规范

### 6.1 角色定位

`agents/interface.yaml` 是中立兼容元数据源。

它的用途是把一个 skill 包装成不同客户端可理解的接口描述，而不污染源目录。

这是 `yao-meta-skill/agents/interface.yaml` 和 `yao-meta-skill/scripts/cross_packager.py` 的核心思想。

### 6.2 建议 schema

```yaml
interface:
  display_name: "GitHub PR Review"
  short_description: "Review PRs and produce actionable feedback"
  default_prompt: "Use this skill when the user asks to review a GitHub PR."
compatibility:
  canonical_format: "agent-skills"
  adapter_targets:
    - "openai"
    - "claude"
    - "generic"
  activation:
    mode: "manual"
    paths: []
  execution:
    context: "inline"
    shell: "bash"
  trust:
    source_tier: "local"
    remote_inline_execution: "forbid"
    remote_metadata_policy: "allow-metadata-only"
  degradation:
    openai: "metadata-adapter"
    claude: "neutral-source-plus-adapter"
    generic: "neutral-source"
```

### 6.3 字段级建议

| 节点 | 字段 | 说明 |
|---|---|---|
| `interface` | `display_name` | 用户界面展示名 |
| `interface` | `short_description` | 短描述 |
| `interface` | `default_prompt` | 默认触发提示 |
| `compatibility` | `canonical_format` | 推荐固定为 `agent-skills` |
| `compatibility` | `adapter_targets` | 目标平台列表 |
| `compatibility.activation` | `mode` | `manual` / `path` / `registry` 等 |
| `compatibility.activation` | `paths` | 允许的激活路径 |
| `compatibility.execution` | `context` | `inline` / `subprocess` / `isolated` |
| `compatibility.execution` | `shell` | 默认 shell |
| `compatibility.trust` | `source_tier` | `local` / `remote` / `mixed` |
| `compatibility.trust` | `remote_inline_execution` | 是否允许远端内联执行 |
| `compatibility.trust` | `remote_metadata_policy` | 远端只传元数据还是允许执行体 |
| `compatibility.degradation` | per-target | 每个平台的退化策略 |

### 6.4 兼容边界

这个文件不应该包含：

- 业务逻辑
- action 脚本
- 评测数据
- 发布证据

它只负责 portable metadata。

---

## 7. `actions.yaml` 规范

### 7.1 这是新增的关键文件

现有仓库没有把 action contract 显式抽出来，这是后续可控调度的缺口。

我们建议新增 `actions.yaml`，并把它作为 runtime 执行的唯一入口声明。

### 7.2 设计目标

`actions.yaml` 要解决的问题是：

- 不要让 runtime 扫描 `scripts/` 猜哪个脚本能跑。
- 不要让 prompt 决定脚本参数。
- 不要让 package 内任意文件都可执行。

必须显式声明 action。

### 7.3 建议 schema

```yaml
schema_version: actions.v1
actions:
  - id: run
    kind: script
    entry: scripts/run.py
    runtime: python3
    timeout_sec: 120
    sandbox: workspace-write
    allow_network: false
    input_schema:
      type: object
      properties:
        task:
          type: string
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
      - writes_report
    idempotency: best_effort

  - id: validate
    kind: script
    entry: scripts/validate.py
    runtime: python3
    timeout_sec: 30
    sandbox: read-only
    allow_network: false
    side_effects: []
```

### 7.4 字段级建议

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | string | 建议 `actions.v1` |
| `actions[].id` | string | 动作唯一标识 |
| `actions[].kind` | string | `script` / `mcp` / `instruction` / `subagent` |
| `actions[].entry` | string | 相对 skill root 的入口 |
| `actions[].runtime` | string | `python3` / `bash` / `node` 等 |
| `actions[].timeout_sec` | number | 超时控制 |
| `actions[].sandbox` | string | `read-only` / `workspace-write` / `network-allowed` 等 |
| `actions[].allow_network` | bool | 是否允许联网 |
| `actions[].input_schema` | object | JSON Schema |
| `actions[].output_schema` | object | JSON Schema |
| `actions[].side_effects` | array[string] | 副作用声明 |
| `actions[].idempotency` | string | `exact` / `best_effort` / `none` |

### 7.5 action kind 设计

| kind | 含义 | 推荐用途 |
|---|---|---|
| `script` | 调本地脚本 | 常规执行、校验、导出 |
| `mcp` | 调外部 MCP 工具 | 需要标准工具协议时 |
| `instruction` | 仅加载文档指导 | 无副作用动作 |
| `subagent` | 生成子代理执行 | 复杂流程拆分 |

### 7.6 runtime 强约束

运行时只能执行 `actions.yaml` 中列出的 action。

禁止：

- 任意脚本发现
- 目录内任意入口自动执行
- 通过 prompt 拼接 shell 命令

这条约束是后续安全、审计和可回归的基础。

---

## 8. `references/`、`scripts/`、`evals/`、`tests/`、`adapters/`、`reports/`

### 8.1 `references/`

`references/` 放长文档，不放逻辑代码。

建议直接复用 `yao-meta-skill/references/` 的组织方式：

- `skill-engineering-method.md`
- `skill-archetypes.md`
- `gate-selection.md`
- `non-skill-decision-tree.md`
- `operating-modes.md`
- `governance.md`
- `resource-boundaries.md`
- `eval-playbook.md`
- `packaging-contracts.md`

这些文件可以直接作为 skill authoring handbook 或内部标准文档模板。

### 8.2 `scripts/`

`scripts/` 是确定性逻辑的载体。

建议把脚本分成 4 类：

| 类型 | 例子 | 责任 |
|---|---|---|
| Authoring scripts | `trigger_eval.py`, `optimize_description.py` | 写 skill、改 trigger、优化边界 |
| Validation scripts | `resource_boundary_check.py`, `governance_check.py` | 发布前校验 |
| Packaging scripts | `cross_packager.py`, `yao.py package` | 目标平台导出 |
| Report scripts | `render_iteration_ledger.py`, `render_portability_report.py` | 生成证据和报告 |

### 8.3 可直接复用的 `yao-meta-skill` 脚本

建议原样复用或直接移植：

- [yao-meta-skill/scripts/trigger_eval.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/trigger_eval.py)
- [yao-meta-skill/scripts/run_eval_suite.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/run_eval_suite.py)
- [yao-meta-skill/scripts/judge_blind_eval.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/judge_blind_eval.py)
- [yao-meta-skill/scripts/resource_boundary_check.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/resource_boundary_check.py)
- [yao-meta-skill/scripts/governance_check.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/governance_check.py)
- [yao-meta-skill/scripts/cross_packager.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/cross_packager.py)
- [yao-meta-skill/scripts/context_sizer.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/context_sizer.py)
- [yao-meta-skill/scripts/promotion_checker.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/promotion_checker.py)
- [yao-meta-skill/scripts/create_iteration_snapshot.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/create_iteration_snapshot.py)

### 8.4 `evals/`

`evals/` 是 skill 的真正规约。

建议至少包含：

- `trigger_cases.json`
- `failure-cases.md`
- `semantic_config.json`
- `packaging_expectations.json`
- `promotion_policy.md`
- `human_review_template.md`

这些文件可以直接借 `yao-meta-skill/evals/` 和 `references/` 里的现成逻辑。

### 8.5 `tests/`

`tests/` 主要放结构回归和失败回归。

建议覆盖：

- frontmatter parse
- manifest schema
- action schema
- packaging failure
- portability contract
- resource boundary
- governance gate

### 8.6 `adapters/`

`adapters/` 放平台导出物或兼容层。

建议内容：

- `targets/openai/adapter.json`
- `targets/openai/agents/openai.yaml`
- `targets/claude/adapter.json`
- `targets/claude/README.md`
- `targets/generic/adapter.json`

这套导出目录可直接复用 `yao-meta-skill/scripts/cross_packager.py` 的结构。

### 8.7 `reports/`

`reports/` 不是日志目录，而是治理证据目录。

建议放：

- `eval_suite.json`
- `family_summary.md`
- `iteration_ledger.md`
- `portability_score.md`
- `promotion_decisions.md`
- `description_drift_history.md`
- `governance_score.json`
- `context_budget.md`

这些报告层是后续晋升和回归判定的依据。

---

## 9. 安装缓存与运行时缓存

### 9.1 本地安装目录

`skillhub/docs/07-skill-protocol.md` 已经给出明确的客户端安装目录顺序：

1. `./.agent/skills/`
2. `~/.agent/skills/`
3. `./.claude/skills/`
4. `~/.claude/skills/`

安装后目录名等于 `skill.slug`。

这是应当保留的互操作约定。

### 9.2 本地安装元数据

建议在本地安装后写入：

- `.astron/metadata.json`

这是 `skillhub` 已经定义过的私有 metadata 文件。

建议包含：

```json
{
  "source": "skillhub",
  "sourceType": "registry",
  "registryUrl": "https://skills.example.com",
  "namespace": "@team-name",
  "skillSlug": "github-pr-review",
  "version": "1.2.0",
  "installedAt": "2026-04-02T10:00:00Z",
  "sha256": "..."
}
```

### 9.3 运行时隔离缓存

运行时缓存建议直接沿用 `AgentSkillOS` 的思路：

- `exec_dir`：系统临时目录中的隔离执行根目录
- `workspace_dir`：执行工作目录
- `.claude/skills/`：复制后的运行时 skill 目录
- `run_dir/logs/`：日志
- `run_dir/meta.json`：任务元数据
- `run_dir/result.json`：结果
- `run_dir/plan.json`：计划

`AgentSkillOS/src/orchestrator/runtime/run_context.py` 已经把这套分离做得很清楚。

### 9.4 缓存边界

必须明确三件事：

- registry 存的是“发布态”
- local install cache 存的是“客户端态”
- run context cache 存的是“单次执行态”

不要混用。

---

## 10. bundle 结构与导出链路

### 10.1 源包到目标包

建议导出分两层：

1. 源包：源码级 skill 目录。
2. 目标包：平台适配导出物或 zip bundle。

### 10.2 `cross_packager.py` 的合同

`yao-meta-skill/scripts/cross_packager.py` 已经把导出合同写得很具体：

- `openai`
- `claude`
- `generic`

每个 target 都有：

- 必需字段
- 必需文件
- 字段映射
- portable execution metadata
- trust-boundary metadata
- degradation strategy

这套思路建议直接继承。

### 10.3 推荐导出结构

```text
dist/
├── targets/
│   ├── openai/
│   │   ├── adapter.json
│   │   └── agents/openai.yaml
│   ├── claude/
│   │   ├── adapter.json
│   │   └── README.md
│   └── generic/
│       └── adapter.json
└── my-skill.zip
```

### 10.4 zip 打包规则

建议 zip 的根目录保留 skill package root 名称。

这一点和 `yao-meta-skill/scripts/cross_packager.py` 的 `make_zip()` 一致：archive 里保留的是 skill 根目录，而不是把文件裸平铺。

### 10.5 skillhub bundle 规则

如果进入 registry，bundle 建议继续沿用 `skillhub` 的对象存储和 bundle 逻辑：

- 文件路径：`skills/{skillId}/{versionId}/{filePath}`
- bundle 路径：`packages/{skillId}/{versionId}/bundle.zip`

下载时：

- 优先使用预构建 bundle
- 如果 bundle 不存在，再 fallback 从文件重新打 zip

`SkillDownloadService` 已经实现了这个 fallback 思路。

---

## 11. `skillhub` 现有模型如何复用

### 11.1 建议直接复用的实体分层

`skillhub` 已经把核心模型拆得很对，建议继续保留：

- `Skill`：技能容器
- `SkillVersion`：版本快照
- `SkillFile`：文件索引
- `SkillTag`：版本分发别名
- `SecurityAudit`：扫描审计

这比“一个 skill 一个大表”要健康得多。

### 11.2 发布链路复用点

`SkillPublishService` 的关键步骤可以直接作为新平台发布链路的原型：

1. 包校验。
2. `SKILL.md` frontmatter 解析。
3. 查找或创建 `Skill`。
4. 创建 `SkillVersion`。
5. 上传 `SkillFile` 到对象存储。
6. 生成 bundle zip。
7. 更新版本统计和最新指针。
8. 提交扫描或 review。

### 11.3 扫描链路复用点

`SecurityScanService` + `SkillScannerAdapter` 已经给出一条可复用的安全扫描外接模式：

- 扫描可在 publish 后异步触发。
- 扫描结果应落审计轨迹。
- 扫描失败不应阻塞整个系统的结构化记录。

### 11.4 下载链路复用点

`SkillDownloadService` 提供了两个很重要的设计：

- `latest` / version / tag 分发入口分开。
- bundle 缺失时允许 fallback zip，但不要把这当作默认路径。

这些设计应该保留。

---

## 12. `AgentSkillOS` 可以复用什么

### 12.1 skill 发现

`AgentSkillOS/src/manager/tree/skill_scanner.py` 的价值在于：

- 从 `SKILL.md` frontmatter 扫描 `name` / `description`
- 目录级发现 skill
- 不依赖复杂索引也能工作

这适合作为客户端本地 skill discovery 的最小实现。

### 12.2 runtime 装载

`AgentSkillOS/src/orchestrator/runtime/run_context.py` 的价值在于：

- 运行时目录和永久目录分离
- skill 复制到临时隔离目录
- workspace 和 logs 分离
- `.env` 可以复制到隔离目录

这是一条非常适合后续 skill runtime 的执行底座。

### 12.3 编排模式

`AgentSkillOS/src/orchestrator/base.py` 定义了 `EngineRequest` / `ExecutionResult` / `ExecutionEngine`，这个接口适合作为 skill runtime 的内部执行合同。

`free-style`、`dag`、`no-skill` 三种模式也可以保留为不同运行制度：

- `no-skill`：没有合适 skill 时的 baseline。
- `free-style`：skill 暴露给 agent，自由调用。
- `dag`：技能依赖明确时的规划执行。

### 12.4 发现与编排分轴

`AgentSkillOS` 最值得保留的纪律是：

- `manager axis` 负责找 skill。
- `orchestrator axis` 负责跑 task。

这两个轴不要揉在一个模块里。

---

## 13. `loomiai-autoresearch` 可以复用什么

### 13.1 pack / project scaffold

`loomiai-autoresearch/src/autoresearch_agent/core/packs/project.py` 已经说明：

- 如何生成项目骨架。
- 如何写入默认目录。
- 如何复制 pack manifest。
- 如何把模板渲染到 workspace。

这对 skill lab 很有帮助，因为 skill lab 也需要一个“受控项目骨架”。

### 13.2 `research.yaml` 思路

`loomiai-autoresearch/src/autoresearch_agent/core/spec/research_config.py` 和 `core/runtime/spec.py` 给了我们一个重要启发：

- 把可变面集中在一个 schema 文件里。
- 把 editable targets 明确成受控变更面。
- 把 outputs / constraints / runtime / pack_config 分层。

后续 skill lab 可以仿照这个思路，做 `skill-research.yaml` 或类似配置文件。

### 13.3 artifact contract

`loomiai-autoresearch/src/autoresearch_agent/core/runtime/manager.py` 的产物契约已经很完整：

- `result.json`
- `summary.json`
- `iteration_history.json`
- `artifact_index.json`
- `best_strategy.py`
- `strategy.patch`
- `report.md`
- `dataset_profile.json`
- `dataset_snapshot.json`

这套 artifact model 非常适合 skill lab。

---

## 14. 运行时怎么调度 action

### 14.1 不要做隐式调度

调度必须显式：

- 先选 `action.id`
- 再查 `actions.yaml`
- 再选 `runner`
- 再进入 sandbox

不能让 runtime 猜文件名或任意 shell。

### 14.2 推荐 runner 类型

| Runner | 说明 | 典型用途 |
|---|---|---|
| `ScriptRunner` | 本地脚本执行 | validate / package / export / report |
| `InstructionRunner` | 只读文档流程 | 人工或 agent guided step |
| `McpRunner` | 调 MCP 工具 | 外部工具集成 |
| `SubagentRunner` | 子代理执行 | 长链路 task 拆分 |

### 14.3 建议 runtime 执行顺序

1. 读取 package root。
2. 验证 `SKILL.md` / `manifest.json` / `actions.yaml` / `agents/interface.yaml`。
3. 计算可用 action。
4. 选择 action。
5. 复制 skill 到运行时隔离目录。
6. 执行指定 runner。
7. 回收 logs / artifacts。
8. 写入 execution record。

### 14.4 执行时的强约束

每个 action 至少要能回答：

- 它做什么。
- 它在哪个 runtime 跑。
- 它是否允许联网。
- 它会写哪里。
- 它的输入输出是什么。
- 它是否幂等。

回答不出来的 action 不应该被发布。

---

## 15. 发布前校验链路

发布前的校验建议按这个顺序执行。

### 15.1 结构校验

负责检查：

- `SKILL.md` 是否存在。
- frontmatter 是否有 `name` / `description`。
- `manifest.json` 是否存在且字段完整。
- `actions.yaml` 是否存在且 schema 合法。
- `agents/interface.yaml` 是否有必需字段。
- 文件数量、文件类型、单文件大小、总包大小是否合规。

可复用：

- [skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/validation/SkillPackageValidator.java](/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/validation/SkillPackageValidator.java)
- [skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/metadata/SkillMetadataParser.java](/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/metadata/SkillMetadataParser.java)

### 15.2 触发与边界校验

负责检查：

- 描述是否能正确路由。
- 是否存在误触发。
- 是否明确禁止不该触发的场景。

可复用：

- [yao-meta-skill/scripts/trigger_eval.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/trigger_eval.py)
- [yao-meta-skill/scripts/run_eval_suite.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/run_eval_suite.py)

### 15.3 质量与回归校验

负责检查：

- 任务边界是否稳定。
- holdout 是否被污染。
- 失败 case 是否回归。

可复用：

- [yao-meta-skill/scripts/judge_blind_eval.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/judge_blind_eval.py)
- [yao-meta-skill/reports/family_summary.md](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/reports/family_summary.md)

### 15.4 资源边界校验

负责检查：

- 文档是否过长。
- 上下文是否超预算。
- references 是否压垮入口。

可复用：

- [yao-meta-skill/scripts/context_sizer.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/context_sizer.py)
- [yao-meta-skill/scripts/resource_boundary_check.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/resource_boundary_check.py)

### 15.5 治理校验

负责检查：

- owner 是否明确。
- maturity 是否达标。
- review cadence 是否存在。
- report / eval / promotion evidence 是否齐全。

可复用：

- [yao-meta-skill/scripts/governance_check.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/governance_check.py)

### 15.6 平台导出校验

负责检查：

- openai / claude / generic 目标文件是否齐全。
- contract fields 是否完整。
- degradation strategy 是否声明。

可复用：

- [yao-meta-skill/scripts/cross_packager.py](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/cross_packager.py)
- [yao-meta-skill/references/packaging-contracts.md](/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/references/packaging-contracts.md)

### 15.7 安全扫描校验

负责检查：

- 包内容是否存在高风险内容。
- 传入/传出路径是否合法。
- 是否满足外部 scanner 要求。

可复用：

- [skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/security/SecurityScanService.java](/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/security/SecurityScanService.java)
- [skillhub/server/skillhub-infra/src/main/java/com/iflytek/skillhub/infra/scanner/SkillScannerAdapter.java](/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-infra/src/main/java/com/iflytek/skillhub/infra/scanner/SkillScannerAdapter.java)

---

## 16. 运行时校验链路

运行时校验的目标不是“重新发布”，而是“确保这次安装和执行安全、稳定、可追踪”。

### 16.1 加载时校验

建议 runtime 在加载 skill 时校验：

- `SKILL.md` 可解析。
- `manifest.json` 和 `actions.yaml` schema 合法。
- 目标 action 存在。
- action 的 entry 在 package root 内。
- sandbox 配置合法。

可复用：

- [AgentSkillOS/src/manager/tree/skill_scanner.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/skill_scanner.py)
- [AgentSkillOS/src/orchestrator/dag/skill_registry.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/skill_registry.py)

### 16.2 安装时校验

建议安装时校验：

- 本地安装目录是否与 `skill.slug` 一致。
- `.astron/metadata.json` 是否写入成功。
- `AGENTS.md` 索引块是否同步成功。
- checksum 是否匹配。

可复用：

- [skillhub/docs/07-skill-protocol.md](/Users/chenge/Desktop/skills-gp- research/skillhub/docs/07-skill-protocol.md)

### 16.3 执行时校验

建议执行时校验：

- action timeout。
- sandbox。
- network allowance。
- workspace 写权限。
- artifacts 是否按约定落盘。

可复用：

- [AgentSkillOS/src/orchestrator/runtime/run_context.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/run_context.py)
- [AgentSkillOS/src/orchestrator/base.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/base.py)

---

## 17. 打包导出链路

### 17.1 源到目标

建议导出顺序如下：

1. 解析源目录。
2. 验证结构和治理。
3. 生成平台适配器。
4. 生成 target bundle。
5. 生成 zip 包。
6. 发布到 registry 或安装目录。

### 17.2 目标文件建议

| target | 必需文件 |
|---|---|
| `openai` | `targets/openai/adapter.json`, `targets/openai/agents/openai.yaml` |
| `claude` | `targets/claude/adapter.json`, `targets/claude/README.md` |
| `generic` | `targets/generic/adapter.json` |

### 17.3 导出时应保留的 portable semantics

`yao-meta-skill` 的 packaging contract 已经明确了必须保留的 4 个语义：

- activation
- execution
- trust
- degradation

这四个语义不能在导出时丢失。

---

## 18. 什么应该新增

下面这些是建议新增，而不是直接从现有仓库搬过来。

### 18.1 新增文件

- `actions.yaml`
- `skill-research.yaml` 或同类 lab config
- `skill_action` 相关 schema 或表
- `skill_install_cache` 相关索引
- `skill_promotion_decision` 相关状态记录

### 18.2 新增 runtime 组件

- `ActionResolver`
- `ActionRunner`
- `PackageSchemaValidator`
- `PlatformAdapterBuilder`
- `SkillInstallCacheManager`
- `SkillActionRegistry`

### 18.3 新增 lab 组件

- `CandidateSkillGenerator`
- `SkillEvalOrchestrator`
- `PromotionGate`
- `RegressionCollector`
- `ArtifactPublisher`

---

## 19. 推荐实施顺序

为了避免一开始就做成大杂烩，建议按下面顺序推进：

### Phase 1: package contract

- 定义 `SKILL.md` / `manifest.json` / `actions.yaml` / `agents/interface.yaml`。
- 落地目录结构。
- 建 schema validator。

### Phase 2: runtime action execution

- 接入 `ActionResolver`。
- 接入 `Runner`。
- 接入安装缓存。
- 接入隔离 run context。

### Phase 3: registry and bundle

- 接入 `Skill` / `SkillVersion` / `SkillFile` / `bundle.zip`。
- 接入 publish / review / scan。
- 接入 target adapters。

### Phase 4: eval and governance

- 接入 trigger eval。
- 接入 regression eval。
- 接入 governance score。
- 接入 promotion decision。

### Phase 5: lab loop

- 接入 candidate generation。
- 接入 skill research config。
- 接入 artifact loop。
- 接入 auto / semi-auto promotion。

---

## 20. 最终落地建议

如果只保留一句话作为工程原则：

> `SKILL.md` 负责“路由”，`manifest.json` 负责“治理”，`actions.yaml` 负责“可执行”，`agents/interface.yaml` 负责“兼容”，`references/scripts/evals/tests/reports` 负责“可维护和可晋升”。

这就是后续实际开发时应遵守的 skill package contract。
