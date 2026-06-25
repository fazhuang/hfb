---
title: Governance Index
document_id: HFB-GOV-INDEX
version: 1.0.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-25
scope: Platform Governance
priority: P0
related_documents:
  - HFB-GOV-0002 Project Constitution
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
---

# 00-governance

平台最高治理制度目录。本目录为全项目最高决策依据。

---

> 层级：**Level 0 — 项目治理**
>
> 优先级：高于所有其他目录（包括 17-Platform-Specifications、16-research-framework）

---

## 治理体系

| # | 文档 | document_id | 层级 | 作用 |
|---|---|---|---|---|
| 0001 | [Project Charter](0001-project-charter.md) | HFB-GOV-0001 | 二级 | 使命、愿景、范围、成功定义、产品依据 |
| 0002 | [Project Constitution](0002-project-constitution.md) | HFB-GOV-0002 | **一级** | 最高治理文件 — 核心原则、技术约束、协作规则、质量红线 |
| 0003 | [Governance](0003-governance.md) | HFB-GOV-0003 | 二级 | 决策机制、角色权限、变更流程、MVP/上线控制 |
| 0004 | [Documentation Rules](0004-documentation-rules.md) | HFB-GOV-0004 | 三级 | 所有文档的格式、YAML、编号、引用强制规范 |
| 0005 | [AI Execution Protocol](0005_AI_Execution_Protocol.md) | HFB-GOV-0005 | 二级 | 所有 AI 的最高执行规范 — 职责边界、启动流程、范围控制 |

### 效力层级

```
Constitution (0002) — 最高
  ├── AI Execution Protocol (0005) — 并行最高 (AI)
  ├── Project Charter (0001)
  ├── Governance (0003)
  └── Documentation Rules (0004)
```

---

## 关键引用

| 依据 | 路径 | 作用 |
|---|---|---|
| 产品实现最高依据 | [docs/17-Platform-Specifications/](../17-Platform-Specifications/) | 所有产品功能实现必须以此为唯一规格来源 |
| MVP 边界 | [HFB-PS-1709](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md) | 第一阶段开发边界，不得逾越 |
| 上线准入标准 | [HFB-PS-1710](../17-Platform-Specifications/1710_Production_Readiness_Specification.md) | 生产环境准入，一票否决 |
| 学术研究最高依据 | [docs/16-research-framework/](../16-research-framework/) | 所有产品功能必须服务于研究框架定义的方向 |

## 快速入口

- **新成员 / 新 AI** → 先读 [0002 Constitution](0002-project-constitution.md)，再读 [0005 AI Protocol](0005_AI_Execution_Protocol.md)
- **开发前** → 查 Constitution §16 MVP 边界、Governance §7
- **上线前** → 查 Constitution §17、Governance §8
- **文档规范** → 查 [0004 Documentation Rules](0004-documentation-rules.md)