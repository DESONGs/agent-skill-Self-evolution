# Registry, Search And Governance 落地设计

Date: 2026-04-02  
Scope: skillhub 作为 skill 资产层的 registry、search、governance、distribution、feedback、candidate ingress  
Status: code-aligned engineering baseline, updated on 2026-04-03

说明：本文主要保留 `skillhub` 来源侧的设计与代码对齐语境。若要判断当前 merged repo `agent-skill-platform/` 内已经落地到哪里的 registry / engine / feedback / promotion 能力，请优先参考 [../plan/v0.5e-implementation-status.md](/Users/chenge/Desktop/skills-gp-%20research/agent-skill-platform/docs/plan/v0.5e-implementation-status.md)。

## 0. 文档边界

本文只讨论 skill 资产层，不讨论 runtime 执行编排细节。

本文的目标不是重新发明一个“大而全 skill service”，而是基于 skillhub 当前已经存在的分层，把 skillhub 收敛成：

- skill registry
- skill search projection
- skill governance center
- skill distribution center
- feedback / candidate ingress

本文明确排除：

- runtime 内部执行状态机
- runtime 如何调 action
- sandbox / scheduler / executor 细节
- agent 在线推理如何选择 skill

runtime 在本文中只被视为 registry 的消费者和 feedback 的生产者。

### 0.1 当前代码对齐状态

截至 2026-04-03，本文已经和 `skillhub/server` 当前实现对齐，以下能力已实际落地：

- publish / promotion 已把 `skill_action`、`skill_environment_profile`、`skill_eval_suite`、`skill_bundle_artifact` 接入主链路：
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillPublishService.java`
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/review/PromotionService.java`
- review / scan 已收敛到 `SAFE -> PENDING_REVIEW`、非 `SAFE -> SCAN_FAILED`，审批严格依赖最新有效 `SAFE` 扫描：
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/review/ReviewService.java`
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/security/SecurityScanService.java`
- governance -> search 已改成统一 rebuild / remove 事件：
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillGovernanceService.java`
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/event/SearchIndexSyncEvent.java`
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/event/SearchIndexEventListener.java`
- search projection 已扩成 latest published only read model，并把 `labels / runtimeTags / actionKinds / successRate / trustScore` 作为 additive fields 暴露：
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/projection/SkillSearchProjectionBuilder.java`
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/postgres/PostgresSearchRebuildService.java`
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/postgres/PostgresFullTextQueryService.java`
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/service/SkillSearchAppService.java`
- distribution 已拆成 public / internal 两轨，public 不暴露 `storageKey`，internal 保留 storage 细节：
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/service/SkillDistributionAppService.java`
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/controller/internal/InternalSkillDistributionController.java`
- download 已追加 append-only feedback，feedback / snapshot / governance signal / candidate ingress 已落地：
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillDownloadService.java`
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillFeedbackIngestionService.java`
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/feedback/SkillScoreSnapshotService.java`
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/service/SkillCandidateAppService.java`
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/service/SkillGovernanceSignalAppService.java`

换句话说，本文不再只是设计稿，而是后端团队当前实现的对齐说明。后续如代码继续演进，应优先更新本文中的 migration、API、job、scope 与 DTO 口径。

## 1. 证据基线

本设计严格基于以下现有文档和代码：

- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/03-registry-search-governance.md`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/docs/01-system-architecture.md`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/docs/04-search-architecture.md`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/docs/07-skill-protocol.md`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/docs/14-skill-lifecycle.md`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/docs/2026-03-20-skill-label-system-design.md`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/docs/2026-04-01-skill-discovery-and-recommendation-architecture.md`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/Skill.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/SkillVersion.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/SkillFile.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/SkillTag.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/SkillVersionStats.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/security/SecurityAudit.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/label/SkillLabel.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillPublishService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/review/ReviewService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/review/PromotionService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillGovernanceService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillDownloadService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/security/SecurityScanService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-infra/src/main/java/com/iflytek/skillhub/infra/scanner/SkillScannerAdapter.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/postgres/PostgresFullTextQueryService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/postgres/PostgresSearchRebuildService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/service/SkillSearchAppService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-infra/src/main/java/com/iflytek/skillhub/infra/jpa/SkillSearchDocumentEntity.java`

为解决 `skill_action`、`skill_environment_profile`、`skill_eval_suite`、`skill_candidate` 的建模缺口，本文还补充使用：

- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/02-skill-package-and-actions.md`
- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/04-skill-factory-and-lab.md`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillLifecycleProjectionService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/SearchVisibilityScope.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/event/SearchIndexEventListener.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/resources/db/migration/V2__phase2_skill_tables.sql`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/resources/db/migration/V14__add_skill_version_stats.sql`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/resources/db/migration/V15__skill_version_download_state.sql`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/resources/db/migration/V34__skill_label_system.sql`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/resources/db/migration/V35__security_audit.sql`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/resources/db/migration/V38__drop_security_audit_skill_version_fk.sql`

## 2. 当前 skillhub 已经可以直接复用的资产边界

### 2.1 现有领域对象直接复用

