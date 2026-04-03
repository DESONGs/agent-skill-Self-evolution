# Skill Package Contract v1

Status: implemented in AgentSkillOS phase 1 on 2026-04-03; this document is the frozen contract plus current code mapping

Owner scope: Contract only

## 0.1 Current Implementation Alignment

截至 2026-04-03，phase 1 已在 `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS` 落地，当前实现与本文设计的对齐关系如下：

- contract parser source of truth：
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/parsers/frontmatter.py`
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/parsers/skill_md.py`
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/parsers/manifest.py`
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/parsers/actions.py`
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/parsers/interface.py`
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/parsers/package.py`
- validator 组合入口：
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/validators/package.py`
- bundler / runtime install：
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/bundler/source_bundle.py`
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/bundler/export_manifest.py`
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/bundler/target_bundle.py`
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/bundler/runtime_install.py`
- runtime 兼容 facade：
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/actions.py`
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/models.py`
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/install.py`
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/resolve.py`

当前代码语义已经按本文冻结为：

- runtime 实际执行面只允许执行 `actions.yaml` 声明的 action
- `strict_actions=False` 只保留 metadata/discovery 兼容语义，不再允许 install/resolve fallback
- discovery/metadata 路径遇到缺失 `actions.yaml` 的 legacy package，会返回 `legacy_actions_contract_missing` warning，并标记 `has_actions_contract=false`
- `allowed-tools` 仍可暴露为 metadata，但不再承担执行授权语义

## 0. Scope

本文只冻结 `Skill Package Contract v1`，覆盖：

- skill 最小工程单元
- package 目录结构
- `SKILL.md` / `manifest.json` / `actions.yaml` / `agents/interface.yaml` 的职责与字段
- package 发布前校验、安装前校验、运行前校验
- bundle 导出结构、安装缓存结构、runtime install 结构
- OpenSkills / Claude / skillhub 的兼容边界
- 现有代码的复用、抽离和新增模块清单

明确不覆盖：

- registry 内部表设计
- runtime mode selection
- task1 的环境哲学
- 调度策略、检索策略、排序策略

## 1. Design Basis

本设计严格基于以下真实文档和代码：

- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/02-skill-package-and-actions.md`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/docs/07-skill-protocol.md`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/docs/14-skill-lifecycle.md`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/SKILL.md`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/manifest.json`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/agents/interface.yaml`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/references/packaging-contracts.md`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/validate_skill.py`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/cross_packager.py`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/governance_check.py`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/resource_boundary_check.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/skill_scanner.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/skill_registry.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/run_context.py`

设计约束来自这些文件中的共同结论：

- 最小互操作边界仍然是 `SKILL.md + references/ + scripts/ + assets/`，不能被内部增强字段破坏。
- `SKILL.md` 负责路由与边界，长文档下沉到 `references/`，确定性逻辑下沉到 `scripts/`。
- `manifest.json` 适合承载治理字段，但不是互操作主文件。
- `agents/interface.yaml` 是中立兼容元数据源，导出时需要保留 activation / execution / trust / degradation 四类语义。
- phase 1 已补上显式 `actions.yaml` 合同，runtime 执行面已收敛到统一 action gate。
- runtime 隔离安装已经从 `RunContext` 骨架演进为 package-aware install layout，并支持 `compat_root` 与 runtime install materialization。

## 2. Contract Decisions

### 2.1 一句话原则

`SKILL.md` 负责路由，`manifest.json` 负责治理，`actions.yaml` 负责可执行面，`agents/interface.yaml` 负责兼容元数据；runtime 只允许执行 `actions.yaml` 显式声明的 action。

### 2.2 v1 术语

- `SkillSourcePackage`：作者维护的源目录
- `SkillBundle`：导出给安装器或 registry 的分发物
- `SkillInstall`：安装到本地兼容目录的可发现目录
- `RuntimeInstall`：单次运行临时隔离区中的可执行副本

### 2.3 v1 不做的事

- 不把 `manifest.json.lifecycle_stage` 绑定到 registry 生命周期状态机
- 不在本阶段定义 `ActionResolver` 的调度策略
- 不允许 runtime 通过扫描 `scripts/` 或 prompt 拼接 shell 决定执行体

