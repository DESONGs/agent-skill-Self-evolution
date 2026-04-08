# Environment Kernel and Runtime

Date: 2026-04-02  
Scope: AgentSkillOS runtime architecture for skill retrieval, orchestration, run isolation, and layering  
Status: engineering design draft, updated against implementation on 2026-04-03

## 1. What This Document Is For

This document is the implementation-facing design for the runtime half of the AgentSkillOS direction.

It does not discuss generic agent philosophy. It answers a narrower engineering question:

- how the system should decide which skills are relevant
- how it should choose an execution mode
- how it should isolate the run
- how it should execute a skill or a graph of skills
- how active/dormant layering should evolve as the skill library grows

The design is based on the current code in:

- [AgentSkillOS/src/manager/registry.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/registry.py)
- [AgentSkillOS/src/manager/base.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/base.py)
- [AgentSkillOS/src/manager/tree/searcher.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/searcher.py)
- [AgentSkillOS/src/manager/tree/layered_searcher.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/layered_searcher.py)
- [AgentSkillOS/src/manager/tree/layer_processor.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/layer_processor.py)
- [AgentSkillOS/src/manager/vector/indexer.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/vector/indexer.py)
- [AgentSkillOS/src/manager/vector/searcher.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/vector/searcher.py)
- [AgentSkillOS/src/orchestrator/registry.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/registry.py)
- [AgentSkillOS/src/orchestrator/base.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/base.py)
- [AgentSkillOS/src/orchestrator/direct/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/direct/engine.py)
- [AgentSkillOS/src/orchestrator/freestyle/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/freestyle/engine.py)
- [AgentSkillOS/src/orchestrator/dag/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/engine.py)
- [AgentSkillOS/src/orchestrator/dag/skill_registry.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/skill_registry.py)
- [AgentSkillOS/src/orchestrator/runtime/run_context.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/run_context.py)
- [AgentSkillOS/src/workflow/service.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/workflow/service.py)
- [AgentSkillOS/src/workflow/models.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/workflow/models.py)
- [AgentSkillOS/src/config.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/config.py)
- [AgentSkillOS/src/constants.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/constants.py)

## 2. Non-Goals

This document does not define:

- registry governance and publish lifecycle
- skill package schema and packaging contracts
- self-research / skill-factory workflows

Those belong to the other documents in the engineering doc set.

This document focuses on runtime:

- Environment Kernel
- skill retrieval
- execution orchestration
- run context
- runner
- mode selection
- active/dormant layering

## 3. Executive Summary

The current AgentSkillOS code already separates skill discovery from task execution. That separation is the key asset to keep.

The next runtime should preserve and formalize this split:

- `manager axis` = discover, index, rank, layer, visualize skills
- `orchestrator axis` = build run context, choose mode, execute plan, persist artifacts

The system should not collapse these axes into one monolithic agent prompt.

Instead, the runtime should be treated as an `Environment Kernel` that:

- classifies the task and available environment
- retrieves candidate skills
- chooses the right execution mode
- hydrates an isolated run workspace
- executes through a strict runner contract
- persists logs, metadata, and results
- feeds telemetry back into retrieval and layering

The strongest existing code paths to reuse are:

- manager registration and plugin discovery
- tree searcher and layering searcher
- run context isolation
- engine registry and mode metadata
- standardized engine request / result models

The parts that should be refactored are:

- the current loose coupling between skill discovery metadata and execution metadata
- the implicit script use inside skill directories
- mode-specific engine behavior that is currently duplicated across engines
- layering logic that is partly hard-coded in file layout and partly controlled by config

### 3.1 Implementation Update (2026-04-03)

The runtime tail described in this document is now partially implemented in the current AgentSkillOS codebase.

Implemented code paths:

- environment contracts and kernel:
  - [AgentSkillOS/src/environment/models.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/environment/models.py)
  - [AgentSkillOS/src/environment/kernel.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/environment/kernel.py)
