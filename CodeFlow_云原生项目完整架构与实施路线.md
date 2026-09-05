# CodeFlow —— AI 驱动的云原生研发协作平台

> 从零到完整实现的 Python 云原生学习项目架构与开发路线  
> 目标：通过一个真实可落地的项目，系统学习 Python 后端、异步编程、微服务、Kafka、Redis、PostgreSQL、Docker、Kubernetes、Helm、CI/CD、可观测性、AI/RAG 等主流技术。

---

## 1. 项目定位

### 1.1 项目简介

CodeFlow 是一个面向软件研发团队的云原生研发协作平台，融合：

- 项目管理
- Issue / Bug / Task
- Kanban 看板
- Git 仓库集成
- Pull Request 管理
- CI/CD Pipeline
- Docker 镜像构建
- Kubernetes 部署
- AI Code Review
- AI Issue 分析
- AI 项目助手
- RAG 企业知识库
- Metrics / Logs / Traces 可观测性

核心设计思想：

> 不为了学习技术而堆技术，而是让每一种技术都解决一个真实问题。

---

# 2. 学习目标

完成项目后，希望能够真正理解并实践：

### Python

- Python 3.12+
- asyncio
- typing
- dataclass / Pydantic
- FastAPI
- SQLAlchemy 2
- pytest
- Ruff
- mypy
- 异步数据库访问
- WebSocket

### 后端

- REST API
- JWT
- OAuth2
- RBAC
- Repository / Service 分层
- 数据库事务
- 缓存
- 分布式锁
- Webhook
- 幂等
- 分页
- API 版本管理

### 微服务

- 服务拆分
- 服务间通信
- Event-driven Architecture
- Kafka
- Consumer Group
- Event Schema
- 重试
- Dead Letter Queue
- Outbox Pattern

### 云原生

- Docker
- Kubernetes
- Helm
- ConfigMap
- Secret
- Deployment
- Service
- Ingress
- HPA
- Job
- CronJob
- PVC
- Readiness / Liveness Probe

### DevOps

- GitHub Actions
- 自动测试
- Docker Build
- 镜像扫描
- 镜像发布
- Kubernetes 自动部署

### Observability

- Prometheus
- Grafana
- Loki
- OpenTelemetry
- Metrics
- Logs
- Traces

### AI

- LLM API
- Prompt Engineering
- Embedding
- Vector Search
- pgvector
- RAG
- AI Code Review
- AI Issue Generator
- AI Project Assistant

---

# 3. 总体架构

```text
                         ┌──────────────────────┐
                         │      Browser         │
                         │   React / Vue        │
                         └──────────┬───────────┘
                                    │
                              HTTPS / WebSocket
                                    │
                         ┌──────────▼───────────┐
                         │    Ingress / Gateway │
                         └──────────┬───────────┘
                                    │
               ┌────────────────────┼────────────────────┐
               │                    │                    │
        ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
        │ User Service│     │Project Svc  │     │ Task Service │
        └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
               │                   │                    │
               └───────────────────┼────────────────────┘
                                   │
                              PostgreSQL
                                   │
                           ┌───────┴────────┐
                           │                │
                         Redis           pgvector
                           │                │
                           └───────┬────────┘
                                   │
                                Kafka
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
 ┌──────▼──────┐           ┌──────▼──────┐            ┌──────▼──────┐
 │ CI Service  │           │ AI Service  │            │Notification │
 └──────┬──────┘           └──────┬──────┘            └─────────────┘
        │                          │
   Docker/K8s                 LLM / RAG
        │                          │
        └──────────────┬───────────┘
                       │
                 Observability
                       │
          ┌────────────┼────────────┐
          │            │            │
     Prometheus      Loki    OpenTelemetry
          │            │            │
          └────────────┴────────────┘
                       │
                    Grafana
```

---

# 4. 推荐技术栈

