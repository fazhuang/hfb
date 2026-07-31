---
title: AI Academic Review Standard
document_id: HFB-AI-0405
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: AI Academic Services
priority: P0
related_documents:
  - HFB-GOV-0002 Project Constitution
  - HFB-GOV-0005 AI Execution Protocol
  - HFB-AI-0401 AI Engineering Standard
  - HFB-AI-0402 RAG Specification
  - HFB-DAT-0301 Data Standard Specification
  - HFB-DAT-0303 Metadata Standard
  - HFB-PS-1705 AI Research Workspace Specification
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
---

# AI Academic Review Standard

## AI 学术审核规范

> 本规范定义平台 AI 输出内容的学术审核标准。
>
> 平台定位为数字人文研究平台，AI 只能作为研究辅助工具，不得代替学术研究本身。
>
> **任何 AI 输出均必须接受本规范约束。**

---

# 第一章 制定目标

建立统一 AI 学术审核体系，确保：

- 学术真实性
- 数据可追溯
- 引文可验证
- 观点可区分
- AI 可解释
- 研究可复现

---

# 第二章 学术原则

平台坚持以下原则：

## Principle 1

Evidence First

证据优先。

所有结论必须具有证据。

---

## Principle 2

Citation First

引用优先。

所有引用必须标明来源。

---

## Principle 3

Human Review Required

重要研究成果必须经过人工审核。

AI 不拥有最终学术解释权。

---

## Principle 4

Version Traceability

所有 AI 输出必须能够定位：

- 数据版本
- Prompt 版本
- 模型版本

---

## Principle 5

Transparent Reasoning

AI 推理过程必须可解释。

不得输出：

"模型认为……"

而不给出依据。

---

# 第三章 AI 输出等级

平台 AI 输出划分为四级。

## Level A

Information Retrieval

信息检索。

仅返回资料。

无需推理。

---

## Level B

Knowledge Organization

知识整理。

允许：

分类。

归纳。

统计。

不得形成学术结论。

---

## Level C

Research Assistance

研究辅助。

允许：

文献综述。

观点对比。

版本比较。

必须：

引用全部来源。

---

## Level D

Academic Suggestion

研究建议。

仅提供：

研究方向。

争议分析。

后续阅读建议。

不得：

替代学术观点。

---

# 第四章 AI 输出组成

所有回答必须包含：

```text
Answer

↓

Evidence

↓

Citation

↓

Confidence

↓

Limitations

↓

Metadata
```

缺少任意部分：

不得发布。

---

# 第五章 Evidence（证据）

证据来源：

仅允许：

- 古籍原文
- 学术论文
- 出版专著
- 官方数据库
- 经审核图片
- 已审核知识库

禁止：

网络转载。

论坛。

博客。

未审核 AI 输出。

---

# 第六章 Citation（引用）

统一引用格式：

古籍：

> 《针灸甲乙经》（人民卫生出版社点校本），卷三，第十二节。

论文：

> 作者，题目，期刊，年份，DOI。

图片：

> 图片名称，馆藏单位，编号。

引用必须可定位。

---

# 第七章 Confidence（可信度）

统一评分：

| 等级 | 分值       |
| ---- | ---------- |
| A    | ≥0.95      |
| B    | 0.90～0.94 |
| C    | 0.80～0.89 |
| D    | <0.80      |

低于：

0.80

必须提示：

可信度较低。

---

# 第八章 AI 观点规范

AI 必须区分：

事实（Fact）

观点（Opinion）

推测（Hypothesis）

不得混写。

例如：

```
事实：

……

观点：

……

推测：

……
```

---

# 第九章 学术争议处理

遇到：

不同版本。

不同学派。

不同研究观点。

AI：

必须：

全部展示。

不得：

自行判断正确答案。

---

# 第十章 多版本原则

涉及：

《针灸甲乙经》

必须说明：

使用版本。

例如：

宋刻本。

明刻本。

人民卫生出版社版。

现代整理版。

禁止：

不同版本混用。

---

# 第十一章 AI 引文检查

所有 AI 输出：

自动经过：

Citation Checker。

检查：

- 来源是否存在；
- 引用是否完整；
- Metadata 是否一致；
- DOI 是否有效（适用于现代论文）。

---

# 第十二章 学术审核流程

统一流程：

```text
AI Output

↓

Automatic Validation

↓

Citation Check

↓

Human Review

↓

Publish
```

未经 Human Review：

不得进入正式知识库。

---

# 第十三章 学术伦理

AI：

不得：

- 编造古籍内容；
- 编造人物关系；
- 编造历史事件；
- 编造参考文献；
- 编造 DOI；
- 编造页码；
- 编造研究成果。

发现：

无法回答。

必须：

明确说明。

---

# 第十四章 可解释性

AI 必须能够解释：

- 为什么引用此文献；
- 为什么选择此版本；
- 为什么推荐此论文；
- 为什么形成当前回答。

禁止：

黑盒推理。

---

# 第十五章 审计要求

所有 AI 输出：

记录：

- Prompt Version
- Model Version
- Context Version
- Retrieval Log
- Citation Log

保存：

不少于五年。

---

# 第十六章 学术质量指标

| 指标            | 标准 |
| --------------- | ---- |
| Citation 完整率 | 100% |
| Evidence 覆盖率 | 100% |
| AI 可解释率     | 100% |
| 来源可追溯率    | 100% |
| 幻觉率          | <1%  |

---

# 第十七章 AI 学术红线

禁止：

- 无来源回答；
- AI 编造引用；
- AI 编造古籍内容；
- AI 编造研究观点；
- AI 修改正式学术数据；
- AI 自动发布研究成果。

违反任一项：

立即停止服务。

---

# 第十八章 修订规则

新增：

审核流程。

评分规则。

引用规范。

必须同步更新：

- AI Engineering Standard
- RAG Specification
- Prompt Engineering Guide
- Context Package

---

# 修订记录

| Version | Date       | Description                              |
| ------- | ---------- | ---------------------------------------- |
| 1.1.0   | 2026-06-25 | 更新related_documents                    |
| 1.0.0   | 2026-06-24 | 首版发布，作为平台 AI 学术审核最高规范。 |