| 对象 | 当前文件 | 继续承担的职责 | 不要再让谁接管 |
|---|---|---|---|
| `Skill` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/Skill.java` | skill 稳定身份、namespace/slug/owner、visibility、status、latest published pointer、全局统计 | runtime |
| `SkillVersion` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/SkillVersion.java` | immutable 版本、发布状态机、manifest/metadata、bundle/download readiness、yank 信息 | runtime |
| `SkillFile` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/SkillFile.java` | version 内文件索引、storage key、checksum、fallback zip 基础 | runtime |
| `SkillTag` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/SkillTag.java` | mutable distribution alias -> version pointer | label / search 分类 |
| `SkillVersionStats` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/SkillVersionStats.java` | 版本下载计数强一致聚合 | feedback 原始事件表 |
| `SkillLabel` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/label/SkillLabel.java` | skill 级分类与治理标签关联 | tag / version route |
| `SecurityAudit` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/security/SecurityAudit.java` | 版本扫描结果、scanner provenance、soft delete audit trail | runtime |

### 2.2 现有服务直接保留

| 服务 | 当前文件 | 当前职责 | Phase 1 处理方式 |
|---|---|---|---|
| `SkillPublishService` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillPublishService.java` | 校验包、写 `Skill` / `SkillVersion` / `SkillFile`、构建 bundle、提审/直发、触发 scan | 保留并扩展 asset normalization |
| `ReviewService` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/review/ReviewService.java` | submit / approve / reject / withdraw review，维护 `latestVersionId` | 保留并补 scan hard gate |
| `PromotionService` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/review/PromotionService.java` | source published version -> target namespace published copy | 保留并扩展复制新资产表 |
| `SkillGovernanceService` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillGovernanceService.java` | archive / unarchive / hide / yank / delete / withdraw pending | 保留为唯一 lifecycle governance owner |
| `SkillDownloadService` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillDownloadService.java` | latest/version/tag download、presign、fallback zip、download counter | 保留并扩展 distribution descriptor |
| `SecurityScanService` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/security/SecurityScanService.java` | 触发 scan、写 `SecurityAudit`、更新 version 状态 | 保留并修正 SAFE / FAIL 状态分流 |
| `SkillScannerAdapter` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-infra/src/main/java/com/iflytek/skillhub/infra/scanner/SkillScannerAdapter.java` | skill-scanner 接入适配 | 保留 |
| `PostgresFullTextQueryService` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/postgres/PostgresFullTextQueryService.java` | ACL-aware PostgreSQL 查询 | 保留为 phase 1 query engine |
| `PostgresSearchRebuildService` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/postgres/PostgresSearchRebuildService.java` | 权威源 -> `skill_search_document` rebuild | 保留，但下沉成 projection builder 外壳 |
| `SkillSearchAppService` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/service/SkillSearchAppService.java` | search DTO assembly、visibility scope 注入 | 保留 |
| `SkillLifecycleProjectionService` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillLifecycleProjectionService.java` | `publishedVersion / ownerPreviewVersion / resolutionMode` | 直接复用为 latest published 统一解释器 |
| `LabelSearchSyncService` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/service/LabelSearchSyncService.java` | after-commit label rebuild 模式 | 直接复用为其它 rebuild 任务样板 |
| `SearchIndexEventListener` | `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/event/SearchIndexEventListener.java` | publish / status change 后同步搜索索引 | 保留并扩展事件源 |

### 2.3 当前实现的四个关键缺口

这四个缺口不是“推翻现有架构”，而是 Phase 1 必须补的工程改造：

1. `latest published only` 语义在文档上已经成立，但 `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/postgres/PostgresSearchRebuildService.java` 当前仍主要从 `Skill.latestVersionId` 取版本，不足以覆盖 fallback 到其它已发布版本的情况。
2. `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/security/SecurityScanService.java` 当前 `processScanResult()` 会把所有结果都推进到 `PENDING_REVIEW`；资产层治理必须改成 `SAFE -> PENDING_REVIEW`，`UNSAFE/ERROR -> SCAN_FAILED`。
3. bundle 目前依赖 `packages/{skillId}/{versionId}/bundle.zip` 约定和对象存储即时探测，缺少独立的 provenance 表。
4. `actions.yaml`、环境声明、eval suite、candidate、promotion decision 还没有成为 registry 一等公民。

## 3. 目标对象模型

skillhub 资产层最终只保留四类对象：

1. 已发布资产主线
   - `Skill`
   - `SkillVersion`
   - `SkillFile`
   - `SkillTag`
   - `SkillLabel`
   - `SecurityAudit`

2. 已发布资产描述面
   - `skill_bundle_artifact`
   - `skill_action`
   - `skill_environment_profile`
   - `skill_eval_suite`

3. 已发布资产信号面
   - `skill_run_feedback`
   - `skill_score_snapshot`
   - `skill_search_document`

4. 预发布候选资产面
   - `skill_candidate`
   - `skill_promotion_decision`

核心原则：

- `Skill` 是身份，不是执行实例。
- `SkillVersion` 是 immutable asset，不是 runtime run。
- `skill_search_document` 是 projection，不是业务真表。
- `skill_run_feedback` 是 append-only signal，不是 lifecycle source-of-truth。
- `skill_candidate` 是 lab->registry 的 ingress object，不是 runtime object。

## 4. 新增表设计

下面的新增表都是 registry / search / governance 的表，不属于 runtime。

### 4.1 `skill_bundle_artifact`

目的：把 bundle 从“约定路径”升级为“受治理的分发制品”。

建议字段：

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `skill_version_id` | 唯一外键，指向 `skill_version.id` |
| `storage_key` | 对象存储 key |
| `content_type` | 默认 `application/zip` |
| `sha256` | bundle 校验和 |
| `size_bytes` | bundle 大小 |
| `build_status` | `BUILDING / READY / FAILED` |
| `manifest_digest` | manifest 摘要 |
| `built_by` | 生成者 |
| `built_at` | 生成时间 |
| `created_at / updated_at` | 审计字段 |

约束：

- `UNIQUE(skill_version_id)`
- `INDEX(build_status, built_at DESC)`

所有 `/download` 与新 `/distribution` API 后续都先查这张表，再决定是否 fallback zip。

### 4.2 `skill_action`

目的：把 `/Users/chenge/Desktop/skills-gp- research/docs/engineering/02-skill-package-and-actions.md` 中 `actions.yaml` 的动作声明变成版本级资产元数据。

建议字段：

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `skill_version_id` | 外键，指向 `skill_version.id` |
| `action_id` | 动作标识，来自 `actions[].id` |
| `display_name` | 可选展示名 |
| `action_kind` | `SCRIPT / MCP / INSTRUCTION / SUBAGENT` |
| `entry_path` | 相对 skill root 的入口 |
| `runtime_family` | `python3 / bash / node / mcp` 等声明值 |
| `environment_profile_id` | 可空，绑定环境声明 |
| `timeout_sec` | 声明值 |
| `sandbox_mode` | `read-only / workspace-write / network-allowed` 等 |
| `allow_network` | 联网声明 |
| `input_schema_json` | JSON Schema |
| `output_schema_json` | JSON Schema |
| `side_effects_json` | 副作用声明数组 |
| `idempotency_mode` | `exact / best_effort / none` |
| `is_default_action` | 是否默认动作 |
| `created_at / updated_at` | 审计字段 |

约束：

- `UNIQUE(skill_version_id, action_id)`
- `INDEX(skill_version_id, action_kind)`

边界：

- 它只记录“声明过什么 action”，不记录“runtime 实际怎么执行”。
- runtime 不得反向修改这张表。

### 4.3 `skill_environment_profile`

目的：把 skill 的运行兼容面做成资产声明，而不是运行时猜测。

建议字段：

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `skill_version_id` | 外键，指向 `skill_version.id` |
| `profile_key` | 例如 `default`、`claude-code`、`openclaw` |
| `display_name` | 展示名 |
| `runtime_family` | 兼容 runtime 家族 |
| `runtime_version_range` | 版本范围声明 |
| `tool_requirements_json` | 工具需求声明 |
| `capability_tags_json` | 运行时 / 工具 / 能力标签 |
| `os_constraints_json` | OS / arch / shell 约束 |
| `network_policy` | 网络要求 |
| `filesystem_policy` | 文件系统写权限声明 |
| `sandbox_mode` | 沙箱建议值 |
| `resource_limits_json` | 超时 / 内存 / 并发等声明 |
| `env_schema_json` | 所需 env / secret schema |
| `is_default_profile` | 默认 profile |
| `created_at / updated_at` | 审计字段 |

约束：

- `UNIQUE(skill_version_id, profile_key)`

边界：

- registry 只保存 profile 声明。
- runtime 只消费 profile；runtime 不拥有 profile 定义权。

### 4.4 `skill_eval_suite`

目的：把 `evals/` 和 gate 元数据做成资产面，用于治理、候选晋升和后续 ranking 解释。

建议字段：

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `skill_version_id` | 外键，指向 `skill_version.id` |
| `suite_key` | suite 标识 |
| `display_name` | 展示名 |
| `suite_type` | `STRUCTURE / TRIGGER / BOUNDARY / RESOURCE / GOVERNANCE / SECURITY / PACKAGING / PROMOTION` |
| `entry_path` | 声明文件或脚本入口 |
| `gate_level` | `REQUIRED / OPTIONAL / ADVISORY` |
| `config_json` | suite 配置 |
| `success_criteria_json` | 成功门槛 |
| `latest_report_key` | 最近一次报告对象 key，可空 |
| `created_at / updated_at` | 审计字段 |

约束：

- `UNIQUE(skill_version_id, suite_key)`

边界：

- 这张表记录的是“可评测性与 gate contract”，不是具体运行时执行日志。
- 具体评测结果进入 `skill_run_feedback` 和 `skill_promotion_decision`。

### 4.5 `skill_run_feedback`

目的：把下载、安装、执行、评分、lab eval 结果统一落成 append-only 信号源。

建议字段：

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `dedupe_key` | 幂等键，唯一 |
| `feedback_source` | `RUNTIME / DOWNLOAD / UI / LAB / MANUAL` |
| `subject_type` | `SKILL / SKILL_VERSION / SKILL_ACTION / CANDIDATE` |
| `skill_id` | 可空，但推荐始终带上 |
| `skill_version_id` | 可空 |
| `skill_action_id` | 可空 |
| `skill_candidate_id` | 可空 |
| `environment_profile_id` | 可空 |
| `source_run_id` | 外部运行 ID / lab run ID |
| `feedback_type` | `DOWNLOAD / INSTALL / EXECUTION / RATING / REPORT / EVAL_RESULT` |
| `success` | 可空 |
| `rating` | 可空 |
| `latency_ms` | 可空 |
| `error_code` | 可空 |
| `payload_json` | 原始上下文 |
| `observed_at` | 事件发生时间 |
| `ingested_at` | 入库时间 |
| `actor_id` | 可空 |

约束：

- `UNIQUE(dedupe_key)`
- `INDEX(skill_id, observed_at DESC)`
- `INDEX(skill_version_id, observed_at DESC)`
- `INDEX(skill_candidate_id, observed_at DESC)`

强约束：

- append-only，不做 update in place。
- 修正事件用新的补偿事件表达，不回写旧事件。
- runtime 只能写 ingress API，不能直接改统计主表。

### 4.6 `skill_candidate`

目的：承接 `/Users/chenge/Desktop/skills-gp- research/docs/engineering/04-skill-factory-and-lab.md` 中 lab 输出的 candidate artifact，把 candidate 变成 registry 的一等 ingress object。

建议字段：

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `candidate_key` | 全局唯一候选键 |
| `candidate_slug` | 人类可读 slug |
| `candidate_spec_json` | candidate canonical spec，对应 `candidate.yaml` |
| `source_kind` | `WORKFLOW / TRANSCRIPT / FAILURE / COMPOSITION / MANUAL` |
| `source_refs_json` | 上游来源引用 |
| `problem_statement` | 解决的问题 |
| `target_user` | 目标用户 |
| `skill_boundary` | 边界说明 |
| `trigger_description` | 触发描述 |
| `anti_triggers_json` | 反触发列表 |
| `default_action_id` | 默认动作 |
| `governance_json` | owner / maturity / review cadence / trust |
| `metrics_json` | trigger / boundary / portability / safety 等 |
| `generated_bundle_key` | lab 产出的 registry-ready bundle |
| `generated_manifest_key` | lab 产出的 manifest |
| `report_index_key` | lab 报告索引 |
| `latest_lab_run_id` | 最近一次实验运行 |
| `promotion_state` | `CREATED / NORMALIZED / LAB_READY / EVALUATED / GATE_PASSED / PROMOTION_PENDING / PUBLISHED / REJECTED / SUPERSEDED / ARCHIVED` |
| `published_skill_id` | 已发布 skill，可空 |
| `published_version_id` | 已发布 version，可空 |
| `created_by` | 创建者 |
| `created_at / updated_at` | 审计字段 |

约束：

- `UNIQUE(candidate_key)`
- `INDEX(promotion_state, updated_at DESC)`

边界：

- `skill_candidate` 不是 public search object。
- candidate 不走现有 `PromotionService`；它有自己单独的 ingress / decision / publish 流。

### 4.7 `skill_promotion_decision`

目的：把 candidate -> published 的晋升决策做成结构化治理对象，而不是散落在报告目录里的自由文本。

建议字段：

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `skill_candidate_id` | 外键，指向 `skill_candidate.id` |
| `decision` | `PROMOTE / REJECT / HOLD / DEMOTE` |
| `decision_mode` | `AUTOMATIC / HUMAN_REVIEW / POLICY` |
| `reasons_json` | 原因数组 |
| `scores_json` | trigger / boundary / security / packaging 等打分 |
| `evidence_index_key` | 证据对象 key |
| `decided_by` | 决策人，可空 |
| `decided_at` | 决策时间 |
| `created_at` | 审计字段 |

约束：

- `INDEX(skill_candidate_id, decided_at DESC)`

强约束：

- append-only。
- 不替代现有 `PromotionRequest`；后者继续服务“已发布 skill 在 namespace 间复制”。

### 4.8 `skill_score_snapshot`

目的：把 ranking / governance 用到的派生分数从在线请求里拿出去。

建议字段：

| 字段 | 说明 |
|---|---|
| `skill_id` | 主键 |
| `latest_published_version_id` | 对应评分版本 |
| `trust_score` | 标签/审核/治理信号 |
| `quality_score` | eval / suite / completeness 信号 |
| `feedback_score` | success / rating / failure 汇总 |
| `success_rate_30d` | 近 30 天成功率 |
| `rating_bayes` | 平滑评分 |
| `download_count_30d` | 近 30 天下载量 |
| `lab_score` | 来自 candidate / promotion decision 的信号 |
| `updated_at` | 快照时间 |

约束：

- `PRIMARY KEY(skill_id)`

说明：

- phase 1 可以先不加 daily rollup 表，直接由 raw events 异步刷新 snapshot。
- 如果 volume 增长，再引入 `skill_feedback_rollup_daily`。

## 5. publish / review / scan / governance / search / download 主链路

### 5.1 Publish 主链路

owner service：

- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillPublishService.java`