- runtime contracts and declared-action execution:
  - [AgentSkillOS/src/orchestrator/runtime/actions.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/actions.py)
  - [AgentSkillOS/src/orchestrator/runtime/install.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/install.py)
  - [AgentSkillOS/src/orchestrator/runtime/envelope.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/envelope.py)
  - [AgentSkillOS/src/orchestrator/runtime/resolve.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/resolve.py)
  - [AgentSkillOS/src/orchestrator/runtime/runners.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/runners.py)
  - [AgentSkillOS/src/orchestrator/runtime/feedback.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/feedback.py)
- workflow integration and metadata backfill:
  - [AgentSkillOS/src/workflow/service.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/workflow/service.py)
  - [AgentSkillOS/src/workflow/models.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/workflow/models.py)
- engine-side resolver injection:
  - [AgentSkillOS/src/orchestrator/freestyle/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/freestyle/engine.py)
  - [AgentSkillOS/src/orchestrator/dag/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/engine.py)

The implemented semantics that supersede earlier draft assumptions are:

- `RuntimeConfig` now carries `feedback_endpoint`, `feedback_auth_token_env`, `feedback_timeout_sec`, `feedback_max_retries`, `max_sandbox`, and `allow_network` in [AgentSkillOS/src/config.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/config.py).
- `TaskRequest`, `EnvironmentRuntimeDefaults`, `TaskContext`, `EnvironmentProfile`, and `ModeDecision` now carry explicit runtime caps in [AgentSkillOS/src/workflow/models.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/workflow/models.py) and [AgentSkillOS/src/environment/models.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/environment/models.py).
- cap precedence is now `request > registry metadata > RuntimeConfig defaults` in [AgentSkillOS/src/environment/kernel.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/environment/kernel.py).
- `free-style` and `dag` both execute declared actions through `ActionResolver(max_sandbox=..., allow_network=...)` instead of carrying implicit script permissions in engine-local logic.
- runtime feedback is now append-only on disk plus optional Generic POST delivery; it is not only a local `meta.json` side effect anymore.
- workflow results now backfill `selected_actions`, `feedback_status`, `max_sandbox`, and `allow_network`, and persist these values into both `run_envelope.json` and `result_envelope.json`.

## 4. Layer Map

The runtime stack should be split into six layers:

1. Environment Kernel
2. Skill Retrieval
3. Mode Selection
4. Execution Orchestration
5. Run Context and Runner
6. Active/Dormant Layering

Each layer has a different contract, a different state surface, and a different ownership boundary.

### 4.1 Manager Axis vs Orchestrator Axis

Keep the following on the `manager axis`:

- skill discovery
- tree search
- vector search
- layered search
- tree building and indexing
- visualization of search results
- dormant index generation

Keep the following on the `orchestrator axis`:

- run context creation
- engine mode selection
- skill installation into the exec workspace
- planning and DAG execution
- direct / freestyle / no-skill execution
- artifact persistence
- run logs and result materialization

Do not move manager responsibilities into orchestrator just because the orchestrator is the thing that finally runs the task.

That separation is the main scalability guardrail.

## 5. Current Code Reuse Matrix

### 5.1 Directly Reusable

These modules can be kept mostly as-is in the new design.

- [AgentSkillOS/src/manager/registry.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/registry.py)
- [AgentSkillOS/src/orchestrator/registry.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/registry.py)
- [AgentSkillOS/src/orchestrator/base.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/base.py)
- [AgentSkillOS/src/orchestrator/runtime/run_context.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/run_context.py)
- [AgentSkillOS/src/manager/tree/searcher.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/searcher.py)
- [AgentSkillOS/src/manager/tree/layered_searcher.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/layered_searcher.py)
- [AgentSkillOS/src/manager/tree/layer_processor.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/layer_processor.py)
- [AgentSkillOS/src/manager/vector/indexer.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/vector/indexer.py)
- [AgentSkillOS/src/manager/vector/searcher.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/vector/searcher.py)
- [AgentSkillOS/src/workflow/models.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/workflow/models.py)
- [AgentSkillOS/src/workflow/service.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/workflow/service.py)

### 5.2 Reusable With Refactor

