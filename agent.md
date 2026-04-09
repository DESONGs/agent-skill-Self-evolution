# Agent Guide

这份文档给后续维护者、自动化代理和协作者使用，说明这个服务包的边界、目录和修改原则。

## 1. 目标

这个包的目标是提供一套可内网部署的团队版技能平台，支持：

- 发布 skill
- 检索 skill
- 执行 skill
- 上报 feedback
- 通过 worker 处理 projection、feedback、promotion 等异步链路

## 2. 默认技术栈

- FastAPI
- Postgres
- Redis + RQ
- MinIO
- Nginx
- Docker Compose

## 3. 关键目录

- `src/agent_skill_platform/`
  - 平台主代码
- `deploy/`
  - 部署说明和 nginx 配置
- `alembic/`
  - 数据库迁移
- `contracts/`
  - skill contract 解析与校验
- `runtime/`
  - runtime 相关实现
- `lab/`
  - lab / proposal / outcome 相关实现
- `tests_v2/`
  - 当前独立部署包的最小测试

## 4. 关键入口

- `docker-compose.yml`
- `README.md`
- `deploy/README.md`
- `src/agent_skill_platform/registry/api.py`
- `src/agent_skill_platform/services/container.py`

## 5. 对外接口

### 健康检查

- `GET /healthz`
- `GET /readyz`

### 发布和查询

- `POST /publish`
- `GET /skills`
- `GET /skills/{skill_id}`
- `GET /skills/projections`
- `GET /skills/{skill_id}/projection`
- `GET /skills/{skill_id}/install-bundle`

### 运行时

- `POST /find-skill`
- `POST /execute-skill`
- `POST /feedback`
- `POST /promotions`

### 内部运维

- `GET /internal/jobs/{job_id}`
- `GET /internal/storage/health`

## 6. 修改原则

- 文档里不要写本地绝对路径
- 对外接口路径尽量保持稳定
- `readyz` 应返回可读状态，不要把底层异常原样暴露成难以判断的错误
- `publish`、`feedback`、`promotion` 改动时，要同时检查 API、对象存储、队列、worker 四条链路
- Docker 启动链有变更时，要优先保证 `docker compose up --build -d` 仍然是标准启动方式

## 7. 发布前检查

至少确认下面几项：

```bash
docker compose up --build -d
docker compose exec -T api curl -sf http://127.0.0.1:8080/healthz
docker compose exec -T api curl -sf http://127.0.0.1:8080/readyz
python -m pytest tests_v2/test_enterprise_assets.py
```

如果改动涉及发布或执行链路，建议额外做：

- `publish -> skills -> projections`
- `execute_skill`
- `feedback -> internal/jobs`

## 8. 当前已知风险

- `skill_versions` 仍使用裸 `version_id` 作为主键
- 当前更适合单团队内部部署，不是多租户方案
- `publish.source` 仍依赖服务端可见路径
- SSO、RBAC、审批 UI 还没有产品化完成

## 9. 文档入口

- `README.md`
- `deploy/README.md`
- `docs/README.md`
- `docs/plan/v0.5e-implementation-status.md`