建议链路：

1. 接收 package entries。
2. 继续复用 `SkillPackageValidator`、`SkillMetadataParser` 校验 `SKILL.md`。
3. 解析可选增强文件：
   - `manifest.json`
   - `actions.yaml`
   - `agents/interface.yaml`
   - `evals/*`
4. 写 `Skill`、`SkillVersion`、`SkillFile`。
5. 构建 bundle，写对象存储。
6. 写 `skill_bundle_artifact`。
7. 写 `skill_action`、`skill_environment_profile`、`skill_eval_suite`。
8. 如果需要审核：
   - 版本进入 `PENDING_REVIEW`
   - 创建 `ReviewTask`
   - 触发 scan
9. 如果直发：
   - 版本进入 `PUBLISHED`
   - 更新 `Skill.latestVersionId`
   - 发布 search rebuild 事件

Phase 1 要求：

- 增强文件缺失时不拒绝发布，保持对 `/Users/chenge/Desktop/skills-gp- research/skillhub/docs/07-skill-protocol.md` 现有 `SKILL.md` 协议兼容。
- 所有增强文件都只做 asset metadata normalization，不下沉 runtime 执行逻辑。

### 5.2 Review 主链路

owner service：

- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/review/ReviewService.java`

建议链路：

1. `submitReview` 只把版本推进到待审队列。
2. `approveReview` 必须同时满足：
   - `SkillVersion.status != SCANNING`
   - 最新 active `SecurityAudit.verdict = SAFE`
   - 没有 slug 冲突的已发布同名 skill
3. 审核通过：
   - `SkillVersion.status = PUBLISHED`
   - `SkillVersion.publishedAt` 写入
   - `Skill.latestVersionId` 指向该版本
   - `Skill.visibility` 同步 `requestedVisibility`
   - 触发 search rebuild
4. 审核拒绝：
   - `SkillVersion.status = REJECTED`
   - 保留版本用于治理或删除
5. 撤回提审：
   - `PENDING_REVIEW -> DRAFT`
   - 删除 `PENDING` review task

Review 永远只处理已发布资产线，不处理 candidate 晋升决策。

### 5.3 Scan 主链路

owner service：

- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/security/SecurityScanService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-infra/src/main/java/com/iflytek/skillhub/infra/scanner/SkillScannerAdapter.java`

