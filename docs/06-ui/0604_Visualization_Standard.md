---
title: Visualization Standard
document_id: HFB-UI-0604
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product Designer
effective_date: 2026-06-24
scope: Academic Visualization
priority: P0
related_documents:
  - HFB-UI-0601 Design System
  - HFB-UI-0602 UI Component Standard
  - HFB-UI-0603 Academic Interaction Standard
  - HFB-DAT-0302 Ontology Specification
  - HFB-DAT-0304 Entity Specification
  - HFB-DAT-0305 Relation Specification
  - HFB-PS-1707 Visualization Knowledge Graph Specification
  - HFB-PS-1709 MVP Implementation Specification
---

# Visualization Standard

## 学术可视化规范

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的数据可视化体系。
>
> 本平台可视化的目标不是展示图表，而是帮助研究者理解知识结构、历史演化、学术传播与人物关系，促进知识发现（Knowledge Discovery）。

---

# 第一章 建设目标

平台可视化必须实现：

- 知识可见（Knowledge Visibility）
- 关系可解释（Explainability）
- 历史可追溯（Traceability）
- 学术可分析（Researchability）
- 数据可探索（Explorability）

任何图表必须服务于学术研究。

---

# 第二章 可视化原则

遵循：

- Evidence First
- Academic First
- Simplicity First
- Consistency First

禁止：

- 为美观而设计图表
- 无数据来源图表
- 无交互图表

---

# 第三章 可视化分类

平台统一支持八类可视化：

| 类型                  | 用途         |
| --------------------- | ------------ |
| Timeline              | 时间演化     |
| Knowledge Graph       | 知识关系     |
| Version Tree          | 版本谱系     |
| Geographic Map        | 地域传播     |
| Citation Network      | 引文网络     |
| Academic Network      | 学术合作网络 |
| Statistical Dashboard | 数据统计     |
| Comparative View      | 对照分析     |

---

# 第四章 时间轴（Timeline）

用于展示：

- 皇甫谧生平
- 《针灸甲乙经》版本演化
- 学术传播历程
- 重大历史事件
- 现代研究发展

支持：

- 年代缩放
- 朝代切换
- 多事件叠加
- 人物筛选

---

# 第五章 知识图谱（Knowledge Graph）

Graph 节点统一来源于：

- Person
- Book
- Version
- Passage
- Paper
- Institution
- Place
- Event

边统一来源于：

Relation。

禁止：

手工绘制关系。

---

# 第六章 版本谱系图

Version Tree：

展示：

```text
原始版本
      │
      ├──宋刻本
      │
      ├──明刻本
      │
      ├──清刻本
      │
      └──现代整理版
```

支持：

- 分支查看
- 差异比较
- Metadata 查看

---

# 第七章 地域传播图

展示：

- 皇甫谧活动地点
- 古籍流传路线
- 学术机构分布
- 地域研究热点

地图必须支持：

- 时间筛选
- 图层切换
- 数据来源查看

---

# 第八章 引文网络

展示：

论文之间：

```text
Paper A

↓

Paper B

↓

Paper C
```

支持：

- 被引次数
- 引用路径
- 研究热点

所有节点均可进入详情页。

---

# 第九章 学术关系网络

展示：

- 学者合作
- 导师关系
- 学术传承
- 研究机构合作

支持：

- 多跳探索
- 时间过滤
- 学科过滤

---

# 第十章 数据统计

Dashboard：

展示：

- 人物数量
- 古籍数量
- 版本数量
- OCR 完成率
- 论文数量
- 引文数量
- AI 检索次数

统计数据必须实时更新。

---

# 第十一章 对照分析

支持：

- 古籍版本比较
- 人物资料比较
- 学术观点比较
- OCR 前后比较

采用：

左右布局。

禁止：

覆盖式比较。

---

# 第十二章 数据来源

所有图表必须提供：

```text
数据来源

↓

更新时间

↓

数据范围

↓

统计规则
```

点击即可查看详情。

---

# 第十三章 交互规范

所有可视化支持：

- Hover
- Click
- Drill Down
- Zoom
- Filter
- Export

禁止：

静态图片替代动态图。

---

# 第十四章 图例规范

统一：

- 节点颜色
- 边颜色
- 图标
- 图例位置

不同图表保持一致。

---

# 第十五章 配色规范

颜色来源：

Design System。

例如：

| 类型 | 颜色          |
| ---- | ------------- |
| 人物 | Academic Blue |
| 古籍 | Vermilion     |
| 地点 | Emerald Green |
| 机构 | Purple        |
| AI   | Indigo        |
| 系统 | Gray          |

不得随意指定颜色。

---

# 第十六章 性能规范

目标：

| 指标           | 标准   |
| -------------- | ------ |
| Graph 首次加载 | ≤2 秒  |
| Timeline 加载  | ≤1 秒  |
| 地图渲染       | ≤2 秒  |
| 节点展开       | ≤300ms |

大规模图谱采用：

增量加载。

---

# 第十七章 导出规范

支持导出：

- PNG
- SVG
- PDF
- JSON
- GraphML（规划）

导出必须保留图例和数据来源。

---

# 第十八章 学术可信性

所有图表必须：

- 可追溯
- 可引用
- 可验证
- 可复现

禁止：

AI 自动生成无来源关系图。

---

# 第十九章 可视化红线

禁止：

- 无来源图表
- 无图例图表
- 手工绘制知识关系
- 娱乐化动画
- 误导性比例
- 隐藏数据来源

违反任一项不得上线。

---

# 第二十章 修订规则

修改可视化规范必须同步更新：

- Design System
- Academic Interaction Standard
- GraphRAG Specification
- Figma Prototype
- Visualization Component Library

未经批准不得修改。

---

# 修订记录

| Version | Date       | Description                            |
| ------- | ---------- | -------------------------------------- |
| 1.1.0   | 2026-06-25 | 更新related_documents                  |
| 1.0.0   | 2026-06-24 | 首版发布，作为平台学术可视化统一规范。 |
