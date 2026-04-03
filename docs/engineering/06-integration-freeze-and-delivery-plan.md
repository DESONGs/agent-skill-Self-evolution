# 集成层冻结与排期摘要

日期：2026-04-02  
状态：frozen-v1  
范围：只做跨层统一、裁剪、冻结、排期；不重写单层详细设计

## 0. 收口依据

本文件只基于以下文档收口，后续跨团队对齐以本文件为准：

- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/README.md`
- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/00-program-overview-and-reuse-map.md`
- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/01-environment-kernel-and-runtime.md`
- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/02-skill-package-and-actions.md`
- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/03-registry-search-governance.md`
- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/04-skill-factory-and-lab.md`
- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/05-implementation-roadmap.md`

## 1. 最终冻结的主接口

集成层只保留四条主线接口：

1. `actions.yaml` schema
2. `RuntimeInstallBundle`
3. `RunFeedbackEnvelope`
4. `PromotionSubmission`

以下对象不再作为集成层主接口冻结：

- `SKILL.md`
- `manifest.json`
- `agents/interface.yaml`
- `CandidateSkillPackage`
- `candidate.yaml`

这些对象仍然存在，但分别归 Package 或 Factory/Lab 内部合同管理，不作为跨团队主线联调入口。

### 1.1 `actions.yaml` schema

定位：skill package 内唯一执行入口声明；runtime 只能按它解析 action，不得扫描 `scripts/` 猜入口。  
主责任层：Package Contracts / Runtime  
冻结结论：

- `schema_version`
- `actions[].id`
- `actions[].kind`
- `actions[].entry`
- `actions[].runtime`
- `actions[].timeout_sec`
- `actions[].sandbox`
- `actions[].allow_network`
- `actions[].input_schema`
- `actions[].output_schema`
- `actions[].side_effects`
- `actions[].idempotency`

冻结规则：

- v1 只支持“显式声明 action -> runtime 解析 runner -> 隔离执行”。
- v1 默认只做单 action 调度，不在集成层引入复合工作流 DSL。
- `default action` 必须能被 package 明确解析；runtime 不允许猜测入口。

不进入 v1 的内容：

- 任意脚本自动发现
- prompt 拼接 shell
- 多步 action 编排 DSL
- 运行时动态修改 action 定义

裁剪依据：

- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/02-skill-package-and-actions.md`
- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/05-implementation-roadmap.md`

### 1.2 `RuntimeInstallBundle`

定位：registry -> runtime 的唯一安装与执行输入；runtime 不直接读取 registry 内部实体。  
主责任层：Registry / Runtime  
冻结字段：

- `skill_id`
- `version_id`
- `slug`
- `bundle_url`
- `bundle_sha256`
- `bundle_size`
- `manifest`
- `actions`
- `default_action_id`
- `runtime_profile`
- `labels`
- `visibility`
- `risk_level`
- `published_at`

冻结规则：

- `RuntimeInstallBundle` 必须是 execution-ready 对象，runtime 拿到后不再二次拼装 registry 数据。
- v1 冻结单一 `runtime_profile`，不冻结多 profile 选择协议。
- `actions` 为安装响应必带字段，避免 runtime 再去 bundle 内做额外 schema 推断。

不进入 v1 的内容：

- registry 内部 JPA/SQL 字段
- search projection 字段全集
- tag/label 写接口
- publish/review/scan/governance 状态机细节
- 多 registry federation

裁剪依据：

- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/00-program-overview-and-reuse-map.md`
- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/03-registry-search-governance.md`
- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/05-implementation-roadmap.md`

### 1.3 `RunFeedbackEnvelope`

定位：runtime -> registry 的唯一执行反馈信封；registry 负责 ingestion、聚合、排序和治理，不由 runtime 承担。  
主责任层：Runtime / Registry  
冻结字段：

- `run_id`
- `skill_id`
- `version_id`
- `source`
- `mode`
- `action_id`
- `task_hash`
- `environment_hash`
- `success`
- `latency_ms`
- `artifact_index`
- `error_code`
- `payload`
- `created_at`

冻结规则：

