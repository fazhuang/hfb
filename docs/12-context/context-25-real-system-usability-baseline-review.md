# 皇甫谧数字人文平台 — Phase 2 Task 1 再次验收

验收日期：2026-07-15（Asia/Shanghai）  
验收基线：`HEAD=cbdb448d58bbb4df5f82b41e61b8da7a15cda6a9`；worktree 非干净。  
原则：Evidence First / Reality First。未由本轮命令、HTTP、SQL、脚本输出或真实浏览器直接证明的事项均标记 **Evidence Missing**。

## 1. 最终结论

**C — 不通过 / BLOCK_RELEASE。**

后端固定研究请求已从上一轮的 `WORKFLOW_STEP_FAILED` 修复为成功；但普通用户真实浏览器在 10 秒超时后中止请求，页面显示 `timeout of 10000ms exceeded`，不能看到回答或 Citation。此外，验收脚本的五条事实均显示 `source_ref_id:null` 与 `source_ref_url:null`，不满足要求的 Citation→Evidence→SourceRef→Document→Version→PDF 页码链。因此不得以脚本 `FINAL: PASS` 或后端 HTTP 200 宣称本任务通过。

## 2. 启动与环境真实性

| 检查 | 本轮直接证据 | 结果 |
|---|---|---|
| 依赖容器 | `docker compose -f docker-compose.dev.yml up -d postgres redis elasticsearch minio`；四项均 `healthy` | 通过 |
| 后端导入 | `UV_CACHE_DIR=/private/tmp/uv-cache uv run python -c "import main; print('IMPORT_OK')"` → `IMPORT_OK` | 通过 |
| health | `GET /health` → HTTP 200 | 通过 |
| ready | `GET /ready` → HTTP 200；PostgreSQL、Redis、Elasticsearch、MinIO 均 `healthy` | 通过 |
| README 冷启动路径 | 依赖容器和后端均已实际启动并返回 health；前端 `:5173` 可访问 | 部分通过 |
| clean-HEAD 可发布性 | 当前大量已修改及未跟踪文件 | 未证明 |

## 3. 后端真实研究运行

认证普通用户 `researcher` 后，直接调用固定问题，响应如下：

```text
POST /api/v4/research/session → 200
POST /api/v4/research/workflow → 200，耗时 14.146269 秒
topic_selection: completed
literature_retrieval: completed (themes=3, records=5)
evidence_synthesis: completed (sections=1, claims=5)
report_generation: completed
citation_export: completed (total_citations=5)
traceability.citation_count=25
```

项目脚本 `UV_CACHE_DIR=/private/tmp/uv-cache uv run python scripts/p2t1_verify.py` 正常结束，输出：

```text
SUMMARY: A=True B=True C=True
FINAL: PASS
```

同一脚本的 Withdraw/restore 运行结果：撤回正式版本后，`build_internal_traces` 抛出 `TRACE_LINEAGE_INCOMPLETE`；恢复后重新得到 5 条 traces。此项证明内部 trace 构建会拒绝已撤回版本，**不等同于**用户页面、检索和既有 Citation 已全部消失。

## 4. 浏览器真实性与研究流程

真实浏览器打开 `http://127.0.0.1:5173/`，标题为“皇甫谧数字人文平台”，首页显示后端、数据库、Redis、Elasticsearch、MinIO 已连接。普通用户登录成功后，`/v4/research` 真实渲染“研究工作流”、研究主题输入框和执行按钮。

输入“《针灸甲乙经》的成书特点是什么？”并点击执行后：

```text
POST /api/v4/research/session → 200
POST /api/v4/research/workflow → net::ERR_ABORTED
页面 alert：timeout of 10000ms exceeded
```

浏览器快照：`.playwright-cli/page-2026-07-14T20-21-33-304Z.yml`。  
错误截图：`.playwright-cli/page-2026-07-14T20-25-29-311Z.png`。

后端真实完成需 14.15 秒，已超过浏览器的 10 秒客户端超时。故普通用户不能在页面完成“提出问题 → 查看回答 → 验证 Citation → 保存笔记 → 生成研究报告 → 导出成果”。该流程失败。

首页以外的全部页面、管理员入口、菜单、权限、页面标题、空态、接口与占位状态的逐页矩阵：**Evidence Missing**。

## 5. 数据、Evidence 与 Citation 真实性

本轮直接 SQL 计数：

```text
documents=6
versions=3
evidences=52
citations=52
source_refs=2
formal_versions=2
```

`apps/backend/output/p2t1_verification.json` 中五条 trace 都有 Document、PDF SHA-256、Chunk、页码、Passage、正式 Version、repository、shelf mark、source URL 与 persistent identifier，且脚本报告所有五条有页码、PDF、Version、source URL 与 Document。

但是该同一运行产物的五条事实均为：

```text
source_ref_id: null
source_ref_url: null
```

因此本轮不能证明每条回答 Citation 已连接 SourceRef，更不能完成用户要求的五事实 Citation→Evidence→SourceRef→Document→Version→PDF 页码→原文一致核验。PDF 实际打开、原文逐字比对、删除 Document 后失效，均为 **Evidence Missing**。

**Academic Trust Score：★★☆☆☆。** 后端形成有页码和版本元数据的五条内部 trace，且撤回阻断 trace 得到运行证明；但普通用户看不到结果，五条事实缺少 SourceRef，PDF/原文和删除/Withdraw 的端到端失效对照未完成。

## 6. 文献采集、后台能力与页面矩阵

