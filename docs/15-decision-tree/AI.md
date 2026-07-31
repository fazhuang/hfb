---
title: 'Decision Tree — AI'
version: '1.0'
status: 'Accepted'
owner: 'AI Lead'
last_updated: '2026-06-24'
related_adr: ['ADR-0006', 'ADR-0007']
---

# Decision Tree — AI

为什么选择自研 Pipeline 而非现成框架。

---

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'fontFamily': 'system-ui' }}}%%
graph TD
  Q1["AI 问答架构？"]
  Q1 -->|"事实型问答\n查段落"| A1["RAG ✅"]
  Q1 -->|"推理型问答\n查关系"| A2["GraphRAG ✅"]

  Q2["RAG 用什么框架？"]
  Q2 -->|"可控\n可溯源"| A2A["自研 Pipeline ✅"]
  Q2 -->|"快速原型"| A2B["LangChain ❌\n黑箱/溯源难"]
  Q2 -->|"微软方案"| A2C["MS GraphRAG ❌\n偏英文"]

  Q3["三层递进 \n为什么？"]
  Q3 -->|"基础不稳\n不盖楼"| A3A["L1→L2→L3 ✅\n每层稳定后再启动下层"]
  Q3 -->|"一次性全做"| A3B["All-in ❌\n风险太高"]
```

## 决策路径

1. 两种问答需求（事实型 vs 推理型）→ 两条路径
2. 现成框架不可溯源 → 自研 Pipeline
3. 分层递进降低风险 → L1(RAG) 稳定后启动 L2(GraphRAG)
4. 古籍领域特殊 → 需要自训练的 NER 模型

## 相关 ADR

- ADR-0006 GraphRAG
- ADR-0007 Milvus

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
