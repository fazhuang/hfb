---
title: Geography Knowledge Model
document_id: HFB-DOM-0807
version: 1.1.0
status: Approved
owner: Academic Committee
reviewer: Chief Knowledge Architect
effective_date: 2026-06-24
scope: Geography Knowledge Model
priority: P0
related_documents:
  - HFB-DOM-0801 Person Knowledge Model
  - HFB-DOM-0802 Book Knowledge Model
  - HFB-DOM-0803 Version Knowledge Model
  - HFB-DOM-0806 Chronology Knowledge Model
  - HFB-DAT-0302 Ontology Specification
  - HFB-PS-1709 MVP Implementation Specification
---

# Geography Knowledge Model
## 地域知识模型

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的地域知识建模标准。
>
> **Geography（地域）不是简单的地点信息，而是平台数字人文研究的一级知识对象。**
>
> 平台不仅研究"在哪里"，更研究"知识如何传播""版本如何流传""学术如何演化""地域如何影响医学思想形成"。

---

# 第一章 建设目标

建立统一地域知识模型，实现：

- 地域标准化表达
- 古今地名统一映射
- 学术传播路径重建
- 地域流派分析
- 空间知识图谱构建
- AI 地域推理

平台将 Geography 定义为一级知识实体。

---

# 第二章 Geography 定义

Geography：

表示具有明确历史、文化或学术意义的空间实体。

包括：

- 国家
- 行政区
- 郡县
- 州府
- 城市
- 山川
- 古道
- 学术机构所在地
- 古籍收藏地
- 医学传播地

不仅表示地理位置，更表示文化与知识传播空间。

---

# 第三章 地域层级

统一层级：

```text
Country
    ↓
Province
    ↓
City
    ↓
County
    ↓
Historic Place
    ↓
Specific Site
```

支持现代行政区与历史行政区并存。

---

# 第四章 唯一标识

统一：

UUID v7。

同时维护：

```text
place_code
```

例如：

```text
PLACE-000001
```

所有地点永久唯一。

---

# 第五章 基础字段

统一字段：

| 字段 | 说明 |
|------|------|
| id | UUID |
| place_code | 地域编码 |
| standard_name | 标准名称 |
| historical_name | 历史名称 |
| aliases | 别称 |
| latitude | 纬度 |
| longitude | 经度 |
| administrative_level | 行政层级 |
| historical_period | 所属历史时期 |
| metadata_id | Metadata |

---

# 第六章 古今地名映射

平台必须建立：

```text
古地名

↓

现代行政区

↓

GIS 坐标
```

例如：

| 古称 | 今称 |
|------|------|
| 安定郡 | 甘肃平凉地区 |
| 京兆 | 陕西西安 |
| 长安 | 西安 |

支持一对多映射。

---

# 第七章 地域分类

统一分类：

```text
Birth Place（出生地）

Residence（居住地）

Academic Center（学术中心）

Book Preservation（藏书地）

Publication（刊刻地）

Research Institution（研究机构）

Transmission Node（传播节点）

Cultural Region（文化区域）
```

支持多重身份。

---

# 第八章 皇甫谧地域模型

重点记录：

- 出生地
- 活动地
- 任职地
- 著述地
- 墓葬地
- 后世纪念地

形成皇甫谧空间活动轨迹。

---

# 第九章 《针灸甲乙经》传播模型

建立：

Transmission Route。

包括：

```text
成书地

↓

刊刻地

↓

收藏地

↓

整理地

↓

数字化机构
```

形成版本传播网络。

---

# 第十章 地域传承模型（平台特色）

建立：

Regional Inheritance Model。

分析：

- 哪些地区研究最活跃
- 哪些地区形成特色学派
- 哪些地区长期持续研究
- 哪些地区贡献重大成果

这是平台特色能力之一。

---

# 第十一章 学术机构模型

关联：

Institution。

包括：

- 大学
- 科研院所
- 博物馆
- 图书馆
- 医学院
- 中医院

建立机构地理网络。

---

# 第十二章 地域研究热点

平台统计：

- 地区论文数量
- 学者数量
- 引文数量
- 项目数量
- 国际合作

自动生成：

Regional Academic Heatmap。

---

# 第十三章 地域传播路径

建立：

Knowledge Transmission Path。

例如：

```text
皇甫谧

↓

西晋

↓

敦煌

↓

日本

↓

现代国际研究
```

支持传播路径可视化。

---

# 第十四章 地图模型

统一支持：

- GIS 地图
- 历史地图
- 学术地图
- 热力图
- 流向图
- 聚类图

支持时间维度联动。

---

# 第十五章 AI 地域推理

AI 支持：

- 地域传播分析
- 学派形成分析
- 学术影响范围分析
- 地域差异分析

回答必须引用：

论文、

版本、

人物、

机构。

---

# 第十六章 Graph 建模

Place 节点允许连接：

- Person
- Book
- Version
- Institution
- Paper
- Event
- Dynasty

形成空间知识图谱。

---

# 第十七章 地域特色分析（平台创新能力）

平台建立：

Regional Characteristics Engine。

自动分析：

- 地域研究特色
- 学术优势
- 高频主题
- 代表人物
- 核心机构
- 国际影响力

支持 AI 自动生成：

《××地区皇甫谧研究报告》。

---

# 第十八章 《针灸甲乙经》专项建设

建立：

## Version Geography

不同版本：

空间分布图。

---

## Research Geography

全球研究机构分布。

---

## Citation Geography

引用来源地域分布。

---

## Academic School Geography

学派地域演化图。

---

## International Communication

国际传播路径。

重点覆盖：

- 中国
- 日本
- 韩国
- 欧洲
- 北美

---

# 第十九章 数据质量

目标：

| 指标 | 标准 |
|------|------|
| 地名标准化率 | 100% |
| 古今映射率 | ≥95% |
| GIS 覆盖率 | ≥95% |
| 地域关系完整率 | ≥95% |
| AI 地域分析准确率 | ≥98% |

---

# 第二十章 Geography 红线

禁止：

- 古今地名混用
- 无坐标地点
- 无来源地域信息
- AI 编造传播路线
- 人工推测学派分布

违反任一项不得进入正式知识库。

---

# 第二十一章 本项目重点创新方向

本平台重点建设以下四项数字人文创新能力：

## 一、地域传承特色识别

自动识别：

论文是否体现地域特色。

---

## 二、地域传播路径重建

自动重建：

《针灸甲乙经》的传播路线。

---

## 三、地域学派分析

自动识别：

各地区研究流派及代表人物。

---

## 四、国际传播研究

自动生成：

《皇甫谧医学思想国际传播分析报告》。

---

# 第二十二章 修订规则

修改 Geography 模型必须同步更新：

- Chronology Knowledge Model
- Academic Citation Model
- Knowledge Graph Model
- GraphRAG Specification
- Visualization Standard

未经学术委员会批准不得修改。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.0.0 | 2026-06-24 | 首版发布，作为平台地域知识模型统一规范。 |