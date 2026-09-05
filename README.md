# CodeFlow

AI 驱动的云原生研发协作平台 —— 微服务版（对应实施路线 Phase 1-6）。

## 架构

```
                        ┌────────────┐
                        │  Gateway   │  :8000  JWT 校验 / 限流 / 路由
                        └─────┬──────┘
          ┌───────────┬───────┼──────────┬──────────────┐
          ▼           ▼       ▼          ▼              ▼
   ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐
   │ user-svc │ │project  │ │ notif-svc│ │ ci-svc    │ │ ...      │
   │ :8001    │ │svc:8002 │ │ :8003    │ │ :8004     │ │          │
   └────┬─────┘ └────┬────┘ └────┬─────┘ └─────┬─────┘ └──────────┘
        │            │Outbox     │消费         │消费 git.push
        ▼            ▼           │             ▼ 执行 Pipeline
  codeflow_users  codeflow_projects │        codeflow_ci
  (独立数据库)    (独立数据库)       │        (独立数据库)
                \            ▼     │         /
                 ▼        Kafka codeflow.*.events
                              │        git.push/pipeline.finished
                 git.push / issue.created / pipeline.finished
```

- **gateway-service**：统一入口，JWT 验签 + Redis 限流 + httpx 反向代理
- **user-service**：注册/登录/refresh、`/internal/users` 内部查询 API（供其他服务解析用户）
- **project-service**：Project/Issue/Comment CRUD、RBAC、项目内 Issue 编号（Redis INCR）、
  Outbox Pattern（业务与事件同事务落库 → Worker 投递 Kafka）、
  GitHub 仓库注册 / Webhook 验签 / git.push 事件 / PR 同步
- **ci-service**：消费 git.push → Pipeline/Build 落库 → 异步执行器跑步骤
  （checkout/install/test/lint/build，日志实时落库，支持取消）→ pipeline.finished 事件
- **notification-service**：Consumer Group 消费事件（幂等 + 重试 + DLQ），写 notifications 表
- **codeflow-common**（libs/common）：JWT/密码、事件信封与 Topic 映射、Redis 工具、Outbox、Kafka Producer

服务间通信：
- 同步：project-service → user-service 内部 API（X-Internal-Token 鉴权 + 内存 TTL 缓存）
- 异步：所有状态变更 → Outbox → Kafka → notification-service（事件契约：payload 自带 watchers）

## 快速启动（容器化）

```powershell
copy .env.example .env      # 修改 SECRET_KEY（必须）
docker compose up -d --build
```

- Gateway/API 文档：http://localhost:8000/docs
- Kafka UI：http://localhost:8080

服务端口：gateway 8000 / user 8001 / project 8002 / notification 8003。

## 本地开发

```powershell
uv sync --all-packages
# 各库迁移
cd services/user-service; uv run --project . alembic upgrade head; cd ../..
cd services/project-service; uv run --project . alembic upgrade head; cd ../..
cd services/notification-service; uv run --project . alembic upgrade head; cd ../..
# 先启动基础设施
docker compose up -d postgres redis kafka
# 分别在 4 个终端启动服务（或 make dev-user / dev-project / ...）
uv run uvicorn user_service.main:app --port 8001 --project services/user-service
uv run uvicorn project_service.main:app --port 8002 --project services/project-service
uv run uvicorn notification_service.main:app --port 8003 --project services/notification-service
uv run uvicorn gateway_service.main:app --port 8000 --project services/gateway-service
```

本地直跑时各服务默认连 `localhost:5432` 的独立库（codeflow_users / codeflow_projects /
codeflow_notifications，见 deploy/postgres/init.sql），`KAFKA_ENABLED=true` 开启 Kafka。

## 工程化增强 / 压测（Phase 14-15）

### Phase 14：韧性能力（libs/common + 各服务）

