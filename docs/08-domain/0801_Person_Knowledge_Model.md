---
title: Person Knowledge Model
document_id: HFB-DOM-0801
version: 1.2.0
status: Approved
owner: Academic Committee
reviewer: Chief Knowledge Architect
effective_date: 2026-08-10
scope: Person Domain Model
priority: P0
related_documents:
  - HFB-DAT-0302 Ontology Specification
  - HFB-DAT-0304 Entity Specification
  - HFB-DAT-0305 Relation Specification
  - HFB-UI-0603 Academic Interaction Standard
  - HFB-AI-0402 RAG Specification
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-RF-1602 Huangfu Mi Studies Framework
  - HFB-ADR-0012 Huangfu Mi Domain Anchor Admission
---

# Person Knowledge Model

## 人物知识模型

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的人物知识建模标准。
>
> Person 是平台最核心的知识实体之一，也是知识图谱、RAG、GraphRAG、数字人文研究及 AI 推理的重要基础。

---

# 第一章 建设目标

建立统一的人物知识模型，实现：

- 人物信息标准化
- 多来源融合
- 学术关系表达
- 时空关联分析
- AI 可推理
- 知识图谱可扩展

平台所有人物均必须遵循本规范。

---

# 第二章 Person 定义

Person：

表示具有明确身份并能够建立学术关系的人物。

包括：

- 皇甫谧
- 医家
- 学者
- 注释者
- 校勘者
- 编者
- 作者
- 导师
- 研究者

Person 不是姓名，而是知识实体。

---

## 2.1 皇甫谧研究域准入与关系回溯规则