- 集成层只冻结 runtime 来源的运行反馈。
- UI/CLI 评分、举报、离线评测结果可以进入 registry，但由 registry 内部适配成统一 feedback event，不新增外部主接口。
- registry 对 feedback 只做 append-only ingestion；聚合和排序影响走异步任务。

不进入 v1 的内容：

- runtime 端 feedback 聚合逻辑
- ranking 在线学习
- 个性化推荐
- 复杂 canary 决策

裁剪依据：

- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/00-program-overview-and-reuse-map.md`
- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/03-registry-search-governance.md`
- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/05-implementation-roadmap.md`

### 1.4 `PromotionSubmission`

定位：lab -> registry 的唯一晋升提交对象；lab 提交证据，registry 决定是否发布。  
主责任层：Factory/Lab / Registry  
冻结字段：

- `candidate_id`
- `candidate_slug`
- `bundle_url`
- `bundle_sha256`
- `manifest`
- `evaluation_summary`
- `regression_report_ref`
- `governance_report_ref`
- `safety_verdict`
- `promotion_decision`
- `recommended_rollout_strategy`
- `submitted_at`

冻结规则：

- `PromotionSubmission` 是“提交审核/发布”的信封，不是直接写 `published`。
- lab 必须附带 registry-ready bundle 和最小证据摘要。
- v1 先支持 manual approval 路径；auto-promotion 只保留字段，不作为一期闭环前提。

不进入 v1 的内容：

- canary 分流协议
- rollback 自动化协议
- active/dormant 自动晋升
- candidate 自举生成 candidate

裁剪依据：

- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/00-program-overview-and-reuse-map.md`
- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/04-skill-factory-and-lab.md`
- `/Users/chenge/Desktop/skills-gp- research/docs/engineering/05-implementation-roadmap.md`

## 2. 前 4 层文档的冲突点与统一结论

| 冲突点 | 冲突来源 | 统一结论 |
|---|---|---|
| runtime 是否可以扫描 `scripts/` 或猜入口 | `02` 强调显式 action；旧 runtime 仍有隐式发现惯性 | 统一为 `actions.yaml` 唯一执行入口，任何隐式发现一律裁掉 |
| registry 给 runtime 的是数据库实体还是 install contract | `00` 提 `RuntimeInstallBundle`；`03` 强调不要暴露实体 | 统一为只暴露 `RuntimeInstallBundle`，且必须 execution-ready |
| install contract 是否只给 bundle 元数据，还是同时带 `actions` 和运行配置 | `00` 示例较丰富，`03` 示例偏最小 | 统一为 v1 直接带 `manifest + actions + default_action_id + runtime_profile`，避免 runtime 二次拼装 |
| feedback envelope 是泛化 `FeedbackEnvelope` 还是 runtime 专用 `RunFeedbackEnvelope` | `00` 更偏 runtime run；`03` 更偏 registry ingestion | 统一为跨层主接口只冻结 `RunFeedbackEnvelope`；其它来源在 registry 内部适配 |
| candidate 是否要作为主接口冻结 | `04` 内部需要 `candidate.yaml`；`05` 曾列出 candidate package envelope | 统一为 candidate 保留为 Factory/Lab 内部 spec，不进入集成层主接口清单 |
| lab 是否直接 publish | `00` 和 `04` 都提 lab -> registry 提交 | 统一为 lab 只发 `PromotionSubmission`；publish/review/versioning 仍归 registry |
| package / registry / runtime 的落地先后顺序 | `02` 的建议顺序偏 package -> runtime -> registry；`05` 偏 package -> registry -> runtime | 统一为 `actions.yaml` -> `RuntimeInstallBundle` -> runtime execution -> `RunFeedbackEnvelope`；registry install contract 必须先于 runtime 主链路完成 |
| candidate editable target 是多文件还是单 spec | `04` 明确建议 `workspace/candidate.yaml` 单一真源 | 统一为二期只冻结 `candidate.yaml` 内部 spec；多文件直接编辑暂缓 |
| promotion 是自动还是人工 | `04` 允许低风险自动晋升；`05` 后续还有 canary/rollback | 统一为二期先落 manual approval + evidence submission；auto-promotion、canary、rollback 延后 |

## 3. 最终分层边界和团队职责

| 层 | 责任 | 输入 / 输出 | 不负责 | Owner |
|---|---|---|---|---|
| Package Contracts | skill 包结构、`actions.yaml` schema、validator、bundler | 输入：skill source；输出：validated package | registry 审核、runtime 检索、promotion 决策 | Track A |
| Registry / Search / Governance | publish、review、scan、search、download、`RuntimeInstallBundle`、feedback ingestion、promotion intake | 输入：package / feedback / promotion submission；输出：install bundle、搜索与治理状态 | skill 执行、lab 实验 | Track B |
| Environment Kernel / Runtime | 检索、模式选择、bundle hydration、action resolve、隔离执行、artifact index、`RunFeedbackEnvelope` | 输入：task + install bundle；输出：run artifacts + feedback | publish/review/scan/search projection/promotion | Track C |
| Factory / Lab | candidate 生成、`candidate.yaml` 内部 spec、materialize、评测、证据收集、`PromotionSubmission` | 输入：workflow / transcript / failure；输出：candidate、evidence、promotion submission | registry 发布、生产检索和执行 | Track D |
| Integration / Migration | 跨接口 mock、contract test、兼容迁移、阶段验收、联调节奏 | 输入：四条主接口 schema；输出：E2E 验收和迁移结果 | 单层业务逻辑实现 | Track E |

阶段激活规则：

- 第一阶段只要求 Track A、B、C、E 进入主开发；Track D 只保留 schema 对齐和脚手架预研。
- 第二阶段再让 Track D 成为主路径开发，并由 Track B 接 `PromotionSubmission`。

## 4. 第一阶段必须落地的 backlog

第一阶段目标只保交付三件事：

1. 新协议 skill 包可发布
2. runtime 可从 registry 拉 bundle 并执行默认 action
3. run feedback 可回流 registry

### 4.1 必做 backlog

| 优先级 | Backlog | Owner | 验收口径 |
|---|---|---|---|
| P0 | 冻结 `actions.yaml` schema v1、validator、mock payload | Track A | schema、validator、example 三件套齐全 |
| P0 | package validator v2，校验 `SKILL.md / manifest.json / actions.yaml / agents/interface.yaml` | Track A | 新协议包能本地校验通过 |
| P0 | bundle exporter / packager 输出标准 zip | Track A | registry 可直接接收 bundle |
| P0 | registry 解析并持久化 action / runtime profile 元数据 | Track B | 新包发布后可查询到 action 元信息 |
| P0 | registry 提供 `RuntimeInstallBundle` 下载/安装响应 | Track B | runtime 能直接拿 install-ready payload |
| P0 | runtime `ActionResolver` 只按 `actions.yaml` 解析 runner | Track C | 默认 action 可被确定性执行 |
| P0 | runtime `RunContext` 落标准 artifact index 和 result summary | Track C | 每次执行都有稳定产物清单 |
| P0 | runtime 生成并上报 `RunFeedbackEnvelope` | Track C | registry 能接到标准反馈 |
| P0 | registry 建 append-only feedback ingestion API 和 event table | Track B | feedback 入库且不要求同步聚合 |
| P1 | feedback aggregate job + projection sync 最小版 | Track B | 成功率/延迟可在 read model 中查看 |
| P1 | 旧 skill 自动补 `actions.yaml` 的迁移脚本 | Track E | 至少一个旧 skill 能迁到新协议 |
| P1 | 主链路 contract test：publish -> install -> run -> feedback | Track E | CI 中可复现整条链路 |
| P2 | `PromotionSubmission` schema、validator、mock 先冻结不实现 | Track D + E | 二期可直接接入，不返工主链路 |

### 4.2 第一阶段明确不做

- candidate generation
- lab runtime
- promotion gate
- canary / rollback
- layered ranking
- 多 registry federation

## 5. 第二阶段再接入的 candidate / lab / promotion 能力

第二阶段只接入与 candidate/lab/promotion 直接相关的能力，不反向改写第一阶段主链路。

### 5.1 必接能力

- `workspace/candidate.yaml` 作为 Factory/Lab 单一真源
- workflow / transcript / failure -> candidate normalize
- candidate materialize -> `SKILL.md / manifest.json / actions.yaml / agents/interface.yaml`
- lab runtime 与固定 pack：trigger / boundary / governance / security / packaging
- 标准 artifact bundle：scorecard、regression、governance、safety
- `PromotionSubmission` 生成与 registry intake
- manual approval -> published version 闭环

### 5.2 第二阶段仍然延后

- auto-promotion 默认开启
- canary 百分比灰度
- rollback 自动化
- dormant -> active 自动晋升
- candidate 自举生成 candidate

## 6. 接口冻结顺序和里程碑顺序

### 6.1 接口冻结顺序

1. `actions.yaml` schema
2. `RuntimeInstallBundle`
3. `RunFeedbackEnvelope`
4. `PromotionSubmission`

冻结原则：

- 前三项服务第一阶段生产主链路，必须先冻结后开发。
- `PromotionSubmission` 同步冻结，但只在第二阶段落实现。
- `candidate.yaml` 不进入集成冻结顺序，只由 Track D 内部维护。

### 6.2 里程碑顺序

| 里程碑 | 目标 | 阶段出口 |
|---|---|---|
| Milestone A：Contracts Frozen | `actions.yaml`、`RuntimeInstallBundle`、`RunFeedbackEnvelope`、`PromotionSubmission` 文档、validator、mock 完成 | 可并行开工 |
| Milestone B：Package Ready | skill v2 package 可验证、可打包、可发布 | registry 主链路可接 |
| Milestone C：Install Ready | registry 返回 install-ready `RuntimeInstallBundle` | runtime 主链路可接 |
| Milestone D：Runtime Ready | runtime 可取 bundle 并执行默认 action | feedback 链路可接 |
| Milestone E：Feedback Ready | `RunFeedbackEnvelope` 入 registry 且可聚合最小指标 | 第一阶段完成 |
| Milestone F：Factory Ready | workflow/failure 可生成 candidate package | 第二阶段开始 |
| Milestone G：Lab Ready | candidate 可进入 lab 并产出完整证据 | promotion 可接 |
| Milestone H：Promotion Ready | `PromotionSubmission` 可被 registry 接收并进入人工审批发布 | 第二阶段完成 |

## 7. 给研发经理的实施摘要

### 7.1 排期建议

按 `/Users/chenge/Desktop/skills-gp- research/docs/engineering/05-implementation-roadmap.md` 的工期合并后，建议排成两个阶段：

- 第一阶段：6 到 10 周
  - 第 1 到 2 周：接口冻结、validator、mock、仓结构和 contract test 骨架
  - 第 3 到 5 周：package + registry install contract
  - 第 5 到 10 周：runtime execution + feedback ingestion
- 第二阶段：8 到 12 周
  - 第 1 到 3 周：candidate normalize + materialize
  - 第 3 到 7 周：lab runtime + artifact bundle + gates
  - 第 6 到 12 周：promotion submission + manual approval publish

### 7.2 人力建议

- Track A：1 到 2 人，第一阶段全程
- Track B：2 人，第一阶段主导，第二阶段继续承接 promotion intake
- Track C：2 人，第一阶段主导
- Track D：第一阶段 0.5 到 1 人预研，第二阶段扩到 2 人
- Track E：1 人贯穿两阶段，负责 contract test、联调和迁移

### 7.3 管理口径

- 不再把 `candidate package envelope` 列为跨团队主接口，避免第一阶段被二期能力拖慢。
- 不允许 runtime 承担 publish/review/scan/governance/search projection。
- 第一阶段验收只看“发布、安装、执行、回传”四段闭环，不看 candidate/lab。
- 第二阶段验收只看“生成、评测、提交、审批发布”四段闭环，不把 canary/rollback 绑进首批交付。

### 7.4 研发经理可直接使用的排期摘要

- 先冻四个接口，但一期只实现前三个生产主链接口，第四个只做 schema 和 mock。
- 一期团队主力投在 Track A/B/C/E，目标是跑通 `publish -> install -> run -> feedback`。
- 二期再启 Track D 主开发，目标是跑通 `ingest -> normalize -> materialize -> evaluate -> submit -> publish`。
- 所有跨团队联调都以本文件为准，不再以单层文档中的局部建议顺序为准。