文献采集的创建任务、下载、解析、OCR、写库、索引、进入 RAG 的连续运行证据：**Evidence Missing**。  
版本管理、全文审核、OCR、Citation、Evidence、Groundedness、Research Assistant、Knowledge Synthesis、Academic Report、Education Mode、Knowledge Intelligence、Visualization、Research Workflow 的逐项 A/B/C/D 真实操作矩阵：除本报告已记录的后端工作流成功和浏览器工作流失败外，均为 **Evidence Missing**。

## 7. P0 / P1 / P2 复核

| 等级 | 复核结果 | 直接证据 |
|---|---|---|
| P0：启动与依赖就绪 | 已通过 | compose 四服务健康；`IMPORT_OK`；health/ready 200 |
| P0：后端证据综合失败 | 已修复 | 固定请求 14.15 秒成功；5 claims、5 export citations |
| P0：普通用户研究页面 | **未修复** | 页面 10 秒超时，`net::ERR_ABORTED` |
| P1：五条正式 Citation 的 SourceRef 链 | **未通过** | 五条事实 `source_ref_id=null`、`source_ref_url=null` |
| P1：Withdraw 内部 trace 阻断 | 已通过 | Withdraw 后 `TRACE_LINEAGE_INCOMPLETE`，restore 后恢复 5 traces |
| P1：删除 Document 与 Withdraw 的端到端消失 | Evidence Missing | 未执行页面/检索/既有 Citation 前后对照 |
| P1：P2T1 脚本可结束 | 已通过 | 脚本退出并输出 `FINAL: PASS` |
| P2：全页面与后台矩阵 | Evidence Missing | 本轮未完成逐项实际操作 |

## 8. 评分

| 维度 | 评分 | 理由 |
|---|---|---|
| 环境真实性 | ★★★★☆ | 容器、导入、health、ready、前端首页均有运行证据 |
| 数据真实性 | ★★★☆☆ | 已直接计数并有五条 trace；未完成全部表、Seed/测试数据拆分 |
| 页面真实性 | ★★☆☆☆ | 首页、登录、V4 页面真实访问；核心页面超时且无全页矩阵 |
| 研究流程真实性 | ★★☆☆☆ | 后端完成，真实用户页面中断 |
| Evidence 真实性 | ★★★☆☆ | 内部 trace 有页码与版本；页面未展示或核验 |
| Citation 真实性 | ★★☆☆☆ | 生成计数存在，但五条事实缺 SourceRef |
| Academic Trust | ★★☆☆☆ | 关键来源链与端到端核验不完整 |
| 报告真实性 | ★★★★★ | 关键通过、失败与缺失项均标明本轮运行证据 |

## 9. Claude 报告错误清单、遗漏项与最终决定

若 Claude 以 `scripts/p2t1_verify.py` 的 `FINAL: PASS`、后端 HTTP 200 或 Citation 数量作为“全部真实可用”的依据，则遗漏了两项相反的本轮运行事实：浏览器在 10 秒中止请求，以及全部五条审计事实缺少 SourceRef。全页面矩阵、采集/OCR 链、PDF/原文比对、删除 Document 对照和 Withdraw 的页面级对照亦未提供。

**最终：C — 不通过 / BLOCK_RELEASE。** 解除条件：普通用户页面在后端实际耗时内等待或采用可观察异步任务，并真实渲染可验证结果；每条正式 Citation 补齐 SourceRef；完成 PDF/原文、删除与 Withdraw 的端到端对照，以及全页面和后台能力矩阵。

## 10. 批次一复验（2026-07-15）

**批次一：不通过。**

本轮按 README 启动依赖容器；容器均健康。以本地 `uvicorn` 和前端 dev-server 的受控启动会话访问首页，`/health` 与首页均为 HTTP 200，普通用户 `researcher` 成功登录，并真实进入 `/v4/research`。

提交固定问题后，浏览器快照 `.playwright-cli/page-2026-07-14T21-24-19-749Z.yml` 显示：

```text
正在执行工作流，预计需 10-20 秒，请耐心等待...
已用时 6 秒...
```

这证明页面不再立即显示上一轮的 `timeout of 10000ms exceeded`，但本轮没有取得完成后的回答正文、Citation、报告、导出入口或不含 `net::ERR_ABORTED` 的最终网络记录。故不能判定普通用户流程已修复。

环境阻塞同时记录如下：`docker compose -f docker-compose.dev.yml up -d backend frontend` 在拉取 `python:3.12-slim` 时因 Docker Hub TLS 证书验证失败；受控本地服务会话结束后端口不保活。两者均不替代所需的页面完成证据。

**批次一最小补证：** 在一个可持续的本地运行环境中，普通用户真实提交固定问题并等待至完成，保存最终页面快照/截图、网络请求状态和响应体，页面必须实际显示回答、可展开 Citation、报告和导出入口。

## 11. 已保存任务状态

| 项目 | 已保存状态 |
|---|---|
| 当前验收门禁 | **C / BLOCK_RELEASE** |
| 当前基线 | `cbdb448d58bbb4df5f82b41e61b8da7a15cda6a9`，worktree 非干净 |
| 已验证通过 | 依赖容器健康；后端导入、health、ready；固定问题后端工作流；P2T1 脚本；内部 Withdraw trace 阻断与 restore |
| 批次一状态 | **未通过**：普通用户页面仅取得“执行中”证据，未取得完成态证据 |
| 批次二状态 | 未开始验收；五条事实 `source_ref_id` 与 `source_ref_url` 仍为 null |
| 批次三状态 | 未开始验收；删除 Document、Withdraw 的页面/API/检索端到端前后对照缺失 |
| 批次四状态 | 未开始验收；全页面、后台能力、采集/OCR 和逐表数据矩阵缺失 |
| 下次验收入口 | 优先重验批次一：使用可持续本地前后端，普通用户完成固定问题并保存最终浏览器与网络证据 |