| 层次 | 技术 |
|---|---|
| 主语言 | Python 3.12+ |
| API | FastAPI |
| Schema | Pydantic v2 |
| ORM | SQLAlchemy 2 |
| Migration | Alembic |
| Database | PostgreSQL |
| Vector | pgvector |
| Cache | Redis |
| MQ | Kafka |
| Frontend | React + TypeScript |
| API Docs | OpenAPI |
| Container | Docker |
| Orchestration | Kubernetes |
| Package | Helm |
| CI/CD | GitHub Actions |
| Metrics | Prometheus |
| Dashboard | Grafana |
| Logs | Loki |
| Trace | OpenTelemetry |
| Testing | pytest |
| Lint | Ruff |
| Type Check | mypy |
| Security Scan | Trivy |
| AI | LLM API |
| RAG | pgvector + Embedding |

---

# 5. 为什么选择 Python

Python 负责：

1. REST API
2. 异步任务
3. Kafka Consumer
4. AI / RAG
5. 数据处理
6. CI/CD 编排
7. WebSocket

Python 最大优势是：

```text
后端工程
    +
AI
    +
数据处理
```

可以使用同一门语言完成。

不建议为了“显得企业级”强行混入 Java。

---

# 6. 微服务拆分

第一版建议控制在 5 个核心服务。

```text
services/

├── gateway-service
├── user-service
├── project-service
├── ci-service
├── ai-service
└── notification-service
```

### 6.1 gateway-service

职责：

- API 统一入口
- JWT 校验
- 路由
- Rate Limit
- WebSocket

### 6.2 user-service

职责：

- 用户
- 登录
- Token
- Organization
- Role
- Permission

### 6.3 project-service

职责：

- Project
- Issue
- Task
- Comment
- Repository
- Pull Request
- Kanban

### 6.4 ci-service

职责：

- Pipeline
- Build
- Docker Build
- Test
- Deploy
- Kubernetes Job

### 6.5 ai-service

职责：

- AI Code Review
- AI Issue Generator
- RAG
- Embedding
- AI Project Assistant

### 6.6 notification-service

职责：

- Email
- WebSocket
- 系统通知
- Pipeline 状态通知

---

# 7. 推荐的数据架构

## 7.1 PostgreSQL

建议先采用单 PostgreSQL 集群。

学习阶段可以：

```text
codeflow
├── users
├── projects
├── issues
├── repositories
├── pipelines
├── deployments
├── ai_reviews
└── notifications
```

生产化演进时，再根据服务边界拆数据库。

---

# 8. 核心数据库表

## users

```text
id
username
email
password_hash
avatar
status
created_at
updated_at
```

## organizations

```text
id
name
owner_id
created_at
```

## projects

```text
id
organization_id
name
description
visibility
created_by
created_at
updated_at
```

## project_members

```text
project_id
user_id
role
created_at
```

## issues

```text
id
project_id
title
description
type
priority
status
assignee_id
creator_id
created_at
updated_at
```

## comments

```text
id
issue_id
user_id
content
created_at
```

## repositories

```text
id
project_id
provider
external_id
url
default_branch
created_at
```

## pull_requests

```text
id
repository_id
external_id
title
description
author_id
status
source_branch
target_branch
created_at
updated_at
```

## pipelines

```text
id
project_id
commit_sha
branch
status
trigger_type
started_at
finished_at
```

## builds

```text
id
pipeline_id
status
logs
image
started_at
finished_at
```

## deployments

```text
id
project_id
environment
image
version
status
deployed_at
```

## ai_reviews

```text
id
pull_request_id
summary
severity
result
created_at
```

## documents

```text
id
project_id
name
content
embedding
created_at
```

---

# 9. Redis 设计

Redis 不仅用于缓存。

## Cache

```text
user:{user_id}
project:{project_id}
issue:{issue_id}
project:{project_id}:members
```

设置 TTL。

## Rate Limit

```text
rate_limit:{user_id}:{minute}
```

## Distributed Lock

```text
lock:pipeline:{pipeline_id}
```

防止同一 Pipeline 重复执行。

## WebSocket 状态

```text
pipeline:{pipeline_id}:status
```

---

# 10. Kafka 设计

建议 Topic：

```text
codeflow.user.events
codeflow.project.events
codeflow.issue.events
codeflow.git.events
codeflow.pipeline.events
codeflow.deployment.events
codeflow.ai.events
codeflow.notification.events
```

