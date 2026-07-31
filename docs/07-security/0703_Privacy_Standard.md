---
title: Privacy & Data Governance Standard
document_id: HFB-SEC-0703
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Data Officer
effective_date: 2026-06-24
scope: Privacy Protection & Data Governance
priority: P0
related_documents:
  - HFB-SEC-0701 Acceptance Specification
  - HFB-SEC-0702 Security Standard
  - HFB-DAT-0301 Data Standard Specification
  - HFB-DAT-0303 Metadata Standard
  - HFB-AI-0402 RAG Specification
  - HFB-PS-1710 Production Readiness Specification
---

# Privacy & Data Governance Standard

## 隐私与数据治理规范

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的数据治理、隐私保护、版权管理及 AI 数据使用边界。
>
> 平台建设目标不仅是数据存储，更要建立**可信、可追溯、可持续演进**的数字人文知识资产体系。

---

# 第一章 建设目标

建立统一的数据治理体系，实现：

- 数据合法
- 来源可信
- 权属明确
- 生命周期完整
- AI 使用可控
- 数据长期可持续维护

---

# 第二章 数据分类

平台数据统一划分为六类：

| 类型           | 内容                                  |
| -------------- | ------------------------------------- |
| Academic Data  | 古籍、论文、人物、版本等学术资源      |
| Metadata       | 元数据                                |
| User Data      | 用户资料、偏好设置                    |
| System Data    | 系统配置、日志                        |
| AI Data        | Prompt、Embedding、检索记录、模型配置 |
| Temporary Data | 缓存、临时文件、任务中间结果          |

不同类别采用不同治理策略。

---

# 第三章 数据所有权

平台明确区分：

| 类型         | 权属                                   |
| ------------ | -------------------------------------- |
| 系统代码     | 项目团队                               |
| 平台元数据   | 平台                                   |
| 古籍数字资源 | 按版权归属管理                         |
| OCR 数据     | 平台维护版本                           |
| 用户上传资料 | 用户所有                               |
| AI 生成内容  | 平台标注为 AI 生成，不作为原始学术成果 |

禁止混淆数据权属。

---

# 第四章 数据来源

所有学术资源必须记录：

- 来源机构
- 来源文献
- 采集时间
- 采集方式
- 版本信息
- 版权状态
- 数据责任人

来源未知的数据不得进入正式知识库。

---

# 第五章 Metadata 管理

所有资源必须关联 Metadata。

Metadata 至少包含：

- UUID
- Title
- Creator
- Source
- License
- Language
- Version
- Created Time
- Updated Time

Metadata 不得缺失。

---

# 第六章 用户隐私

平台采集用户信息坚持最小化原则。

仅允许采集：

- 登录账号
- 必要身份信息
- 用户偏好
- 操作记录

禁止采集与平台无关的个人信息。

---

# 第七章 用户行为数据

记录：

- 登录
- 检索
- 收藏
- AI 对话
- 数据导出

用途：

- 安全审计
- 产品优化
- 学术统计

不得用于商业营销。

---

# 第八章 AI 数据边界

AI 可访问：

- 已授权知识库
- 已公开学术资源
- 用户授权项目

AI 不得：

- 越权访问
- 调用未授权数据
- 输出隐藏数据

---

# 第九章 Prompt 数据治理

Prompt 属于平台核心资产。

统一管理：

- Version
- Author
- Change Log
- Review Status
- Release Version

Prompt 不得直接覆盖历史版本。

---

# 第十章 Embedding 数据

Embedding：

属于 AI 索引数据。

必须：

- 可重建
- 可删除
- 可更新

禁止作为唯一数据源。

---

# 第十一章 数据生命周期

统一生命周期：

```text
Collect

↓

Review

↓

Publish

↓

Maintain

↓

Archive

↓

Retire
```

任何数据不得直接删除。

---

# 第十二章 数据版本管理

适用于：

- 古籍
- OCR
- Metadata
- Prompt
- Knowledge Graph

所有版本永久保留。

---

# 第十三章 数据共享

平台支持：

- API
- JSON
- CSV
- RDF（规划）

共享前必须完成：

- 权限校验
- 版权确认
- Metadata 校验

---

# 第十四章 数据脱敏

必须脱敏：

- 用户邮箱
- 手机号
- Token
- API Key
- 身份凭证

日志不得出现敏感数据。

---

# 第十五章 学术版权

所有资源必须标明：

- 版权所有者
- 引用方式
- License
- 使用限制

禁止移除版权信息。

---

# 第十六章 数据质量

目标：

| 指标            | 标准  |
| --------------- | ----- |
| Metadata 完整率 | 100%  |
| 来源完整率      | 100%  |
| UUID 覆盖率     | 100%  |
| 重复率          | <0.5% |
| AI 数据可追溯率 | 100%  |

---

# 第十七章 数据审计

所有关键操作记录：

- 创建
- 修改
- 删除（逻辑删除）
- 导出
- AI 使用

审计记录不得删除。

---

# 第十八章 数据销毁

仅允许：

- 测试数据
- 临时缓存
- 已失效索引

正式学术资源不得物理删除。

采用归档管理。

---

# 第十九章 数据治理红线

禁止：

- 来源不明数据入库
- 删除 Metadata
- 覆盖历史版本
- AI 使用未授权数据
- 删除审计记录
- 导出未授权数据
- 移除版权信息

违反任一项立即停止发布。

---

# 第二十章 修订规则

修改本规范必须同步更新：

- Data Standard Specification
- Metadata Standard
- Security Standard
- RAG Specification
- Knowledge Graph Specification

未经批准不得修改。

---

# 修订记录

| Version | Date       | Description                                |
| ------- | ---------- | ------------------------------------------ |
| 1.1.0   | 2026-06-25 | 更新related_documents                      |
| 1.0.0   | 2026-06-24 | 首版发布，作为平台隐私与数据治理统一规范。 |
