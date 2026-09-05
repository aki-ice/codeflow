# CodeFlow Kubernetes 部署（Phase 9：手写 YAML）

按照「先手写 YAML 理解 K8s，再学 Helm」的原则，本目录包含全部核心资源。

## 资源清单

| 文件 | 资源 | 学习点 |
|---|---|---|
| 00-namespace.yaml | Namespace | 资源隔离 |
| 01-config.yaml | Secret + ConfigMap×2 | 密钥与配置分离；ConfigMap 挂载 init.sql |
| 02-postgres.yaml | Secret + StatefulSet + Service + PVC | 有状态应用、volumeClaimTemplates、exec 探针 |
| 03-redis.yaml | Deployment + Service | readiness/liveness 探针 |
| 04-kafka.yaml | Deployment(KRaft) + Service | 环境变量配置、tcpSocket 探针 |
| 05~09-*.yaml | Deployment + Service（+HPA/Ingress） | 多副本、资源限额、探针、HPA、Ingress |
| 10-migrate-jobs.yaml | Job×4 | 用 Job 跑数据库迁移，与应用启动解耦 |

## 部署步骤

```bash
# 0. 构建镜像（在仓库根目录；本地 kind/minikube 需先 load 镜像）
docker build -f services/user-service/Dockerfile -t codeflow/user-service:dev .
docker build -f services/project-service/Dockerfile -t codeflow/project-service:dev .
docker build -f services/notification-service/Dockerfile -t codeflow/notification-service:dev .
docker build -f services/ci-service/Dockerfile -t codeflow/ci-service:dev .
docker build -f services/gateway-service/Dockerfile -t codeflow/gateway-service:dev .
# kind: kind load docker-image codeflow/user-service:dev ... / minikube: minikube image load ...

# 1. 基础设施
kubectl apply -f deploy/k8s/00-namespace.yaml
kubectl apply -f deploy/k8s/01-config.yaml
kubectl apply -f deploy/k8s/02-postgres.yaml
kubectl apply -f deploy/k8s/03-redis.yaml
kubectl apply -f deploy/k8s/04-kafka.yaml
kubectl -n codeflow wait --for=condition=ready pod -l app=postgres --timeout=120s

# 2. 数据库迁移（Job）
kubectl apply -f deploy/k8s/10-migrate-jobs.yaml
kubectl -n codeflow get jobs -w   # 等待 4 个 Job Complete

# 3. 应用服务
kubectl apply -f deploy/k8s/05-user-service.yaml
kubectl apply -f deploy/k8s/06-project-service.yaml
kubectl apply -f deploy/k8s/07-notification-service.yaml
kubectl apply -f deploy/k8s/08-ci-service.yaml
kubectl apply -f deploy/k8s/09-gateway.yaml

# 4. 验证
kubectl -n codeflow get pods,svc
kubectl -n codeflow port-forward svc/gateway 8000:8000
curl http://localhost:8000/health
```

## 修改密钥

```bash
kubectl -n codeflow edit secret codeflow-secrets   # 或改 01-config.yaml 后重新 apply + 滚动重启
kubectl -n codeflow rollout restart deploy
```

## 注意

- **Ingress**：需要集群安装 ingress-nginx 并配置 `codeflow.local` 域名解析（或用 port-forward）
- **HPA**：需要 metrics-server（kind/minikube 默认可能未装）
- **镜像**：`imagePullPolicy: IfNotPresent` + 本地镜像，仅适合开发集群
- **Kafka**：单节点 KRaft，生产环境应使用 Strimzi Operator
- **Secret**：明文 YAML 仅用于学习，生产用 sealed-secrets / vault