These modules are useful, but should be abstracted before being treated as final runtime contracts.

- [AgentSkillOS/src/orchestrator/dag/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/engine.py)
- [AgentSkillOS/src/orchestrator/freestyle/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/freestyle/engine.py)
- [AgentSkillOS/src/orchestrator/direct/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/direct/engine.py)
- [AgentSkillOS/src/orchestrator/dag/skill_registry.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/skill_registry.py)
- [AgentSkillOS/src/manager/vector/__init__.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/vector/__init__.py)
- [AgentSkillOS/src/config.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/config.py)
- [AgentSkillOS/src/constants.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/constants.py)

### 5.3 Should Be Split or Replaced

These pieces currently work, but they should not remain the long-term runtime seam.

- mode-specific prompt assembly hidden inside engine classes
- implicit discovery of `SKILL.md` content as the only runtime skill contract
- implicit fallback between directory layout, tree files, and vector files
- duplicated logic for logging, workspace setup, and result persistence across engines

## 6. Environment Kernel

The Environment Kernel is the decision layer in front of runtime execution.

It does not execute skills itself. It answers:

- what environment am I in
- what capabilities are available
- what run mode should be used
- which skills should be considered
- which skills should be excluded

### 6.1 Responsibilities

The kernel should own:

- task classification
- skill group resolution
- manager selection
- mode recommendation
- guardrail evaluation
- execution envelope creation

### 6.2 Inputs

The kernel should read from:

- task description
- optional preselected skills
- user-provided files
- current skill group
- config.yaml runtime settings
- active/dormant layering state
- available manager implementation

### 6.3 Outputs

The kernel should emit an execution envelope with:

- selected manager
- selected execution mode
- candidate skill ids
- whether copy-all is allowed
- runtime constraints
- workspace layout
- expected artifact paths

### 6.4 Suggested Interface

The first implementation can be a thin internal service with a typed output, for example:

```python
@dataclass(frozen=True)
class EnvironmentProfile:
    task: str
    request_mode: str
    effective_mode: str
    mode_source: str
    skill_group: str
    manager_name: str
    orchestrator_name: str
    selected_skill_ids: list[str]
    copy_all_skills: bool
    file_paths: list[str]
    allowed_tools: list[str] | None
    layering_mode: str
    execution_timeout: float | None
    max_sandbox: str
    allow_network: bool
    retrieval_metadata: dict[str, Any]
```

Suggested methods:

- `classify(task_request) -> EnvironmentProfile`
- `select_manager(profile) -> BaseManager`
- `select_mode(profile, retrieval_result) -> str`
- `validate(profile) -> list[str]`

### 6.5 Reuse and Refactor

Reuse:

- [AgentSkillOS/src/constants.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/constants.py) for skill groups and baseline tools
- [AgentSkillOS/src/config.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/config.py) for manager/orchestrator config loading
- [AgentSkillOS/src/workflow/models.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/workflow/models.py) for task request shape

Refactor:

- `TaskRequest` should be split into a user-facing request and an internal environment profile
- manager selection should not be spread across `workflow/service.py` and engine constructors

## 7. Skill Retrieval

Skill retrieval belongs to the manager axis.

The current design already has the right conceptual split:

- `BaseManager` defines `build`, `search`, and visualization hooks
- `manager/registry.py` discovers managers lazily
- `Searcher` performs tree-based search
- `VectorSearcher` performs semantic similarity search
- `LayeredSearcher` composes active and dormant retrieval

### 7.1 Reuse Targets

Keep and reuse:

- [AgentSkillOS/src/manager/base.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/base.py)
- [AgentSkillOS/src/manager/registry.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/registry.py)
- [AgentSkillOS/src/manager/tree/searcher.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/searcher.py)
- [AgentSkillOS/src/manager/vector/searcher.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/vector/searcher.py)
- [AgentSkillOS/src/manager/tree/layered_searcher.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/layered_searcher.py)

### 7.2 Target Boundary

The manager should own only retrieval and indexing logic.

It should not:

- create run directories
- copy skill directories into an execution workspace
- execute the selected skill
- persist run results

That work belongs to orchestrator.

### 7.3 Retrieval Contract

The retrieval layer should output a normalized result structure.

Current code already has this shape in:

- [AgentSkillOS/src/manager/base.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/base.py)
- [AgentSkillOS/src/manager/tree/searcher.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/searcher.py)
- [AgentSkillOS/src/manager/vector/__init__.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/vector/__init__.py)

Recommended normalized result:

```python
@dataclass
class SkillRetrievalResult:
    query: str
    selected_skills: list[dict]
    dormant_suggestions: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
```

### 7.4 What to Keep From Tree Search

The tree searcher is useful because it already supports:

- recursive branch selection
- pruning
- per-node result metadata
- event callbacks for progress tracking

Relevant file:

- [AgentSkillOS/src/manager/tree/searcher.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/searcher.py)

What should remain:

- the recursive search concept
- the `SearchResult` structure
- the progress events

What should be abstracted:

- any hard dependency on a single static tree layout
- any assumption that tree search is the only retrieval strategy

### 7.5 What to Keep From Vector Search

Vector search is a useful complement, not a replacement.

Relevant files:

- [AgentSkillOS/src/manager/vector/indexer.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/vector/indexer.py)
- [AgentSkillOS/src/manager/vector/searcher.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/vector/searcher.py)

Reuse:

- ChromaDB as a dormant or semantic retrieval backend
- the batch embedding and cache validation flow
- metadata payloads for skill results

Refactor:

- vector retrieval should become one retrieval backend behind a manager interface, not the whole retrieval story
- the final retrieval output should be normalized with tree and layering results

## 8. Mode Selection

Mode selection belongs to the orchestrator axis, but it should be informed by the environment kernel.

The current runtime already has three meaningful execution modes:

- `no-skill`
- `free-style`
- `dag`

These are defined in:

- [AgentSkillOS/src/orchestrator/direct/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/direct/engine.py)
- [AgentSkillOS/src/orchestrator/freestyle/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/freestyle/engine.py)
- [AgentSkillOS/src/orchestrator/dag/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/engine.py)

### 8.1 Selection Rules

Recommended mode selection policy:

- choose `no-skill` when no relevant skill is found or the task is clearly baseline-only
- choose `dag` when more than one skill has explicit dependency ordering
- choose `free-style` when the skill set is known but the agent should decide how to use it
- choose `dag` or `free-style` based on config policy when multiple skills are available
- choose `no-skill` as a safety fallback if skill installation or validation fails

### 8.2 Target Boundary

The mode selector should not be hidden inside each engine constructor.

It should be an explicit policy layer that sits between retrieval and orchestration.

Suggested interface:

```python
@dataclass(frozen=True)
class ModeDecision:
    mode: str
    rationale: str
    selected_skill_ids: list[str]
    copy_all_skills: bool
    allowed_tools: list[str] | None = None
    max_sandbox: str = "workspace-write"
    allow_network: bool = False
```

### 8.3 Implemented Runtime Cap Policy

Runtime caps are now treated as first-class environment-kernel output rather than ad hoc engine options.

Implemented merge precedence:

1. explicit `TaskRequest.max_sandbox` / `TaskRequest.allow_network`
2. registry metadata snapshot carried from retrieval
3. `RuntimeConfig.max_sandbox` / `RuntimeConfig.allow_network`

The resolved values are emitted on both:

- `EnvironmentProfile`
- `ModeDecision`

And are injected into:

- `ActionResolver` in [AgentSkillOS/src/orchestrator/freestyle/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/freestyle/engine.py)
- `ActionResolver` in [AgentSkillOS/src/orchestrator/dag/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/engine.py)

This means the environment kernel now controls whether a declared action may exceed the current run's sandbox or network policy.

### 8.4 Reuse and Refactor

Reuse:

- [AgentSkillOS/src/orchestrator/base.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/base.py) for request/result shape
- [AgentSkillOS/src/orchestrator/registry.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/registry.py) for engine discovery
- [AgentSkillOS/src/workflow/service.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/workflow/service.py) for current mode-routing behavior

