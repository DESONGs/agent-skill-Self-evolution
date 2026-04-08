# Agent Skill Platform

这个仓库现在包含两层内容：

- 一层是已经收口完成的 v0.5 核心能力：skill 检索、执行、反馈、promotion 闭环
- 一层是可部署的团队版服务：`enterprise_v2/`

如果你的目标是直接部署给团队使用，优先看：

- `enterprise_v2/README.md`
- `enterprise_v2/deploy/README.md`

## 现在这套系统可以做什么

它适合把团队里的重复工作沉淀成 skill，然后统一发布、检索、执行和回收反馈。

适用场景例如：

- 运维团队：巡检、故障分级、变更检查
- 安全团队：告警归类、证据收集、工单补全
- 数据团队：固定分析流程、日报生成、质量检查
- 研究团队：重复调研、报告生成、反馈回流

## 当前仓库状态

当前主干代码已经完成 v0.5 范围内的收口，核心链路包括：

- `find_skill -> execute_skill -> runtime -> feedback`
- `feedback -> case -> decision -> proposal/candidate -> promotion intake -> outcome`
- `script / agent / ai_decision` 三类 skill 的统一运行 contract
- projection-backed hybrid search
- bounded multi-step runtime planner

实现状态说明见：

- `docs/plan/v0.5e-implementation-status.md`

## 仓库结构

### 核心实现

- `src/`
- `integration/`
- `runtime/`
- `tests/`

这部分是 v0.5 收口后的核心代码和兼容层。

### 团队部署版

- `enterprise_v2/`

这部分是面向 8 人团队内网部署的服务版本，默认栈为：

- FastAPI API
- Postgres
- Redis + RQ
- MinIO
- Nginx

## 团队部署入口

如果你要实际拉起服务，请直接进入 `enterprise_v2/`：

```bash
cd enterprise_v2
cp .env.example .env
docker compose up --build -d
```

部署后主要接口包括：

- `GET /healthz`
- `GET /readyz`
- `POST /publish`
- `GET /skills`
- `GET /skills/projections`
- `POST /find-skill`
- `POST /execute-skill`
- `POST /feedback`
- `POST /promotions`
- `GET /internal/jobs/{job_id}`

## 已验证的真实链路

`enterprise_v2` 已经做过真实 Docker 基础设施连调，跑通过：

- `healthz / readyz`
- `publish -> skills -> projections`
- `publish -> projection job -> internal job status`
- `execute_skill`
- `feedback -> feedback job -> internal job status`

也就是说，Postgres、Redis、MinIO、API、Worker 不是停在配置状态，而是已经有实际启动和接口验证结果。

## 当前限制

- 当前更适合单团队内部部署，不是多租户版本
- `publish` 仍依赖服务端可见路径
- `skill_versions` 目前仍使用裸 `version_id` 作为主键，长期多人使用前建议升级版本键模型
- SSO、细粒度权限、审批 UI 还没有产品化完成

## 文档入口

- 总体状态：`docs/plan/v0.5e-implementation-status.md`
- 文档索引：`docs/README.md`
- 团队部署说明：`enterprise_v2/README.md`
- 团队运维说明：`enterprise_v2/deploy/README.md`
