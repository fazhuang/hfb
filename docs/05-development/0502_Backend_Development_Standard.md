---
title: Backend Development Standard
document_id: HFB-DEV-0502
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Backend Development
priority: P0
related_documents:
  - HFB-DEV-0501 Development Specification
  - HFB-ARC-0201 Technical Blueprint
  - HFB-DAT-0301 Data Standard Specification
  - HFB-PS-1709 MVP Implementation Specification
---

# Backend Development Standard
## 后端开发规范

> 本规范定义平台后端开发的统一标准。
>
> 所有 FastAPI 服务、API 接口、数据库访问、业务逻辑、后台任务、AI 服务接口均必须遵循本规范。

---

# 第一章 建设目标

后端必须满足：

- 高内聚
- 低耦合
- 易维护
- 易扩展
- 易测试
- 可观测
- 可审计

---

# 第二章 技术栈

统一采用：

| 模块 | 技术 |
|------|------|
| Framework | FastAPI |
| Python | 3.12+ |
| ORM | SQLAlchemy 2.x |
| Migration | Alembic |
| Validation | Pydantic v2 |
| Async | asyncio |
| Testing | pytest |
| Dependency | uv |

未经 ADR，不得更换核心框架。

---

# 第三章 项目目录

```text
apps/backend/

app/
├── api/
├── core/
├── db/
├── middleware/
├── models/
├── repositories/
├── schemas/
├── services/
├── startup/
├── tasks/
├── integrations/
└── utils/
```

目录职责不得交叉。

---

# 第四章 Controller（API）

Controller 只负责：

- 参数接收
- 参数校验
- 调用 Service
- 返回 Response

不得：

- 编写业务逻辑
- 写 SQL
- 调用 ORM
- 拼装复杂数据

---

# 第五章 Service

Service 是业务中心。

负责：

- 业务规则
- 工作流
- 权限判断
- 数据组合
- AI 服务协调

禁止：

直接访问数据库连接。

必须通过 Repository。

---

# 第六章 Repository

Repository 负责：

- 查询
- 新增
- 修改
- 删除
- 分页
- 排序

禁止：

业务规则。

禁止：

权限判断。

---

# 第七章 Schema

统一：

Pydantic v2。

划分：

```text
Create

Update

Response

Query
```

禁止：

直接返回 ORM Model。

---

# 第八章 Model

所有 Model：

继承：

BaseEntity。

必须包含：

- UUID
- version
- status
- created_at
- updated_at

业务字段不得写入 BaseEntity。

---

# 第九章 Dependency Injection

统一采用：

FastAPI Depends。

禁止：

全局单例。

禁止：

Service 相互直接实例化。

---

# 第十章 配置管理

统一：

Settings。

来源：

Environment Variables。

禁止：

硬编码：

- URL
- Token
- Password
- API Key

---

# 第十一章 异常处理

统一：

Exception Middleware。

统一错误结构：

```json
{
  "success": false,
  "code": "...",
  "message": "...",
  "details": {}
}
```

禁止：

print(Exception)。

---

# 第十二章 日志规范

统一：

Structured Logging。

必须记录：

- request_id
- trace_id
- user_id
- api
- latency
- status

敏感信息必须脱敏。

---

# 第十三章 数据库事务

统一：

Service 控制事务边界。

Repository 不开启事务。

禁止：

嵌套事务。

---

# 第十四章 后台任务

统一放置：

```text
tasks/
```

包括：

- OCR
- 索引构建
- 数据同步
- AI 批处理

必须：

支持重试。

支持日志。

支持状态跟踪。

---

# 第十五章 外部集成

统一：

```text
integrations/
```

例如：

- OpenAI
- Claude
- Gemini
- Elasticsearch
- MinIO

禁止：

业务模块直接访问第三方 SDK。

---

# 第十六章 API 版本管理

统一：

```text
/api/v1/
```

重大升级：

建立：

```text
/api/v2/
```

禁止：

修改旧接口行为。

---

# 第十七章 安全规范

必须支持：

- JWT
- RBAC
- 输入校验
- SQL 注入防护
- 文件类型校验
- 请求限流
- 审计日志

---

# 第十八章 测试规范

必须包含：

- Unit Test
- Integration Test
- API Test

覆盖率：

≥90%。

所有新增 Service 必须有测试。

---

# 第十九章 性能规范

目标：

| 指标 | 标准 |
|------|------|
| API 响应 | ≤300ms |
| DB 查询 | ≤100ms |
| 并发支持 | ≥1000 QPS（架构目标） |
| 启动时间 | ≤10 秒 |

---

# 第二十章 可观测性

统一支持：

- Health Check
- Metrics
- Trace
- Structured Log

所有核心服务必须可监控。

---

# 第二十一章 后端开发红线

禁止：

- Controller 写业务
- Service 写 SQL
- Repository 写业务
- ORM 直接返回 API
- 硬编码配置
- 无测试提交
- 无日志异常处理
- 未注册 API

违反任一项不得合并。

---

# 第二十二章 修订规则

修改本规范必须：

1. 建立 ADR；
2. 更新 Development Specification；
3. 更新 Blueprint；
4. 更新 Context Package；
5. 项目负责人批准。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.0.0 | 2026-06-24 | 首版发布，作为平台后端开发统一规范。 |