Refactor:

- move selection logic out of `workflow/service.py` and into a kernel/service boundary
- the `mode` field should become a derived decision, not just a caller-provided string

## 9. Execution Orchestration

Execution orchestration belongs to the orchestrator axis.

The orchestrator should:

- receive the environment profile and selected mode
- create a run context
- install/copy the selected skill set
- open the execution client
- run the task through the selected engine
- persist metadata, logs, and results

### 9.1 Reuse Targets

Relevant files:

- [AgentSkillOS/src/orchestrator/base.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/base.py)
- [AgentSkillOS/src/orchestrator/registry.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/registry.py)
- [AgentSkillOS/src/orchestrator/dag/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/engine.py)
- [AgentSkillOS/src/orchestrator/freestyle/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/freestyle/engine.py)
- [AgentSkillOS/src/orchestrator/direct/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/direct/engine.py)
- [AgentSkillOS/src/workflow/service.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/workflow/service.py)

### 9.2 Current Orchestration Strengths

The current code already does three important things correctly:

1. It standardizes requests through `EngineRequest`.
2. It standardizes outputs through `ExecutionResult`.
3. It keeps engine registration separate from engine implementation.

Those are the right foundational seams.

### 9.3 Target Boundary

The orchestrator should own:

- run lifecycle
- artifact lifecycle
- task-to-engine dispatch
- input file hydration
- skill copy/install behavior
- run-level logging

The orchestrator should not own:

- semantic skill discovery
- index building
- active/dormant layering policy
- vector/tree retrieval strategy

### 9.4 Suggested Internal Split

The new orchestrator should internally split into:

- `RunCoordinator`
- `ModeExecutor`
- `ArtifactWriter`
- `ExecutionLogger`

These can initially live inside the same package, but they should be separated conceptually.

## 10. Run Context

Run context is the physical isolation layer.

The current implementation is one of the strongest pieces in the repository and should be preserved conceptually.

Relevant file:

- [AgentSkillOS/src/orchestrator/runtime/run_context.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/run_context.py)

### 10.1 What It Already Does Well

Current behavior already establishes a clean isolation boundary:

- creates a temporary execution root
- creates a separate execution directory
- creates a separate workspace directory
- keeps permanent run metadata in a separate run directory
- copies skills into the isolated execution tree
- copies input files into workspace
- persists meta and result files

### 10.2 What to Preserve

Preserve the following ideas:

- `exec_dir` is ephemeral and isolated
- `run_dir` is permanent
- `workspace_dir` is where outputs go
- `.claude/skills` is the execution-time skill mount point

### 10.3 What to Refactor

The current `RunContext` mixes too many concerns:

- directory creation
- skill copying
- file copying
- metadata persistence
- result persistence
- log path management

Recommended long-term split:

- `RunFilesystem`
- `RunMetadataStore`
- `SkillMountManager`
- `WorkspaceStager`

### 10.4 Suggested Data Structures

The runtime should surface these explicit concepts:

```python
@dataclass(frozen=True)
class RunEnvelope:
    run_id: str
    task: str
    mode: str
    exec_dir: Path
    workspace_dir: Path
    run_dir: Path
    logs_dir: Path
    skills_dir: Path
    selected_skills: list[str]
    files: list[str]
    allowed_tools: list[str] | None
    copy_all_skills: bool
    environment: dict[str, Any]
    retrieval: dict[str, Any]
    installs: list[dict[str, Any]]
    metadata: dict[str, Any]
```

```python
@dataclass(frozen=True)
class RunManifest:
    run_id: str
    task: str
    mode: str
    selected_skills: list[str]
    files: list[str]
    created_at: str
```

### 10.5 Execution Time Order

The runtime should always follow this order:

1. create `run_dir`
2. create `exec_dir`
3. copy environment files if needed
4. copy or mount skills
5. copy user files
6. write run manifest
7. execute the engine
8. write result and summary
9. finalize logs

That order should be stable and testable.

