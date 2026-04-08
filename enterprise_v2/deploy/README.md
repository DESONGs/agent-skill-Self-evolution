# Deployment Guide

这份文档只讲 `enterprise_v2/` 的实际部署、启动、排障和恢复。

## 1. 组件

- `nginx`：团队访问入口
- `api`：对外 HTTP API
- `worker`：Redis/RQ 后台任务消费
- `postgres`：技能、版本、projection、job、feedback、promotion 状态库
- `redis`：任务队列
- `minio`：对象存储

## 2. 启动前准备

1. 复制环境文件：

```bash
cp .env.example .env
```

2. 按需修改：

- 数据库密码
- MinIO 账号密码
- bucket 名称
- nginx 暴露端口

3. 确认 Docker / Docker Compose 可用。

## 3. 首次启动

```bash
docker compose up --build -d
```

启动逻辑说明：

- `api` 会在启动前执行 `alembic upgrade head`
- `worker` 只负责消费队列，不再重复跑 migration
- 运行期代理变量会被 compose 显式清空，避免容器内部访问 `minio/postgres/redis` 被宿主机代理错误劫持

## 4. 启动后检查

### 容器状态

```bash
docker compose ps -a
```

### 探针

```bash
docker compose exec -T api curl -sf http://127.0.0.1:8080/healthz
docker compose exec -T api curl -sf http://127.0.0.1:8080/readyz
docker compose exec -T api curl -sf http://127.0.0.1:8080/internal/storage/health
```

### 内网入口

- 默认通过 nginx 暴露：`http://<server>:8088`

## 5. 最小 smoke test

### 5.1 拷入示例 skill

```bash
docker compose cp ./tests/fixtures/github-pr-review api:/tmp/github-pr-review
```

### 5.2 发布

```bash
docker compose exec -T api curl -s -X POST http://127.0.0.1:8080/publish \
  -H 'Content-Type: application/json' \
  -d '{"source":"/tmp/github-pr-review"}'
```

### 5.3 查询

```bash
docker compose exec -T api curl -s http://127.0.0.1:8080/skills
docker compose exec -T api curl -s http://127.0.0.1:8080/skills/projections
```

### 5.4 执行

```bash
docker compose exec -T api curl -s -X POST http://127.0.0.1:8080/execute-skill \
  -H 'Content-Type: application/json' \
  -d '{"skill_id":"github-pr-review","parameters":{"task":"review PR #42"}}'
```

### 5.5 反馈入队

```bash
docker compose exec -T api curl -s -X POST http://127.0.0.1:8080/feedback \
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

### 5.6 查看后台任务

```bash
docker compose exec -T api curl -s http://127.0.0.1:8080/internal/jobs/<job_id>
docker compose logs --no-color worker --tail 200
```

## 6. 运行期注意事项

- `publish.source` 必须是 API 服务可见路径，不是调用端本地路径
- `worker` 处理 projection、feedback、promotion 等异步任务
- scratch 目录只存临时执行内容，不是权威状态

## 7. 常见故障

### `readyz` 失败

重点检查：

- `.env` 中的 `AGENT_SKILL_PLATFORM_S3_ENDPOINT_URL`
- MinIO 用户名和密码
- 容器内是否残留宿主机代理变量

验证：

```bash
docker compose exec -T api env | rg '^(HTTP_PROXY|HTTPS_PROXY|NO_PROXY|http_proxy|https_proxy|no_proxy)='
```

### `publish` 失败

重点检查：

- skill 包结构是否完整
- `actions.yaml` 是否存在
- `SKILL.md` 名称与包根目录是否一致
- `source` 路径是否在 API 容器内可见

### worker 没消费任务

重点检查：

- Redis 是否健康
- worker 日志是否正在监听 `feedback / promotion / projection`

## 8. 备份

- Postgres：逻辑备份或卷级快照
- MinIO：bucket 备份或对象存储版本化
- Redis：AOF 已启用，可用于基础恢复
- scratch 卷：不需要备份

## 9. 升级

```bash
docker compose build api worker
docker compose up -d api worker nginx
```

如果 schema 有变更，`api` 会在启动时自动执行 migration。

## 10. 恢复

- Postgres 损坏：先恢复数据库，再恢复 MinIO 对象
- MinIO 不可用：读写路径降级失败，`readyz` 应该返回异常
- Redis 丢失：已入库但未处理的 job 可以根据 `job_runs` 重新入队
