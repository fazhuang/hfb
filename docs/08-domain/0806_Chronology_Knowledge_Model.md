---
title: Chronology Knowledge Model
document_id: HFB-DOM-0806
version: 1.1.0
status: Approved
owner: Academic Committee
reviewer: Chief Knowledge Architect
effective_date: 2026-06-24
scope: Chronology Knowledge Model
priority: P0
related_documents:
  - HFB-DOM-0801 Person Knowledge Model
  - HFB-DOM-0802 Book Knowledge Model
  - HFB-DOM-0803 Version Knowledge Model
  - HFB-DOM-0805 Paper Knowledge Model
  - HFB-DAT-0302 Ontology Specification
  - HFB-PS-1709 MVP Implementation Specification
---

# Chronology Knowledge Model
## 时间知识模型

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的时间知识建模标准。
>
> **Chronology（时间）不是普通日期字段，而是数字人文研究中的一级知识对象。**
>
> 平台所有人物活动、古籍成书、版本流传、学术发展、地域传播均建立统一时间知识体系。

---

# 第一章 建设目标

建立统一时间知识模型，实现：

- 历史时间标准化
- 多历法统一表达
- 朝代与年号映射
- 学术事件关联
- AI 时间推理
- 知识图谱时序分析

---

# 第二章 Chronology 定义

Chronology：

表示具有明确历史意义的时间实体。

包括：

- 年
- 月
- 日（适用时）
- 朝代
- 年号
- 历史时期
- 时间区间
- 学术阶段

不仅表示日期，更表示历史语义。

---

# 第三章 时间层级

统一模型：

```text
Era（历史时期）
      ↓
Dynasty（朝代）
      ↓
Reign Title（年号）
      ↓
Year（年份）
      ↓
Month（月）
      ↓
Day（日）
```

支持不同精度的数据。

---

# 第四章 唯一标识

统一：

UUID v7。

同时维护：

```text
chrono_code
```

例如：

```text
TIME-000001
```

---

# 第五章 时间字段

统一字段：

| 字段 | 说明 |
|------|------|
| id | UUID |
| chrono_code | 时间编码 |
| dynasty | 朝代 |
| reign_title | 年号 |
| western_year | 公元纪年 |
| lunar_year | 干支纪年（适用时） |
| start_date | 起始时间 |
| end_date | 结束时间 |
| certainty | 时间可信度 |

---

# 第六章 时间表达

平台支持：

- 公元纪年
- 朝代纪年
- 年号纪年
- 干支纪年
- 模糊时间
- 时间区间

例如：

```text
西晋初年

约公元282年

太康三年

三国晚期
```

均可规范表达。

---

# 第七章 不确定时间

统一采用可信度模型：

| 类型 | 示例 |
|------|------|
| Exact | 公元282年 |
| Approximate | 约282年 |
| Before | 282年前 |
| After | 282年后 |
| Range | 280—285年 |
| Unknown | 不详 |

支持历史文献的不确定表达。

---

# 第八章 时间实体关系

Chronology 可关联：

- Person
- Book
- Version
- Paper
- Event
- Place
- Institution

形成时间知识网络。

---

# 第九章 历史事件

建立：

Historical Event。

例如：

- 皇甫谧出生
- 《针灸甲乙经》成书
- 某版本刊刻
- 学术会议召开
- 论文发表

事件均关联时间。

---

# 第十章 人物时间轴

自动生成：

Person Timeline。

包括：

- 生卒
- 任职
- 著述
- 学术活动

支持跨人物比较。

---

# 第十一章 古籍时间轴

Book Timeline：

展示：

- 成书
- 注释
- 刊刻
- 校勘
- 数字化

形成古籍生命周期。

---

# 第十二章 版本时间轴

Version Timeline：

展示：

- 刊刻
- 收藏
- 流传
- 点校
- 数字化

支持版本演化分析。

---

# 第十三章 学术时间轴

Research Timeline：

展示：

- 皇甫谧研究发展
- 《针灸甲乙经》研究热点
- 地域研究变化
- 国际传播历程

支持年度统计。

---

# 第十四章 AI 时间推理

AI 支持：

- 时间排序
- 时间跨度分析
- 同期人物分析
- 朝代推理
- 历史背景分析

所有结论必须引用来源。

---

# 第十五章 Graph 建模

Chronology 节点允许关联：

- Person
- Book
- Version
- Event
- Place
- Paper

支持时序知识图谱。

---

# 第十六章 检索模型

支持：

- 朝代
- 年号
- 公元年份
- 时间区间
- 历史时期

支持自然语言：

例如：

> "西晋时期关于针灸的重要著作"

---

# 第十七章 《皇甫谧》专项建设

建立：

## 皇甫谧时间轴

完整展示：

- 生平
- 著述
- 学术活动

---

## 《针灸甲乙经》时间轴

展示：

- 成书
- 流传
- 刊刻
- 校勘
- 数字化

---

## 皇甫谧研究时间轴

统计：

近现代研究成果的发展历程。

---

# 第十八章 数据质量

目标：

| 指标 | 标准 |
|------|------|
| 时间标准化率 | 100% |
| 朝代映射率 | 100% |
| 年号映射率 | 100% |
| 时间关联率 | ≥95% |
| AI 时间推理准确率 | ≥98% |

---

# 第十九章 Chronology 红线

禁止：

- 混用时间格式
- 无来源时间
- 人工推测年代
- AI 编造历史时间
- 删除历史记录

违反任一项不得进入正式知识库。

---

# 第二十章 修订规则

修改 Chronology 模型必须同步更新：

- Geography Knowledge Model
- Knowledge Graph Model
- Academic Citation Model
- GraphRAG Specification

未经学术委员会批准不得修改。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.0.0 | 2026-06-24 | 首版发布，作为平台时间知识模型统一规范。 |