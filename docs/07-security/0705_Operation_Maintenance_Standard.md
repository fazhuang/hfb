---
title: Operation & Maintenance Standard
document_id: HFB-SEC-0705
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Operations Officer
effective_date: 2026-06-24
scope: Platform Operation & Maintenance
priority: P0
related_documents:
  - HFB-SEC-0701 Acceptance Specification
  - HFB-SEC-0702 Security Standard
  - HFB-SEC-0704 Backup & Disaster Recovery Standard
  - HFB-DEV-0509 CI/CD Standard
  - HFB-DEV-0510 Release Management Standard
  - HFB-PS-1710 Production Readiness Specification
---

# Operation & Maintenance Standard

## 平台运维规范

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的统一运行维护标准。
>
> 运维不仅负责"系统可运行"，更负责平台稳定性、知识资产安全、AI 服务连续性以及学术服务质量。

---

# 第一章 建设目标

平台运维目标：

- Stable（稳定）
- Reliable（可靠）
- Observable（可观测）
- Recoverable（可恢复）
- Sustainable（可持续）

运维工作的核心目标是保障平台长期稳定运行。

---

# 第二章 运维范围

统一纳入运维管理：

| 模块            | 内容                 |
| --------------- | -------------------- |
| Application     | 前端、后端服务       |
| Database        | PostgreSQL           |
| Search          | Elasticsearch        |
| Object Storage  | MinIO                |
| AI Service      | RAG、LLM 服务        |
| Knowledge Graph | Neo4j（规划）        |
| Vector Database | Milvus（规划）       |
| Documentation   | docs/ 文档体系       |
| CI/CD           | GitHub Actions       |
| Infrastructure  | Docker、服务器、网络 |

---

# 第三章 运维原则

遵循：

- Automation First
- Monitoring First
- Prevention First
- Traceability First

优先自动化，而非人工干预。

---

# 第四章 环境管理

平台统一环境：

```text
Local
   ↓
Development
   ↓
Testing
   ↓
Staging
   ↓
Production
```

禁止跨环境直接部署。

---

# 第五章 服务监控

监控对象：

- API
- 数据库
- 检索服务
- AI 服务
- 文件存储
- CPU
- Memory
- Disk
- Network

所有关键服务必须纳入监控。

---

# 第六章 日志管理

统一日志分类：

| 类型        | 内容        |
| ----------- | ----------- |
| Application | 应用日志    |
| Access      | 访问日志    |
| Security    | 安全日志    |
| Audit       | 审计日志    |
| AI          | AI 调用日志 |
| System      | 系统日志    |

日志格式统一采用结构化输出（JSON）。

---

# 第七章 告警机制

平台建立三级告警：

| 等级 | 响应要求      |
| ---- | ------------- |
| P1   | 立即处理      |
| P2   | 30 分钟内响应 |
| P3   | 24 小时内处理 |

所有告警均生成事件编号。

---

# 第八章 服务健康检查

所有服务必须提供：

```text
/health

/ready

/live
```

检查内容：

- 服务状态
- 数据库连接
- 缓存连接
- 检索服务
- AI 服务

---

# 第九章 性能监控

持续监控：

- API 延迟
- SQL 执行时间
- AI 响应时间
- 检索耗时
- 页面加载时间

超过阈值自动告警。

---

# 第十章 AI 服务监控

重点监控：

- Prompt 版本
- Token 消耗
- 检索命中率
- 引文完整率
- Hallucination 指标
- 模型可用率

AI 服务异常必须优先定位。

---

# 第十一章 数据质量监控

每日自动检查：

- Metadata 完整率
- Entity 完整率
- Relation 完整率
- OCR 成功率
- 引文完整率
- 数据重复率

异常自动生成数据质量报告。

---

# 第十二章 检索质量监控

持续监控：

- Elasticsearch 命中率
- RAG Recall
- Citation Accuracy
- 检索耗时

任何异常必须记录原因。

---

# 第十三章 运维变更

所有变更必须：

```text
申请

↓

评审

↓

实施

↓

验证

↓

归档
```

禁止直接修改生产环境。

---

# 第十四章 巡检制度

建立固定巡检：

| 周期   | 内容               |
| ------ | ------------------ |
| 每日   | 服务状态、日志     |
| 每周   | 数据质量、备份     |
| 每月   | 安全检查、性能分析 |
| 每季度 | 架构评估、容量规划 |

巡检结果形成正式报告。

---

# 第十五章 SLA 指标

平台目标：

| 指标          | 标准   |
| ------------- | ------ |
| 系统可用率    | ≥99.9% |
| API 可用率    | ≥99.9% |
| AI 服务可用率 | ≥99.5% |
| 检索可用率    | ≥99.9% |

---

# 第十六章 运维文档

必须维护：

- Deployment Guide
- Recovery Guide
- Monitoring Guide
- Incident Manual
- Change Log
- Runbook

文档必须同步更新。

---

# 第十七章 故障管理

流程：

```text
发现

↓

定位

↓

隔离

↓

恢复

↓

验证

↓

复盘
```

所有故障必须形成 RCA（Root Cause Analysis）。

---

# 第十八章 运维红线

禁止：

- 无审批修改生产环境
- 无监控运行服务
- 无日志排查问题
- 无备份执行变更
- 无回滚方案发布
- 删除审计日志
- 跳过巡检

违反任一项立即停止运维操作。

---

# 第十九章 持续优化

运维团队持续优化：

- 自动化脚本
- 监控规则
- 告警策略
- AI 服务质量
- 检索性能
- 数据质量

形成持续改进闭环。

---

# 第二十章 修订规则

修改运维规范必须同步更新：

- Security Standard
- Backup & Disaster Recovery Standard
- CI/CD Standard
- Release Management Standard
- Infrastructure ADR

未经批准不得修改。

---

# 修订记录

| Version | Date       | Description                          |
| ------- | ---------- | ------------------------------------ |
| 1.1.0   | 2026-06-25 | 更新related_documents                |
| 1.0.0   | 2026-06-24 | 首版发布，作为平台统一运行维护规范。 |
