# Context 33 — 项目当前状态快照（Phase A0 完整闭环 + 在线来源准入表单）

**日期**: 2026-08-19
**版本**: v1.0
**范围**: 全项目当前状态记录 — 已完成工作、门禁、部署、阻塞、下一步
**目的**: 固化当前项目状态，作为后续 AI / 维护者进入项目时的统一上下文入口

---

## 1. 状态概览（一句话）

**Phase A0 证据原生管线已形成「生成 → 审批 → 发布 → 审计」完整闭环；古籍上传仍被治理阻塞（Research Lead 空缺），但已配套在线准入表单与审批流，技术侧 100% 就绪。**

---

## 2. 本阶段完成的全部工作

### 2.1 Phase A0 证据原生候选发布管线（核心）

| 环节 | 说明 |
| ---- | ---- |
| 候选生成 | `POST /extractions`（手动落库）+ `POST /extractions/generate`（AI/规则自动抽取） |
| 候选列表 | `GET /extractions`（分页 + status/session/passage/mine 过滤）+ `GET /extractions/{id}` |
| 人工审批 | `POST /extractions/{id}/approval`（通过并发布）+ `POST /extractions/{id}/rejection`（驳回） |
| 双哈希 grounding | `app/db/grounding.py` 共享 create/publish 的哈希与跨度计算，永不漂移 |
| 原子发布 | `CandidatePublishUnitOfWork` 单事务内验证归属链 + grounding + 发布 Evidence+Citation |
| 追加式审计 | `CandidateAuditLog` + 双方言 DDL 触发器（禁 UPDATE/DELETE + 禁孤儿 INSERT） |
| 漂移检测 | chunk 被篡改 → 409 GROUNDING_DRIFT + 状态 drift_invalid + 审计落库 |

**关键设计**：候选必须锚定真实 chunk 双哈希；审批时重新验证，任何漂移都 fail-closed 拒绝发布。AI 绝不负责定位引文跨度（非逐字子串则回退规则前缀）。

### 2.2 古籍上传 fail-closed 门控

- `POST /api/v1/documents/upload` 在读取文件前检查 `SOURCE_ADMISSION_OPEN`（默认 `False`）。
- 前端 `ClassicalUploadForm.vue` 已升级为真实表单（门控关闭时展示 409）。
- 测试覆盖：门控关闭 409 / 打开 201 摄入 / 跨 session 403 / 错误 MIME 422 全分支。

### 2.3 版本比较工作流接入候选审批

- `GET /extractions` 支持 `passage_id` 过滤（candidate.chunk_id → chunks.passage_id）。
- `EvidenceVerifyStep` 新增「候选证据」区：展示每版本待审批候选数 + 审批入口。
- 打通 #1 核心工作流（Evidence-backed Version Comparison）与 Phase A0 管线。

### 2.4 生产语料解冻治理文档（4 份）

| 文档 | 作用 |
| ---- | ---- |
| HFB-DAT-0307 解冻作战手册 | 技术就绪清单 + 治理动作 + 验收标准 |
| HFB-DAT-0308 填写指引 | 0306 §3 逐字段格式示范（类别特征占位，不含真实来源） |
| HFB-GOV-0006 任命决议模板 | Steering Committee 任命 Research Lead 的决议模板 |
| 0306 准入清单（原有） | 13 行待 Research Lead 真实填写 |

### 2.5 在线来源准入表单 + 审批流（最新）

把 0306 §3 数字化为平台内可追溯表单：

| 端点 | 作用 | 权限 |
| ---- | ---- | ---- |
| `GET /source-admissions` | 13 行视图 + 进度汇总 | `source_admission.read` |
| `PUT /source-admissions/{key}` | Research Lead 填写/提交 | `source_admission.create` |
| `POST /source-admissions/{key}/review` | Steering 审核通过/驳回 | `source_admission.review` |

前端 `/source-admission`：13 行分组清单 + 内联填写 + 审核按钮 + 进度汇总。

**关键边界**：审核通过仅记录治理决定，**不自动开 `SOURCE_ADMISSION_OPEN`**（0306 §6.3 不自动放行），flag 仍由部署层手动翻转。

---

## 3. 门禁状态（全绿）

| 门禁 | 结果 |
| ---- | ---- |
| 后端单测 | 2498 passed, 1 deselected（PG 相关测试） |
| 前端 vitest | 767 passed |
| E2E (chromium) | 98 passed |
| mypy strict | 22 文件 clean |
| ruff | 全绿 |
| eslint / vue-tsc | 全绿 |
| 设计合规 | 新组件零违规 |

---

## 4. 部署状态（本地）

| 服务 | 地址 | 状态 |
| ---- | ---- | ---- |
| 后端 (uvicorn --reload) | `http://127.0.0.1:8000` | healthy |
| 前端 (vite dev) | `http://localhost:5173` | 200 |
| PostgreSQL | `localhost:5432`（db `hfb`，user `hfb`） | 运行中 |
| Redis | `localhost:6379` | 运行中 |
| Elasticsearch | `localhost:9200` | 运行中 |
| MinIO | `localhost:9000/9001` | 运行中 |

测试用户：`researcher / researcher123`、`admin / admin123`。

---

## 5. 数据 / 迁移状态

- 迁移链 head：`source_admission_entries`（最新）。
- dev DB `hfb` 已迁移到 head。
- RBAC 已重新 seed（`source_admission` 资源 8 权限 + 角色映射）。
- `SOURCE_ADMISSION_OPEN=False`（fail-closed，符合预期）。

---

## 6. Git 状态

- 分支：`main`，与 `origin/main` 同步。
- Tag：`v0.2.0-phase-a0`（Phase A0 归档）、`v0.2.0-e0-candidate-20260809`、`v0.1.0-literature-compliance`。
- 最近提交主线：`7e4396a`（上传表单）→ … → `58dcb0a`（准入表单页面）。
- 未跟踪文件：`hfm.jpeg`、`motionsites-prompts/`（嵌套 git 仓库，gitignored，与主线无关）。

---

## 7. 阻塞项（唯一）

**生产语料解冻** —— Research Lead 职位空缺：

- 0306 准入清单 §3 全部 13 行空白、§4 零签署。
- 解冻唯一路径：任命 Research Lead → 填写 0306 §3/§4（或在线表单 `/source-admission`）→ Codex 验收 → Steering 放行 → 置 `SOURCE_ADMISSION_OPEN=true`。
- 技术侧 100% 就绪，无额外工程。

---

## 8. 下一步方向（候选）

1. **任命 Research Lead**（组织动作，唯一硬阻塞）。
2. 审批页完善（提交人姓名、chunk 上下文、驳回理由详情）。
3. AI 批量抽取（session/文档多 chunk 批量 generate）。
4. 导出链路核验（审批发布的 Evidence 进入研究记录导出）。
5. 「全部 13 行通过」的一键放行提示（仅展示，不自动执行）。

---

## 9. 关键决策记录

- **UUID v7 默认主键**（RFC 9562），前端 guardId 正则已放宽至任意 RFC 4122 版本。
- **UoW 在持久层**：`CandidatePublishUnitOfWork` / `CandidateCreateUnitOfWork` 属 `app/db`，service 层不碰 session/repository。
- **AI 元数据 fail-closed**：拒绝 unknown/空白/NaN/±Infinity 占位。
- **审计追加式**：`CandidateAuditLog` 扩展 `Base`（无软删），DDL 触发器禁篡改。
- **来源准入不自动放行**：在线审批通过 ≠ 开 flag，部署层显式翻转。
