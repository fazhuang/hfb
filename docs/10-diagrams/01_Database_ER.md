---
title: Database ER Diagram
document_id: HFB-DGM-0002
version: 0.1.0
status: Draft
owner: Tech Lead
reviewer: —
effective_date: 2026-06-24
scope: Data Architecture
priority: P1
tags:
  - database
  - er
  - mermaid
---

# 01 Database ER — 核心数据库 ER 图

---

> **版本:** V0.1
> **状态:** Draft
> **适用范围:** 后端 · 数据 · AI
> **维护者:** 技术负责人

## 1. 核心 ER 图

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'fontFamily': 'system-ui' }}}%%
erDiagram
  Person ||--o{ Relation : source
  Person ||--o{ Relation : target
  Book ||--o{ Version : has
  Version ||--o{ Chapter : contains
  Chapter ||--o{ Passage : contains
  Passage ||--o{ Relation : "refers_to"
  Passage }o--o{ Entity : mentions
  Entity ||--o{ Relation : source
  Entity ||--o{ Relation : target
  Paper }o--o{ Entity : cites
  User ||--o{ Passage : imports
  User ||--o{ Relation : verifies

  Person {
    uuid id PK
    string name
    string name_zh
    int birth_year
    int death_year
    string courtesy_name
    string dynasty
    text biography
  }

  Book {
    uuid id PK
    string title
    string title_zh
    string author
    string dynasty
    string genre
    string year_range
  }

  Version {
    uuid id PK
    uuid book_id FK
    string version_type
    string version_name
    string era
    string repository
  }

  Chapter {
    uuid id PK
    uuid version_id FK
    int chapter_number
    string title
    int sort_order
  }

  Passage {
    uuid id PK
    uuid chapter_id FK
    int position
    string source_type
    uuid source_passage_id FK
    text content_original
    text content_modern
    text annotation
  }

  Paper {
    uuid id PK
    string title
    string authors
    int year
    string journal
    string doi
  }

  Entity {
    uuid id PK
    string entity_type
    string name
    string name_zh
    jsonb attributes
  }

  Relation {
    uuid id PK
    uuid source_entity_id FK
    uuid target_entity_id FK
    string relation_type
    uuid source_passage_id FK
    float confidence
    bool is_verified
    uuid verified_by FK
  }

  User {
    uuid id PK
    string username
    string email
    string role
    string password_hash
  }
```

## 2. 实体说明

| 实体 | 表名 | 说明 | 关键字段 |
|---|---|---|---|
| Person | `persons` | 历史/现代人物 | name, name_zh, birth_year, death_year, dynasty |
| Book | `books` | 古籍 | title, author, dynasty, genre |
| Version | `versions` | 书籍版本（底本/校本/注本） | version_type, version_name, era |
| Chapter | `chapters` | 版本内的章节 | chapter_number, title |
| Passage | `passages` | 最小文本单元 | content_original, content_modern, annotation |
| Paper | `papers` | 现代研究论文 | title, authors, year, doi |
| Entity | `entities` | 通用实体基表 | entity_type, name, attributes(JSONB) |
| Relation | `relations` | 实体间关系 | relation_type, confidence, is_verified |
| User | `users` | 学术用户 | username, email, role |

## 3. 关系说明

| 源 | 目标 | 关系类型 | 说明 |
|---|---|---|---|
| Book | Version | 1:N | 一部书有多个版本 |
| Version | Chapter | 1:N | 一个版本有多个章节 |
| Chapter | Passage | 1:N | 一个章节有多个段落 |
| Passage | Relation | 1:N | 关系可追溯到出处段落 |
| Entity | Relation | 1:N（源） | 一个实体作为关系起点 |
| Entity | Relation | 1:N（目标） | 一个实体作为关系终点 |
| Passage | Entity | M:N | 段落与实体间的提及关系 |
| User | Passage | 1:N | 记录导入者 |
| User | Relation | 1:N | 记录验证者 |
| Paper | Entity | M:N | 论文与实体的引用关系 |

## 4. 设计要点

- **Entity 是基表**：Person 继承 Entity，共享 id 空间。通过 `entity_type` 字段区分具体类型，通过 `attributes` JSONB 存储类型特有属性
- **Passage 是最小单元**：所有文本内容以 Passage 为单位存储，NLP 和 AI 处理在 Passage 粒度进行
- **Relation 可溯源**：每条 Relation 关联到一个 Passage，确保 AI 抽取的关系可以追溯到原文出处
- **Version 是核心抽象**：同一书籍的不同版本是独立的 Version 记录，通过 `version_type` 区分底本/校本/注本

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
