---
title: System Architecture
document_id: HFB-DGM-0001
version: 0.1.0
status: Draft
owner: Tech Lead
reviewer: —
effective_date: 2026-06-24
scope: Architecture
priority: P1
tags:
  - architecture
  - mermaid
  - c4
---

# 00 System Architecture — 六层系统架构图

---

> **版本:** V0.1
> **状态:** Draft
> **适用范围:** 技术团队
> **维护者:** 技术负责人

## 1. 六层架构总览

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'fontFamily': 'system-ui' }}}%%
graph TB
  subgraph L1["L1 接入层"]
    client["用户（学术研究者）"]
    nginx["Nginx 反向代理"]
    client --> nginx
  end

  subgraph L2["L2 应用层"]
    fastapi["FastAPI 应用服务器"]
    auth["认证模块"]
    nginx --> fastapi
    fastapi --> auth
  end

  subgraph L3["L3 领域层"]
    lit["文献管理服务"]
    ent["实体管理服务"]
    ver["版本管理服务"]
    search["搜索服务"]
    fastapi --> lit
    fastapi --> ent
    fastapi --> ver
    fastapi --> search
  end

  subgraph L4["L4 AI 层"]
    rag["RAG 问答引擎"]
    graphrag["GraphRAG 推理引擎"]
    ner["NER 实体识别"]
    emb["Embedding 服务"]
    lit --> rag
    ent --> graphrag
    lit --> ner
    lit --> emb
  end

  subgraph L5["L5 数据层"]
    pg[("PostgreSQL\n关系数据")]
    vec[("pgvector\n向量存储")]
    neo[("Neo4j\n图存储")]
    cache[("Redis\n缓存")]
    lit --> pg
    ent --> pg
    ver --> pg
    rag --> vec
    graphrag --> neo
    ner --> pg
    emb --> vec
    fastapi --> cache
  end

  subgraph L6["L6 基础设施层"]
    docker["Docker 容器"]
    ci["GitHub Actions CI/CD"]
    monitor["监控 & 日志"]
    backup["备份系统"]
    docker --> pg
    docker --> neo
    ci --> docker
    monitor --> docker
    backup --> pg
  end
```

## 2. 层级职责

| 层 | 名称 | 职责 | 对外接口 | 依赖 |
|---|---|---|---|---|
| L1 | 接入层 | HTTPS 终止、路由、限流、静态资源 | 80/443 | — |
| L2 | 应用层 | REST API、请求验证、认证授权 | `/api/v1/*` | L1 |
| L3 | 领域层 | 业务逻辑、领域规则、数据转换 | Python 模块 | L5 |
| L4 | AI 层 | RAG、GraphRAG、NER、Embedding | Python 模块 | L3, L5 |
| L5 | 数据层 | 持久化、查询、缓存 | 5432/7687/7474/6379 | L6 |
| L6 | 基础设施层 | 部署、CI/CD、监控、备份 | — | — |

## 3. 关键数据流

### RAG 问答流

```
用户提问 → L2(API) → L4(RAG) → L5(pgvector检索) → L4(LLM生成) → L2 → 用户
```

### 实体关系推理流

```
用户提问 → L2(API) → L4(GraphRAG) → L5(Neo4j子图) → L4(LLM推理) → L2 → 用户
```

### 文献导入流

```
管理员 → L2(API) → L3(文献服务) → L5(PostgreSQL) → L4(Embedding) → L5(pgvector)
```

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
