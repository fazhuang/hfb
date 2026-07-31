---
title: Testing Standard
document_id: HFB-DEV-0506
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Software Quality Assurance
priority: P0
related_documents:
  - HFB-DEV-0501 Development Specification
  - HFB-DEV-0504 API Design Standard
  - HFB-DEV-0505 Database Development Standard
  - HFB-AI-0402 RAG Specification
  - HFB-AI-0405 AI Academic Review Standard
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
---

# Testing Standard

## 测试规范

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的统一测试体系。
>
> 平台测试不仅验证程序正确性，还必须验证学术数据质量、数字人文资源完整性、AI 输出可信度及长期演进能力。

---

# 第一章 测试目标

平台测试覆盖以下五个维度：

- 软件质量（Software Quality）
- 数据质量（Data Quality）
- 学术质量（Academic Quality）
- AI 质量（AI Quality）
- 运维质量（Operational Quality）

任何 Sprint 均不得跳过测试。

---

# 第二章 测试金字塔

统一采用四层测试体系：

```text
End-to-End Test
        ▲
Integration Test
        ▲
API Test
        ▲
Unit Test
```

要求：

- Unit Test：数量最多
- Integration Test：验证模块协作
- API Test：验证接口契约
- E2E Test：验证完整业务流程

---

# 第三章 测试分类

平台测试划分为十二类：

| 类型               | 是否必须 |
| ------------------ | -------- |
| Unit Test          | √        |
| Integration Test   | √        |
| API Test           | √        |
| UI Test            | √        |
| Database Test      | √        |
| Migration Test     | √        |
| Security Test      | √        |
| Performance Test   | √        |
| Academic Data Test | √        |
| Citation Test      | √        |
| AI Test            | √        |
| E2E Test           | √        |

---

# 第四章 单元测试

Backend：

统一：

pytest

Frontend：

统一：

Vitest

要求：

所有：

Service

Repository

Utility

必须拥有测试。

覆盖率：

Backend ≥90%

Frontend ≥80%

---

# 第五章 集成测试

验证：

- API ↔ Service
- Service ↔ Repository
- Repository ↔ Database
- AI ↔ Search
- AI ↔ Citation

不得仅测试单个模块。

---

# 第六章 API 测试

所有公开 API 必须验证：

- HTTP Method
- 参数校验
- 返回结构
- 权限控制
- 异常处理
- OpenAPI 一致性

API 文档与实现必须一致。

---

# 第七章 数据库测试

验证：

- Migration
- Constraint
- Foreign Key
- Version
- Metadata
- Audit

任何 Migration 必须可：

升级

↓

回滚

↓

再次升级

---

# 第八章 学术数据测试

平台特有测试。

验证：

- 人物信息完整性
- 古籍元数据完整性
- 章节结构完整性
- 多版本对应关系
- 文献来源合法性

不得存在：

来源未知资源。

---

# 第九章 引文测试

所有引用必须验证：

- 引文存在
- 引文格式
- 页码
- 版本
- DOI（适用时）
- Metadata

禁止：

AI 编造引用。

---

# 第十章 多版本测试

重点验证：

《针灸甲乙经》

多个版本：

- 是否正确关联
- 是否能够比对
- 是否能够定位 Passage
- 是否保持引用一致

任何版本不得覆盖历史版本。

---

# 第十一章 AI 测试

验证：

- Prompt
- RAG
- Citation
- Confidence
- Explainability

测试包括：

正常输入

异常输入

空输入

长文本

冲突文献

版本冲突

---

# 第十二章 AI 幻觉测试

建立：

Hallucination Dataset。

验证：

AI 是否：

- 编造人物
- 编造古籍
- 编造论文
- 编造 DOI
- 编造引用

目标：

Hallucination <1%。

---

# 第十三章 OCR 测试（规划）

OCR 模块上线后验证：

- 识别率
- 版面恢复
- 古籍断句
- 人工校勘一致率

OCR 测试数据长期维护。

---

# 第十四章 RAG 测试

验证：

- Recall
- Precision
- Citation
- Metadata
- Retrieval

不得：

仅测试生成结果。

必须测试：

Retriever。

---

# 第十五章 GraphRAG 测试（规划）

验证：

- Entity
- Relation
- Evidence
- Multi-hop
- Explainability

所有 Graph 推理：

必须可解释。

---

# 第十六章 UI 测试

验证：

- 响应式
- Design System
- 国际化
- 可访问性
- 浏览器兼容

支持：

Chrome

Safari

Firefox

Edge

---

# 第十七章 性能测试

目标：

| 指标   | 标准   |
| ------ | ------ |
| API    | ≤300ms |
| Search | ≤1s    |
| AI     | ≤3s    |
| 页面   | ≤2s    |
| 首屏   | ≤2.5s  |

性能测试：

纳入 CI。

---

# 第十八章 安全测试

验证：

- SQL Injection
- XSS
- CSRF
- 文件上传
- JWT
- RBAC
- Rate Limit

高危漏洞：

零容忍。

---

# 第十九章 自动化测试

统一：

GitHub Actions。

每次提交执行：

- Lint
- Test
- Build

主分支：

增加：

Security Scan。

---

# 第二十章 测试数据管理

建立：

Test Fixture。

不得：

使用生产数据。

测试数据：

版本管理。

长期维护。

---

# 第二十一章 测试通过标准（Definition of Test Done）

一个 Sprint 完成必须满足：

- 单元测试通过
- 集成测试通过
- API 测试通过
- 数据测试通过
- AI 测试通过（适用）
- 安全测试通过
- CI 全绿

任何一项失败：

Sprint 不得结束。

---

# 第二十二章 测试红线

禁止：

- 删除测试绕过失败
- 修改断言迎合错误实现
- 使用假数据验证真实业务
- 跳过 Migration 测试
- 跳过 Citation 测试
- 跳过 Academic Data 测试
- 未达到覆盖率要求

违反任一项不得合并。

---

# 第二十三章 修订规则

修改测试规范必须同步更新：

- CI Pipeline
- Sprint Template
- AI Evaluation Dataset
- Acceptance Specification
- Context Package

未经批准不得修改。

---

# 修订记录

| Version | Date       | Description                      |
| ------- | ---------- | -------------------------------- |
| 1.0.0   | 2026-06-24 | 首版发布，作为平台统一测试规范。 |