例如 Git Push：

```json
{
  "event_id": "uuid",
  "event_type": "git.push",
  "project_id": 100,
  "repository_id": 20,
  "branch": "main",
  "commit_sha": "abc123",
  "timestamp": "2026-01-01T10:00:00Z"
}
```

消费者：

```text
git.push
   │
   ├── CI Service
   ├── AI Service
   └── Notification Service
```

---

# 11. Kafka 必须学习的工程能力

不要只会 Producer / Consumer。

需要逐步实现：

### Consumer Group

```text
ci-worker-1
ci-worker-2
ci-worker-3
```

### Retry

```text
Kafka
 ↓
Consumer
 ↓
Failure
 ↓
Retry
 ↓
Failure
 ↓
DLQ
```

### Dead Letter Queue

```text
codeflow.pipeline.events.DLQ
```

### Idempotency

通过：

```text
event_id
```

保证同一个事件不会重复执行。

---

# 12. Outbox Pattern

这是非常值得写到简历里的内容。

传统方式：

```text
DB Transaction
      +
Kafka Send
```

可能出现：

```text
DB 成功
Kafka 失败
```

导致数据不一致。

改成：

```text
Application
    │
    ├── Business Table
    │
    └── Outbox Table
             │
             ▼
       Outbox Worker
             │
             ▼
           Kafka
```

这样可以学习：

- 最终一致性
- 事务
- 消息可靠投递

---

# 13. FastAPI 项目结构

每个服务建议统一结构：

```text
project-service/

├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── deps.py
│   │   └── routes/
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── logging.py
│   │
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── repositories/
│   ├── events/
│   └── db/
│
├── tests/
├── alembic/
├── Dockerfile
├── pyproject.toml
└── README.md
```

推荐分层：

```text
Router
  ↓
Service
  ↓
Repository
  ↓
Database
```

不要：

```text
Router
 ↓
SQLAlchemy
```

把所有逻辑塞到 API 中。

---

# 14. API 设计

## 用户

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
GET  /api/v1/users/me
```

## Project

```text
POST   /api/v1/projects
GET    /api/v1/projects
GET    /api/v1/projects/{id}
PATCH  /api/v1/projects/{id}
DELETE /api/v1/projects/{id}
```

## Issue

```text
POST   /api/v1/projects/{id}/issues
GET    /api/v1/projects/{id}/issues
GET    /api/v1/issues/{id}
PATCH  /api/v1/issues/{id}
DELETE /api/v1/issues/{id}
```

## Pipeline

```text
POST /api/v1/projects/{id}/pipelines
GET  /api/v1/pipelines/{id}
POST /api/v1/pipelines/{id}/cancel
GET  /api/v1/pipelines/{id}/logs
```

## AI

```text
POST /api/v1/ai/code-review
POST /api/v1/ai/issue-analysis
POST /api/v1/ai/chat
POST /api/v1/ai/documents
```

---

# 15. Git Webhook

GitHub / GitLab：

```text
Git Push
    ↓
Webhook
    ↓
Gateway
    ↓
Validate Signature
    ↓
Kafka
```

一定要验证：

```text
Webhook Signature
```

避免任何人伪造请求。

---

# 16. CI/CD 架构

完整 Pipeline：

```text
Developer
    │
    │ git push
    ▼
GitHub
    │
    │ Webhook
    ▼
CodeFlow
    │
    ▼
Kafka
    │
    ▼
CI Service
    │
    ├── Checkout
    ├── Install
    ├── Test
    ├── Lint
    ├── Security Scan
    ├── Docker Build
    ├── Docker Push
    └── Kubernetes Deploy
```

---

# 17. CI Worker

不要直接在 FastAPI Web 进程里执行：

```bash
docker build
pytest
kubectl apply
```

应该：

```text
API
 ↓
Kafka
 ↓
CI Worker
 ↓
Kubernetes Job
```

每次构建创建一个独立 Job：

```text
pipeline-job-182
```

Job 完成后自动删除。

---

# 18. Kubernetes 架构

```text
Kubernetes Cluster

