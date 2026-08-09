# E0 生产发布决策包（Production Release Go/No-Go Decision Package）

**文档编号:** E0-2026-08-09
**决策日期:** 2026-08-09
**生成者:** Claude Code (Codex) — 独立复验
**目标受众:** PO 及架构团队
**紧急程度:** 非紧急（正常发布窗口）

---

## 1. 发布候选基线与链条追踪（Release Baseline & Lineage）

### 1.1 发布候选 HEAD

| 属性 | 值 |
|---|---|
| **HEAD Commit SHA** | `ffc5b5a5089d3f1e8a96aa8aaaaa789cb51c360f` |
| **Commit 消息** | `docs: Phase 10 — PASS D2, unblock BLOCK_RELEASE, all gates green` |
| **提交时间** | `2026-08-09T13:28:30+08:00` |
| **分支** | `master` |
| **远端仓库** | `https://github.com/fazhuang/hfb.git` |
| **远端分支** | `origin/master` |
| **工作区状态** | `git status --short` 输出为空 — **Clean** |
| **空白符/格式** | `git diff --check` 无报错 — **通过** |
| **apps/ 业务代码变动** | `git diff HEAD~1 -- 'apps/'` 输出 0 行 — **零变动** |

### 1.2 链条追踪 — Phase 10 候选证据归档

| 链条节点 | SHA/标识 | 说明 |
|---|---|---|
| D2-FINAL 候选基线 | `5f1ea42249c87f5030ec3f0aea4284ae7b8b0aa9` | Phase 10 全部门禁基准 SHA |
| 发布候选 HEAD | `ffc5b5a5089d3f1e8a96aa8aaaaa789cb51c360f` | 当前 HEAD（docs: 无 apps/ 变动） |
| 证据归档文档 | `docs/13-release/phase10-candidate-evidence.md` | D2-FINAL 终期归档，记录 5/5 CI 全绿 |
| CI Build Run | https://github.com/fazhuang/hfb/actions/runs/31295398193 | ✅ success |
| CI Test Run | https://github.com/fazhuang/hfb/actions/runs/31295398226 | ✅ success |
| CI Documentation Run | https://github.com/fazhuang/hfb/actions/runs/31295398194 | ✅ success |
| CI Lint Run | https://github.com/fazhuang/hfb/actions/runs/31295398187 | ✅ success |
| CI Security Run | https://github.com/fazhuang/hfb/actions/runs/31295398192 | ✅ success |

### 1.3 HEAD → D2 基线链条一致性声明

`ffc5b5a` 与 `5f1ea42` 之间的差异仅限于 `docs/` 目录文件（Phase 10 文档更新），`apps/` 及 `packages/` 代码树完全一致。发布候选 HEAD 等同于在 D2 全绿门禁基线上追加纯文档提交。

---

## 2. 构建产物与镜像版本声明（Build Artifacts & Versions）

### 2.1 应用版本

| 组件 | 版本 | 说明 |
|---|---|---|
| 平台整体 | `0.2.0` | `pyproject.toml` / `package.json` 统一版本号 |
| 后端 | `huangfumi-platform==0.2.0` | Python 3.12+, FastAPI |
| 前端 | `@hfb/frontend@0.2.0` | Vue 3.5, TypeScript 5.7, Vite 6 |

### 2.2 Docker 镜像标签/基础镜像

| 服务 | 基础镜像 | 自定义 Dockerfile |
|---|---|---|
| Backend | `python:3.12-slim` | `docker/prod/Dockerfile.backend` |
| Frontend | `node:22-slim` (build) → `nginx:1.27-alpine` (runtime) | `docker/prod/Dockerfile.frontend` |
| PostgreSQL | `pgvector/pgvector:pg16` | 无（官方镜像） |
| Redis | `redis:7-alpine` | 无（官方镜像） |
| MinIO | `minio/minio:latest` | 无（官方镜像） |
| Elasticsearch | `docker.elastic.co/elasticsearch/elasticsearch:8.17.0` | 无（官方镜像） |
| Neo4j (post-MVP) | `neo4j:5` | 无（官方镜像，post-mvp profile） |

### 2.3 依赖包锁文件校验和

