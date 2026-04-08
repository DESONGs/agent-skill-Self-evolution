# Skill Package Contract v1 Implementation Alignment

Date: 2026-04-03

Primary design doc:

- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/06-skill-package-contract-v1.md`

## 1. Purpose

本文记录 `Skill Package Contract v1` 在 `AgentSkillOS` 中的当前实现入口，避免设计稿与代码入口脱节。

不扩展讨论：

- registry 内部表设计
- runtime mode selection
- task1 环境哲学

## 2. Current Code Mapping

### 2.1 Parser Source of Truth

- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/parsers/frontmatter.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/parsers/skill_md.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/parsers/manifest.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/parsers/actions.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/parsers/interface.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/parsers/package.py`

兼容 facade：

- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/actions.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/models.py`

要求：

- runtime 不再自写 `actions.yaml` / frontmatter parser
- package metadata 与 action contract 的原始解析 authority 一律来自 `skill_contract/parsers`

### 2.2 Validator Chain

发布前校验入口：

- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/validators/package.py`

当前组合顺序：

1. `package_structure`
2. `skill_md`
3. `manifest`
4. `actions`
5. `interface`
6. `governance`
7. `resource_boundary`
8. `export`
9. `runtime_entry`

对应模块：

- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/validators/package_structure.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/validators/skill_md.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/validators/manifest.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/validators/actions.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/validators/interface.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/validators/governance.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/validators/resource_boundary.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/validators/export.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/validators/runtime_entry.py`

## 3. Runtime Contract Snapshot

### 3.1 Execution Gate

- runtime 实际执行面只允许执行 `actions.yaml` 显式声明的 action
- `scripts/` 中未被 `actions.yaml` 引用的文件，不构成可执行 contract
- `allowed-tools` 只作为 metadata 暴露，不再承担执行授权语义

执行相关入口：

- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/install.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/resolve.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/engine.py`

### 3.2 Missing `actions.yaml` Policy

- discovery / metadata 路径允许识别 legacy package
- compatibility warning code：`legacy_actions_contract_missing`
- metadata 需显式标记 `has_actions_contract = false`
- install / hydrate / resolve / execution 路径一律要求存在 `actions.yaml`
- `strict_actions=False` 仅保留 metadata/discovery 兼容语义，不再允许 install-time 或 execution-time fallback

metadata 入口：

- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/models.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/skill_registry.py`

## 4. Bundle And Install Layout

### 4.1 Bundler

- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/bundler/source_bundle.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/bundler/export_manifest.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/bundler/target_bundle.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/bundler/runtime_install.py`

### 4.2 Runtime Materialization

runtime install 默认复制：

- `SKILL.md`
- `manifest.json`
- `actions.yaml`
- `agents/`
- `references/`
- `scripts/`
- `assets/`

runtime install 默认不复制：

- `tests/`
- `reports/`
- `evals/`
- `adapters/`

运行时 install/layout 入口：

- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/bundler/runtime_install.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/run_context.py`

## 5. Adapter Mapping

- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/adapters/base.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/adapters/openai.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/adapters/claude.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/skill_contract/adapters/generic.py`

导出边界仍保持：

- neutral source 不被 target adapter 反向写回
- `activation` / `execution` / `trust` / `degradation` 四类 portable semantics 必须可保真导出

## 6. Regression Coverage

当前与本 contract 直接相关的测试入口：

- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/tests/test_runtime_actions.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/tests/test_runtime_actions_install.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/tests/test_runtime_resolve.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/tests/skill_contract/test_parsers_and_validators.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/tests/skill_contract/test_bundler_and_adapters.py`
- `/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/tests/orchestrator/test_skill_contract_integration.py`

2026-04-03 的定向回归结果：

- `40 passed`
- 1 个现有 pytest 配置 warning：`asyncio_mode` 未识别
