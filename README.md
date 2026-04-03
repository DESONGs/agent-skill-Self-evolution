# Agent Skill Self-Evolution

一个可持续开发的 Python 主干仓，用来承载 Agent Skill Self-Evolution 的五条核心能力：

- skill package contract
- environment kernel + runtime
- skill lab
- Python registry
- 研究设计文档归档

这个仓不是“聚合壳”了。主运行路径已经切到仓内一等源码，`upstream_snapshot/` 只保留迁移参考，不再作为运行依赖。

## 项目是什么

Agent Skill Self-Evolution 的目标，不是只做一个能跑脚本的 harness，而是把 skill 的定义、安装、执行、反馈、实验、晋升和注册表接成同一条工程链路。

这个仓当前聚焦四个冻结主接口：

- `actions.yaml` schema
- `RuntimeInstallBundle`
- `RunFeedbackEnvelope`
- `PromotionSubmission`

## 仓内已经包含什么

### 1. Skill Contract

- 主源码：`src/skill_contract/`
- 统一 API：`src/agent_skill_platform/contracts/`
- 能力：解析 `SKILL.md` / `manifest.json` / `actions.yaml` / `interface.yaml`，校验 skill package，构建 source bundle，生成 runtime install 物料

### 2. Environment Kernel + Runtime

- 主源码：
  - `src/manager/`
  - `src/orchestrator/`
  - `src/workflow/`
- Runtime 主源码：`src/orchestrator/runtime/`
- 统一 API：
  - `src/agent_skill_platform/kernel/`
  - `src/agent_skill_platform/runtime/`
- 能力：engine/manager 注册发现、runtime install hydration、action resolve、runner 执行、artifact 扫描、feedback envelope 生成

### 3. Skill Lab

- 主源码：`src/autoresearch_agent/`
- 统一 API：`src/agent_skill_platform/lab/`
- 能力：初始化 lab project、运行 skill research pipeline、产出生成包、构建 `PromotionSubmission`

### 4. Python Registry

- 主源码：`src/agent_skill_platform/registry/`
- 技术栈：FastAPI + SQLite + local file storage
- 能力：
  - publish skill package / bundle
  - resolve `RuntimeInstallBundle`
  - ingest `RunFeedbackEnvelope`
  - intake `PromotionSubmission`
  - list/get published skills

### 5. Research Archive

- 设计文档：`docs/engineering/`
- 集成收口文档：`docs/engineering/06-integration-freeze-and-delivery-plan.md`

## 仓结构

```text
agent-skill-platform/
├── docs/
├── packages/
├── runtimes/
├── services/
├── src/
│   ├── agent_skill_platform/
│   ├── autoresearch_agent/
│   ├── manager/
│   ├── orchestrator/
│   ├── skill_contract/
│   └── workflow/
├── tests/
├── upstream_snapshot/
└── pyproject.toml
```

说明：

- `src/agent_skill_platform/` 是对外稳定 API 与 CLI
- `src/skill_contract/`、`src/orchestrator/`、`src/autoresearch_agent/` 等是实际主源码
- `upstream_snapshot/` 是迁移参考快照，不参与主运行路径

## 快速开始

### 安装

```bash
cd agent-skill-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

如果你要启用较完整的 kernel / lab 依赖，可以额外安装：

```bash
pip install -e '.[kernel]'
```

### 看仓内路径

```bash
asp paths
```

### 校验一个 skill package

```bash
asp validate-package tests/fixtures/github-pr-review
```

### 构建 install bundle

```bash
asp build-install-bundle tests/fixtures/github-pr-review
```

### 直接执行 runtime

```bash
asp run-runtime tests/fixtures/github-pr-review --action-input '{"task":"review-pr"}'
```

### 启动本地 registry

```bash
asp registry serve --root .data/registry --host 127.0.0.1 --port 8000
```

### 发布一个 skill 到 registry

```bash
asp registry publish tests/fixtures/github-pr-review --root .data/registry
```

### 解析 install bundle

```bash
asp registry install-bundle github-pr-review --root .data/registry
```

### 初始化并运行 skill lab

```bash
asp init-skill-lab /tmp/asp-skill-lab --project-name Demo --overwrite
asp run-skill-lab /tmp/asp-skill-lab
asp build-promotion-submission /tmp/asp-skill-lab <run_id>
```

## 冻结接口

### `actions.yaml`

- skill package 的动作合同
- runtime resolver / runner 的唯一动作入口

### `RuntimeInstallBundle`

- registry 对 runtime 的安装合同
- install hydration、action resolve、bundle checksum 都以它为主

### `RunFeedbackEnvelope`

- runtime append-only feedback 记录
- registry feedback ingestion 的唯一写入对象

### `PromotionSubmission`

- skill lab 向 registry/promotion 审核面提交的最终对象
- 用来承接实验、评估、生成包和晋升申请

## 对外 API

仓内固定公共 Python API：

- `agent_skill_platform.contracts.validate_skill_package`
- `agent_skill_platform.runtime.build_runtime_install_bundle`
- `agent_skill_platform.runtime.hydrate_runtime_install`
- `agent_skill_platform.runtime.run_runtime`
- `agent_skill_platform.lab.init_skill_lab_project`
- `agent_skill_platform.lab.run_skill_lab_project`
- `agent_skill_platform.lab.build_promotion_submission`
- `agent_skill_platform.registry.publish_package`
- `agent_skill_platform.registry.resolve_install_bundle`
- `agent_skill_platform.registry.ingest_feedback`
- `agent_skill_platform.registry.submit_promotion`

统一 CLI：

- `asp validate-package`
- `asp build-install-bundle`
- `asp run-runtime`
- `asp init-skill-lab`
- `asp run-skill-lab`
- `asp build-promotion-submission`
- `asp registry serve`
- `asp registry publish`
- `asp registry install-bundle`
- `asp registry ingest-feedback`
- `asp registry submit-promotion`

## 开发路线

当前已经打通的最小闭环：

- `publish -> install bundle -> hydrate -> execute action -> feedback`
- `init skill lab -> run -> build promotion submission -> registry intake`

下一步适合继续增强的方向：

- registry 的更完整搜索、版本治理和审核流
- kernel 的更多 execution engine
- skill lab 的更强 candidate/lab/promotion 自动化

## 设计文档索引

核心设计文档在 `docs/engineering/`：

- `README.md`
- `00-program-overview-and-reuse-map.md`
- `01-environment-kernel-and-runtime.md`
- `02-skill-package-and-actions.md`
- `03-registry-search-governance.md`
- `04-skill-factory-and-lab.md`
- `05-implementation-roadmap.md`
- `06-integration-freeze-and-delivery-plan.md`

## 上游来源与演化

这个仓是面向 `https://github.com/DESONGs/agent-skill-Self-evolution.git` 的新主干，不再依赖原工作区绝对路径。

迁移来源主要有两部分：

- `AgentSkillOS`：contract / runtime / kernel 相关实现
- `loomiai-autoresearch`：skill lab / research pipeline 相关实现

这些上游源码的迁移快照保留在 `upstream_snapshot/`，仅用于对照和后续重构参考。