namespace: codeflow

├── gateway
├── user-service
├── project-service
├── ci-service
├── ai-service
├── notification-service
│
├── postgresql
├── redis
├── kafka
│
├── prometheus
├── grafana
└── loki
```

---

# 19. Kubernetes 核心资源

每个服务：

```text
Deployment
Service
ConfigMap
Secret
HPA
```

例如：

```text
project-service Deployment
       │
       ├── Pod
       ├── Pod
       └── Pod
```

Service：

```text
project-service:8000
```

HPA：

```text
CPU > 70%
    ↓
2 replicas
    ↓
4 replicas
    ↓
8 replicas
```

---

# 20. Helm

目录：

```text
helm/

└── codeflow/
    ├── Chart.yaml
    ├── values.yaml
    └── templates/
        ├── deployment.yaml
        ├── service.yaml
        ├── ingress.yaml
        ├── configmap.yaml
        ├── secret.yaml
        └── hpa.yaml
```

环境：

```text
values-dev.yaml
values-test.yaml
values-prod.yaml
```

---

# 21. Docker

每个 Python 服务独立 Dockerfile。

建议使用：

```text
multi-stage build
non-root user
minimal base image
healthcheck
```

示意：

```text
Builder Image
     ↓
Install Dependencies
     ↓
Runtime Image
     ↓
Run FastAPI
```

不要使用 root 用户运行应用。

---

# 22. Docker Compose

开发环境先用 Compose：

```text
docker-compose.yml

├── postgres
├── redis
├── kafka
├── prometheus
├── grafana
├── loki
├── gateway
├── user-service
├── project-service
├── ci-service
└── ai-service
```

目标：

```bash
docker compose up -d
```

即可启动整个开发环境。

---

# 23. CI/CD

GitHub Actions：

```text
.github/workflows/

├── test.yml
├── build.yml
├── security.yml
└── deploy.yml
```

Pipeline：

```text
git push
   ↓
pytest
   ↓
ruff
   ↓
mypy
   ↓
Trivy
   ↓
Docker Build
   ↓
Docker Push
   ↓
Kubernetes Deploy
```

---

# 24. 测试策略

## Unit Test

测试：

```text
Service
Repository
Utils
Business Rules
```

## API Test

使用：

```text
pytest
httpx
```

测试：

```text
POST /projects
GET /projects
PATCH /projects/{id}
```

## Integration Test

测试：

```text
FastAPI
+
PostgreSQL
+
Redis
+
Kafka
```

最终：

```text
Unit Test
   +
Integration Test
   +
API Test
```

---

# 25. 可观测性

## Metrics

Prometheus 收集：

```text
http_requests_total
http_request_duration_seconds
http_errors_total
kafka_consumer_lag
pipeline_duration_seconds
ai_request_total
ai_request_duration_seconds
```

---

# 26. Grafana Dashboard

至少制作：

### API Dashboard

```text
QPS
P50
P95
P99
Error Rate
```

### Kubernetes Dashboard

```text
CPU
Memory
Pod Count
Restart Count
```

### Kafka Dashboard

```text
Messages
Consumer Lag
Throughput
```

### CI Dashboard

```text
Build Success Rate
Average Build Time
Failed Builds
```

### AI Dashboard

```text
Request Count
Latency
Token Usage
Failure Rate
```

---

# 27. 日志

应用统一输出 JSON：

```json
{
  "timestamp": "...",
  "level": "INFO",
  "service": "project-service",
  "trace_id": "...",
  "user_id": "...",
  "message": "project created"
}
```

Loki 收集。

Grafana 查询：

```text
{service="project-service"}
```

---

# 28. Distributed Tracing

使用 OpenTelemetry。

一次请求：

```text
Gateway
   │
   ▼
Project Service
   │
   ├── Redis
   │
   └── PostgreSQL
```

Trace：

```text
Request
 ├── Gateway 5ms
 ├── Project Service 35ms
 ├── Redis 2ms
 └── PostgreSQL 20ms
