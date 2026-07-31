# 09-prompts

Prompt 资产库。平台所有 Prompt 的统一存储、版本管理及分发目录。

---

> 层级：**Level 6 — 执行工具与上下文**（低于 00-governance、17-Platform-Specifications、04-ai）
>
> 本目录所有 Prompt 受 HFB-GOV-0005 AI Execution Protocol 约束，遵循 HFB-AI-0404 Prompt Engineering Guide 的工程规范。
>
> **Prompt 是项目正式资产（Project Asset），与源代码具有同等重要性。**

---

## Prompt 资产体系

### 按 AI 模型分

| 模型         | 目录                                      | README | 说明                                  |
| ------------ | ----------------------------------------- | ------ | ------------------------------------- |
| Claude       | [claude/](claude/README.md)               | ✅     | Claude 专用 Prompt — 编码、文档、审查 |
| Codex        | [codex/](codex/README.md)                 | ✅     | Codex 专用 Prompt — 审计、安全扫描    |
| Gemini       | [gemini/](gemini/README.md)               | ✅     | Gemini 专用 Prompt — UI/UX 评审       |
| GPT          | [gpt/](gpt/README.md)                     | ✅     | GPT 专用 Prompt — 产品规划、创意写作  |
| DeepResearch | [deep-research/](deep-research/README.md) | ✅     | Deep Research 专用 Prompt — 文献调研  |

### 共享 Prompt

| 编号 | 文档                                                                  | 模型   | 用途                  |
| ---- | --------------------------------------------------------------------- | ------ | --------------------- |
| P001 | [Claude_Sprint00_Docs_Foundation](Claude_Sprint00_Docs_Foundation.md) | Claude | Sprint 0 文档奠基指令 |
| P002 | [Codex_Docs_Audit](Codex_Docs_Audit.md)                               | Codex  | 文档体系审计验收      |
| P003 | [Gemini_UI_Academic_Review](Gemini_UI_Academic_Review.md)             | Gemini | UI 风格与学术表达评审 |

### 版本管理

| 目录/文件                                | 说明                      |
| ---------------------------------------- | ------------------------- |
| [versions/](versions/README.md)          | Prompt 版本索引与完整历史 |
| [prompt-template.md](prompt-template.md) | Prompt 编写模板           |

---

## AI 角色与 Prompt 职责

依据 [HFB-GOV-0005 AI Execution Protocol](../00-governance/0005_AI_Execution_Protocol.md)：

| AI              | Prompt 用途                      | 职责边界                  |
| --------------- | -------------------------------- | ------------------------- |
| **ChatGPT**     | 产品规划、Sprint 拆解、架构设计  | 批准 Sprint、定义 Roadmap |
| **Claude Code** | 编码实现、重构、测试、文档创建   | 不得自行增加需求          |
| **Codex**       | 架构审计、安全审计、代码质量检查 | 不得直接修改代码          |
| **Gemini**      | UI/UX 评审、学术表达、信息架构   | 不得修改业务逻辑          |

---

## Prompt 工程规范

所有 Prompt 遵循 [HFB-AI-0404 Prompt Engineering Guide](../04-ai/0404_Prompt_Engineering_Guide.md)：

- 统一版本管理（Semantic Versioning）
- 必须包含：目标、适用模型、System Prompt、User Prompt、输入/输出示例、已知限制
- 禁止硬编码 Prompt 于代码中
- 修改后必须重新测试并记录 Changelog

---

## 关联目录

| 目录                                                               | 关系            | 说明                                          |
| ------------------------------------------------------------------ | --------------- | --------------------------------------------- |
| [docs/04-ai/](../04-ai/)                                           | Prompt 工程规范 | 遵循 0404 Prompt Engineering Guide 的工程约束 |
| [docs/00-governance/](../00-governance/)                           | AI 执行约束     | 受 0005 AI Execution Protocol 约束            |
| [docs/templates/](../templates/)                                   | Prompt 模板     | 提供 Prompt 编写模板                          |
| [docs/17-Platform-Specifications/](../17-Platform-Specifications/) | 产品上下文      | Prompt 必须引用 17 系列产品规格               |

---

## 快速入口

- **编写 Prompt** → [prompt-template.md](prompt-template.md)
- **查看版本历史** → [versions/](versions/README.md)
- **Claude Prompt** → [claude/](claude/README.md)
- **Codex Prompt** → [codex/](codex/README.md)
- **Gemini Prompt** → [gemini/](gemini/README.md)
- **GPT Prompt** → [gpt/](gpt/README.md)