### 10.6 Current Persisted Runtime Artifacts

The current implementation now persists a broader standardized runtime surface than the original draft assumed.

Implemented runtime files under `run_dir/`:

- `environment.json`
- `retrieval.json`
- `run_envelope.json`
- `installs.json`
- `artifact_index.json`
- `result_envelope.json`
- `feedback.json`
- `feedback_outbox/`
- compatibility files `meta.json` and `result.json`

Relevant implementation:

- [AgentSkillOS/src/orchestrator/runtime/run_context.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/run_context.py)
- [AgentSkillOS/src/orchestrator/runtime/envelope.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/envelope.py)
- [AgentSkillOS/src/orchestrator/runtime/feedback.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/feedback.py)

## 11. Runner

Runner means the concrete execution implementation used by a mode.

The current code already suggests three runner types:

- direct runner
- freestyle runner
- DAG runner

### 11.1 Existing Runner Implementations

Relevant files:

- [AgentSkillOS/src/orchestrator/direct/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/direct/engine.py)
- [AgentSkillOS/src/orchestrator/freestyle/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/freestyle/engine.py)
- [AgentSkillOS/src/orchestrator/dag/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/engine.py)

### 11.2 Recommendation

The long-term contract should be explicit:

```python
class ExecutionRunner(Protocol):
    async def run(self, envelope: RunEnvelope, request: EngineRequest) -> ExecutionResult: ...
```

Then implement:

- `DirectRunner`
- `FreestyleRunner`
- `DagRunner`
- `InstructionRunner`
- `ScriptRunner`
- `McpRunner`
- `SubagentRunner`

### 11.3 What to Keep

Keep the current behavior that each runner:

- constructs a mode-specific prompt
- opens a `SkillClient`
- sets up logging
- saves completion artifacts

### 11.4 What to Remove

Do not let each runner own its own private interpretation of:

- workspace layout
- skill mounting
- log file naming
- metadata file naming

Those should live in shared runtime infrastructure.

### 11.5 Shared Runner Input

Each runner should receive the same shared input envelope and only vary in execution strategy.

That shared input should include:

- run envelope
- selected skill ids
- copied files
- allowed tools
- runtime config

### 11.6 Implemented Declared-Action Runtime Path

The current runtime implementation is now stricter than the original draft text.

What is now true in code:

- `free-style` no longer exposes raw skill directories as implicit execution capability; it builds a bounded action catalog from hydrated installs in [AgentSkillOS/src/orchestrator/runtime/execution.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/execution.py) and [AgentSkillOS/src/orchestrator/freestyle/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/freestyle/engine.py).
- `dag` nodes now resolve `(skill_id, action_id, action_input)` through the same runtime contracts in [AgentSkillOS/src/orchestrator/dag/graph.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/graph.py) and [AgentSkillOS/src/orchestrator/dag/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/engine.py).
- `ActionResolver` is the only gate that can approve declared actions for execution in [AgentSkillOS/src/orchestrator/runtime/resolve.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/resolve.py).
- legacy `SKILL.md only` skills are still executable, but only through a synthetic default `instruction` action created during package loading in [AgentSkillOS/src/orchestrator/runtime/install.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/install.py) and [AgentSkillOS/src/orchestrator/runtime/models.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/runtime/models.py).

## 12. Skill Registry Loading

The runtime needs two registries:

1. the manager registry for retrieval plugins
2. the orchestrator registry for execution plugins

Relevant files:

- [AgentSkillOS/src/manager/registry.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/registry.py)
- [AgentSkillOS/src/orchestrator/registry.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/registry.py)

### 12.1 Reuse

The lazy pkgutil discovery pattern is worth keeping.

It gives the system plugin-style extensibility without manual import chains.

### 12.2 Refactor

The registries should expose a more explicit plugin descriptor surface.

Suggested fields:

- plugin id
- description
- version
- supported capabilities
- UI contribution
- runtime capabilities

### 12.3 Boundary

The manager registry should not know about execution details.

The orchestrator registry should not know about search internals.

## 13. DAG Execution

