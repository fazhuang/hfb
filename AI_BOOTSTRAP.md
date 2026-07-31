# AI Bootstrap — 皇甫谧数字人文平台

**Purpose**: AI agent entry point. Read this file first when joining the project.

**Language**: Chinese (中文) — all docs are in Chinese. Code identifiers may use English.

**Version**: 0.2.0 | **Sprint**: Sprint 0.2 (Repository Foundation) | **Date**: 2025-06-24

---

## 项目接手阅读顺序 (New Developer Onboarding)

如果你是新人接手本项目，按此顺序阅读：

```
1. README.md                              ← 项目是什么、技术栈、目录结构
2. PROJECT_STATUS.md                       ← 当前 Sprint、进度、风险
3. ROADMAP.md                              ← 全局路线图 (Sprint 0 ~ 16)
4. docs/00-governance/01_Project_Constitution.md  ← 最高约束力：怎么决策
5. docs/01-product/00_Product_Roadmap.md   ← 产品愿景与路线图
6. docs/02-architecture/00_Technical_Blueprint.md ← 系统架构蓝图
7. docs/05-development/00_Development_Specification.md ← 开发规范与工具链
8. docs/11-adr/README.md                   ← 架构决策记录索引
9. CONTRIBUTING.md                         ← 贡献流程、Commit 规范、PR 流程
10. repo.manifest.json                     ← 机器可读项目清单
```

---

## Claude 开发前阅读顺序 (Claude Code — Before Writing Code)

Claude 在开始**任何代码开发**之前，必须按此顺序阅读：

```
1. AI_BOOTSTRAP.md (this file)             ← 知道规则
2. README.md                               ← 知道项目是什么
3. repo.manifest.json                      ← 知道项目结构、技术栈、ADR 索引
4. docs/00-governance/0004-documentation-rules.md ← 知道文档格式规范
5. docs/05-development/00_Development_Specification.md ← 知道代码规范
6. docs/04-ai/00_AI_Engineering_Standard.md ← 知道 AI 模块标准
7. docs/11-adr/                            ← 知道已有架构决策 (ADR-0001 ~ 0010)
8. docs/09-prompts/README.md               ← 知道 Prompt 模板库
9. docs/12-context/{currentSprint}/        ← 知道当前 Sprint 上下文
10. pyproject.toml + ruff.toml             ← 知道 Python 规范 (ruff, mypy, pytest)
11. eslint.config.mjs + .prettierrc        ← 知道 Node 规范
```

**关键约束**:

- 所有代码必须先通过 `make lint` 再提交
- Type hints 必须完整 (mypy strict)
- 测试覆盖率目标: 业务逻辑 ≥80%，工具函数 ≥90%
- 架构变更必须走 ADR 流程

---

## Codex 审计前阅读顺序 (Codex — Before Audit)

Codex 在执行**代码审计**之前，必须按此顺序阅读：

```
1. AI_BOOTSTRAP.md (this file)             ← 知道禁止事项
2. docs/07-security/00_Acceptance_Specification.md ← 安全验收标准
3. docs/02-architecture/00_Technical_Blueprint.md  ← 系统架构（找攻击面）
4. docs/04-ai/00_AI_Engineering_Standard.md ← AI 模块安全边界
5. docs/03-data/00_Data_Standard.md        ← 数据安全边界
6. repo.manifest.json                      ← 技术栈（CVE 扫描范围）
7. .github/workflows/security.yml          ← 已有安全扫描规则
8. .pre-commit-config.yaml                 ← 已有 Git hooks (gitleaks)
```

**审计维度** (来自 `docs/07-security/`):

- OWASP Top 10
- API 安全 (JWT、RBAC、Rate Limiting)
- 数据安全 (加密、脱敏、审计日志)
- AI 安全 (Prompt Injection、模型安全)
- 依赖供应链安全

---

## Gemini 评审前阅读顺序 (Gemini — Before Review)

Gemini 在执行**文档/设计评审**之前，必须按此顺序阅读：

