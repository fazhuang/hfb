---
title: Academic Interaction Standard
document_id: HFB-UI-0603
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product Designer
effective_date: 2026-06-24
scope: Academic Interaction Experience
priority: P0
related_documents:
  - HFB-UI-0601 Design System
  - HFB-UI-0602 UI Component Standard
  - HFB-AI-0405 AI Academic Review Standard
  - HFB-DAT-0304 Entity Specification
  - HFB-DAT-0305 Relation Specification
  - HFB-PS-1703 Platform Navigation Interaction Specification
  - HFB-PS-1705 AI Research Workspace Specification
  - HFB-PS-1709 MVP Implementation Specification
---

# Academic Interaction Standard
## 学术交互规范

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的学术交互模式。
>
> 本平台不是传统 CMS，不是普通管理后台，也不是聊天机器人，而是**数字人文智能研究平台**。
>
> 所有交互设计必须服务于**研究、考证、比较、发现、引用**五类学术活动。

---

# 第一章 设计理念

平台交互遵循：

> **Research First · Evidence First · Knowledge First**

任何交互都必须帮助用户完成学术研究，而不是增加视觉效果。

---

# 第二章 用户角色

平台主要用户：

| 用户 | 核心目标 |
|------|----------|
| 学者 | 深度研究 |
| 教师 | 教学备课 |
| 学生 | 学习与查阅 |
| 医学研究者 | 文献考证 |
| 数字人文研究者 | 数据分析 |
| 管理员 | 数据维护 |

不同角色允许拥有不同默认工作台。

---

# 第三章 学术工作流

平台支持统一研究流程：

```text
发现资料

↓

阅读资料

↓

比较资料

↓

建立关联

↓

形成观点

↓

引用资料

↓

导出成果
```

所有功能均围绕此流程设计。

---

# 第四章 首页交互

首页不是门户网站。

首页应提供：

- 全局搜索
- 最近研究
- 最新资源
- AI 学术助手
- 热门研究主题
- 我的收藏
- 我的项目

首页即研究入口。

---

# 第五章 全局搜索

统一搜索入口：

支持：

- 人物
- 古籍
- 版本
- 篇章
- 论文
- 图片
- 地点
- 时间

支持自然语言检索。

---

# 第六章 古籍阅读交互

阅读界面必须支持：

- 原文
- 现代标点
- 注释
- 校勘
- 行号
- 页码
- 引文复制

不得跳转多个页面完成阅读。

---

# 第七章 多版本比较

Version Compare：

支持：

```text
A 版本

←→

B 版本
```

同时支持：

- 行级比较
- 段落比较
- 差异高亮
- 引文同步

比较过程中不得丢失上下文。

---

# 第八章 人物研究交互

人物页面包括：

- 生平
- 时间轴
- 著作
- 学术影响
- 相关人物
- 地图
- 图片

支持一键进入关联知识。

---

# 第九章 学术关系探索

Knowledge Graph：

支持：

- 展开关系
- 多跳探索
- 来源查看
- 证据查看
- 路径分析

用户始终知道关系来源。

---

# 第十章 AI 学术助手

AI 页面必须包含：

```text
问题

↓

回答

↓

证据

↓

引用

↓

可信度

↓

继续研究建议
```

不得只有聊天窗口。

---

# 第十一章 引文交互

任何引用支持：

- 一键复制
- BibTeX
- RIS
- GB/T 7714
- APA
- MLA

引用格式自动生成。

---

# 第十二章 时间轴交互

Timeline：

支持：

- 朝代切换
- 时间缩放
- 人物过滤
- 著作过滤
- 历史事件联动

时间轴可直接跳转资源。

---

# 第十三章 地图交互

Academic Map：

支持：

- 人物活动轨迹
- 古籍传播路径
- 学派分布
- 地域研究成果

地图不是普通 GIS。

强调学术传播。

---

# 第十四章 文献研究交互

论文页面：

支持：

- 摘要
- DOI
- 引文
- 作者
- 机构
- 关联人物
- 关联古籍

支持快速建立研究网络。

---

# 第十五章 OCR 校勘交互

OCR 页面：

左右布局：

```text
原始扫描

↓

OCR 文本

↓

人工校勘
```

所有修改必须保留历史记录。

---

# 第十六章 收藏与项目

用户可建立：

- 收藏夹
- 研究项目
- 阅读清单
- 引文清单

支持多人协作（规划）。

---

# 第十七章 AI 可解释性交互

AI 回答必须支持：

- 查看引用
- 查看推理依据
- 查看检索文献
- 查看 Prompt 版本（管理员）
- 查看模型版本（管理员）

保证研究透明。

---

# 第十八章 学术成果导出

支持导出：

- PDF
- Word
- Markdown
- BibTeX
- CSV
- JSON（研究数据）

导出内容自动附带引用信息。

---

# 第十九章 交互质量指标

目标：

| 指标 | 标准 |
|------|------|
| 检索成功率 | ≥95% |
| 三步内完成主要任务 | ≥90% |
| AI 引文展示率 | 100% |
| 多版本比较响应 | ≤2 秒 |
| 学术资源定位成功率 | ≥98% |

---

# 第二十章 学术交互红线

禁止：

- AI 无引用回答
- 阅读跳转过多页面
- 多版本覆盖显示
- 隐藏数据来源
- 删除历史记录
- 娱乐化交互设计
- 广告式推荐

违反任一项不得上线。

---

# 第二十一章 修订规则

修改学术交互规范必须同步更新：

- Design System
- UI Component Standard
- AI Academic Review Standard
- Prototype（Figma）
- 用户研究报告

未经批准不得修改。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.1.0 | 2026-06-25 | 更新related_documents |
| 1.0.0 | 2026-06-24 | 首版发布，作为平台学术交互统一规范。 |