The DAG path is the most structured execution mode.

Relevant files:

- [AgentSkillOS/src/orchestrator/dag/engine.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/engine.py)
- [AgentSkillOS/src/orchestrator/dag/graph.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/graph.py)
- [AgentSkillOS/src/orchestrator/dag/throttler.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/throttler.py)
- [AgentSkillOS/src/orchestrator/dag/skill_registry.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/orchestrator/dag/skill_registry.py)

### 13.1 Keep

Keep the current separation of:

- planner prompt
- dependency graph
- execution throttling
- skill registry inside the DAG runtime

### 13.2 Refactor

Move the DAG planning output into a typed plan object, not just an ad hoc JSON blob.

Suggested plan entities:

- `Plan`
- `PlanNode`
- `PlanEdge`
- `ExecutionPhase`

### 13.3 Why This Matters

Once skill libraries grow, execution becomes a graph problem, not a prompt problem.

The current DAG design is the right place to encode that transition.

## 14. Active / Dormant Layering

Layering is a retrieval optimization and a governance mechanism.

It should remain on the manager axis.

Relevant files:

- [AgentSkillOS/src/manager/tree/layered_searcher.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/layered_searcher.py)
- [AgentSkillOS/src/manager/tree/layer_processor.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/layer_processor.py)
- [AgentSkillOS/src/manager/vector/searcher.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/vector/searcher.py)

### 14.1 Current Behavior

The current code already supports two important layering strategies:

- directory mode
- install-count mode

And it already supports two dormant retrieval paths:

- vector search
- keyword fallback

### 14.2 What to Keep

Keep these ideas:

- active tree and dormant index are separate artifacts
- dormant suggestions can be returned alongside active results
- the system can fall back from vector to keyword retrieval
- pinning can keep selected skills active

### 14.3 What to Refactor

Current layering logic is split across configuration, file layout, and runtime fallback.

That should be normalized into one explicit layering policy object.

Suggested interface:

```python
@dataclass(frozen=True)
class LayeringPolicy:
    mode: str
    active_threshold: int
    max_dormant_suggestions: int
    dormant_search_keyword_enabled: bool
    dormant_index_path: Path | None
```

### 14.4 Rebuild Flow

The rebuild flow should be:

1. load original tree
2. collect all skills
3. enrich with install or usage stats
4. classify active vs dormant
5. emit active tree
6. emit dormant index
7. persist artifacts atomically

That flow is already present in [AgentSkillOS/src/manager/tree/layer_processor.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/manager/tree/layer_processor.py) and should be preserved, but given a clearer data contract.

### 14.5 Scaling Guidance

When skill count grows, the system should prefer:

- active tree for low-latency search
- dormant vector search for semantic recall
- dormant keyword search for deterministic fallback

That is the right balance between correctness and runtime cost.

## 15. Workflow Entry Point

The workflow layer is the glue between task requests, skill discovery, run context creation, and engine execution.

Relevant files:

- [AgentSkillOS/src/workflow/service.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/workflow/service.py)
- [AgentSkillOS/src/workflow/models.py](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/src/workflow/models.py)

### 15.1 Reuse

Keep:

- `TaskRequest`
- `TaskConfig`
- `TaskResult`
- batch result accumulation
- event callback plumbing

### 15.2 Refactor

Move these responsibilities out of `workflow/service.py`:

- mode decision
- environment classification
- retrieval backend selection
- run envelope construction

That file should become a coordinator, not a policy container.

### 15.3 Suggested Call Flow

```text
TaskRequest
  -> Environment Kernel
  -> Skill Retrieval Manager
  -> Mode Decision
  -> Run Envelope
  -> Orchestrator Engine
  -> ExecutionResult
```

## 16. Proposed Target Module Boundaries

The long-term module split should look like this:

```text
src/
  environment/
    kernel.py
    profile.py
    mode_selector.py
  manager/
    registry.py
    base.py
    tree/
    vector/
  orchestrator/
    registry.py
    base.py
    runtime/
    direct/
    freestyle/
    dag/
  workflow/
    service.py
    models.py
```

