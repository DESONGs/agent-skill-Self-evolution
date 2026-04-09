# Agent Skill Platform Enterprise V2

这是一个面向小团队内部部署的技能平台服务包，适合把重复工作沉淀成 skill，然后统一发布、检索、执行和回收反馈。

适用场景例如：

- 运维团队：巡检、故障分级、变更检查
- 安全团队：告警归类、工单补全、证据收集
- 数据团队：固定分析流程、日报生成、质量检查
- 研究团队：重复调研、报告生成、反馈回流

## 默认架构

- `api`：HTTP API 服务
- `worker`：异步任务消费
- `postgres`：权威状态库
- `redis`：任务队列
- `minio`：对象存储
- `nginx`：内网入口

## 适用方式

推荐通过 HTTP API 使用：

- 内部前端
- 内部机器人
- Python/CLI 自动化脚本
- CI/CD 发布流程

MCP 更适合做上层接入适配，不建议直接当成底层主入口。

## 快速启动

1. 复制环境文件：

```bash
cp .env.example .env
```

2. 启动整套服务：

```bash
docker compose up --build -d
```

3. 检查容器状态：

```bash
docker compose ps -a
```

4. 检查探针：

```bash
docker compose exec -T api curl -sf http://127.0.0.1:8080/healthz
docker compose exec -T api curl -sf http://127.0.0.1:8080/readyz
```

5. 通过 nginx 暴露的内网端口访问：

- 默认入口：`http://<server>:8088`

## 部署结构

```text
team client / bot / ui
        |
      nginx
        |
       api  --------> postgres
        |              |
        |              +--> skills / versions / projections / jobs / feedback / promotion
        |
        +-----------> redis -----> worker
        |
        +-----------> minio -----> packages / bundles / feedback / promotion / artifacts
```

## 核心接口

### 健康检查

- `GET /healthz`
- `GET /readyz`

### 技能发布与查询

- `POST /publish`
- `GET /skills`
- `GET /skills/{skill_id}`
- `GET /skills/projections`
- `GET /skills/{skill_id}/projection`
- `GET /skills/{skill_id}/install-bundle`

### 在线检索与执行

- `POST /find-skill`
- `POST /execute-skill`

### 反馈与后台任务

- `POST /feedback`
- `POST /promotions`
- `GET /internal/jobs/{job_id}`
- `GET /internal/storage/health`

## 请求示例

### 发布一个 skill

```bash
curl -X POST http://<server>:8088/publish \
  -H 'Content-Type: application/json' \
  -d '{"source":"/path/to/skill-package"}'
```

注意：

- `source` 是 API 服务所在环境可见的路径
- 如果通过 Docker 部署，路径必须存在于 `api` 容器里
- 做 smoke test 时可以先用 `docker compose cp` 把示例 skill 拷进容器

### 查找 skill

```bash
curl -X POST http://<server>:8088/find-skill \
  -H 'Content-Type: application/json' \
  -d '{
    "query":"github review",
    "limit":5,
    "filters":{"skill_type":"script"}
  }'
```

### 执行 skill

```bash
curl -X POST http://<server>:8088/execute-skill \
  -H 'Content-Type: application/json' \
  -d '{
    "skill_id":"github-pr-review",
    "parameters":{"task":"review PR #42"}
  }'
```

### 上报反馈

```bash
curl -X POST http://<server>:8088/feedback \
  -H 'Content-Type: application/json' \
  -d '{
    "run_id":"run-001",
    "mode":"execute",
    "skill_id":"github-pr-review",
    "version_id":"1.0.0",
    "action_id":"run",
    "success":true,
    "latency_ms":123,
    "token_usage":{},
    "artifact_count":0,
    "error_code":null,
    "layer_source":"active",
    "feedback_source":"RUNTIME",
    "feedback_type":"EXECUTION",
    "created_at":"2026-04-09T01:19:30Z",
    "metadata":{"note":"smoke"}
  }'
```

## 已验证链路

当前版本已经做过真实 Docker 基础设施连调，跑通过：

- `healthz / readyz`
- `publish -> skills -> projections`
- `publish -> projection job -> internal job status`
- `execute_skill`
- `feedback -> feedback job -> internal job status`

这意味着 Postgres、Redis、MinIO、API、Worker 已经有实际启动和接口验证结果。

## 已知限制

- 当前更适合单团队内部部署，不是多租户版本
- `publish` 依赖服务端可见路径，暂时不是浏览器上传 zip 模式
- `skill_versions` 仍使用裸 `version_id` 作为主键，多团队长期使用前建议升级版本键模型
- 细粒度权限、SSO、审批 UI 还没有做成完整产品能力

## 运维常用命令

```bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f postgres
docker compose logs -f redis
docker compose logs -f minio
docker compose down
```

## 文档入口

- 部署与恢复：`deploy/README.md`
- 当前状态：`docs/plan/v0.5e-implementation-status.md`
- 文档索引：`docs/README.md`
- 维护说明：`agent.md`