```

可以定位：

> 为什么 API 慢？

---

# 29. AI 架构

AI Service：

```text
                 AI Service
                     │
          ┌──────────┼──────────┐
          │          │          │
       Chat      Code Review   RAG
          │          │          │
          └──────────┼──────────┘
                     │
                    LLM
                     │
                Embedding
                     │
                  pgvector
```

---

# 30. AI Code Review

流程：

```text
Pull Request
    ↓
获取 Diff
    ↓
代码预处理
    ↓
Prompt
    ↓
LLM
    ↓
结构化 JSON
    ↓
ai_reviews
    ↓
PR 页面
```

输出：

```json
{
  "summary": "存在潜在性能问题",
  "issues": [
    {
      "severity": "high",
      "file": "user.py",
      "line": 120,
      "message": "可能存在 N+1 查询",
      "suggestion": "使用批量查询"
    }
  ]
}
```

---

# 31. RAG

企业文档：

```text
docs/
├── architecture.md
├── coding-style.md
├── api.md
└── deployment.md
```

流程：

```text
Document
   ↓
Chunk
   ↓
Embedding
   ↓
pgvector
   ↓
Similarity Search
   ↓
Context
   ↓
LLM
```

---

# 32. AI Project Assistant

用户：

> 为什么这个服务最近经常重启？

AI 可以结合：

```text
Kubernetes Metrics
+
Logs
+
Trace
+
项目文档
+
最近部署记录
```

形成：

```text
问题
 ↓
数据检索
 ↓
RAG
 ↓
LLM
 ↓
根因分析
```

这是比普通 ChatGPT 对话更有项目价值的 AI 场景。

---

# 33. 安全设计

必须学习：

### Authentication

```text
JWT
Access Token
Refresh Token
```

### Authorization

```text
RBAC
```

### Secret

不要：

```text
DATABASE_PASSWORD=123456
```

提交到 Git。

使用：

```text
Kubernetes Secret
```

### Webhook

验证：

```text
HMAC Signature
```

### API

实现：

```text
Rate Limit
Input Validation
CORS
Security Headers
```

---

# 34. 项目目录

推荐最终 Monorepo：

```text
codeflow/

├── services/
│   ├── gateway-service/
│   ├── user-service/
│   ├── project-service/
│   ├── ci-service/
│   ├── ai-service/
│   └── notification-service/
│
├── frontend/
│
├── libs/
│   ├── event-schema/
│   ├── logging/
│   ├── tracing/
│   └── common/
│
├── deploy/
│   ├── docker/
│   ├── compose/
│   ├── k8s/
│   └── helm/
│
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── development/
│   └── operations/
│
├── .github/
│   └── workflows/
│
├── Makefile
├── README.md
└── LICENSE
```

---

# 35. 本地开发环境

建议：

```text
Windows
  │
  ├── WSL2
  │
  ├── Docker Desktop
  │
  └── VS Code / PyCharm
```

Python 环境：

```text
uv
```

建议统一：

```bash
uv sync
```

---

# 36. Makefile

统一开发命令：

```bash
make install
make dev
make test
make lint
make format
make migrate
make docker-build
make docker-up
make k8s-dev
make logs
```

目标：

> 不让开发者记住几十条命令。

---

# 37. 从零开始的开发路线

## Phase 0：准备环境

学习：

```text
Git
Linux
Docker
Python
PostgreSQL
Redis
```

完成：

```bash
python --version
docker --version
kubectl version
git --version
```

---

# 38. Phase 1：Python 基础项目

只做：

```text
FastAPI
PostgreSQL
SQLAlchemy
Alembic
pytest
```

完成：

```text
用户注册
用户登录
Project CRUD
Issue CRUD
Comment
```

暂时不要微服务。

---

# 39. Phase 2：认证与权限

加入：

```text
JWT
OAuth2
RBAC
```

完成：

```text
Admin
Developer
Viewer
```

实现权限：

```text
Admin
 ├── Create
 ├── Update
 ├── Delete
 └── Manage Members

Developer
 ├── Create Issue
 ├── Comment
 └── Run Pipeline

Viewer
 └── Read