建议链路：

1. publish 或 resubmit 触发 `triggerScan()`。
2. 先写一条新的 `SecurityAudit`，保证多轮扫描可追踪。
3. 版本进入 `SCANNING`。
4. scanner completion 后：
   - 写回 `SecurityAudit.scanId / verdict / findings / duration`
   - `SAFE -> PENDING_REVIEW`
   - `SUSPICIOUS / UNSAFE / scanner error -> SCAN_FAILED`
5. Governance / Review 只读取 `SecurityAudit`，不自己计算扫描结果。

这个改造与当前代码相比的唯一关键变化，是不能再把所有扫描结果都推进到 `PENDING_REVIEW`。

### 5.4 Governance 主链路

owner service：

- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillGovernanceService.java`

治理动作保持现状：

- hide / unhide
- archive / unarchive
- withdraw pending version
- delete non-published version
- yank published version

Phase 1 补充要求：

- governance 动作后统一触发 search projection rebuild 或 remove。
- yank / delete / archive 之后必须重算 latest published pointer。
- governance 不直接改 `skill_search_document`，只发事件。
- governance 不处理 runtime run，也不处理 install cache。

### 5.5 Search 主链路

owner modules：

- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/postgres/PostgresSearchRebuildService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/postgres/PostgresFullTextQueryService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/service/SkillSearchAppService.java`