```
1. AI_BOOTSTRAP.md (this file)             ← 知道规则
2. docs/00-governance/01_Project_Constitution.md ← 治理原则
3. docs/00-governance/0004-documentation-rules.md ← 文档格式规范
4. docs/01-product/00_Product_Roadmap.md   ← 产品方向
5. docs/02-architecture/00_Technical_Blueprint.md ← 架构蓝图
6. docs/06-ui/00_Design_System.md          ← 设计系统
7. docs/04-ai/00_AI_Engineering_Standard.md ← AI 标准
8. docs/15-decision-tree/                  ← 决策树（验证技术选型）
9. docs/11-adr/                            ← 已有 ADR（不重复质疑已决策项）
10. ROADMAP.md                              ← 全局路线图（评审是否对齐）
```

**评审维度**:

- 文档一致性 — 与 Constitution/Blueprint/ADR 是否一致
- 完整性 — 是否覆盖所需章节
- 可实现性 — 技术方案是否可行
- 中文质量 — 术语、表达是否准确
- 上下游对齐 — 该文档与前后环节文档是否对齐

---

## 禁止事项 (Forbidden — All AI Agents)

以下事项**所有 AI 代理均不得执行**:

1. **不得开发业务代码** — Sprint 0.2 仅建设仓库基础设施。业务代码从 Sprint 1 开始。
2. **不得开发页面** — 前端页面从 Sprint 2 开始。
3. **不得开发数据库** — 数据库 Schema 从 Sprint 3 开始。
4. **不得开发 API** — API 端点从 Sprint 6 开始 (后端基础设施在 Sprint 1 搭建)。
5. **不得修改 docs/ 内容** — 文档体系在 Sprint 0.1 已完成，不得修改。
6. **不得新增需求** — 需求冻结在当前 Sprint 范围。新需求写入 Issue 或下个 Sprint 规划。
7. **不得删除任何文件** — 除非明确指示，否则只允许创建和修改。
8. **不得修改 LICENSE 中版权方名称**。
9. **不得绕过 CI 检查** — 所有代码必须通过 lint/test/build 流水线。
10. **不得在 main 分支直接提交** — 始终通过 Feature Branch + PR 流程。

---

## 当前 Sprint 入口

| 字段         | 值                    |
| ------------ | --------------------- |
| **Sprint**   | Sprint 0.2            |
| **主题**     | Repository Foundation |
| **状态**     | ✅ 完成               |
| **入口文档** | `PROJECT_STATUS.md`   |
| **ROADMAP**  | `ROADMAP.md`          |
| **机器清单** | `repo.manifest.json`  |

### Sprint 0.2 产出

- Monorepo 完整目录结构
- GitHub 社区文件 (Issue/PR 模板, CODEOWNERS, SECURITY, CODE_OF_CONDUCT)
- 根目录文档 (README, LICENSE, CHANGELOG, CONTRIBUTING, ROADMAP, PROJECT_STATUS)
- Git 规范 (.editorconfig, .gitattributes, .gitignore, .pre-commit-config.yaml)
- Python 规范 (pyproject.toml, ruff.toml, mypy.ini, pytest.ini)
- Node 规范 (package.json, pnpm-workspace.yaml, eslint, prettier, tsconfig)
- Docker 配置 (4 Dockerfiles, 2 compose files, nginx.conf, .env.example)
- CI/CD (5 workflows: docs, lint, test, build, security)
- Scripts (6: setup, dev, lint, test, format, release) + Makefile (14 targets)
- Templates (6: ADR, API, Sprint, Review, Issue, Meeting)
- VS Code 工作区配置

### 下一 Sprint

| 字段       | 值                                         |
| ---------- | ------------------------------------------ |
| **Sprint** | Sprint 1                                   |
| **主题**   | Backend Core Infrastructure                |
| **目标**   | FastAPI 项目骨架、数据库连接、健康检查端点 |
| **状态**   | 🔲 等待开始                                |

---

> **给下一个 AI Agent 的提示**: 如果你是来接手的，从「项目接手阅读顺序」开始。如果你是来写代码的 Claude，从「Claude 开发前阅读顺序」开始。如果你不知道当前 Sprint 是什么，读 `PROJECT_STATUS.md`。
