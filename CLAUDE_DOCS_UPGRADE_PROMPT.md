# Claude Code 指令：皇甫谧数字人文平台 Docs 体系升级

你现在负责升级《皇甫谧数字人文与中医经典智能研究平台》的 `docs/` 文档体系。

## 一、最高目标

以现有：

```text
docs/16-research-framework/
docs/17-Platform-Specifications/
```

为新的设计基线，对 `docs/00-governance` 到 `docs/15-decision-tree` 以及根目录索引文档进行统一升级。

本任务不是新增更多文档，而是将已有文档统一提升为可直接服务产品实现、Claude Code 开发、Codex 审计、Gemini 产品评审的工程化文档体系。

最高原则：

> 一切文档服务产品实现。

---

## 二、执行前强制要求

先执行：

```bash
find docs -maxdepth 3 -type f | sort
find docs -maxdepth 3 -type d | sort
```

然后生成：

```text
docs/DOCS_STRUCTURE_AUDIT.md
```

内容包括：

- 当前目录结构；
- 重复文件；
- 命名异常；
- 缺失 README；
- 缺失 YAML Header；
- 与 16/17 不一致的文档；
- 建议归档文件。

不要立刻重写全部文档，必须先完成盘点。

---

## 三、必须保留的设计基线

不得破坏以下目录：

```text
docs/16-research-framework/
docs/17-Platform-Specifications/
```

它们是本轮升级的最高依据。

如果前面文档与 16/17 冲突，以 16/17 为准。

---

## 四、重复文档处理

以下属于明确重复或异常，必须处理：

```text
docs/00-governance/00_Project_Charter.md
docs/00-governance/0001-project-charter.md

docs/00-governance/01_Project_Constitution.md
docs/00-governance/0002-project-constitution.md

docs/03-data/0302_Ontology_Specification.md.md

docs/07-security/00_Acceptance_Specification.md
docs/07-security/0701_Acceptance_Specification.md
```

处理规则：

1. 保留编号规范版本；
2. 统一文件名为 `NNNN_English_Title.md`；
3. 被替代文件迁入：

```text
docs/_archive/legacy/
```

4. 不得直接删除；
5. 更新 documentation-index.md。

---

## 五、统一 Header

所有 P0 核心 Markdown 文档必须具备：

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

document_id 规则：

```text
00-governance         HFB-GOV-0001
01-product            HFB-PRD-0101
02-architecture       HFB-ARC-0201
03-data               HFB-DATA-0301
04-ai                 HFB-AI-0401
05-development        HFB-DEV-0501
06-ui                 HFB-UI-0601
07-security           HFB-SEC-0701
08-domain             HFB-DOM-0801
09-prompts            HFB-PRM-0901
10-diagrams           HFB-DIA-1001
11-adr                HFB-ADR-0001
12-context            HFB-CTX-1201
13-machine            HFB-MCH-1301
14-knowledge          HFB-KB-1401
15-decision-tree      HFB-DT-1501
```

---

## 六、升级重点目录

### 第一批 P0

优先升级：

```text
docs/README.md
docs/documentation-index.md
docs/00-governance/
docs/01-product/
docs/02-architecture/
docs/03-data/
docs/04-ai/
docs/05-development/
docs/06-ui/
docs/07-security/
docs/08-domain/
```

这些文档必须与 17 系列产品规格完全一致。

### 第二批 P1

随后升级：

```text
docs/09-prompts/
docs/10-diagrams/
docs/11-adr/
docs/13-machine/
docs/14-knowledge/
docs/15-decision-tree/
docs/templates/
```

### 第三批 P2

整理：

```text
docs/12-context/
docs/18-academic-assets/
```

---

## 七、内容升级标准

文档必须从“说明文档”升级为“产品实现约束文档”。

每份文档应回答：

- 这个文档指导什么开发？
- 约束什么模块？
- 与 16/17 哪些文档关联？
- Claude 开发时必须遵守什么？
- Codex 验收时检查什么？
- 哪些功能不在当前范围？

避免空泛愿景。

---

## 八、禁止事项

禁止：

- 新增 18、19、20 等大目录扩张；
- 继续生成大量 Framework；
- 自行改变 16/17 已确定方向；
- 重命名大量目录导致路径失效；
- 删除旧文档不备份；
- 写没有验收标准的文档；
- 让 AI 生成不能被验证的学术结论。

---

## 九、必须生成的汇总文档

完成后生成：

```text
docs/DOCS_STRUCTURE_AUDIT.md
docs/UPGRADE_REPORT.md
docs/DOCS_CHANGELOG.md
```

其中：

`UPGRADE_REPORT.md` 必须包括：

- 修改了哪些文件；
- 归档了哪些文件；
- 新增了哪些文件；
- 修复了哪些命名问题；
- 哪些文档仍需人工确认；
- 下一步建议。

---

## 十、执行方式

采用小步提交。

建议顺序：

```text
Step 1: 盘点 docs
Step 2: 修复重复和命名异常
Step 3: 升级根 README 与 documentation-index
Step 4: 升级 00~02
Step 5: 升级 03~08
Step 6: 升级 09~15
Step 7: 生成报告
```

每一步完成后运行：

```bash
find docs -maxdepth 3 -type f | sort
grep -R "^document_id:" docs --include="*.md"
```

确保文档结构一致。

---

## 十一、最终完成标准

只有同时满足以下条件，才可声明完成：

- `docs/DOCS_STRUCTURE_AUDIT.md` 存在；
- `docs/UPGRADE_REPORT.md` 存在；
- `docs/DOCS_CHANGELOG.md` 存在；
- 重复文档已归档；
- `.md.md` 已修复；
- P0 文档均有 YAML Header；
- 16/17 未被破坏；
- documentation-index.md 与实际结构一致；
- 所有升级结果服务产品实现。