| 文件 | 大小 | MD5 | SHA256 |
|---|---|---|---|
| `pnpm-lock.yaml` | 136,065 bytes | `b6dbd9852d24ae56396c98c546208fc6` | `75617a599736c700623c4dcfd686b578de859529d5e335cee60a7e53d1aa72ef` |

### 2.4 前端构建产物标识

| 产物 | MD5 | SHA256 |
|---|---|---|
| `apps/frontend/dist/index.html` | `e2db79e54171ee48e6fe1339744c29a1` | `3e5b6a6bf385ce69aff0edff100c2611e6bc02e6213ee10ac03b044d6861720d` |

### 2.5 核心前端依赖（运行时）

| 包 | 版本约束 |
|---|---|
| vue | `^3.5.0` |
| pinia | `^2.3.0` |
| vue-router | `^4.5.0` |
| axios | `^1.7.0` |
| @lucide/vue | `^1.24.0` |
| vis-data | `^8.0.3` |
| vis-network | `^10.1.0` |
| vue-i18n | `^10.0.0` |

### 2.6 核心后端依赖（运行时）

| 包 | 版本约束 |
|---|---|
| fastapi | `>=0.115.0` |
| uvicorn[standard] | `>=0.34.0` |
| pydantic[email] | `>=2.10.0` |
| sqlalchemy[asyncio] | `>=2.0.36` |
| asyncpg | `>=0.30.0` |
| alembic | `>=1.14.0` |
| redis | `>=5.2.0` |
| elasticsearch[async] | `>=8.17.0,<9.0.0` |
| minio | `>=7.2.0` |

---

## 3. 生产配置与安全性评估（Config & Credentials Audit）

### 3.1 生产环境变量清单

以下清单来源于 `docker-compose.prod.yml` 与 `.env.example`（**严禁将真实密钥写入本文档**）。

#### 必需变量（缺少将导致容器启动失败）

| 变量 | 用途 | 存储位置 |
|---|---|---|
| `POSTGRES_PASSWORD` | PostgreSQL 数据库密码 | `<SECRET_STORE_KEY>` |
| `REDIS_PASSWORD` | Redis 认证密码 | `<SECRET_STORE_KEY>` |
| `MINIO_ROOT_USER` | MinIO 对象存储管理员用户名 | `<SECRET_STORE_KEY>` |
| `MINIO_ROOT_PASSWORD` | MinIO 对象存储管理员密码 | `<SECRET_STORE_KEY>` |
| `ELASTICSEARCH_PASSWORD` | Elasticsearch `elastic` 用户密码 | `<SECRET_STORE_KEY>` |

#### 可选变量（有默认值）

| 变量 | 默认值 | 用途 |
|---|---|---|
| `ENVIRONMENT` | `production` | 运行环境标识 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `BACKEND_PORT` | `8000` | 后端服务端口 |
| `FRONTEND_PORT` | `80` | 前端 Nginx 端口 |
| `POSTGRES_HOST` | `postgres` | PostgreSQL 主机名 |
| `POSTGRES_PORT` | `5432` | PostgreSQL 端口 |
| `POSTGRES_DB` | `hfb` | 数据库名 |
| `POSTGRES_USER` | `hfb` | 数据库用户 |
| `REDIS_HOST` | `redis` | Redis 主机名 |
| `REDIS_PORT` | `6379` | Redis 端口 |
| `MINIO_HOST` | `minio` | MinIO 主机名 |
| `MINIO_PORT` | `9000` | MinIO API 端口 |
| `MINIO_CONSOLE_PORT` | `9001` | MinIO 控制台端口 |
| `ELASTICSEARCH_HOST` | `elasticsearch` | Elasticsearch 主机名 |
| `ELASTICSEARCH_PORT` | `9200` | Elasticsearch 端口 |
| `ELASTICSEARCH_USER` | `elastic` | Elasticsearch 用户名 |

#### AI/LLM 相关变量（可选，不影响核心功能）

| 变量 | 用途 | 存储位置 |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API 密钥 | `<SECRET_STORE_KEY>` |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | `<SECRET_STORE_KEY>` |
| `DEFAULT_LLM_MODEL` | 默认 LLM 模型（默认 `gpt-4o`） | — |
| `DEFAULT_EMBEDDING_MODEL` | 默认嵌入模型（默认 `text-embedding-3-small`） | — |

#### 安全敏感变量

