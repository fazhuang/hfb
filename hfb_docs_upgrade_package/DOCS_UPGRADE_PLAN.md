# 皇甫谧数字人文平台 Docs 升级总方案

## 1. 总目标

以 `16-research-framework` 与 `17-Platform-Specifications` 为新的设计基线，对现有 `docs/` 目录进行反向统一升级。

本次升级不是继续扩充文档数量，而是：

- 保留现有目录与编号体系；
- 合并重复文档；
- 清理命名混乱；
- 统一 YAML Header；
- 统一文档结构；
- 统一产品实现导向；
- 让文档直接服务 Claude Code 开发、Codex 审计、Gemini 产品评审。

最高原则：

> 一切文档服务产品实现。

---

## 2. 新设计基线

本轮升级以以下两组文档为最高约束：

```text
docs/16-research-framework/
docs/17-Platform-Specifications/
```

其中：

- 16 系列定义平台研究方法论；
- 17 系列定义平台产品实现规格；
- 01~15 系列必须向 16/17 系列对齐；
- 不再生成脱离产品实现的理论文档。

---

## 3. 升级范围

需要升级的目录：

```text
00-governance
01-product
02-architecture
03-data
04-ai
05-development
06-ui
07-security
08-domain
09-prompts
10-diagrams
11-adr
12-context
13-machine
14-knowledge
15-decision-tree
templates
README.md
documentation-index.md
```

暂不重写：

```text
16-research-framework
17-Platform-Specifications
18-academic-assets
```

16/17 仅进行索引校验与命名统一，不做内容重写。

---

## 4. 优先级

### P0：必须优先升级

```text
00-governance
01-product
02-architecture
03-data
04-ai
05-development
06-ui
07-security
08-domain
README.md
documentation-index.md
```

### P1：第二批升级

```text
09-prompts
10-diagrams
11-adr
13-machine
14-knowledge
15-decision-tree
templates
```

### P2：整理归档

```text
12-context
18-academic-assets
```

---

## 5. 命名统一规则

统一目录名保持现状，不做大规模迁移。

但文件命名应统一：

```text
NNNN_English_Title.md
```

例如：

```text
0001_Project_Charter.md
0201_System_Architecture.md
0504_API_Design_Standard.md
```

需要处理的异常：

```text
00_Project_Charter.md
01_Project_Constitution.md
0001-project-charter.md
0002-project-constitution.md
0302_Ontology_Specification.md.md
00_Acceptance_Specification.md
```

处理策略：

- 保留最新正式版本；
- 重复旧文件迁移至 `docs/_archive/legacy/`；
- 修正 `.md.md`；
- 更新 documentation-index.md。

---

## 6. 文档统一 Header

所有核心 Markdown 文档统一使用：

```yaml
---
title:
document_id:
version: 1.0.0
status: Approved
owner:
reviewer:
effective_date: 2026-06-24
scope:
priority: P0
related_documents:
---
```

不同目录 document_id 前缀：

```text
00-governance        HFB-GOV
01-product           HFB-PRD
02-architecture      HFB-ARC
03-data              HFB-DATA
04-ai                HFB-AI
05-development       HFB-DEV
06-ui                HFB-UI
07-security          HFB-SEC
08-domain            HFB-DOM
09-prompts           HFB-PRM
10-diagrams          HFB-DIA
11-adr               HFB-ADR
12-context           HFB-CTX
13-machine           HFB-MCH
14-knowledge         HFB-KB
15-decision-tree     HFB-DT
16-research-framework HFB-RF
17-Platform-Specifications HFB-PS
```

---

## 7. 核心文档结构

每份核心文档统一采用：

```text
YAML Header

# English Title
## 中文标题

> 文档定位说明

# 第一章 目标与范围
# 第二章 设计原则
# 第三章 核心对象
# 第四章 功能/规范内容
# 第五章 工作流程
# 第六章 数据要求
# 第七章 AI 要求
# 第八章 权限与安全
# 第九章 测试与验收
# 第十章 后续演进

# 修订记录

文件路径

阶段定位
```

工程类文档可扩展到 20 章，但必须避免空泛。

---

## 8. 内容收敛原则

禁止：

- 为了完整而无限扩展；
- 重复 16/17 系列已有内容；
- 产生不可开发、不可验收的理论描述；
- 新增大量未来愿景；
- 让 Claude 自行解释产品方向。

必须：

- 指向具体产品实现；
- 明确开发边界；
- 明确验收标准；
- 明确与 17 系列关系；
- 明确 Claude/Codex/Gemini 分工。

---

## 9. 交付结果

升级完成后应形成：

```text
docs/
├── README.md
├── documentation-index.md
├── _archive/
│   └── legacy/
├── 00-governance/
├── 01-product/
├── ...
├── 17-Platform-Specifications/
└── templates/
```

并生成：

```text
docs/UPGRADE_REPORT.md
docs/DOCS_STRUCTURE_AUDIT.md
docs/DOCS_CHANGELOG.md
```

---

## 10. 验收标准

必须满足：

- 无重复核心文档；
- 无 `.md.md`；
- 所有 P0 文档有 YAML Header；
- 所有 document_id 唯一；
- documentation-index.md 与文件真实存在状态一致；
- 01~15 与 16/17 不冲突；
- 所有文档服务产品实现；
- Claude 能根据文档开发；
- Codex 能根据文档验收。