## 3. Standard Directory Structure

v1 标准目录结构如下：

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

### 3.1 必需项

- `SKILL.md`
- `actions.yaml`
- `agents/interface.yaml`

### 3.2 条件必需项

- `manifest.json`
  - 对内部发布、治理、导出为必需
  - 对 OpenSkills / Claude 兼容发现不是必需

### 3.3 可选项

- `references/`
- `scripts/`
- `evals/`
- `tests/`
- `adapters/`
- `reports/`
- `assets/`

## 4. File Contracts

## 4.1 `SKILL.md`

### 职责

- 定义触发语义
- 定义适用边界和 exclusion
- 提供高层执行骨架
- 提供输出契约

### 不负责

- 不承载治理主数据
- 不承载平台导出元数据
- 不承载 action registry
- 不承载长篇实现细节

### frontmatter schema 建议

必需字段：

| 字段 | 类型 | 规则 |
|---|---|---|
| `name` | string | kebab-case，作为安装目录名和 lookup key |
| `description` | string | 1-2 句，表示何时触发 |

建议字段：

| 字段 | 类型 | 规则 |
|---|---|---|
| `version` | string | 源包版本，建议与 `manifest.json.version` 一致 |
| `tags` | array[string] | 用于检索和分类 |
| `category` | string | skill 家族类别 |
| `owner` | string | 责任人或团队标识 |
| `status` | string | `experimental` / `active` / `deprecated` |
| `metadata` | object | 非兼容字段 |
| `x-*` | any | 平台私有扩展，兼容客户端必须可忽略 |

正文段落建议固定为：

- `Router Rules`
- `Modes` 或 `Boundaries`
- `Compact Workflow`
- `Output Contract`
- `Reference Map`

v1 校验规则：

- frontmatter 必须存在
- `name` 与 `description` 必填
- `name` 必须与安装目录 slug 一致
- `description` 不允许为空串
- 正文必须出现至少一个边界信号
  - 例如 `Do not use`、`Out of scope`、`Should not trigger`

## 4.2 `manifest.json`

### 职责

- 治理属性
- 包版本
- 维护责任
- 发布前 gate 所需的声明

### 不负责

- 不承担 OpenSkills / Claude 的发现协议
- 不声明具体 action 入口
- 不声明平台适配器导出文件

### schema 建议

```json
{
  "name": "github-pr-review",
  "version": "1.0.0",
  "owner": "platform-agent-team",
  "updated_at": "2026-04-02",
  "status": "active",
  "maturity_tier": "production",
  "lifecycle_stage": "library",
  "context_budget_tier": "production",
  "review_cadence": "quarterly",
  "target_platforms": ["openai", "claude", "generic"],
  "factory_components": ["references", "scripts", "evals", "reports"],
  "risk_level": "medium",
  "default_runtime_profile": "python311-safe"
}
```

字段建议：

| 字段 | 必需性 | 类型 | 规则 |
|---|---|---|---|
| `name` | MUST | string | 必须等于 `SKILL.md.name` |
| `version` | MUST | string | semver 或 semver-compatible |
| `owner` | MUST | string | 团队或个人 owner |
| `updated_at` | MUST | string | `YYYY-MM-DD` |
| `status` | MUST | string | `experimental` / `active` / `deprecated` |
| `maturity_tier` | MUST | string | `scaffold` / `production` / `library` / `governed` |
| `review_cadence` | MUST | string | `monthly` / `quarterly` / `semiannual` / `annual` / `per-release` |
| `target_platforms` | SHOULD | array[string] | 至少包含 `generic`，导出器据此生成目标 |
| `factory_components` | SHOULD | array[string] | 声明本包实际使用的可选目录 |
| `context_budget_tier` | SHOULD | string | `resource_boundary_check` 使用 |
| `risk_level` | SHOULD | string | `low` / `medium` / `high` |
| `default_runtime_profile` | MAY | string | 给安装器或运行器选 sandbox profile 用 |
| `lifecycle_stage` | MAY | string | 仅表示源包治理阶段，不等于 registry 生命周期状态 |
| `deprecation_note` | CONDITIONAL | string | `status=deprecated` 时建议必填 |