建议链路：

1. publish / review / governance / label / feedback snapshot 更新后，发出 rebuild 任务。
2. projection builder 从权威源重建单 skill 的 `skill_search_document`。
3. query 时由 app service 先构建 `SearchVisibilityScope`。
4. SQL 层先做 ACL / visibility / status 过滤，再做全文检索，再做排序。
5. API assembly 层只负责把 hit id 映射成 summary response。

### 5.6 Download / Distribution 主链路

owner service：

- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillDownloadService.java`

建议链路：

1. `latest / version / tag` 解析到 version。
2. 校验 namespace、visibility、status、hidden、published accessibility。
3. 先读 `skill_bundle_artifact`。
4. 若 bundle 就绪：
   - 获取 metadata
   - 生成 presigned url
   - 记录 download counter
   - 追加一条 `skill_run_feedback(feedback_source=DOWNLOAD, feedback_type=DOWNLOAD)`
5. 若 bundle 缺失：
   - 通过 `SkillFile` fallback build zip
   - 标记 `fallbackBundle=true`
6. 对外提供两套接口：
   - 现有 `/download`：保留 raw zip 下载
   - 新增 `/distribution`：返回 install descriptor

## 6. Search projection 模型

### 6.1 逻辑模型：`skill_latest_published_doc`

逻辑上，search 只认一条对象：

- 一个 skill 对应一条文档
- 文档内容永远来自 latest published version
- 如果没有任何 published version，则这个 skill 不应有 public search 主文档

这与 `/Users/chenge/Desktop/skills-gp- research/skillhub/docs/14-skill-lifecycle.md` 第 3 节完全一致。

### 6.2 物理模型：继续复用 `skill_search_document`

phase 1 不新增 `skill_latest_doc` 实体表，继续扩展现有：

- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-infra/src/main/java/com/iflytek/skillhub/infra/jpa/SkillSearchDocumentEntity.java`

建议新增列：

| 字段 | 来源 | 用途 |
|---|---|---|
| `latest_published_version_id` | `SkillLifecycleProjectionService` | 强化 latest published only 语义 |
| `latest_published_version` | `SkillVersion.version` | 搜索结果展示 |
| `published_at` | `SkillVersion.publishedAt` | freshness |
| `label_slugs` | `skill_label + label_definition` | facet/filter |
| `runtime_tags` | `skill_environment_profile` | discovery/filter |
| `tool_tags` | `skill_environment_profile` | discovery/filter |
| `action_kinds` | `skill_action` | discovery/filter |
| `trust_score` | `skill_score_snapshot` | ranking |
| `quality_score` | `skill_score_snapshot` | ranking |
| `feedback_score` | `skill_score_snapshot` | ranking |
| `success_rate_30d` | `skill_score_snapshot` | governance / ranking |
| `scan_verdict` | `SecurityAudit` | governance / UI |
| `review_state` | `SkillVersion.status` | governance / UI |

### 6.3 latest published only 的实现约束

必须明确以下硬约束：

1. `Skill.latestVersionId` 的唯一业务语义是 latest published pointer。
2. projection builder 不能只信任数据库中的 pointer；它必须在 pointer 失效时 fallback 到“该 skill 最新 `PUBLISHED` 版本”。
3. 若 skill 没有任何 `PUBLISHED` 版本：
   - public search document 删除
   - internal owner preview 不进入 public search
4. `tag` 指向的版本不改变 search projection 的内容。
5. `candidate` 不进入 public search。

这意味着 `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/postgres/PostgresSearchRebuildService.java` 必须改成复用 `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillLifecycleProjectionService.java` 的 published resolver，而不是直接把 `Skill.latestVersionId` 当成足够条件。

### 6.4 projection builder 的输入源

单条 search doc 的权威输入源应固定为：

- `Skill`
- `SkillVersion` 中的 latest published version
- `SkillLabel`
- `LabelDefinition`
- `LabelTranslation`
- `SkillAction`
- `SkillEnvironmentProfile`
- `SkillEvalSuite`
- `SecurityAudit`
- `SkillScoreSnapshot`

生成规则：

- `title`: `Skill.displayName`，为空则降级到 `Skill.slug`
- `summary`: `Skill.summary`
- `keywords`: frontmatter keywords + label translations + runtime/tool/action 文本
- `search_text`: slug + summary + frontmatter 非保留字段 + profile/action/eval 的可搜索文本
- `visibility`: `Skill.visibility`
- `status`: `Skill.status`
- `semantic_vector`: phase 1 继续可选

### 6.5 查询侧的固定边界

ACL 和治理过滤必须在 query 侧先执行，排序只能在通过 ACL 的候选集上做。

当前 `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/postgres/PostgresFullTextQueryService.java` 已经体现了正确顺序：

- `PUBLIC`
- `NAMESPACE_ONLY + memberNamespaceIds`
- `PRIVATE + (adminNamespaceIds or ownerId)`
- `s.status = ACTIVE`
- `s.hidden = FALSE`
- namespace 未归档或调用者是成员

phase 1 保持这条顺序，不把 ACL 放进离线 projection。

## 7. label、tag、ACL、visibility 的边界

### 7.1 label 和 tag 必须彻底分开

| 维度 | label | tag |
|---|---|---|
| 绑定层级 | skill 级 | version 路由级 |
| 当前表 | `skill_label` | `skill_tag` |
| 当前文档依据 | `/Users/chenge/Desktop/skills-gp- research/skillhub/docs/2026-03-20-skill-label-system-design.md` | `/Users/chenge/Desktop/skills-gp- research/skillhub/docs/07-skill-protocol.md` |
| 语义 | 分类、推荐、治理信号 | `latest / stable / beta / candidate` 等分发别名 |
| 是否进 search facet | 是 | 否 |
| 是否直接影响 download resolve | 否 | 是 |
| 是否允许 runtime 回写 | 否 | 否 |

硬约束：