```

---

# 40. Phase 3：Redis

加入：

```text
Cache
Rate Limit
Distributed Lock
```

学习：

```text
Cache Aside
TTL
Lock
Atomic Operation
```

---

# 41. Phase 4：Kafka

首先只实现：

```text
Project Created
Project Updated
Issue Created
Issue Updated
```

然后增加：

```text
Git Push
Pull Request
Pipeline
Deployment
```

---

# 42. Phase 5：微服务

把单体拆分：

```text
Monolith
   ↓
User Service
Project Service
CI Service
AI Service
Notification Service
```

重点学习：

```text
Service Boundary
API Contract
Event Contract
Failure Handling
```

---

# 43. Phase 6：Git 集成

接入：

```text
GitHub
```

实现：

```text
Repository
Webhook
Commit
Pull Request
```

事件进入 Kafka。

---

# 44. Phase 7：CI

实现：

```text
Push
 ↓
Webhook
 ↓
Kafka
 ↓
CI Worker
 ↓
Test
 ↓
Docker Build
```

先不要 Kubernetes。

---

# 45. Phase 8：Docker

所有服务容器化：

```text
gateway
user
project
ci
ai
notification
```

完成：

```bash
docker compose up
```

一键运行。

---

# 46. Phase 9：Kubernetes

学习顺序：

```text
Pod
 ↓
Deployment
 ↓
Service
 ↓
ConfigMap
 ↓
Secret
 ↓
Ingress
 ↓
PVC
 ↓
Job
 ↓
HPA
```

不要一开始直接 Helm。

先手写 YAML，理解 Kubernetes。

---

# 47. Phase 10：Helm

把：

```text
K8s YAML
```

模板化。

实现：

```bash
helm install codeflow ./helm/codeflow
```

---

# 48. Phase 11：CI/CD

实现：

```text
Git Push
 ↓
GitHub Actions
 ↓
Test
 ↓
Build Image
 ↓
Trivy
 ↓
Push Registry
 ↓
Helm Upgrade
 ↓
Kubernetes
```

---

# 49. Phase 12：Observability

加入：

```text
Prometheus
Grafana
Loki
OpenTelemetry
```

先 Metrics。

然后 Logs。

最后 Traces。

---

# 50. Phase 13：AI

依次实现：

```text
LLM Chat
 ↓
AI Issue Generator
 ↓
AI Code Review
 ↓
Embedding
 ↓
pgvector
 ↓
RAG
 ↓
AI Project Assistant
```

---

# 51. Phase 14：工程化增强

最终增加：

```text
Retry
Timeout
Circuit Breaker
Idempotency
Outbox
DLQ
Rate Limit
Audit Log
Health Check
Graceful Shutdown
```

---

# 52. Phase 15：压力测试

工具：

```text
Locust
```

测试：

```text
100 users
500 users
1000 users
```

观察：

```text
QPS
P95
P99
CPU
Memory
DB
Redis
Kafka
```

然后使用 HPA：

```text
CPU > 70%
 ↓
Scale Out
```

验证 Kubernetes 自动扩容。

---

# 53. 一个完整业务链路

最终做一次完整演示：

```text
Developer
    │
    │ git push
    ▼
GitHub
    │
    │ webhook
    ▼
Gateway
    │
    ▼
Kafka
    │
    ├───────────────┐
    ▼               ▼
CI Service       AI Service
    │               │
    ▼               ▼
Test             Code Review
    │               │
    ▼               ▼
Docker Build      AI Result
    │
    ▼
Registry
    │
    ▼
Kubernetes
    │
    ▼
Deployment
    │
    ▼
Prometheus
    │
    ▼
