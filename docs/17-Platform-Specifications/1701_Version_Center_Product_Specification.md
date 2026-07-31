---
title: Version Center Product Specification
document_id: HFB-PS-1701
version: 1.0.0
status: Approved
owner: Product Committee
reviewer: Chief Product Architect
effective_date: 2026-06-24
scope: Version Center
priority: P0
related_documents:
  - HFB-RF-1604 Versionology Research Framework
  - HFB-DOM-0803 Version Knowledge Model
  - HFB-DOM-0804 Passage Knowledge Model
  - HFB-UI-0601 Design System
  - HFB-DEV-0504 API Design Standard
  - HFB-GOV-0001 Project Charter
  - HFB-PS-1709 MVP Implementation Specification
---

# Version Center Product Specification

## 版本中心产品规格书

> 本规格书定义《皇甫谧数字人文与中医经典智能研究平台》Version Center（版本中心）的产品定位、功能边界、信息架构、交互方式、AI 能力及验收标准。
>
> Version Center 是平台版本管理、版本比较、版本研究及版本知识图谱的核心业务模块。

---

# 第一章 产品定位

Version Center 是平台管理所有古籍版本的统一入口。

Version 不仅是一本书。

Version 是平台中的一级核心知识对象（Core Knowledge Object）。

平台所有：

- Passage
- Annotation
- Citation
- Evidence
- Knowledge Graph
- AI Research

均围绕 Version 建立关联。

---

# 第二章 产品目标

Version Center 应满足：

## 学术目标

支持：

- 古籍版本管理
- 版本比较
- 校勘研究
- 版本谱系研究
- 学术引用

---

## 产品目标

实现：

- 全生命周期版本管理
- 可视化版本关系
- AI 辅助版本研究
- GraphRAG 检索
- 数字版本展示

---

# 第三章 用户角色

Version Center 支持：

| 角色       | 权限         |
| ---------- | ------------ |
| 超级管理员 | 全部权限     |
| 学术管理员 | 管理版本资料 |
| 研究人员   | 创建研究数据 |
| 普通用户   | 浏览公开版本 |
| 游客       | 浏览开放资源 |

---

# 第四章 功能模块

Version Center 包括：

```text
Dashboard

↓

Version Library

↓

Version Detail

↓

Version Compare

↓

Version Timeline

↓

Version Genealogy

↓

Version Graph

↓

Version Workspace
```

---

# 第五章 信息架构

```
Version Center
│
├── Dashboard
├── Version List
├── Version Detail
├── Compare
├── Timeline
├── Genealogy
├── Graph
├── Research
└── Settings
```

所有页面保持统一导航。

---

# 第六章 Version Dashboard

Dashboard 展示：

- Version 总数
- 已数字化数量
- 馆藏数量
- 国家分布
- 朝代分布
- 最新研究
- 最新更新
- AI 推荐研究

支持快速进入各模块。

---

# 第七章 Version Library

列表支持：

- 名称
- 朝代
- 作者
- 收藏机构
- 国家
- 类型
- 完整度
- 是否公开

支持：

- 搜索
- 排序
- 筛选
- 收藏
- 标签
- 批量操作

---

# 第八章 Version Detail

详情页包括：

## 基本信息

- 名称
- 别名
- 年代
- 作者
- 收藏机构
- 来源
- 简介

## 数字资源

- 高清影像
- OCR
- PDF
- IIIF（预留接口）

## 学术信息

- 校勘
- Passage
- Citation
- Evidence

## AI

- AI 总结
- AI 版本分析
- AI 风险提示

---

# 第九章 Version Compare

支持：

任意两个以上版本比较。

比较内容：

- 字词差异
- 段落差异
- 注释差异
- 页码映射
- 图像比较
- AI 差异分析

比较结果可导出。

---

# 第十章 Version Timeline

时间轴展示：

- 创作时间
- 刊刻时间
- 收藏时间
- 数字化时间
- 研究时间

支持缩放。

支持点击进入详情。

---

# 第十一章 Version Genealogy

展示：

版本谱系。

例如：

```text
底本
│
├── 宋本
│
├── 元本
│
├── 明本
│
└── 清本
```

支持折叠。

支持 Graph 切换。

---

# 第十二章 Version Graph

Graph 节点：

- Version
- Passage
- Person
- Institution
- Citation
- Evidence

关系：

- Derived From
- Copied From
- Referenced By
- Annotated By

支持：

- 放大
- 缩小
- 搜索
- 路径分析

---

# 第十三章 AI Workspace

Version Workspace 包括：

左侧：

Version Graph

中间：

Document Viewer

右侧：

AI Research Assistant

底部：

Evidence Panel

支持：

- AI 对话
- 自动引用
- 自动生成研究笔记
- 自动生成比较报告

---

# 第十四章 数据模型

Version 必须至少包含：

- Version ID
- Title
- Dynasty
- Year
- Author
- Institution
- Country
- Language
- Status
- Visibility

禁止页面直接操作数据库。

所有数据均通过 Service 层获取。

---

# 第十五章 API 规范

统一 REST API：

```text
GET /versions

GET /versions/{id}

POST /versions

PUT /versions/{id}

DELETE /versions/{id}

GET /versions/{id}/graph

GET /versions/{id}/timeline

POST /versions/compare
```

后续 GraphQL 可作为扩展。

---

# 第十六章 UI 设计规范

采用：

平台统一 Layout。

要求：

- 三栏布局
- 响应式设计
- 深色模式
- 学术风格
- 支持国际化

所有图谱保持统一视觉语言。

---

# 第十七章 AI 能力

AI 默认支持：

- Version QA
- 自动总结
- 自动引用
- 版本比较
- 校勘建议
- 研究笔记
- AI Workspace

所有回答必须引用平台证据。

---

# 第十八章 非功能要求

要求：

- 页面加载 <2 秒（常规数据集）
- 图谱响应流畅
- 支持万级 Version
- 全文搜索
- 权限控制
- 操作日志
- 自动备份

---

# 第十九章 验收标准

Version Center 必须完成：

- Version CRUD
- Compare
- Timeline
- Graph
- Workspace
- AI Assistant
- 权限控制
- 国际化
- API
- 单元测试
- E2E 测试

全部通过后方可验收。

---

# 第二十章 后续扩展

未来扩展：

- IIIF 深度集成
- 三维古籍展示
- OCR 在线校正
- AI 自动校勘
- 国际馆藏同步
- 多平台联邦检索

保持模块持续演进。

---

# 修订记录

| Version | Date       | Description                                                          |
| ------- | ---------- | -------------------------------------------------------------------- |
| 1.0.0   | 2026-06-24 | 首版发布，定义 Version Center 产品规格，为平台开发提供统一实现标准。 |
