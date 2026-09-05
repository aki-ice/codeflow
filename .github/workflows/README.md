# CI/CD（Phase 11）

三个 workflow：

```
push/PR ──► test.yml        ruff + mypy + pytest + helm lint（质量门禁）
main   ──► build.yml        构建 5 个镜像 → Trivy 安全扫描 → 推送 GHCR
tag v* ──► deploy.yml       helm upgrade 自动部署到 Kubernetes
```

## test.yml

- `astral-sh/setup-uv` 安装 uv，`uv sync --all-packages` 装全部 workspace 依赖
- 测试用 SQLite 内存，**无需任何服务容器**，跑得快且稳定
- helm lint 保证 chart 模板可渲染

## build.yml

- matrix 策略并行构建 5 个服务镜像
- `docker/build-push-action` + GHA 缓存（按服务分 scope）
- Trivy 扫描 CRITICAL/HIGH 漏洞（`exit-code: 0` 先观察，严格后可改 1 阻断合并）
- 推送 GHCR：tag 触发用 `v1.0.0`，main 触发用 `sha-xxxxxxx`

## deploy.yml

- Helm chart 一键部署（config/secret/迁移 Job/服务/HPA/Ingress 全在 chart 里）
- 迁移 Job 以 `helm.sh/hook: pre-install,pre-upgrade` 在服务启动前运行
- `--wait` 等待 rollout 完成才标记成功

## 需要手动配置的 Secrets（仓库 Settings → Secrets → Actions）

| Secret | 说明 |
|---|---|
| `KUBE_CONFIG` | base64 编码的 kubeconfig：`base64 -w0 ~/.kube/config`（部署集群 API 访问凭据） |
| `SECRET_KEY` | 生产 JWT 签名密钥（helm 部署时注入） |
| `INTERNAL_TOKEN` | 服务间内部调用令牌 |

> 无集群时可先只启用 test.yml / build.yml；deploy.yml 手动触发（workflow_dispatch）。
