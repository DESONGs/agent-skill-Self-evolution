# Skill Factory / Skill Lab 实现对齐说明

更新日期：2026-04-03

本文只记录已经落地到代码里的 `Skill Factory / Skill Lab` 行为，用于避免设计文档落后于代码。

边界保持不变：

- 不展开主 runtime 执行模式设计
- 不展开 registry 内部表结构设计
- 只覆盖 `skill_research` pack、lab pipeline、submission/export、CLI/MCP 接口面

目标规格仍然在 [06-skill-factory-lab-delivery-spec.md](/Users/chenge/Desktop/skills-gp-%20research/docs/engineering/06-skill-factory-lab-delivery-spec.md)；本文只回答“现在代码已经做到了什么”。

## 1. 当前代码入口

### 1.1 core pack / scaffold

已落地文件：

- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/packs/loader.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/packs/project.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/project/scaffold.py`

当前行为：

- `PackLoader` 可发现并加载 `skill_research` pack manifest。
- pack loader 已支持按 manifest entrypoint 动态加载 builder / evaluator / template 文件。
- project scaffold 已按 pack 维度支持额外目录和 pack 自带模板。
- `skill_research` 的 editable target 已切换为 `workspace/candidate.yaml`。
- `research.yaml` 可直接由 pack 自带模板生成，而不是走默认 strategy research 模板。
- scaffold 会为 `skill_research` 自动补齐 `datasets/input.json` 占位文件，避免初始化后立刻因数据源缺失而失败。

### 1.2 skill lab pipeline

已落地文件：

- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/skill_lab/__init__.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/skill_lab/pipeline.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/runtime/manager.py`

当前行为：

- `RuntimeManager.create_run()` 在 `pack.id == "skill_research"` 时，进入专门的 skill lab 分支。
- `run_skill_lab()` 会执行：
  1. 读取 `workspace/candidate.yaml`
  2. 通过 pack `builder_module` materialize package
  3. 通过 pack evaluator 生成 gate 报告
  4. 计算 `gate_summary / metrics / promotion decision`
  5. 写 `result.json / summary.json / run_manifest.json / artifact_index.json / report.md`
- `validate_skill_project()` 会在临时目录里 materialize candidate，并跑一遍 gate 侧验证，但不会把 materialized package 持久写回 workspace。

### 1.3 CLI / MCP 路由

已落地文件：

- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/cli/runtime.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/cli/main.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/mcp/server.py`

当前行为：

- CLI 已不再维护一套单独的硬编码 skill runtime。
- `init / validate / run / continue / status / artifacts / submit-promotion` 已统一走真实 pack manifest 和 `RuntimeManager`。
- `submit_promotion()` 会先读取 pack 的 `submission_builder`，再把 run-local submission 结果镜像到项目内的 `workspace/submissions/<candidate_slug>-<run_id>/`。
- MCP 仍复用现有 server，只透传 CLI/runtime 层能力，不新增独立的 skill-lab server。

## 2. 当前 skill_research pack

已落地文件：

- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/pack.yaml`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/templates/research.yaml`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/templates/candidate.yaml`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/templates/SKILL.md.j2`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/templates/manifest.json.j2`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/templates/actions.yaml.j2`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/templates/interface.yaml.j2`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/builders/materialize_candidate.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/builders/export_submission_bundle.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/evaluators/trigger_pack.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/evaluators/action_pack.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/evaluators/boundary_pack.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/evaluators/governance_pack.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/evaluators/resource_pack.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/evaluators/safety_pack.py`

当前 manifest entrypoints：

- `research_template`
- `candidate_template`
- `builder_module`
- `submission_builder`
- `trigger_evaluator`
- `action_evaluator`
- `boundary_evaluator`
- `governance_evaluator`
- `resource_evaluator`
- `safety_evaluator`

兼容性说明：

- 旧的 `*_module` entrypoint key 也仍然保留在 `pack.yaml` 中，方便现有代码兼容。
- core skill lab pipeline 当前优先读取无 `_module` 的 evaluator key，以及 `builder_module`。

## 3. 当前 scaffold 行为

`ar init <project_root> --pack skill_research` 当前会创建：

```text
<project_root>/
├── research.yaml
├── datasets/
│   ├── README.md
│   ├── input.json
│   ├── trigger/train/
│   ├── trigger/dev/
│   ├── trigger/holdout/
│   ├── boundary/
│   ├── action/
│   ├── safety/
│   └── baselines/
├── workspace/
│   ├── candidate.yaml
│   ├── generated/
│   ├── baselines/
│   ├── submissions/
│   └── sources/
├── artifacts/
├── .autoresearch/
│   ├── runs/
│   ├── cache/
│   └── state/
│       ├── pack_manifest.json
│       └── skill_research.pack.json
└── packs/
    └── skill_research/