Grafana
```

这个链路可以作为整个项目最重要的 Demo。

---

# 54. 简历项目描述

项目名称：

> CodeFlow —— AI 驱动的云原生研发协作平台

项目描述：

> 基于 Python/FastAPI 构建的事件驱动型云原生研发协作平台，提供项目管理、Git 集成、CI/CD、Kubernetes 部署及 AI 代码审查能力。

技术栈：

> Python、FastAPI、PostgreSQL、Redis、Kafka、Docker、Kubernetes、Helm、GitHub Actions、Prometheus、Grafana、Loki、OpenTelemetry、RAG、pgvector、LLM。

项目亮点：

1. 基于 FastAPI + asyncio 构建异步微服务，并采用 SQLAlchemy 2 + PostgreSQL 实现核心业务数据管理。
2. 基于 Kafka 构建事件驱动架构，实现 Git、CI、AI、通知服务之间的异步解耦，并实现 Consumer Group、Retry、DLQ、幂等及 Outbox Pattern。
3. 使用 Redis 实现热点数据缓存、Rate Limit 及分布式锁，降低数据库访问压力。
4. 基于 Docker + Kubernetes + Helm 完成微服务容器化及集群部署，并通过 HPA 实现服务自动扩缩容。
5. 使用 GitHub Actions 建立 CI/CD 流程，实现自动测试、Docker 镜像构建、安全扫描及 Kubernetes 自动部署。
6. 基于 Prometheus、Grafana、Loki、OpenTelemetry 构建 Metrics、Logs、Traces 一体化可观测体系。
7. 基于 LLM、Embedding、pgvector、RAG 实现 AI Code Review、AI Issue 分析及项目知识库问答。

---

# 55. 面试重点

项目完成后，至少要能回答：

### Python

- asyncio 和多线程有什么区别？
- FastAPI 为什么适合异步 API？
- Pydantic 做什么？
- SQLAlchemy Session 怎么管理？

### Redis

- Cache Aside 是什么？
- Redis 分布式锁有什么坑？
- 缓存穿透、击穿、雪崩如何解决？

### Kafka

- Kafka 为什么吞吐量高？
- Consumer Group 是什么？
- 消息重复消费怎么办？
- 如何保证消息不丢？
- DLQ 怎么设计？
- Outbox Pattern 为什么需要？

### Kubernetes

- Pod / Deployment / Service 的区别？
- Ingress 做什么？
- ConfigMap 和 Secret？
- HPA 怎么工作？
- Readiness / Liveness？
- Pod 为什么会 CrashLoopBackOff？

### Docker

- Image 和 Container？
- Multi-stage Build？
- 为什么不能 root 运行？

### CI/CD

- Pipeline 怎么设计？
- 如何实现自动回滚？
- 镜像怎么版本管理？

### Observability

- Metrics / Logs / Traces 的区别？
- P95 / P99？
- Trace ID 如何贯穿微服务？

### AI

- RAG 为什么需要？
- Chunk 怎么切？
- Embedding 是什么？
- Vector Search 怎么工作？
- 如何降低 LLM 幻觉？
- AI Code Review 如何保证输出结构稳定？

---

# 56. 不建议一开始做的东西

不要一开始加入：

```text
Service Mesh
Istio
ArgoCD
Terraform
Spark
Flink
ELK
Prometheus Operator
复杂 Agent
多数据库
多云
```

原因：

> 这些技术不是不能学，而是会让项目复杂度快速失控。

等核心系统稳定之后，再选 1~2 个扩展。

---

# 57. 后期进阶方向

如果第一版完成，可以继续：

## GitOps

```text
GitHub
 ↓
Argo CD
 ↓
Kubernetes
```

## Infrastructure as Code

```text
Terraform
 ↓
Cloud
```

## Service Mesh

```text
Istio
```

## Event Streaming

```text
Kafka
 ↓
Flink
```

## AI Agent

```text
AI Agent
 ↓
Git
 ↓
Issue
 ↓
CI
 ↓
K8s
```

但是这些属于 V2 / V3。

---

# 58. 最终版本路线

```text
V0.1
│
├── FastAPI
├── PostgreSQL
└── CRUD

V0.2
│
├── JWT
├── RBAC
└── Redis

V0.3
│
├── Kafka
├── Event
└── Webhook

V0.4
│
├── Microservices
└── CI

V0.5
│
└── Docker

V0.6
│
├── Kubernetes
└── Helm

V0.7
│
└── CI/CD

V0.8
│
├── Prometheus
├── Grafana
├── Loki
└── OpenTelemetry

V0.9
│
├── LLM
├── AI Review
└── RAG