| 变量 | 用途 | 存储位置 |
|---|---|---|
| `SECRET_KEY` | FastAPI 应用密钥 | `<SECRET_STORE_KEY>` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | `<SECRET_STORE_KEY>` |
| `JWT_ALGORITHM` | JWT 签名算法（默认 `HS256`） | — |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | JWT 过期时间（默认 `60`） | — |

#### Post-MVP Profile 变量（非必需）

| 变量 | 用途 | 存储位置 |
|---|---|---|
| `NEO4J_USER` | Neo4j 用户名（默认 `neo4j`） | — |
| `NEO4J_PASSWORD` | Neo4j 密码 | `<SECRET_STORE_KEY>` |

### 3.2 密钥明文禁令检查

本文档及其引用文档 **不包含任何真实密钥、密码或 API Token 明文**。所有敏感值已替换为 `<SECRET_STORE_KEY>` 占位符或 `change-me` 样例占位符。

### 3.3 数据库 Migration 状态

| 属性 | 值 |
|---|---|
| Migration 管理工具 | Alembic（`apps/backend/alembic.ini`） |
| Migration 脚本目录 | `apps/backend/app/db/migrations/versions/` |
| Migration 文件数量 | 24 |
| 总代码行数 | 3,288 lines |
| 最近 Migration | `rag_evidence_binding_v2.py` |

### 3.4 Schema 向下兼容性评估

- **数据库引擎:** PostgreSQL 16（`pgvector/pgvector:pg16` 镜像）— 上游已发布，稳定维护。
- **Migration 历史:** 24 个顺序迁移文件均为增量添加（新增表/列/约束），无破坏性 DROP/SHRINK 操作。
- **回滚策略:** 发布候选 HEAD 的 Schema 与 D2 基线 `5f1ea42` 一致（`apps/` 无变动）。回滚至上一版本时无需执行 Schema 降级迁移 — 当前 Schema 为纯增量。
- **数据完整性:** Migration 均使用 `ALTER TABLE ... ADD COLUMN` / `CREATE TABLE` / `ADD CONSTRAINT` 模式，不删除或修改已有数据结构。
- **兼容性结论:** ✅ 向下兼容，支持无缝切换与回滚。

---

## 4. 部署、健康检查与烟雾路径剧本（SOP & Smoke Scenarios）

### 4.1 生产环境标准部署步骤（SOP）

> **警告：以下步骤非执行指令，仅作为标准化 SOP 参考。实际执行需 PO 书面授权。**

#### 前置条件

1. `.env` 文件已配置所有必需变量，密钥从安全的 Secret Store 获取
2. Docker 及 Docker Compose 已安装在目标主机
3. 目标主机有至少 8 GB 可用内存和 20 GB 可用磁盘空间
4. 端口 80、8000、5432、6379、9000、9200 可用（或通过环境变量自定义）

#### 部署步骤

```bash
# Step 1: 拉取代码
git fetch origin master
git checkout ffc5b5a5089d3f1e8a96aa8aaaaa789cb51c360f

# Step 2: 验证工作区干净
git status --short  # 必须为空

# Step 3: 验证锁文件完整性
md5sum pnpm-lock.yaml  # 预期: b6dbd9852d24ae56396c98c546208fc6 (MD5)
# 或
shasum -a 256 pnpm-lock.yaml  # 预期: 75617a599736c700623c4dcfd686b578de859529d5e335cee60a7e53d1aa72ef

# Step 4: 构建并启动所有服务
docker compose -f docker-compose.prod.yml up -d --build

# Step 5: 运行数据库迁移（如需要）
docker exec hfb-backend alembic upgrade head

# Step 6: 等待所有健康检查通过
docker ps --filter "name=hfb-" --format "table {{.Names}}\t{{.Status}}"
```

#### 预期运行服务

| 容器名 | 健康检查端点 |
|---|---|
| `hfb-backend` | `curl http://localhost:8000/health` |
| `hfb-frontend` | `curl http://localhost:80/health` |
| `hfb-postgres` | `pg_isready` |
| `hfb-redis` | `redis-cli ping` |
| `hfb-minio` | `curl http://localhost:9000/minio/health/live` |
| `hfb-elasticsearch` | `curl http://localhost:9200/_cluster/health` |

### 4.2 部署后健康检查探针

#### HTTP 探针