```

实现位置：

- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/packs/project.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/cli/runtime.py`

当前与规格的一个重要区别：

- `init` 阶段只创建 `workspace/generated/` 目录，不会立即把 materialized skill package 写进 `workspace/generated/<slug>/`。
- 真实的 generated package 发生在 `validate` 的临时 materialization，或 `run` 的 run-local artifacts 写盘。

## 4. 当前 candidate scaffold 行为

当前 `workspace/candidate.yaml` 由 pack 模板生成，schema 为 `skill.candidate.v1`。

实现位置：

- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/templates/candidate.yaml`

当前默认内容已经包含：

- `candidate` 身份信息
- `sources.normalized_summary`
- `qualification.reasons`
- `skill.trigger_description`
- `skill.anti_triggers`
- `skill.boundary.owns / does_not_own`
- `skill.workflow.inputs / steps / outputs`
- `actions.default_action`
- 两个默认 action：
  - `materialize_package`
  - `evaluate_package`
- `package.target_platforms`
- `governance`
- `lab`
- `promotion`

当前默认 candidate 不是空壳，可以直接进入 lab gate。

## 5. 当前 generated package 与 artifact 形态

### 5.1 validate

`validate_skill_project()` 当前会：

1. 读取 `workspace/candidate.yaml`
2. 在临时目录调用 `materialize_candidate()`
3. 执行 pack evaluators
4. 计算：
   - `gate_summary`
   - `metrics`
5. 返回结构化 payload，但不持久写 artifacts

返回面重点字段：

- `ok`
- `pack`
- `candidate`
- `gate_summary`
- `metrics`

### 5.2 run

`run_skill_lab()` 当前会把候选物料写到 run 目录下，而不是写回 workspace：

```text
.autoresearch/runs/<run_id>/
├── run_manifest.json
├── run_spec.json
├── result.json
├── summary.json
└── artifacts/
    ├── candidate.yaml
    ├── generated_skill_package/
    ├── trigger_eval.json
    ├── action_eval.json
    ├── boundary_eval.json
    ├── governance_eval.json
    ├── resource_eval.json
    ├── safety_eval.json
    ├── route_scorecard.json
    ├── packaging_eval.json
    ├── gate_summary.json
    ├── promotion_decision.json
    ├── iteration_history.json
    ├── candidate_patch.json
    ├── report.md
    └── artifact_index.json
```

实现位置：

- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/skill_lab/pipeline.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/core/runtime/manager.py`

### 5.3 generated skill package

当前 materializer 会在 run-local generated package 中产出：

- `SKILL.md`
- `manifest.json`
- `actions.yaml`
- `agents/interface.yaml`
- `candidate.yaml`
- `references/README.md`
- `evals/README.md`
- `reports/README.md`
- `scripts/` 下按 action contract 生成的 placeholder script

当前位置不是 workspace cache，而是：

- `.autoresearch/runs/<run_id>/artifacts/generated_skill_package/`

## 6. 当前 metrics / gate / promotion 语义

当前 `metrics` 字段包括：

- `trigger_precision`
- `boundary_quality`
- `action_contract_completeness`
- `governance_score`
- `resource_budget_ok`
- `safety_score`
- `packaging_score`

当前 gate 汇总包括：

- `trigger`
- `action`
- `boundary`
- `governance`
- `resource`
- `safety`
- `packaging`

当前 promotion 决策枚举为：

- `automatic_promote`
- `manual_review`
- `blocked`

当前 promotion state 枚举为：

- `gate_passed`
- `promotion_pending`
- `gate_failed`

当前默认 scaffold 因为 action 的 `sandbox` 是 `workspace-write`，所以即使 gate 全部通过，promotion 决策也会是：

- `decision: manual_review`
- `state: promotion_pending`

这不是 bug，而是当前 safety/governance 规则的显式结果。

## 7. 当前 submit promotion 行为

当前 `submit_promotion()` 行为分两段：

1. CLI/runtime 读取 pack manifest 的 `submission_builder`
2. pack builder 从 `run_dir/artifacts/generated_skill_package` 生成 zip 和 submission manifest
3. CLI/runtime 再把 submission 输出镜像到 `workspace/submissions/<candidate_slug>-<run_id>/`

实现位置：

- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/cli/runtime.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/packs/skill_research/builders/export_submission_bundle.py`

当前 submission builder 返回的字段包括：

- `ok`
- `run_id`
- `candidate_id`
- `candidate_slug`
- `submission_root`
- `submission_manifest_path`
- `submission_manifest`
- `package_path`
- `bundle_path`
- `package_sha256`
- `generated_package_dir`
- `artifacts_dir`

当前项目内的 submission 镜像目录包含：

- `skill-package.zip`
- `submission_manifest.json`
- `report.md`
- `promotion_decision.json`

## 8. 当前 CLI / MCP 接口

### 8.1 CLI

当前不是单独的 `skill-lab` 命令组，而是复用已有 CLI：

- `ar init <project_root> --pack skill_research`
- `ar validate <project_root>`
- `ar run <project_root>`
- `ar continue <run_id> --project-root <project_root>`
- `ar status <run_id> --project-root <project_root>`
- `ar artifacts <run_id> --project-root <project_root>`
- `ar submit-promotion <run_id> --project-root <project_root>`
- `ar pack list`
- `ar pack install <pack_id> --project-root <project_root>`

实现位置：

- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/cli/main.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/cli/runtime.py`

### 8.2 status payload

`RuntimeManager.status()` 针对 skill lab 返回的不是 strategy runtime 的 `fitness / accuracy / best_config`，而是：

- `run_id`
- `status`
- `updated_at`
- `metrics`
- `gate_passed`
- `promotion_decision`

### 8.3 MCP

当前仍复用现有 MCP server。

实现位置：

- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/src/autoresearch_agent/mcp/server.py`

当前和 skill lab 直接相关的 tool 面：

- `validate_project`
- `get_run_status`
- `list_artifacts`
- `submit_promotion`

`submit_promotion` 会透传 CLI/runtime 层的 submission payload。

## 9. 当前测试覆盖

已落地测试：

- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/tests/test_pack_loader.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/tests/test_project_scaffold.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/tests/test_runtime_flow.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/tests/test_cli_smoke.py`
- `/Users/chenge/Desktop/skills-gp- research/loomiai-autoresearch/tests/test_skill_lab_flow.py`

当前 skill lab 相关测试已覆盖：

- `skill_research` pack 可被发现和 scaffold
- `workspace/candidate.yaml` 用 YAML 方式加载
- `validate_skill_project()` 跑通
- `RuntimeManager.run()` 进入 skill lab 分支
- `status()` 返回 `metrics / gate_passed / promotion_decision`
- `list_artifacts()` 返回 run-local artifact index
- `export_submission_bundle()` 可生成 zip 和 submission manifest
- MCP `submit_promotion` tool 跑通

2026-04-03 当前定向回归结果：

- `python3 -m unittest loomiai-autoresearch.tests.test_pack_loader`
- `python3 -m unittest loomiai-autoresearch.tests.test_project_scaffold`
- `python3 -m unittest loomiai-autoresearch.tests.test_runtime_flow`
- `python3 -m unittest loomiai-autoresearch.tests.test_skill_lab_flow`
- `python3 -m unittest loomiai-autoresearch.tests.test_cli_smoke`
- `python3 -m unittest discover -s loomiai-autoresearch/tests -p 'test_*.py'`

结果：

- `22` 个测试通过

## 10. 当前实现与 06 规格的差异

以下差异是“已知且当前有意接受”的，不应在联调时误判为 bug：

1. `init` 不会立即把 package materialize 到 `workspace/generated/<slug>/`。
2. generated package 的当前真源位置是 run artifacts：
   - `.autoresearch/runs/<run_id>/artifacts/generated_skill_package/`
3. `validate` 使用临时 materialization，不落盘 artifacts。
4. CLI 还没有拆出 `skill-factory build-candidate` 这一类专用命令，当前入口仍是通用 `ar`。
5. Factory 输入来源的 `workflow / transcript / failure / recurring_composition` 归一化 builder 还没有单独实现；当前依赖 scaffold 直接产出初版 candidate。
6. evaluators 目前是第一阶段可运行版本，结构已经齐，但判定逻辑仍偏轻量。
7. 当前 `workspace/submissions` 是 CLI submit 时的镜像目录，不是 pack builder 的直接输出目录。

## 11. 下一个需要继续同步文档的点

如果后续代码继续推进，下列变化需要同步回本文或 `06` 规格：

- 真正落地 Factory source ingestion builder
- `datasets/trigger|boundary|action|safety` 被 eval pipeline 实际消费
- evaluator 从结构检查升级到真实 regression/safety 套件
- `workspace/generated/<slug>` 成为持久 generated cache
- `submit_promotion` 增加更完整的 evidence bundle
- CLI 从通用 `ar` 拆出更明确的 factory/lab 子命令
