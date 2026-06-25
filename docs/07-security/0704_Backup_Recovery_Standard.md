---
title: Backup & Disaster Recovery Standard
document_id: HFB-SEC-0704
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Infrastructure Officer
effective_date: 2026-06-24
scope: Backup & Disaster Recovery
priority: P0
related_documents:
  - HFB-SEC-0701 Acceptance Specification
  - HFB-SEC-0702 Security Standard
  - HFB-SEC-0703 Privacy & Data Governance Standard
  - HFB-DEV-0510 Release Management Standard
  - HFB-DAT-0301 Data Standard Specification
  - HFB-PS-1710 Production Readiness Specification
---

# Backup & Disaster Recovery Standard
## 备份与灾难恢复规范

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的统一备份、恢复、容灾及业务连续性标准。
>
> 平台承载数字人文知识资产，其核心目标不是恢复系统，而是**保证学术成果永久保存、知识资产永不丢失、研究过程可持续延续。**

---

# 第一章 建设目标

建立统一灾备体系，实现：

- 数据零丢失（关键资源）
- 快速恢复
- 业务连续
- 全程可审计
- 可验证
- 可演练

备份不仅是运维任务，也是平台治理的重要组成部分。

---

# 第二章 保护对象

统一纳入灾备管理：

| 类型 | 内容 |
|------|------|
| Application | 前后端应用 |
| PostgreSQL | 主数据库 |
| MinIO | 古籍图片、附件、OCR 文件 |
| Elasticsearch | 检索索引 |
| Neo4j（规划） | 知识图谱 |
| Milvus（规划） | 向量索引 |
| Prompt Library | Prompt 资产 |
| Governance Docs | docs/ 文档体系 |
| CI/CD | GitHub Actions 配置 |
| Git Repository | 源代码仓库 |

所有资产均需定义备份策略。

---

# 第三章 备份原则

遵循：

- 3-2-1 原则
- 自动备份
- 增量优先
- 定期验证
- 异地保存

即：

- 至少 3 份副本
- 存放于 2 种不同介质
- 至少 1 份异地备份

---

# 第四章 数据库备份

PostgreSQL：

采用：

```text
每日全量

+

每小时 WAL

+

PITR
```

恢复目标：

- RPO ≤ 1 小时
- RTO ≤ 30 分钟

---

# 第五章 对象存储备份

MinIO：

备份内容：

- 古籍扫描件
- OCR 文件
- 图片资源
- 用户上传附件

采用：

对象版本控制（Versioning）。

禁止覆盖原文件。

---

# 第六章 检索索引恢复

Elasticsearch：

索引属于可重建资源。

恢复流程：

```text
恢复数据库
      │
      ▼
重建索引
      │
      ▼
验证一致性
```

索引不得作为唯一数据来源。

---

# 第七章 知识图谱恢复（规划）

Neo4j：

恢复对象：

- 节点
- 关系
- 属性
- 图配置

恢复后必须重新验证：

Evidence 一致性。

---

# 第八章 向量数据库恢复（规划）

Milvus：

Embedding：

必须支持：

- 全量重建
- 增量同步

向量数据不得作为唯一知识来源。

---

# 第九章 Prompt 资产恢复

Prompt Library：

备份内容：

- Prompt
- Version
- Changelog
- Review Status
- Release History

Prompt 必须支持历史回滚。

---

# 第十章 治理文档备份

docs/：

包括：

- Charter
- Constitution
- ADR
- Blueprint
- Standards
- Sprint

所有文档进入 Git 永久版本管理。

---

# 第十一章 Git 仓库保护

采用：

- GitHub
- 本地镜像
- 定期离线备份

禁止：

唯一代码仓库存储。

---

# 第十二章 自动备份

自动执行：

| 周期 | 内容 |
|------|------|
| 每小时 | WAL、日志 |
| 每日 | 数据库、对象存储 |
| 每周 | 全量镜像 |
| 每月 | 长期归档 |

所有任务必须自动执行。

---

# 第十三章 恢复验证

每次恢复必须验证：

- 数据完整性
- Metadata
- Entity
- Relation
- 引文
- 检索功能
- AI 检索

恢复成功后生成验证报告。

---

# 第十四章 灾难等级

统一定义：

| 等级 | 说明 |
|------|------|
| P1 | 全站不可用 |
| P2 | 核心功能不可用 |
| P3 | 单模块异常 |
| P4 | 非关键故障 |

不同等级采用不同恢复策略。

---

# 第十五章 应急响应

流程：

```text
发现

↓

确认

↓

隔离

↓

恢复

↓

验证

↓

复盘

↓

更新规范
```

所有事件必须形成 Incident Report。

---

# 第十六章 灾备演练

至少：

每半年一次。

演练内容：

- 数据恢复
- 系统恢复
- Prompt 恢复
- 检索恢复
- 文档恢复

演练结果纳入项目档案。

---

# 第十七章 恢复指标

目标：

| 指标 | 标准 |
|------|------|
| 数据恢复成功率 | 100% |
| 文档恢复成功率 | 100% |
| Prompt 恢复成功率 | 100% |
| 数据一致性 | 100% |
| 恢复验证完成率 | 100% |

---

# 第十八章 灾备红线

禁止：

- 无备份上线
- 无恢复验证
- 删除历史备份
- 唯一存储副本
- 未测试恢复流程
- 覆盖历史版本
- 无异地备份

违反任一项不得进入生产环境。

---

# 第十九章 持续改进

每次灾备事件结束后必须：

- 更新恢复流程
- 更新备份策略
- 更新自动化脚本
- 更新风险清单
- 更新治理文档

形成闭环。

---

# 第二十章 修订规则

修改灾备规范必须同步更新：

- Security Standard
- Release Management Standard
- CI/CD Standard
- Deployment Guide
- Infrastructure ADR

未经批准不得修改。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.1.0 | 2026-06-25 | 更新related_documents |
| 1.0.0 | 2026-06-24 | 首版发布，作为平台备份与灾难恢复统一规范。 |