| 能力 | 实现 | 解决的问题 |
|---|---|---|
| **Retry** | `codeflow_common.retry.async_retry`：指数退避+抖动 | user-service 瞬时抖动导致跨服务调用失败 |
| **Circuit Breaker** | `codeflow_common.breaker`：closed/open/half-open，UserClient 内部 API 调用全走熔断 | 下游宕机时上游快速失败，不堆积连接 |
| **Idempotency** | `Idempotency-Key` 头 + Redis 快照（TTL 24h），重复请求返回缓存响应；Redis 降级为直接执行 | 网络重试导致重复建项目 |
| **Audit Log** | user/project 各自库 `audit_logs` 表：注册/登录/登录失败/项目增删改/成员变更；`GET /api/v1/audit`（项目成员）/ `GET /users/me/audit` | 安全合规溯源；失败登录独立提交防回滚丢失 |
| **/ready 探针** | DB 连通性检查，K8s readinessProbe 可用 | 区分"进程活着"和"可以接流量" |
| 幂等消费/DLQ/限流/优雅停机 | 之前阶段已实现 | — |

### 压测（Phase 15, loadtest/locustfile.py）

```powershell
uv run locust -f loadtest/locustfile.py --headless -u 30 -r 5 -t 60s --host http://localhost:8000
```

实测结果（30 用户 / 60s，本地笔记本）：
- **2383 请求，0 失败**，~40 req/s；核心 CRUD P50 20-30ms / P99 270-340ms
- 压测还抓出一个真 bug：审计表 `resource_id` 传 int 在 Postgres 报错（SQLite 宽松掩盖）——**这就是压测的价值**
- 注册/登录 4-9s：bcrypt 高成本哈希在并发下的 CPU 争抢（安全权衡，可按硬件调 cost factor）
- 观察：Grafana API Overview 看板实时 QPS/P95；K8s 部署后 HPA 随 CPU 自动扩容（需 metrics-server）

## 手动配置项（.env）

| 配置 | 说明 |
|---|---|
| `SECRET_KEY` | **必须修改**，JWT 签名密钥，所有服务一致 |
| `INTERNAL_TOKEN` | 服务间内部 API 令牌 |
| `GITHUB_WEBHOOK_SECRET` | GitHub Webhook 验签密钥（与仓库 Webhook 设置一致；留空仅本地开发） |
| `GITHUB_TOKEN` | GitHub PAT，同步 Pull Request 用（Phase 6） |
| `LLM_API_KEY` | **可选**，OpenAI/DeepSeek 等 Key（Phase 13；留空用 Mock 降级） |
| `LLM_BASE_URL` / `LLM_MODEL` | OpenAI 兼容接口地址与模型名 |

## 测试 / 质量

```powershell
uv run pytest services        # 16 个用例（user 5 + project 11，SQLite 内存）
uv run ruff check services libs
uv run mypy libs/common services
```

## 可观测性 / AI（Phase 12-13）

### 可观测性（deploy/observability/）

```
各服务 /metrics (codeflow_http_requests_total, ..._duration_seconds_bucket)
  → Prometheus(:9090) → Grafana(:3000, 预置 CodeFlow API Overview 看板)
容器日志 → Loki(:3100)   OTel Traces → Jaeger(:16686, OTEL_ENABLED=true 开启)
```

- 访问 Grafana：http://localhost:3000（admin/admin），QPS/P50/P95/P99/错误率/日志已预置
- Traces：在 `.env` 加 `OTEL_ENABLED=true` 后重启服务，跨服务 trace 在 Jaeger UI 查询
- **容器日志进 Loki 需手动安装 docker 插件**（Docker Desktop 限制需手动执行一次）：
  `docker plugin install grafana/loki-docker-driver:2.9.10 --alias loki --grant-all-permissions`

### AI 服务（ai-service :8005, codeflow_ai 库）