- search projection 可以写 label 文本，不能把 tag 文本当分类写进去。
- `/download`、`/resolve` 可以接收 tag，不能接收 label。
- runtime 永远不负责 label/tag 的写入。

### 7.2 ACL 和 visibility 在搜索里的位置

ACL 的 owner service 仍然是 app + search query 两层：

- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/service/SkillSearchAppService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/SearchVisibilityScope.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/postgres/PostgresFullTextQueryService.java`

职责拆分：

- app service 负责把当前用户上下文投影成 `SearchVisibilityScope`
- search query service 负责把 scope 翻译成 SQL 过滤
- projection 只保存 `visibility` 和 `ownerId` 等冗余字段，不计算 ACL

### 7.3 visibility 与 hidden 的边界

`visibility` 和 `hidden` 不是一回事：

- `visibility` 是访问控制语义，属于 search / distribution 的输入
- `hidden` 是治理覆盖层，属于 governance 的输出

phase 1 保持当前做法：

- `visibility` 冗余到 `skill_search_document`
- `hidden` 继续通过 join `skill` 做 query-time 过滤

## 8. 对象存储 key、bundle、fallback zip、distribution API

### 8.1 skill 资产对象 key

phase 1 直接保留现有 key 体系，不做破坏性改动：

- 源文件：`skills/{skillId}/{versionId}/{normalizedPath}`
- bundle：`packages/{skillId}/{versionId}/bundle.zip`

这与以下现有实现一致：

- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillPublishService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillDownloadService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillGovernanceService.java`

原因：

- 当前数据已按这个 key 生成。
- 现有 delete / download / fallback 逻辑都依赖这个约定。
- phase 1 的重点是给它补 provenance，不是改 key 体系。

### 8.2 candidate 对象 key

为 `skill_candidate` 单独开前缀，不复用 published skill key：

- spec：`candidates/{candidateId}/spec/candidate.yaml`
- generated bundle：`candidates/{candidateId}/bundles/registry-ready.zip`
- reports：`candidates/{candidateId}/reports/{runId}/{artifactName}`

candidate 和 published asset 的对象 key 必须分域，避免误删和生命周期混淆。

### 8.3 fallback zip 的定位

fallback zip 继续保留，但角色只能是：

- 分发兜底
- 历史 bundle 缺失时的兼容路径

它不是新的 canonical artifact。

canonical artifact 只能是：

- `skill_bundle_artifact.storage_key` 指向的 bundle

### 8.4 distribution API

phase 1 保留现有下载 API：

- `GET /api/v1/skills/{namespace}/{slug}/download`
- `GET /api/v1/skills/{namespace}/{slug}/versions/{version}/download`
- `GET /api/v1/skills/{namespace}/{slug}/tags/{tagName}/download`

新增 descriptor API：

- `GET /api/v1/skills/{namespace}/{slug}/distribution`
- `GET /api/v1/skills/{namespace}/{slug}/versions/{version}/distribution`
- `GET /api/v1/skills/{namespace}/{slug}/tags/{tagName}/distribution`

建议响应：

```json
{
  "skillId": 101,
  "versionId": 1001,
  "namespace": "@team-ai",
  "slug": "github-pr-review",
  "resolvedBy": {
    "kind": "LATEST",
    "value": "latest"
  },
  "bundle": {
    "downloadUrl": "https://...",
    "sha256": "abc123",
    "sizeBytes": 123456,
    "contentType": "application/zip",
    "fallbackBundle": false
  },
  "manifest": {},
  "actions": [
    {
      "id": "run",
      "kind": "SCRIPT",
      "environmentProfile": "default"
    }
  ],
  "environmentProfiles": [
    {
      "profileKey": "default",
      "runtimeFamily": "claude-code"
    }
  ],
  "labels": ["code-review", "github"],
  "visibility": "PUBLIC",
  "publishedAt": "2026-04-02T00:00:00Z",
  "scanVerdict": "SAFE"
}
```

运行时只能消费 descriptor，不应该看到对象存储拼 key 的规则。

## 9. feedback ingestion：append-only 设计，以及它如何服务 ranking / governance / lab

### 9.1 append-only 原则

`skill_run_feedback` 是原始信号表，必须遵守：

- 单条事件只插入，不原地更新
- 幂等靠 `dedupe_key`
- 修正靠补偿事件，而不是修改旧事件
- download、install、execution、rating、lab eval 都落同一表

### 9.2 ingestion owner

建议新增：

- domain service：`SkillFeedbackIngestionService`
  - 建议路径：`/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillFeedbackIngestionService.java`
- app service：`SkillFeedbackIngestionAppService`
  - 建议路径：`/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/service/SkillFeedbackIngestionAppService.java`

建议 API：

- `POST /api/v1/internal/skill-feedback`

phase 1 不要求 runtime 批量上报；先支持单 envelope 幂等写入即可。

### 9.3 feedback 如何服务 ranking

raw event 不直接进在线查询。

异步流程：

1. `skill_run_feedback` append
2. `SkillScoreSnapshotRefreshJob` 读取 raw events
3. upsert `skill_score_snapshot`
4. 触发 search projection rebuild，回填：
   - `feedback_score`
   - `success_rate_30d`
   - `trust_score`
   - `quality_score`

这样做的结果：

- search 排序是 snapshot 驱动，不是在线聚合
- query SQL 不直接扫 feedback 原始表

### 9.4 feedback 如何服务 governance

治理只使用聚合信号，不使用单条 noisy event 直接封禁。

建议治理读法：

- `success_rate_30d` 持续低于阈值 -> 进入人工复核队列
- `feedback_score` 连续下降 -> 降低 search rank
- 高频 failure + 特定 error_code -> 触发安全/质量复查
- 低质量但高下载 skill -> 标记“高风险高影响”，优先治理

这部分建议新建内部 app service：

- `SkillGovernanceSignalAppService`
  - 建议路径：`/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/service/SkillGovernanceSignalAppService.java`

### 9.5 feedback 如何服务 lab

