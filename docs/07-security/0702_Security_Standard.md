---
title: Security Standard
document_id: HFB-SEC-0702
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Information Security Officer
effective_date: 2026-06-24
scope: Platform Security
priority: P0
related_documents:
  - HFB-SEC-0701 Acceptance Specification
  - HFB-DEV-0502 Backend Development Standard
  - HFB-DEV-0504 API Design Standard
  - HFB-DEV-0509 CI_CD_Standard
  - HFB-DAT-0301 Data Standard Specification
  - HFB-PS-1710 Production Readiness Specification
---

# Security Standard

## 平台安全规范

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的统一安全标准。
>
> 平台属于数字人文研究基础设施，承载学术成果、古籍资源、AI 服务及知识图谱，因此安全建设必须贯穿系统生命周期。

---

# 第一章 建设目标

建立覆盖平台全生命周期的安全体系，实现：

- 身份可信
- 权限可控
- 数据可保护
- 操作可审计
- 风险可预警
- 安全可追溯

安全设计必须前置，而不是上线前补充。

---

# 第二章 安全架构

平台采用纵深防御（Defense in Depth）：

```text
Client
    │
API Gateway
    │
Authentication
    │
Authorization
    │
Application
    │
Database
    │
Object Storage
    │
Audit & Monitoring
```

每一层均承担独立安全职责。

---

# 第三章 身份认证

统一采用：

- JWT Access Token
- Refresh Token
- HTTPS

规划支持：

- OAuth2
- OpenID Connect
- 高校统一身份认证（CAS / OAuth）

禁止明文身份认证。

---

# 第四章 权限模型

统一采用：

```text
User
   ↓
Role
   ↓
Permission
```

RBAC 为唯一权限模型。

后续可扩展 ABAC，但不得替代 RBAC。

---

# 第五章 平台角色

统一角色：

| 角色           | 权限         |
| -------------- | ------------ |
| Super Admin    | 平台治理     |
| Academic Admin | 学术资源管理 |
| Data Curator   | 数据整理     |
| Researcher     | 科研使用     |
| Teacher        | 教学使用     |
| Student        | 学习使用     |
| Guest          | 公开访问     |

权限最小化原则。

---

# 第六章 API 安全

所有 API 必须：

- JWT 校验
- RBAC 校验
- 参数校验
- 请求日志
- Request ID

禁止匿名访问管理接口。

---

# 第七章 输入安全

统一校验：

- Path
- Query
- Body
- Header
- Upload

所有输入均视为不可信。

禁止：

SQL 拼接。

---

# 第八章 文件安全

允许上传：

- PDF
- DOCX
- TXT
- XML（规划）
- 图片（TIFF/JPG/PNG）

上传后必须：

- MIME 校验
- 后缀校验
- 病毒扫描（规划）
- 文件重命名
- 元数据提取

禁止直接保存用户文件名。

---

# 第九章 数据安全

敏感数据包括：

- 用户信息
- 操作日志
- AI Prompt（管理员）
- API Key
- Token

必须加密存储。

不得写入日志。

---

# 第十章 数据传输

统一：

HTTPS。

禁止：

HTTP。

内部服务：

逐步支持：

mTLS（规划）。

---

# 第十一章 密钥管理

统一来源：

Environment Variables。

生产环境：

使用：

Secret Manager（规划）。

禁止：

```text
API Key

Password

Token
```

提交至 Git。

---

# 第十二章 AI 安全

AI 模块必须防范：

- Prompt Injection
- Prompt Leakage
- 数据越权
- 幻觉引用
- 恶意输入

AI 不得访问未经授权的数据。

---

# 第十三章 学术资源安全

所有资源必须：

- 来源可追溯
- Metadata 完整
- 修改可审计
- 删除可恢复

禁止直接覆盖原始数据。

---

# 第十四章 日志审计

统一记录：

- 登录
- 查询
- 修改
- 删除
- AI 调用
- 权限变更

日志至少保存五年。

---

# 第十五章 漏洞管理

统一等级：

| 等级     | 处理要求           |
| -------- | ------------------ |
| Critical | 立即修复，阻塞上线 |
| High     | Sprint 内修复      |
| Medium   | 两个 Sprint 内修复 |
| Low      | 纳入技术债管理     |

---

# 第十六章 安全扫描

CI 自动执行：

- Secret Scan
- Dependency Scan
- SAST
- License Audit

规划增加：

- DAST
- Container Scan

---

# 第十七章 安全事件

发生安全事件必须：

```text
发现

↓

隔离

↓

分析

↓

修复

↓

复盘

↓

更新规范
```

所有事件形成正式报告。

---

# 第十八章 安全指标

目标：

| 指标           | 标准        |
| -------------- | ----------- |
| Critical 漏洞  | 0           |
| High 漏洞      | 0（上线前） |
| JWT 覆盖率     | 100%        |
| RBAC 覆盖率    | 100%        |
| 审计日志覆盖率 | 100%        |

---

# 第十九章 安全红线

禁止：

- 默认账号密码
- 明文密码
- 明文 Token
- SQL 拼接
- 权限绕过
- Git 提交 Secret
- AI 越权访问
- 删除审计日志

违反任一项立即停止上线。

---

# 第二十章 修订规则

修改安全规范必须同步更新：

- Acceptance Specification
- Backend Development Standard
- API Design Standard
- CI/CD Standard
- Incident Response Plan（规划）

未经批准不得修改。

---

# 修订记录

| Version | Date       | Description                      |
| ------- | ---------- | -------------------------------- |
| 1.1.0   | 2026-06-25 | 更新related_documents            |
| 1.0.0   | 2026-06-24 | 首版发布，作为平台统一安全规范。 |