V1.0
│
├── Production-like Architecture
├── Load Test
├── Security
├── Observability
└── Documentation
```

---

# 59. 最重要的开发原则

### 原则 1

> 先单体，后微服务。

### 原则 2

> 先理解 Kubernetes YAML，再学习 Helm。

### 原则 3

> 先实现 Kafka 基础消息，再学习 Outbox / DLQ。

### 原则 4

> AI 最后加入，而不是项目第一天就调用 LLM。

### 原则 5

> 每加入一个技术，都必须解决一个真实问题。

### 原则 6

> 所有核心代码自己实现，不要完全依赖 AI 生成。

### 原则 7

> 每完成一个阶段，都写 README、架构图和技术总结。

---

# 60. 最终项目目标

最终 CodeFlow 应该能够做到：

```text
                 CodeFlow
                    │
       ┌────────────┼────────────┐
       │            │            │
    Project        Git          AI
       │            │            │
     Issue        PR          RAG
       │            │            │
     Task        Webhook      LLM
       │            │            │
       └────────────┼────────────┘
                    │
                  Kafka
                    │
                   CI
                    │
                 Docker
                    │
               Kubernetes
                    │
             ┌──────┼──────┐
             │      │      │
          Metrics  Logs  Traces
             │      │      │
             └──────┼──────┘
                    │
                  Grafana
```

完成这个项目后，你不应该只是：

> “会 Python / FastAPI / Docker / Kubernetes。”

而应该能够真正解释：

> **为什么这么设计、服务为什么这么拆、Kafka 为什么放这里、Redis 解决什么问题、Kubernetes 为什么需要 HPA、消息重复怎么办、服务故障怎么办、如何监控、如何部署、AI 为什么使用 RAG，以及整个系统出现问题时如何定位。**

这才是这个项目作为简历项目的真正价值。

---

# 61. 建议的最终学习顺序

```text
Python
  ↓
FastAPI
  ↓
PostgreSQL
  ↓
SQLAlchemy
  ↓
Redis
  ↓
Kafka
  ↓
Microservices
  ↓
Docker
  ↓
Kubernetes
  ↓
Helm
  ↓
GitHub Actions
  ↓
Prometheus / Grafana
  ↓
Loki / OpenTelemetry
  ↓
LLM
  ↓
RAG / pgvector
  ↓
压力测试
  ↓
安全
  ↓
生产化
```

> **不要同时学习全部技术。**
>
> 每一阶段都应该有一个可以运行的版本。

---

# 62. 第一阶段实际任务清单

第一阶段不要碰 Kafka、K8s、AI。

只完成：

```text
[ ] 创建 Git Repository
[ ] 创建 Python 3.12 项目
[ ] 配置 uv
[ ] 配置 Ruff
[ ] 配置 mypy
[ ] 配置 pytest
[ ] 创建 FastAPI
[ ] 创建 PostgreSQL
[ ] 配置 SQLAlchemy
[ ] 配置 Alembic
[ ] 创建 users
[ ] 创建 projects
[ ] 创建 issues
[ ] 创建 comments
[ ] 实现用户注册
[ ] 实现登录
[ ] 实现 JWT
[ ] 实现 Project CRUD
[ ] 实现 Issue CRUD
[ ] 实现 Comment
[ ] 编写 Unit Test
[ ] 编写 API Test
[ ] Docker 化
[ ] Docker Compose
```

完成后，再进入 Redis。

---

# 63. 结论

CodeFlow 的核心不是“功能多”，而是通过一个完整项目学习：

```text
代码
 ↓
API
 ↓
数据库
 ↓
缓存
 ↓
消息
 ↓
微服务
 ↓
容器
 ↓
Kubernetes
 ↓
CI/CD
 ↓
Observability
 ↓
AI
```

最终形成一个可以：

- 本地运行
- Docker Compose 启动
- Kubernetes 部署
- GitHub Actions 自动发布
- Prometheus/Grafana 监控
- Kafka 事件驱动
- AI/RAG 辅助研发

的完整云原生项目。

**推荐目标：先完成 V0.1，再逐步迭代到 V1.0。**