lab 不应该绕过 registry 去自建一套“published skill 表现库”。

统一做法：

- lab run 也写 `skill_run_feedback(feedback_source=LAB, subject_type=CANDIDATE or SKILL_VERSION)`
- candidate 晋升前，`skill_promotion_decision` 可引用同一批 feedback summary 和 report key
- candidate 发布后，published skill 继续沿用相同信号模型

这样 ranking / governance / lab 三条线共享同一份原始信号源和快照层。

## 10. runtime 与 registry 的接口边界

### 10.1 runtime 只允许做什么

runtime 对 registry 的合法交互只有四类：

1. 读取 search / recommend 结果
2. 读取 distribution descriptor
3. 下载 bundle
4. 上报 feedback envelope

### 10.2 runtime 绝不能承担什么

以下能力绝不能由 runtime 承担：

- 发布 `Skill` / `SkillVersion`
- 写 `SkillFile` / `SkillTag` / `SkillLabel`
- 审核 `ReviewTask`
- 做 namespace promotion
- 触发或裁决 `SecurityAudit`
- 维护 `Skill.latestVersionId`
- 构建或重建 `skill_search_document`
- 直接增删对象存储的 canonical bundle
- 直接写 `skill_score_snapshot`
- 直接做 candidate 晋升决策

一句话概括：

- runtime 只消费资产，不拥有资产。

### 10.3 registry 暴露给 runtime 的稳定合同

registry 对 runtime 只暴露两类稳定合同：

- distribution contract
- feedback ingest contract

registry 不向 runtime 暴露：

- 数据表结构
- object storage key 规则
- search projection schema
- governance 内部状态机

## 11. 建议保留的服务、建议新增的 app service / async job / projection builder

### 11.1 直接保留并扩展

| 保留对象 | 动作 |
|---|---|
| `SkillPublishService` | 增加 asset normalization、bundle artifact 持久化 |
| `ReviewService` | 增加 SAFE scan hard gate |
| `PromotionService` | 增加复制 `skill_bundle_artifact` / `skill_action` / `skill_environment_profile` / `skill_eval_suite` |
| `SkillGovernanceService` | 保持唯一 lifecycle mutator |
| `SkillDownloadService` | 增加 distribution descriptor，优先读 `skill_bundle_artifact` |
| `SecurityScanService` | 增加 `SCAN_FAILED` 分流 |
| `PostgresFullTextQueryService` | 保持 query engine，不直接碰主表 |
| `PostgresSearchRebuildService` | 变成 thin rebuild facade，内部委托 projection builder |
| `SkillSearchAppService` | 保持 DTO assembly |
| `LabelSearchSyncService` | 作为 after-commit async rebuild 模式复用 |

### 11.2 新增 domain service

建议新增：

- `SkillAssetNormalizationService`
  - 解析 `manifest.json`、`actions.yaml`、`agents/interface.yaml`、`evals/*`
- `SkillBundleArtifactService`
  - bundle provenance、sha256、metadata
- `SkillFeedbackIngestionService`
  - append-only feedback 写入
- `SkillScoreSnapshotService`
  - raw events -> snapshot
- `SkillCandidateService`
  - candidate ingress、状态迁移
- `SkillCandidatePromotionService`
  - candidate -> publish orchestration
- `SkillPromotionDecisionService`
  - promotion decision ledger

建议文件路径：

- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillAssetNormalizationService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillBundleArtifactService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillFeedbackIngestionService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/skill/service/SkillScoreSnapshotService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/candidate/SkillCandidateService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/candidate/SkillCandidatePromotionService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-domain/src/main/java/com/iflytek/skillhub/domain/candidate/SkillPromotionDecisionService.java`

### 11.3 新增 app service

建议新增：

- `SkillDistributionAppService`
  - `/distribution` API
- `SkillFeedbackIngestionAppService`
  - internal feedback API
- `SkillCandidateAppService`
  - candidate ingress / query
- `SkillGovernanceSignalAppService`
  - governance panel / low quality queue

建议文件路径：

- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/service/SkillDistributionAppService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/service/SkillFeedbackIngestionAppService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/service/SkillCandidateAppService.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/service/SkillGovernanceSignalAppService.java`

### 11.4 新增 async job / projection builder

建议新增：

- `SkillSearchProjectionBuilder`
  - 单 skill 权威源 -> search doc
- `SkillFeedbackAggregationJob`
  - raw feedback -> snapshot
- `SkillBundleArtifactBackfillJob`
  - 从历史对象存储回填 bundle provenance
- `SkillAssetMetadataBackfillJob`
  - 从历史包内容回填 action/env/eval
- `SkillSearchProjectionRebuildJob`
  - admin/manual rebuild

建议文件路径：

- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-search/src/main/java/com/iflytek/skillhub/search/projection/SkillSearchProjectionBuilder.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/task/SkillFeedbackAggregationJob.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/job/SkillBundleArtifactBackfillJob.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/job/SkillAssetMetadataBackfillJob.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/job/SkillSearchProjectionRebuildJob.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/task/ScoreSnapshotBootstrapJob.java`

## 12. 第一阶段 migration 与 API 增量方案

### 12.1 Flyway schema migration

现有 migration 最高已经到：

- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/resources/db/migration/V38__drop_security_audit_skill_version_fk.sql`

建议 phase 1 新增：

1. `V39__skill_registry_asset_metadata.sql`
   - `skill_bundle_artifact`
   - `skill_action`
   - `skill_environment_profile`
   - `skill_eval_suite`
2. `V40__feedback_candidate_registry_assets.sql`
   - `skill_run_feedback`
   - `skill_score_snapshot`
   - `skill_candidate`
   - `skill_promotion_decision`
3. `V41__expand_skill_search_document_asset_fields.sql`
   - 扩 `skill_search_document`
   - 增索引

约束：

- Flyway 只做 DDL。
- 任何需要访问对象存储的 backfill，都不要塞进 SQL migration。

当前代码对应文件：

- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/resources/db/migration/V39__skill_registry_asset_metadata.sql`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/resources/db/migration/V40__feedback_candidate_registry_assets.sql`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/resources/db/migration/V41__expand_skill_search_document_asset_fields.sql`

补充说明：

- phase 1 的 feedback / snapshot / candidate / promotion decision 已合并落在 `V40__feedback_candidate_registry_assets.sql`，不再拆成独立的 `V41__skill_candidate_and_promotion_decision.sql`。
- 设计稿中的早期草案如果提到 `V42__expand_skill_search_document_asset_fields.sql`，应以当前实际实现的 `V41` 为准。

### 12.2 数据 backfill

建议通过后台 job 做：

1. `SkillBundleArtifactBackfillJob`
   - 读取 `packages/{skillId}/{versionId}/bundle.zip`
   - 回填 `skill_bundle_artifact`
2. `SkillAssetMetadataBackfillJob`
   - 对历史 published version 重新解析增强文件
   - 无增强文件则写空集合，不报错
3. `SkillSearchProjectionRebuildJob`
   - 用新 projection builder 重建全量 search docs
4. `ScoreSnapshotBootstrapJob`
   - 先用现有 `Skill.downloadCount` / `SkillVersionStats.downloadCount` 初始化 snapshot

当前代码对应文件：

- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/job/SkillBundleArtifactBackfillJob.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/job/SkillAssetMetadataBackfillJob.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/job/SkillSearchProjectionRebuildJob.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/task/SkillFeedbackAggregationJob.java`
- `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/task/ScoreSnapshotBootstrapJob.java`

补充说明：

- `SkillFeedbackAggregationJob` 会在 snapshot 刷新后发布 search rebuild 事件。
- `ScoreSnapshotBootstrapJob` 会在 bootstrap 缺失快照后发布 search rebuild 事件。
- `SkillAssetMetadataBackfillJob` 当前会把 action 回填并重新关联到回填后的 environment profile id。

### 12.3 API 增量，不破坏现有客户端

保留不变：

- publish API
- search API
- download API
- label / tag API
- governance API

新增 API：

- `GET /api/v1/skills/{namespace}/{slug}/distribution`
- `GET /api/v1/skills/{namespace}/{slug}/versions/{version}/distribution`
- `GET /api/v1/skills/{namespace}/{slug}/tags/{tagName}/distribution`
- `GET /api/v1/internal/skills/{namespace}/{slug}/distribution`
- `GET /api/v1/internal/skills/{namespace}/{slug}/versions/{version}/distribution`
- `GET /api/v1/internal/skills/{namespace}/{slug}/tags/{tagName}/distribution`
- `POST /api/v1/internal/skill-feedback`
- `POST /api/v1/internal/candidates`
- `GET /api/v1/internal/candidates`
- `GET /api/v1/internal/candidates/{candidateId}`
- `POST /api/v1/internal/candidates/{candidateId}/promotion-decisions`
- `POST /api/v1/internal/candidates/{candidateId}/publish`
- `GET /api/v1/internal/governance-signals/skills`

additive response fields：

- skill detail / version detail 可新增：
  - `actions`
  - `environmentProfiles`
  - `evalSuites`
  - `bundle`
- search response 可新增：
  - `labels`
  - `runtimeTags`
  - `actionKinds`
  - `successRate`
  - `trustScore`

当前代码口径补充：

- public `/distribution` 返回体不暴露 `bundle.storageKey` 和 `files[].storageKey`
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/dto/SkillDistributionResponse.java`
- internal `/distribution` 返回体保留 storage 细节，仅用于 review / admin / debug
  - `/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-app/src/main/java/com/iflytek/skillhub/dto/internal/InternalSkillDistributionResponse.java`
- internal API token scope 当前已固定：
  - `skill:feedback` -> `POST /api/v1/internal/skill-feedback`
  - `skill:internal-read` -> internal distribution GET、candidate GET/list
  - `skill:candidate` -> candidate create / decision / publish
  - `skill:governance` -> governance signal GET
  - 路由策略文件：`/Users/chenge/Desktop/skills-gp- research/skillhub/server/skillhub-auth/src/main/java/com/iflytek/skillhub/auth/policy/RouteSecurityPolicyRegistry.java`

### 12.4 发布兼容策略

phase 1 必须保证：

- 只含 `SKILL.md` 的历史包仍可继续发布和下载
- 没有 `actions.yaml` 的 skill，`skill_action` 为空集合即可
- 没有 `manifest.json` / `evals/` 的 skill，不阻断发布，但在 snapshot 中记为低完整度

### 12.5 第一阶段拆任务建议

后端可以按五条并行线拆：

1. Schema / entity / repository
   - 新表、JPA entity、repository port、infra adapter
2. Publish / promotion / distribution
   - publish 扩 asset normalization
   - promotion 复制资产元数据
   - distribution descriptor API
3. Search projection
   - `latest published only`
   - projection builder
   - rebuild listener / admin job
4. Feedback / snapshot / governance signal
   - feedback ingest
   - snapshot job
   - governance signal read model
5. Candidate ingress
   - candidate 表
   - promotion decision
   - candidate publish orchestration

## 13. 最终结论

skillhub 现在不需要再变成一个 runtime 一体化系统，反而应该把已经存在的正确边界继续收紧：

- `Skill / SkillVersion / SkillFile / SkillTag / SkillLabel / SecurityAudit` 继续作为资产层主对象
- `skill_action / skill_environment_profile / skill_eval_suite` 进入版本级资产描述面
- `skill_run_feedback` 作为 append-only 信号源，`skill_score_snapshot` 作为 ranking / governance 快照层
- `skill_candidate / skill_promotion_decision` 作为 lab -> registry 的 ingress 面
- `skill_search_document` 明确只表示 latest published only 的 projection
- distribution 由 registry 提供稳定 descriptor，runtime 只消费，不拥有这层

如果 phase 1 只保留一句工程原则，那就是：

> registry 负责定义、治理、分发和解释 skill 资产；runtime 负责消费这些资产并回传信号，但绝不拥有这些资产。