### 16.1 What New Modules Would Do

- `environment/kernel.py`
  - classify task environment
  - select manager and mode
- `environment/mode_selector.py`
  - explicit mode policy
- `orchestrator/runtime/run_context.py`
  - keep isolation and staging logic
- `orchestrator/runtime/runner.py`
  - shared runner protocol and common execution helpers

### 16.2 What Existing Modules Should Not Do Anymore

- `manager` should not mount skill files
- `orchestrator` should not discover tree structures
- `workflow` should not hide policy decisions

## 17. Execution Sequence

The full runtime sequence should be stable and testable:

1. receive task request
2. build environment profile
3. select skill retrieval backend
4. retrieve candidate skills
5. choose execution mode
6. create run envelope
7. stage files into workspace
8. mount selected skills
9. execute runner
10. persist result and summary
11. persist feedback and flush outbox delivery
12. update layering indexes if required

## 18. Implementation Phases

### Phase 1: Contract Hardening

Goal:

- make the current boundaries explicit

Deliverables:

- typed environment profile
- explicit mode decision object
- shared run envelope
- explicit runner protocol

### Phase 2: Refactor Common Execution Plumbing

Goal:

- remove duplication between direct / freestyle / dag engines

Deliverables:

- shared logging helper
- shared workspace staging helper
- shared execution summary builder
- shared file copy / skill mount helper

### Phase 3: Formalize Layering

Goal:

- make active/dormant layering an explicit policy

Deliverables:

- policy object
- artifact generation contract
- deterministic fallback path

### Phase 4: Harden Retrieval

Goal:

- improve retrieval quality and traceability

Deliverables:

- retrieval metadata snapshot
- manager result schema normalization
- search backend comparison hooks

## 19. Risks

### Risk 1: Mode Logic Drift

If mode selection stays buried inside per-engine code, the system will accumulate inconsistent behavior.

Mitigation:

- centralize mode decision
- keep engine logic focused on execution only

### Risk 2: Workspace Leakage

If skill packages are not copied into an isolated run directory, execution may accidentally read from host state.

Mitigation:

- keep `exec_dir` isolated
- keep `run_dir` separate from the repo

### Risk 3: Layering Becomes Configuration Sprawl

If layering policy spreads across config, path layout, and ad hoc fallbacks, it becomes impossible to reason about.

Mitigation:

- normalize layering into a single policy surface
- make active/dormant artifacts explicit

### Risk 4: Retrieval and Execution Become Coupled

If execution starts depending on retrieval internals or retrieval starts depending on runner details, both sides become harder to evolve.

Mitigation:

- enforce `manager axis` and `orchestrator axis` separation

### Risk 5: Duplicate Run Plumbing

The three engines already show signs of duplicated setup, logging, and persistence.

Mitigation:

- extract shared runtime helpers early

## 20. Suggested Test Strategy

The runtime refactor should be backed by the following tests:

- manager registry discovery test
- orchestrator registry discovery test
- environment profile selection test
- mode selection test
- run context isolation test
- direct/freestyle/dag runner contract test
- feedback reporter delivery / queued-state test
- runtime cap precedence and resolver-enforcement test
- layered search active/dormant test
- vector fallback test
- workflow integration test

The current repository already contains a lot of this test shape implicitly.

Relevant evidence:

- [AgentSkillOS/tests](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/tests)
- [AgentSkillOS/config/eval](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/config/eval)
- [AgentSkillOS/scripts](/Users/chenge/Desktop/skills-gp- research/AgentSkillOS/scripts)

## 21. Final Recommendation

Keep the current `AgentSkillOS` split, but make it more explicit:

- `manager axis` stays responsible for discovery, indexing, and layering
- `orchestrator axis` stays responsible for mode selection, run isolation, and execution
- `workflow` becomes a thin coordinator
- `run_context` becomes the shared isolation primitive
- `dag`, `free-style`, and `no-skill` become execution strategies behind a shared contract

This is the most direct path from the current repository to a production-grade runtime kernel.