| 接口 | 说明 |
|---|---|
| `POST /api/v1/ai/chat` | LLM 问答，`project_id` + `use_rag` 自动检索知识库上下文 |
| `POST /api/v1/ai/code-review` | diff → 结构化 JSON 审查（summary/severity/issues[]），存 ai_reviews |
| `POST /api/v1/ai/issue-analysis` | Issue 标题/描述 → 分类 + 优先级建议 |
| `POST /api/v1/ai/documents` | 文档入库：Chunk → Embedding → pgvector(`embedding_vec <=>`) |
| `POST /api/v1/ai/documents/search` | 相似度检索（pgvector 优先，无则 Python 余弦降级） |

- **未配置 `LLM_API_KEY` 时自动降级 MockLLMClient**（规则化确定性输出，本地零成本演示）
- Postgres 镜像为 `pgvector/pgvector:pg16`，启动时自动 `CREATE EXTENSION vector` + 建向量列
- AI 指标：`codeflow_ai_requests_total{endpoint}` / `codeflow_ai_request_duration_seconds`

## 端到端验证过的链路

1. 注册 → 登录（user-service）→ 网关 401 拦截未认证请求
2. 建项目 → 添加成员（project-service 经内部 API 解析用户）→ 建 Issue（Redis 编号）
3. user/project 事件经 Outbox → Kafka → notification-service 消费 → 通知写库 → 查询
4. GitHub Webhook（HMAC）→ git.push 事件 → Kafka `codeflow.git.events`
5. git.push → ci-service 消费 → Pipeline 执行（5 步骤，日志落库）→ pipeline.finished 事件
   → `GET /api/v1/pipelines/{id}/logs` 查看构建日志
6. Prometheus 抓取全部服务 /metrics；Grafana 预置 API Overview 看板（QPS/P95/P99/错误率/日志）
7. AI：知识库入库(pgvector) → 相似检索 → RAG 问答；diff → AI Code Review（结构化 JSON 入库）

## Kubernetes / Helm / CI/CD（Phase 9-11）

| 目录 | 内容 |
|---|---|
| `deploy/k8s/` | Phase 9 手写 YAML：Namespace/Secret/ConfigMap/StatefulSet/Deployment/Job/HPA/Ingress/探针 |
| `deploy/helm/codeflow/` | Phase 10 Helm chart：`helm install codeflow deploy/helm/codeflow`（服务/迁移Job/基础设施全部模板化） |
| `.github/workflows/` | Phase 11 CI/CD：test.yml（质量门禁）→ build.yml（构建+Trivy 扫描+GHCR）→ deploy.yml（Helm 自动部署） |

```bash
# Helm 一键部署（需 helm + 集群）
helm install codeflow deploy/helm/codeflow -n codeflow --create-namespace
```

## 目录

```
libs/common/            codeflow_common 共享库（security/envelope/redis/outbox/kafka/
                        metrics/tracing/retry/breaker/idempotency/audit）
services/
├── gateway-service/    gateway_service
├── user-service/       user_service（users, audit, outbox）
├── project-service/    project_service（projects, issues, comments,
│                        repositories, pull_requests, audit, outbox）
├── notification-service/ notification_service（notifications）
├── ci-service/         ci_service（pipelines, builds, outbox）
└── ai-service/         ai_service（documents+pgvector, ai_reviews, RAG）
loadtest/               Locust 压测脚本（Phase 15）
deploy/
├── docker/             Dockerfile 模板
├── helm/codeflow/      Phase 10 Helm chart
├── k8s/                Phase 9 手写 K8s 清单
├── observability/      Phase 12 Prometheus/Grafana/Loki 配置
└── postgres/init.sql   多库初始化
.github/workflows/      Phase 11 CI/CD（test/build/deploy）
scripts/start-all.ps1   重启后一键恢复本地全栈
```

## 后续路线

- Phase 12：Prometheus / Grafana / Loki / OpenTelemetry（可观测性）
- Phase 13：LLM / AI Code Review / RAG（pgvector）
- Phase 14-15：工程化增强（Outbox DLQ 补偿/审计/压测 Locust）