根据 [ADR-0012](file:///users/likeming/sites/hfb/docs/11-adr/ADR-0012-HuangfuMi-Domain-Anchor-Admission.md)，为防止知识图谱无序膨胀与 GraphRAG 语义漂移，所有进入平台的 Person 实体均须遵循严格的研究域准入与关系回溯规则。

### 2.1.1 唯一主锚点定位
固定 **皇甫谧** (`person:huangfu_mi` / `ENTITY-PER-0001`) 作为研究域全局唯一主锚点 (Primary Domain Anchor)。平台内所有 Person 实体及关系的准入合法性，均需基于其与主锚点的图拓扑可达性与学术关联度进行判定。

### 2.1.2 锚点可达性与步长约束 ($N \le 3$)
1. **证据链路径追溯**：每一个准入为 `verified`（已验证）状态的 Person 实体，必须具备至少一条可追溯至主锚点 `person:huangfu_mi` 的可靠古籍证据链路径。
2. **步长硬约束**：锚点可达路径步长必须满足 $N \le 3$（即在图拓扑中与主锚点连接的最短距离不超过 3 步）。
3. **`anchor_path` 预计算保存**：在实体审核发布（Publish）阶段，后台自动计算并持久化保存实体至主锚点的最短路径 `anchor_path`（例如：`["ENTITY-PER-0001", "REL-0023", "ENTITY-PER-0042"]`），避免在线检索时的漫游开销。
4. **无链实体处理**：凡无有效证据链追溯至主锚点或路径步长 $N > 3$ 的 Person 实体，一律置为 `pending`（待考）状态，禁止作为正式学术实体公开发布。

### 2.1.3 三态生命周期与状态变更约束
Person 实体与关系采用三态隔离生命周期：

- **`pending`（待考）**：新录入、人工草稿或暂未建立可靠主锚点证据链的实体。仅限研究员/管理员在特定“待考工作台”中受控检索与考据研讨。
- **`verified`（已验证）**：通过古籍证据校验、满足 $N \le 3$ 锚点可达性约束且通过学术审核的正式实体。全面对全局 RAG、GraphRAG 及前台视图开放。
- **`excluded`（排除）**：经学术考据认定为与皇甫谧及《针灸甲乙经》无关、伪作或被废弃的实体。全站硬隔离屏蔽。

**状态变更流转约束规则：**
1. **`pending` $\rightarrow$ `verified`**：当且仅当补充了有效的古籍证据链，校验存在 $N \le 3$ 的主锚点可达路径并预计算保存 `anchor_path`，且通过学术审核时，方可升级为 `verified`。
2. **`verified` $\rightarrow$ `pending`（动态降级）**：当支撑实体的古籍证据被撤销、标记失效或关联关系删除，导致其失去所有满足 $N \le 3$ 的主锚点可达路径时，系统自动触发降级机制，将其重置为 `pending`。
3. **`pending` / `verified` $\rightarrow$ `excluded`**：当学术考据确定实体与研究域彻底无关或属于错误建模时，由研究员/管理员手动标记为 `excluded`，强制屏蔽。

### 2.1.4 检索与 RAG 硬过滤约束
- **全局硬过滤屏蔽**：全局 RAG 向量检索、GraphRAG 子图漫游、API 导出及匿名/普通视图，必须在数据库与搜索引擎层面施加强制过滤（`status == 'verified'`），绝对禁止 `pending` 与 `excluded` 状态的数据泄漏至生成上下文。
- **特定工作台受控访问**：`pending` 数据仅在登录研究员与管理员的“待考工作台”（Pending Workbench）中提供显式过滤检索。

---

# 第三章 Person 生命周期

统一生命周期：

```text
Collect

↓

Verify

↓

Normalize

↓

Publish

↓

Maintain

↓

Archive
```

所有修改均保留历史版本。

---

# 第四章 Person 唯一标识

统一采用：

UUID v7。

同时维护：

```text
person_code
```

例如：

```text
PERSON-00000001
```

不得使用姓名作为唯一标识。

---

# 第五章 核心字段

Person 至少包含：

| 字段        | 说明                 |
| ----------- | -------------------- |
| id          | UUID                 |
| person_code | 人物编码             |
| name        | 标准姓名             |
| aliases     | 别名、字、号、谥号等 |
| gender      | 性别                 |
| birth_year  | 生年                 |
| death_year  | 卒年                 |
| dynasty     | 朝代                 |
| ethnicity   | 民族（适用时）       |
| occupation  | 身份/职业            |
| biography   | 生平简介             |
| metadata_id | 元数据关联           |

---

# 第六章 扩展字段

支持：

- 籍贯
- 活动地区
- 师承
- 学派
- 官职
- 爵位
- 医学流派
- 社会身份
- 研究方向（现代人物）

采用可扩展属性模型。

---

# 第七章 人物分类

统一分类：

```text
Ancient Person

Modern Scholar

Institution Member

Historical Figure

Medical Practitioner

Research Contributor
```

一个人物可属于多个分类。

---

# 第八章 时间属性

支持：

- 生卒年
- 活跃年代
- 朝代
- 年号
- 历史时期

支持：

不确定时间表达：

例如：

```text
约215年

三国时期

西晋初年
```

---

# 第九章 地理属性

支持关联：

- 出生地
- 活动地
- 任职地
- 著述地
- 墓葬地（适用时）

统一关联：

Place Entity。

禁止文本硬编码。

---

# 第十章 著作关系

Person 可关联：

- Book
- Paper
- Annotation
- Commentary
- Translation

关系必须标明角色：

```text
Author

Editor

Commentator

Translator

Compiler
```

---

# 第十一章 人物关系

支持：

- 师承
- 同门
- 合作者
- 家族
- 学术影响
- 引用关系
- 被研究关系

关系必须关联：

Evidence。

---

# 第十二章 学术影响

记录：

- 代表著作
- 学术贡献
- 医学贡献
- 后世评价
- 现代研究情况

支持：

引用来源。

---

# 第十三章 图片资源

支持关联：

- 肖像
- 石刻
- 雕像
- 手稿
- 文献照片

所有图片必须关联：

Metadata。

---

# 第十四章 时间轴

自动生成：

Person Timeline。

包括：

- 出生
- 求学
- 著述
- 任职
- 学术事件
- 卒年

时间轴数据来源可追溯。

---

# 第十五章 AI 表示

AI 检索 Person 时：

必须返回：

```text
人物

↓

基本信息

↓

代表著作

↓

学术关系

↓

引用来源

↓

可信度
```

不得返回未经验证信息。

---

# 第十六章 Graph 建模

Person 节点允许连接：

- Person
- Book
- Version
- Paper
- Place
- Institution
- Event

所有边必须：

具备 Relation Type。

---

# 第十七章 Metadata

每个 Person 必须关联：

- 来源
- 编辑记录
- 创建者
- 审核状态
- License
- 更新时间

Metadata 缺失不得发布。

---

# 第十八章 数据质量

目标：

| 指标            | 标准 |
| --------------- | ---- |
| Metadata 完整率 | 100% |
| 人物唯一性      | 100% |
| 来源完整率      | 100% |
| Graph 可连接率  | 100% |
| AI 可解释率     | 100% |

---

# 第十九章 Person 红线

禁止：

- 重复人物
- 无来源人物
- 无 Metadata
- 姓名作为主键
- AI 编造人物
- 未建立关系直接发布

违反任一项不得进入正式知识库。

---

# 第二十章 修订规则

修改 Person 模型必须同步更新：

- Ontology Specification
- Entity Specification
- Relation Specification
- Knowledge Graph Model
- RAG Specification

未经学术委员会批准不得修改。

---

# 修订记录

| Version | Date       | Description                              |
| ------- | ---------- | ---------------------------------------- |
| 1.0.0   | 2026-06-24 | 首版发布，作为平台人物知识模型统一规范。 |
| 1.2.0   | 2026-08-10 | 新增 2.1 节皇甫谧研究域准入与关系回溯规则，补充三态生命周期隔离与锚点可达性约束 (ADR-0012)。 |
