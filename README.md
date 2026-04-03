# Agent Skill Platform

独立聚合目录，用来把之前分散落在不同仓库里的 phase 1/2 改动收拢成一个可单独上传 GitHub 的目录。

这个目录当前合拢了三条已经落地的代码线：

- `Skill Package Contract`：来自 vendored `AgentSkillOS` contract/parser/validator/bundler 代码
- `Runtime Install + Feedback`：来自 vendored `AgentSkillOS` runtime install/resolve/envelope/feedback 代码
- `Skill Factory / Skill Lab`：来自 vendored `loomiai-autoresearch` 的 `skill_research` pack、lab pipeline、CLI/MCP 入口

同时保留一层统一 facade：

- `src/agent_skill_platform/contracts.py`
- `src/agent_skill_platform/runtime.py`
- `src/agent_skill_platform/lab.py`
- `src/agent_skill_platform/models.py`
- `src/agent_skill_platform/platform.py`

## Layout

```text
agent-skill-platform/
├── docs/
├── packages/
│   └── skill-contracts/
├── runtimes/
│   ├── environment-kernel/
│   └── skill-runtime/
├── services/
│   ├── skill-lab/
│   └── skill-registry/
├── src/
│   └── agent_skill_platform/
├── tests/
├── vendor/
│   ├── agentskillos/
│   └── autoresearch/
└── platform.yaml
```

## What Was Copied

### Vendored from `AgentSkillOS`

- `vendor/agentskillos/src/skill_contract/`
- `vendor/agentskillos/src/orchestrator/runtime/`
- `vendor/agentskillos/src/config.py`
- `vendor/agentskillos/src/constants.py`

### Vendored from `loomiai-autoresearch`

- `vendor/autoresearch/src/autoresearch_agent/`

### Copied docs

- `docs/engineering/*`
- `docs/2026-04-02-agent-skill-environment-engineering.md`
- `docs/2026-04-03-skill-package-contract-v1-implementation-alignment.md`

## Unified Entry Points

安装依赖后，可直接用统一 CLI：

```bash
python -m agent_skill_platform paths
python -m agent_skill_platform validate-package tests/fixtures/valid_skill_package
python -m agent_skill_platform build-install-bundle tests/fixtures/valid_skill_package
python -m agent_skill_platform init-skill-lab /tmp/skill-lab-demo --overwrite
python -m agent_skill_platform run-skill-lab /tmp/skill-lab-demo
python -m agent_skill_platform build-promotion-submission /tmp/skill-lab-demo <run_id>
```

## Notes

- 这是“独立上传目录”，不是原仓库的软引用壳。
- vendored 代码已经复制进本目录；后续上传 GitHub 不依赖原工作区路径。
- `services/skill-registry/` 当前保留的是冻结边界和对接说明，registry 生产实现仍需按 `skillhub` 方向继续抽取。
