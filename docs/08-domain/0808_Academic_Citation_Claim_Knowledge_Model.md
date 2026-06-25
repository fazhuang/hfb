---
title: Academic Citation & Claim Knowledge Model
document_id: HFB-DOM-0808
version: 1.1.0
status: Approved
owner: Academic Committee
reviewer: Chief Knowledge Architect
effective_date: 2026-06-24
scope: Academic Citation, Evidence & Claim Knowledge Model
priority: P0
related_documents:
  - HFB-DOM-0805 Paper Knowledge Model
  - HFB-DOM-0804 Passage Knowledge Model
  - HFB-DOM-0807 Geography Knowledge Model
  - HFB-AI-0403 GraphRAG Specification
  - HFB-SEC-0703 Privacy & Data Governance Standard
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-RF-1609 Academic Citation Network Research Framework
---

# Academic Citation & Claim Knowledge Model
## 学术引文与学术观点知识模型

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的**学术观点（Claim）—证据（Evidence）—引文（Citation）**知识模型。
>
> **这是整个平台最具学术价值的模型之一。**
>
> 平台不仅保存论文，更保存论文中的观点、证据链、争议与学术共识，使 AI 能够回答"为什么"，而不仅是"是什么"。

---

# 第一章 建设目标

建立现代数字人文学术知识体系，实现：

- 学术观点结构化
- 引文标准化
- 证据链管理
- 学术争议分析
- 学术共识分析
- AI 可解释推理

---

# 第二章 核心对象

平台建立四类一级对象：

```text
Paper

↓

Claim（观点）

↓

Evidence（证据）

↓

Citation（引文）
```

所有 AI 推理均围绕四类对象展开。

---

# 第三章 Claim 定义

Claim：

表示论文提出的一个独立学术观点。

例如：

> 皇甫谧《针灸甲乙经》系统整理了《黄帝内经》《明堂经》等早期针灸文献。

这是一个 Claim，而不是论文本身。

---

# 第四章 Claim 唯一标识

统一：

UUID v7。

同时维护：

```text
claim_code
```

例如：

```text
CLAIM-000001
```

Claim 是平台一级知识实体。

---

# 第五章 Claim 字段

统一字段：

| 字段 | 说明 |
|------|------|
| id | UUID |
| claim_code | 观点编号 |
| title | 观点标题 |
| statement | 完整观点 |
| confidence | 可信度 |
| status | 学术状态 |
| paper_id | 来源论文 |
| metadata_id | Metadata |

---

# 第六章 学术状态

统一：

```text
Established（共识）

Supported（支持）

Disputed（争议）

Hypothesis（假说）

Deprecated（已否定）
```

AI 必须区分不同状态。

---

# 第七章 Evidence 模型

Evidence：

表示支持或反驳 Claim 的证据。

来源包括：

- 古籍
- 条文
- 论文
- 校勘
- 图像
- 文物
- 出土资料
- 官方数据库

Evidence 必须可追溯。

---

# 第八章 Evidence 字段

统一：

| 字段 | 内容 |
|------|------|
| evidence_id | UUID |
| type | 类型 |
| source | 来源 |
| quotation | 引文 |
| location | 定位信息 |
| confidence | 可信度 |

---

# 第九章 Citation 模型

Citation：

支持：

- Book
- Version
- Passage
- Paper
- Figure
- Dataset

统一生成：

- GB/T 7714
- APA
- MLA
- Chicago
- BibTeX
- RIS

---

# 第十章 学术争议模型

建立：

Academic Debate。

例如：

```text
观点A

↓

支持证据

↓

反对观点

↓

反对证据

↓

当前学术共识
```

支持多个学派共存。

---

# 第十一章 学术共识模型

平台自动分析：

```text
Claim

↓

Supporting Papers

↓

Supporting Evidence

↓

Consensus Score
```

形成：

Consensus Index。

---

# 第十二章 引文传播模型

建立：

Citation Network。

展示：

- 谁引用谁
- 哪部古籍被引用最多
- 哪位学者影响最大
- 哪一观点传播最快

形成引文知识图谱。

---

# 第十三章 地域观点分析

结合 Geography：

自动分析：

- 甘肃观点
- 陕西观点
- 日本观点
- 韩国观点
- 欧洲观点

比较不同地区研究特点。

---

# 第十四章 时间演化

结合 Chronology：

展示：

```text
观点提出

↓

学界讨论

↓

形成争议

↓

逐步共识

↓

最新研究
```

形成观点生命周期。

---

# 第十五章 AI 学术推理

AI 回答必须展示：

```text
问题

↓

Claim

↓

Evidence

↓

Citation

↓

Counter Evidence（如存在）

↓

Consensus

↓

AI 综合分析
```

AI 不得跳过证据链。

---

# 第十六章 Knowledge Graph

建立：

```text
Person

↓

Paper

↓

Claim

↓

Evidence

↓

Passage

↓

Book

↓

Version
```

形成多层知识图谱。

---

# 第十七章 《皇甫谧》专项建设

建立：

## 皇甫谧观点库

收录：

全部代表性学术观点。

---

## 《针灸甲乙经》争议库

记录：

所有重要争议。

例如：

- 成书时间
- 成书来源
- 文本来源
- 编纂方式

---

## 校勘证据库

建立：

Evidence Database。

---

## 学术共识数据库

自动计算：

Consensus Score。

---

## AI 学术综述

自动生成：

- 国内研究现状
- 国际研究现状
- 主要争议
- 最新进展
- 未来方向

全部引用来源。

---

# 第十八章 数据质量

目标：

| 指标 | 标准 |
|------|------|
| Claim 来源率 | 100% |
| Evidence 可追溯率 | 100% |
| Citation 标准化率 | 100% |
| AI 引证完整率 | ≥99% |
| 共识分析准确率 | ≥95% |

---

# 第十九章 Academic 红线

禁止：

- AI 编造 Claim
- 无 Evidence 的 Claim
- 无 Citation 的 AI 回答
- 删除争议观点
- 隐藏反对证据
- 修改引用内容

违反任一项不得上线。

---

# 第二十章 平台核心创新能力

平台最终形成四项核心能力：

## 1. AI 学术问答

回答全部可引用。

---

## 2. AI 学术综述

自动生成综述。

---

## 3. AI 学术争议分析

自动比较：

不同观点。

---

## 4. AI 学术共识分析

自动判断：

当前主流观点。

这是国内数字人文平台的重要创新能力。

---

# 第二十一章 修订规则

修改 Academic Citation 模型必须同步更新：

- Knowledge Graph Model
- Paper Knowledge Model
- GraphRAG Specification
- AI Prompt Standard
- AI Evaluation Standard

未经学术委员会批准不得修改。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.0.0 | 2026-06-24 | 首版发布，作为平台学术观点、证据与引文知识模型统一规范。 |