v1 约束：

- `manifest.json.lifecycle_stage` 明确不等于 `/Users/chenge/Desktop/skills-gp- research/skillhub/docs/14-skill-lifecycle.md` 中的 `SkillVersion.status`
- registry 的 `latest published` 语义来自发布系统，不从本文件推导

## 4.3 `actions.yaml`

### 职责

- 声明运行时允许执行的 action 列表
- 声明每个 action 的执行入口、执行约束、输入输出契约
- 作为 runtime 唯一的 action allowlist

### 不负责

- 不承担平台兼容导出
- 不直接描述路由触发
- 不携带运行结果

### v1 schema

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
```

字段建议：

| 字段 | 必需性 | 类型 | 规则 |
|---|---|---|---|
| `schema_version` | MUST | string | 固定为 `actions.v1` |
| `actions` | MUST | array | 至少 1 个 action |
| `actions[].id` | MUST | string | skill 内唯一 |
| `actions[].kind` | MUST | string | `script` / `mcp` / `instruction` / `subagent` |
| `actions[].entry` | CONDITIONAL | string | `script` / `instruction` 必填，相对 package root |
| `actions[].runtime` | CONDITIONAL | string | `script` 必填，`python3` / `bash` / `node` 等 |
| `actions[].timeout_sec` | MUST | integer | 正整数 |
| `actions[].sandbox` | MUST | string | `read-only` / `workspace-write` / `network-allowed` |
| `actions[].allow_network` | MUST | boolean | 显式声明 |
| `actions[].input_schema` | SHOULD | object | JSON Schema 子集 |
| `actions[].output_schema` | SHOULD | object | JSON Schema 子集 |
| `actions[].side_effects` | SHOULD | array[string] | 显式副作用 |
| `actions[].idempotency` | SHOULD | string | `exact` / `best_effort` / `none` |

`kind` 语义：

| kind | 执行体 | v1 说明 |
|---|---|---|
| `script` | 本地脚本 | v1 主路径 |
| `mcp` | MCP tool 调用 | 只冻结合同，不定义调度实现 |
| `instruction` | 只读文档或模板 | 不允许产生隐式 shell |
| `subagent` | 子代理计划入口 | 只冻结入口字段，不讨论编排模式 |

v1 强约束：

- runtime 只允许执行 `actions.yaml` 里的 action
- runtime 不得扫描 `scripts/` 自动发现入口
- runtime 不得从 prompt 中拼接 shell 命令得到执行入口
- `actions[].entry` 必须位于 package root 内，禁止 `..` 路径逃逸
- 未在 `actions.yaml` 中声明的 `scripts/*.py` 一律不可执行

## 4.4 `agents/interface.yaml`

### 职责

- 作为 neutral source metadata
- 作为 target adapter 的输入源
- 承载 portability semantics

### 不负责

- 不承载治理状态
- 不承载 action registry
- 不承载评测和报告

### schema 建议

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

字段建议：

| 节点 | 字段 | 必需性 | 规则 |
|---|---|---|---|
| `interface` | `display_name` | MUST | UI 展示名 |
| `interface` | `short_description` | MUST | 短描述 |
| `interface` | `default_prompt` | MUST | 默认提示 |
| `compatibility` | `canonical_format` | MUST | 固定 `agent-skills` |
| `compatibility` | `adapter_targets` | MUST | 导出目标列表 |
| `compatibility.activation` | `mode` | MUST | `manual` / `path_scoped` |
| `compatibility.activation` | `paths` | CONDITIONAL | `path_scoped` 时必填 |
| `compatibility.execution` | `context` | MUST | `inline` / `fork` |
| `compatibility.execution` | `shell` | MUST | `bash` / `powershell` |
| `compatibility.trust` | `source_tier` | MUST | `local` / `managed` / `plugin` / `remote` |
| `compatibility.trust` | `remote_inline_execution` | MUST | `forbid` / `allow` |
| `compatibility.trust` | `remote_metadata_policy` | MUST | 远端元数据策略 |
| `compatibility.degradation` | `<target>` | MUST | 每个 adapter target 都必须有值 |

v1 必须保留的 portability semantics：

- activation
- execution
- trust
- degradation

## 5. Directory Boundaries

## 5.1 `references/`

职责：

- 长文档
- 决策依据
- playbook
- 不能成为 runtime 隐式入口

边界：

- 不允许被当作可执行脚本扫描
- `instruction` 类型 action 可以引用 `references/`，但必须通过 `actions.yaml` 显式声明

## 5.2 `scripts/`

职责：

- 确定性逻辑
- validator、bundler、reporter、runtime 脚本入口

边界：

- 只能作为被 `actions.yaml` 引用的执行体
- 不能通过文件名约定自动执行
- 允许包含 authoring / validation / packaging / report 四类脚本

## 5.3 `evals/`

职责：

- trigger 回归
- holdout/failure 样本
- packaging expectations
- promotion policy

边界：

- 属于发布前 gate，不属于 runtime 默认执行面
- 不允许作为普通业务 action 的默认输入目录

v1 建议最小文件：

- `trigger_cases.json`
- `failure-cases.md`
- `packaging_expectations.json`

## 5.4 `tests/`

职责：

- parser / validator / bundler 的单测和 fixture
- regression tests

边界：

- 不属于 runtime install 默认内容
- 不导出到 target adapter

## 5.5 `adapters/`

职责：

- 平台导出产物的缓存或模板
- 不能成为 neutral source of truth

边界：

- source of truth 仍是 `SKILL.md` 和 `agents/interface.yaml`
- `adapters/` 中的内容可重建，不应手工编辑为主

## 5.6 `reports/`

职责：

- 治理证据
- eval 结果
- portability / governance / context reports

边界：

- 不是 runtime 日志目录
- 不是 source contract 的一部分
- 不导出到 target adapter

## 6. Action Contract And Runtime Boundary

## 6.1 核心规则

runtime 执行面必须满足以下 gate：

1. 读取 package root
2. 解析 `SKILL.md`、`manifest.json`、`actions.yaml`、`agents/interface.yaml`
3. 解析目标 `action_id`
4. 校验 action 存在且 entry 在 root 内
5. 根据 `kind` 和 `sandbox` 调 runner

## 6.2 Allowlist 规则

任何执行请求如果不满足下面任一条，必须直接拒绝：

- `action_id` 不存在
- `kind` 未知
- `entry` 不存在
- `entry` 指向 package root 外
- `runtime` 与 `kind` 不匹配
- `sandbox` 或 `allow_network` 超过运行器支持边界

## 6.3 Side Effect 规则

`actions[].side_effects` 是审计字段，不是注释字段。v1 至少支持：

- `writes_workspace`
- `writes_report`
- `reads_reference`
- `writes_cache`
- `network_call`

如果声明与实际 runner capability 不匹配，运行前校验必须失败。

## 7. Bundle, Install Cache, Runtime Install

## 7.1 导出结构

v1 bundler 输出目录：

```text
dist/
├── manifest.json
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

说明：

- `manifest.json` 为 bundler 生成的导出清单，不等于源包 `manifest.json`
- `targets/*` 为目标适配导出物
- `my-skill.zip` 保留 skill 根目录，不裸平铺文件

## 7.2 安装缓存结构

兼容安装根目录遵循 `/Users/chenge/Desktop/skills-gp- research/skillhub/docs/07-skill-protocol.md`：

1. `./.agent/skills/<slug>/`
2. `~/.agent/skills/<slug>/`
3. `./.claude/skills/<slug>/`
4. `~/.claude/skills/<slug>/`

安装后目录结构：

```text
<install-root>/<slug>/
├── SKILL.md
├── manifest.json
├── actions.yaml
├── agents/interface.yaml
├── references/
├── scripts/
├── assets/
└── .astron/
    └── metadata.json
```

`.astron/metadata.json` v1 建议字段：

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

## 7.3 runtime install 结构

runtime install 是单次运行隔离区里的 materialized copy，v1 推荐结构：

```text
<exec_dir>/
├── .agent/
│   └── skills/
│       └── <slug>/
│           ├── SKILL.md
│           ├── manifest.json
│           ├── actions.yaml
│           ├── agents/interface.yaml
│           ├── references/
│           ├── scripts/
│           └── assets/
├── workspace/
└── .env
```

per-run 持久化目录：

```text
<run_dir>/
├── logs/
├── meta.json
├── result.json
└── plan.json
```

实现说明：

- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/run_context.py` 的双目录模型可直接复用
- 当前代码把 skills materialize 到 `.claude/skills/`
- v1 contract 推荐抽成可配置 `compat_root`，默认优先 `.agent/skills/`
- 为兼容现有 AgentSkillOS，可在 phase 1 先支持 `.claude/skills/` materialization，再切换到通用根

## 7.4 runtime install 内容裁剪

v1 默认包含：

- `SKILL.md`
- `manifest.json`
- `actions.yaml`
- `agents/interface.yaml`
- `references/`
- `scripts/`
- `assets/`

v1 默认排除：

- `tests/`
- `reports/`

按 action profile 条件包含：

- `evals/`
- `adapters/`

## 8. Validation Pipeline

## 8.1 发布前校验

发布前校验顺序：

1. package structure validator
2. `SKILL.md` validator
3. `manifest.json` validator
4. `actions.yaml` validator
5. `agents/interface.yaml` validator
6. governance validator
7. resource boundary validator
8. packaging/export validator

每层校验产物必须能输出 machine-readable JSON report。

### 结构校验

检查项：

- `SKILL.md` 存在
- `actions.yaml` 存在
- `agents/interface.yaml` 存在
- 文件白名单、单文件大小、总包大小、文件数量

### `SKILL.md` 校验

检查项：

- frontmatter 存在
- `name` / `description` 存在
- `name` 为 kebab-case

### `manifest.json` 校验

检查项：

- 必需字段完整
- `updated_at` 为日期
- `name` 与 `SKILL.md.name` 一致
- `status=deprecated` 时 `deprecation_note` 是否补齐

### `actions.yaml` 校验

检查项：

- `schema_version == actions.v1`
- action id 唯一
- `kind` 合法
- `entry` 合法且位于 package root 内
- `script` action 的 `runtime` 必填
- `timeout_sec > 0`
- `input_schema` / `output_schema` 为 object

### `interface.yaml` 校验

检查项：

- `display_name` / `short_description` / `default_prompt`
- `canonical_format`
- `adapter_targets`
- activation / execution / trust / degradation 完整
- `degradation` 必须覆盖所有 `adapter_targets`

### governance 校验

检查项：

- owner、review cadence、maturity tier
- 证据目录是否满足声明
- maturity 与 evidence 分数是否匹配

### resource boundary 校验

检查项：

- `SKILL.md` 是否过重
- `references/` / `scripts/` / `reports/` 是否有未声明目录
- initial load token 是否超预算

### 导出校验

检查项：

- 目标文件齐全
- 目标字段齐全
- portable semantics 未丢失

## 8.2 运行时校验

运行时只做 install-safe 和 execution-safe 校验，不重复做发布治理判断。

加载时校验：

- 目录结构合法
- 目标 action 存在
- `entry` 在 root 内
- `sandbox` / `allow_network` 是受支持值

安装时校验：

- 安装目录名等于 `skill.slug`
- `.astron/metadata.json` 写入成功
- checksum 匹配

执行前校验：

- timeout 合法
- action kind 与 runner 能力匹配
- side effects 与 sandbox 匹配
- runtime install 中存在被引用文件

## 8.3 打包导出链路

导出顺序：

1. parse package
2. validate source contract
3. build target adapter payload
4. materialize `targets/*`
5. zip source package
6. emit export report

## 9. Compatibility Boundary

## 9.1 OpenSkills / Claude

兼容边界保持最小集合：

- `SKILL.md`
- `references/`
- `scripts/`
- `assets/`

兼容要求：

- 安装目录名必须等于 `SKILL.md.name`
- 发现顺序必须兼容 `.agent/skills` 与 `.claude/skills`
- `manifest.json` / `actions.yaml` / `agents/interface.yaml` 为增强字段，兼容客户端可忽略

## 9.2 skillhub

skillhub 兼容边界：

- 服务端只需要 `name` / `description` / `version` 这类技能元数据
- `location` 和 `AGENTS.md` 生成是客户端职责
- `latest` 必须严格表示 latest published
- 公开安装、下载、搜索只能绑定已发布版本

v1 约束：

- contract 层只依赖 published bundle 语义
- 不定义 registry 内部表
- 不定义 registry review workflow 细节

## 9.3 中立源和目标适配的边界

neutral source of truth：

- `SKILL.md`
- `agents/interface.yaml`

治理 source of truth：

- `manifest.json`

execution source of truth：

- `actions.yaml`

target adapter：

- 由 bundler 根据 neutral source 生成
- 不反向写回 source package

## 10. Reuse, Refactor, New Work

## 10.1 可直接复用

### 直接复用的结构与字段样本

- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/SKILL.md`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/manifest.json`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/agents/interface.yaml`
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/references/packaging-contracts.md`

### 直接复用的脚本骨架

- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/validate_skill.py`
  - 可作为 package validator 入口骨架
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/cross_packager.py`
  - 可作为 bundler 和 adapter emitter 骨架
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/resource_boundary_check.py`
  - 可作为 context/resource validator 骨架
- `/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/governance_check.py`
  - 可作为 governance validator 骨架
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/run_context.py`
  - 可作为 runtime install 与 per-run storage 骨架

## 10.2 需要抽离重构

### frontmatter parser

以下两个文件都在做简化 frontmatter 解析，但都不应继续作为 v1 的标准 parser：

- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/skill_scanner.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/skill_registry.py`

原因：

- 只支持 `key: value` 级别的简单行解析
- 对嵌套对象、数组和复杂 YAML 不稳
- parser 重复实现，缺少共享 contract

重构目标已在 phase 1 落地：

- 统一 parser 已抽到：
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/parsers/frontmatter.py`
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/parsers/package.py`
- discovery 和 registry 应只消费共享 parser 输出，不再各自维护 frontmatter 解析逻辑

### 发现与注册模型

`/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/skill_registry.py` 仍可暴露 `allowed-tools` metadata，但执行权限已经迁移到 `actions.yaml`；当前 runtime contract 入口为：

- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/models.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/install.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/resolve.py`

### `validate_skill.py`

`/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/validate_skill.py` 目前没有覆盖：

- `actions.yaml`
- 文件白名单、大小限制、数量限制
- package root 内路径约束
- source package 与 install layout 的一致性

因此应抽成独立 validator 组合器，而不是继续以单文件脚本直接扩展。

### `governance_check.py`

`/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/governance_check.py` 可以复用 scoring 思路，但 `lifecycle_stage` 校验当前复用了 `ALLOWED_MATURITY`，不适合作为 v1 的最终字段校验逻辑，需要拆出独立的 lifecycle/package-stage validator。

### `cross_packager.py`

`/Users/chenge/Desktop/skills-gp- research/yao-meta-skill/scripts/cross_packager.py` 目前：

- 以 `SKILL.md` + `agents/interface.yaml` 作为 neutral source
- 能生成 `targets/openai|claude|generic`
- 能做 expectation-based 导出校验

但还缺：

- 读取和验证 `actions.yaml`
- 读取源包 `manifest.json`
- source bundle 与 runtime bundle 的分层
- install cache metadata 生成

因此建议拆成 parser + adapter builder + bundle writer 三层。

### `RunContext`

`/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/run_context.py` 已在 phase 1 中抽成可配置 `compat_root`，并区分：

- install cache
- runtime install
- per-run log/result storage

当前默认 runtime materialization 规则与本文一致：

- 默认复制 `SKILL.md` / `manifest.json` / `actions.yaml`
- 默认复制 `agents/` / `references/` / `scripts/` / `assets/`
- 默认不复制 `tests/` / `reports/` / `evals/` / `adapters/`

## 10.3 Phase 1 已新增实现

- `actions.yaml` 作为 runtime action contract
- 统一 contract parser 层：
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/parsers/*`
- 统一 validator 层：
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/validators/*`
- source bundle writer：
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/bundler/source_bundle.py`
- runtime install materializer：
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/bundler/runtime_install.py`
- target adapter builder：
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/bundler/target_bundle.py`
- action allowlist facade / resolver：
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/actions.py`
  - `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/resolve.py`

## 11. Phase 1 Module List

Phase 1 只落 package contract，不落调度模式。

### parser 模块

当前实现文件名如下：

- `skill_contract/parsers/frontmatter.py`
  - 输入 `SKILL.md` frontmatter 片段
  - 输出 `SkillFrontmatter`
- `skill_contract/parsers/skill_md.py`
  - 输入 `SKILL.md`
  - 输出 `SkillMarkdownDocument`
- `skill_contract/parsers/manifest.py`
  - 输入 `manifest.json`
  - 输出 `SkillManifest`
- `skill_contract/parsers/actions.py`
  - 输入 `actions.yaml`
  - 输出 `SkillActionsDocument`
- `skill_contract/parsers/interface.py`
  - 输入 `agents/interface.yaml`
  - 输出 `SkillInterfaceDocument`
- `skill_contract/parsers/package.py`
  - 组装四类 parser 输出

兼容 facade：

- `orchestrator/runtime/actions.py`
  - 保留 runtime 侧 `ActionManifest` / `ActionSpec`
  - 原始 `actions.yaml` 读取委托给 `skill_contract/parsers/actions.py`
- `orchestrator/runtime/models.py`
  - package metadata 读取委托给 `skill_contract/parsers/package.py`

### validator 模块

- `skill_contract/validators/package_structure.py`
- `skill_contract/validators/skill_md.py`
- `skill_contract/validators/manifest.py`
- `skill_contract/validators/actions.py`
- `skill_contract/validators/interface.py`
- `skill_contract/validators/governance.py`
- `skill_contract/validators/resource_boundary.py`
- `skill_contract/validators/export.py`
- `skill_contract/validators/runtime_entry.py`
- `skill_contract/validators/package.py`
  - 当前总装顺序为：
  - `package_structure`
  - `skill_md`
  - `manifest`
  - `actions`
  - `interface`
  - `governance`
  - `resource_boundary`
  - `export`
  - `runtime_entry`

### bundler 模块

- `skill_contract/bundler/source_bundle.py`
  - 生成 source zip
- `skill_contract/bundler/export_manifest.py`
  - 生成导出 `manifest.json`
- `skill_contract/bundler/target_bundle.py`
  - 写 `targets/openai|claude|generic`
- `skill_contract/bundler/runtime_install.py`
  - 生成 runtime install 目录

### adapter 模块

- `skill_contract/adapters/base.py`
- `skill_contract/adapters/openai.py`
- `skill_contract/adapters/claude.py`
- `skill_contract/adapters/generic.py`

### phase 1 交付标准

- 可以从一个 skill source package 解析四类 contract 文件
- 可以跑完整 package 校验
- 可以导出 `openai` / `claude` / `generic` 三类 target
- 可以 materialize runtime install 目录
- runtime 对未声明 action 一律拒绝

## 12. Implementation Notes

为避免 contract 和实现再次分叉，phase 1 开发必须遵守：

- parser 只有一份 source of truth，不允许每个子系统各写一份 frontmatter parser
- validator 返回结构化 JSON，不只打印字符串
- bundler 不得修改 source package
- adapter 只从 neutral source 生成，不反向污染 `SKILL.md`
- runtime install materializer 不得默认复制 `tests/` 和 `reports/`
- `strict_actions=False` 只允许 metadata/discovery 降级，不允许 install/resolve/execution fallback
- 缺失 `actions.yaml` 的 legacy package 只能作为 metadata-only skill 被发现，warning code 统一为 `legacy_actions_contract_missing`
- runtime compatibility facade 可以保留类型名，但原始解析 authority 必须委托 `skill_contract`

## 13. Acceptance Checklist

本设计稿落地完成的最小验收标准：

- skill package 目录结构固定
- 四类 contract 文件都有明确 parser 与 validator
- `actions.yaml` 成为 runtime 唯一 action allowlist
- 导出结构、安装缓存结构、runtime install 结构固定
- OpenSkills / Claude / skillhub 的边界固定
- 现有可复用、需重构、需新增模块全部明确

当前 phase 1 代码已满足上述最小验收标准，对应实现入口见 `0.1 Current Implementation Alignment`。