| 探针 | 方法 | 端点 | 期待响应 | 超时 |
|---|---|---|---|---|
| Backend Liveness | GET | `http://localhost:8000/health` | 200 OK | 10s |
| Frontend Liveness | GET | `http://localhost:80/health` | 200 OK | 10s |
| Backend Readiness | GET | `http://localhost:8000/api/v1/` | 200 OK (JSON) | 15s |

#### TCP 探针

| 服务 | 端口 | 超时 |
|---|---|---|
| PostgreSQL | 5432 | 5s |
| Redis | 6379 | 5s |
| MinIO | 9000 | 5s |
| Elasticsearch | 9200 | 10s |

### 4.3 核心业务烟雾测试路径（Smoke Scenarios）

烟雾测试应使用真实浏览器 + 真实测试用户账户执行。

#### Smoke-1: 健康检查（无认证）

1. `GET /health` → 200 OK
2. `GET /api/v1/` → 200 OK (JSON)

#### Smoke-2: 用户认证链路

1. 浏览器访问 `http://<HOST>/login`
2. 使用测试用户 `<TEST_USER_PASSWORD_FROM_ENV>` 登录
3. 验证：重定向至研究首页，JWT Token 写入 localStorage
4. 刷新页面，验证会话保持

#### Smoke-3: 核心查询链路

1. 登录后访问研究搜索页面
2. 输入关键词（如"针灸"）执行搜索
3. 验证：返回结果列表，非空，渲染正确
4. 点击任一结果，验证：条文详情页正常渲染

#### Smoke-4: AI 辅助功能链路（如有 LLM Key 配置）

1. 在条文详情页触发 AI 分析
2. 验证：返回 AI 分析结果，内容非空
3. 无 LLM Key 时此步骤可跳过

#### Smoke-5: Citation 及证据链路

1. 在条文详情页点击"保存引用"
2. 验证：Citation 成功保存
3. 进入 Research Reports，导出报告
4. 验证：报告生成成功，含正确 Citation 编号

### 4.4 生产资源配置参考

| 服务 | CPU Limit | Memory Limit |
|---|---|---|
| Backend | 2 cores | 2 GB |
| Frontend (Nginx) | — | — |
| PostgreSQL | 2 cores | 4 GB |
| Elasticsearch | — | 2 GB (JVM) |

---

## 5. 回滚触发机制与责任矩阵（Rollback SOP & Escalation Matrix）

### 5.1 回滚触发条件

以下任一条件满足时立即触发回滚：

| 条件编号 | 指标 | 阈值 | 检测方式 |
|---|---|---|---|
| R1 | API 5xx 错误率 | > 1%（观察窗口内） | 应用日志 / 反向代理监控 |
| R2 | P95 API 响应延迟 | > 2000ms（观察窗口内） | APM / 反向代理日志 |
| R3 | 数据库连接失败率 | > 0%（任何失败） | Backend 健康检查失败 |
| R4 | 健康检查连续失败 | ≥ 3 次 | Docker healthcheck / 外部探针 |
| R5 | 数据校验异常 | 任何数据不一致报告 | 用户反馈 / 自动化校验 |
| R6 | 安全事件 | 任何未授权访问或数据泄露迹象 | 安全监控 / 审计日志 |

### 5.2 观察窗口期

**默认观察窗口：部署后 30 分钟**

- T+0 ~ T+10: 密集监控期，每 1 分钟检查健康探针
- T+10 ~ T+30: 稳定观察期，每 5 分钟检查关键指标
- T+30: 若无触发条件，观察期结束，标记为正常发布

### 5.3 回滚操作 SOP

```bash
# Step 1: 停止当前部署
docker compose -f docker-compose.prod.yml down

# Step 2: 切换到上一个已知正常版本
# （替换 <PREVIOUS_SHA> 为上一个生产基线）
git checkout <PREVIOUS_SHA>

# Step 3: 重新构建并启动
docker compose -f docker-compose.prod.yml up -d --build

# Step 4: 验证回滚后健康状态
curl -f http://localhost:8000/health
curl -f http://localhost:80/health

# Step 5: 执行 Smoke-1 ~ Smoke-3 验证
```

### 5.4 Schema 降级说明

当前发布候选 HEAD (`ffc5b5a`) 与 D2 基线 (`5f1ea42`) 的 `apps/` 代码完全一致，Migration 为纯增量。回滚至前一版本无需执行 Schema 降级操作。

若回滚跨越多个版本且涉及 Migration 降级，使用 Alembic 降级：

```bash
docker exec hfb-backend alembic downgrade -1  # 回退一个版本
```

### 5.5 责任矩阵（Escalation Matrix）

| 角色 | 职责 | 通知方式 |
|---|---|---|
| **PO（产品负责人）** | 最终发布 Go/No-Go 决策；回滚授权 | Email / 即时通讯 |
| **架构负责人** | 部署技术审批；回滚执行监督；Schema 兼容性终裁 | Email / On-call 电话 |
| **运维/DevOps** | 实际部署执行；健康监控；回滚第一响应人 | On-call PagerDuty / 告警群 |
| **后端 Lead** | API 异常排查；数据库问题诊断 | 即时通讯 / On-call |
| **前端 Lead** | UI 渲染异常排查；浏览器兼容性 | 即时通讯 |
| **安全工程师** | 安全事件响应（触发条件 R6） | On-call 电话 |

### 5.6 日志与告警监控入口

| 监控目标 | 工具/入口 | 说明 |
|---|---|---|
| 应用日志 | Docker logs (`docker logs hfb-backend`) | 结构化日志，`LOG_LEVEL=INFO` |
| 反向代理日志 | Nginx access/error log (`docker logs hfb-frontend`) | HTTP 请求与错误 |
| 数据库慢查询 | PostgreSQL `log_min_duration_statement` | 建议设置 500ms 阈值 |
| 容器资源 | `docker stats` / Prometheus + Grafana | CPU / Memory / Network |
| 健康检查 | Docker healthcheck + 外部 Uptime Monitor | 30s 间隔，3 次重试 |

---

## 6. 门禁全盘汇总与发布建议（Release Gate Summary）

### 6.1 D2-FINAL 门禁逐项

| 门禁 | 指标 | 结果 | 状态 |
|---|---|---|---|
| D2-COV | Backend `percent_covered` ≥ 90.01% | 90.0174% | ✅ PASS |
| D2-E2E | Browser E2E 27/27 | 27 passed, 0 failed | ✅ PASS |
| D2-SEC | `pnpm audit` 0 vulnerabilities | 0 known | ✅ PASS |
| CI Build | GitHub Actions | success | ✅ PASS |
| CI Test | GitHub Actions | success | ✅ PASS |
| CI Documentation | GitHub Actions | success | ✅ PASS |
| CI Lint | GitHub Actions (ruff + prettier + vue-tsc) | success | ✅ PASS |
| CI Security | GitHub Actions | success | ✅ PASS |
| Worktree Clean | `git status --short` | Clean | ✅ PASS |
| Apps Diff | `git diff HEAD~1 -- 'apps/'` | 0 lines | ✅ PASS |
| Whitespace Check | `git diff --check` | No output | ✅ PASS |

### 6.2 发布候选最终评估

| 评估维度 | 结论 |
|---|---|
| 代码冻结 | ✅ 已冻结 — 无 `apps/` 变动，仅 docs 追加 |
| CI 门禁 | ✅ 5/5 全绿 |
| 安全审计 | ✅ 0 known vulnerabilities |
| 测试覆盖 | ✅ Backend 90.02%, Frontend 371 unit + 27 E2E |
| Schema 兼容 | ✅ 向下兼容，支持无缝回滚 |
| 配置审计 | ✅ 无密钥明文泄露 |
| BLOCK_RELEASE | ✅ 正式解封（Phase 10 D2-FINAL） |

### 6.3 最终建议

**GO / NO-GO 建议：GO**

全部门禁满足，发布候选已冻结，无阻塞项。建议 PO 在 2026-08-09 发布窗口内授权生产部署。

---

## 7. 审批签署

| 角色 | 签名 | 日期 |
|---|---|---|
| PO（产品负责人） | ______________________ | ________ |
| 架构负责人 | ______________________ | ________ |
| DevOps / 运维 | ______________________ | ________ |

---

**文档版本:** 1.0
**生成 SHA:** `ffc5b5a5089d3f1e8a96aa8aaaaa789cb51c360f`
**证据索引:** `docs/13-release/phase10-candidate-evidence.md`
**BLOCK_RELEASE 状态:** ✅ 已解封
