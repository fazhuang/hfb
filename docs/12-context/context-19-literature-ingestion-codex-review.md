# Context 19: 文献元数据采集器 Codex 再次验收

**验收日期:** 2026-07-10
**验收对象:** `apps/backend/app/services/literature_ingestion/`、`scripts/run_ingestion.py`、`tests/unit/test_literature_ingestion_*.py`、`backend/pyproject.toml`
**必须测试命令:** `cd backend && uv run pytest`
**结论:** **PASS**

## 结论摘要

当前 worktree 已关闭上一轮阻塞项，可以按本轮验收口径放行。

本次重新验收确认：

1. `cd backend && uv run pytest` 已能发现并运行测试，不再是 0 tests。
2. 采集器只构造并保存元数据字段，没有 PDF 下载、PDF 字节缓存或全文写入路径。
3. `source_url` 已在 `LiteratureItem` 构造阶段强制非空且必须为 HTTP(S) URL。
4. CORE 不再把 `downloadUrl` 保存为主 `source_url`，而是保存 `https://core.ac.uk/works/{id}`。
5. DOI 去重大小写不敏感；无 DOI 记录已按规范化 `title + year` 去重，并在保存阶段二次检查。
6. `session.flush()` 失败会记录到 `job.error_count` 和 `job.errors`，失败 job 不会被标记为成功。
7. 采集器专项测试和仓库全量测试均通过。

当前门禁：**PASS**。

## 验收矩阵

| 验收项                      | 结论 | 证据                                                                                                                                                                                                                |
| --------------------------- | ---: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 是否真的只采集元数据        | PASS | `LiteratureItem` 只定义 title、source_url、source、authors、year、abstract、keywords、doi、journal、is_open_access、language；`_save_items()` 只写入 `Paper` 的元数据字段，未写 `Paper.full_text`。                 |
| 是否没有下载 PDF            | PASS | OpenAlex、Crossref、CORE、PubMed/Europe PMC、Internet Archive 客户端只调用搜索/元数据 API；专项测试扫描客户端源码，禁止 `.pdf`、`fulltext`、`full_text`、`full text`、`download.pdf` 请求痕迹。                     |
| 是否没有绕过登录            | PASS | 未发现 cookie、账号密码登录、付费墙绕过、模拟登录逻辑。CORE 仅在存在 `CORE_API_KEY` 时使用官方 `Authorization: Bearer` API key。                                                                                    |
| 是否每条记录有 `source_url` | PASS | `LiteratureItem.__post_init__()` 拒绝空 title/source/source_url，并要求 `source_url` 以 `http://` 或 `https://` 开头；客户端统一通过 `try_create()` 丢弃非法记录；`_save_items()` 保存前再次拒绝空 `source_url`。   |
| 是否去重可靠                | PASS | `dedup_key()` 对 DOI 做小写规范化；无 DOI 记录使用规范化标题和年份。`filter_new_items()` 对 DB 现有无 DOI 记录执行规范化 title/year 比较；`_save_items()` 保存阶段也对无 DOI 记录二次检查，避免绕过过滤后重复入库。 |
| 是否失败状态正确            | PASS | `IngestionJob.finish()` 仅在 `error_count == 0` 时 `success=True`；未知 source、页面错误、保存异常、flush 失败都会增加 `error_count` 并记录 `errors`。                                                              |
| 是否有测试覆盖              | PASS | 采集器专项测试增至 43 个，覆盖 source_url 非空/URL 校验、CORE work URL、无全文字段、无 PDF/fulltext 请求痕迹、大小写/空白去重、保存阶段去重、flush 失败状态。                                                       |
| 是否全量测试通过            | PASS | 必须命令 `cd backend && uv run pytest` 通过；仓库根 `uv run pytest` 也通过。                                                                                                                                        |

## 关键源码证据

### source_url 强制校验

- `apps/backend/app/services/literature_ingestion/__init__.py:39-48`：`__post_init__()` 拒绝空 title、空 source、空 source_url，并要求 HTTP(S) URL。
- `apps/backend/app/services/literature_ingestion/__init__.py:62-68`：`try_create()` 对非法记录返回 `None`，客户端不会把非法 item 加入结果。
- `apps/backend/app/services/literature_ingestion/orchestrator.py:139-143`：保存前再次拒绝空 `source_url` 并记录 job error。

### 元数据-only 与不下载 PDF

- `apps/backend/app/services/literature_ingestion/__init__.py:23-37`：标准化记录没有 full_text、pdf_data、download_url 字段。
- `apps/backend/app/services/literature_ingestion/orchestrator.py:176-186`：保存 `Paper` 时只写 title、authors、year、abstract、keywords、doi、source_url、journal、language。
- `tests/unit/test_literature_ingestion_compliance.py:149-175`：测试确认客户端返回 `LiteratureItem`，不是全文或原始文本。
- `tests/unit/test_literature_ingestion_compliance.py:177-195`：测试扫描客户端源码，不允许 PDF/fulltext 请求痕迹。

### CORE downloadUrl 边界

- `apps/backend/app/services/literature_ingestion/core_client.py:52-64`：`source_url` 使用 `https://core.ac.uk/works/{id}`；`downloadUrl` 只用于 `is_open_access` 布尔判断，没有保存为主来源 URL。
- `tests/unit/test_literature_ingestion_compliance.py:197-208`：测试约束 CORE 使用 work/detail URL，不把 `downloadUrl` 作为 `source_url`。

### 去重可靠性

- `apps/backend/app/services/literature_ingestion/__init__.py:50-60`：统一 dedup key 和 `normalized_title()` 逻辑。
- `apps/backend/app/services/literature_ingestion/__init__.py:134-171`：DB 过滤使用大小写不敏感 DOI 和规范化 title/year。
- `apps/backend/app/services/literature_ingestion/orchestrator.py:145-174`：保存阶段复查 DOI；无 DOI 记录按规范化 title/year 二次检查。
- `tests/unit/test_literature_ingestion_dedup.py:132-197`：覆盖 DOI 大小写、title/year 大小写和空白差异。
- `tests/unit/test_literature_ingestion_dedup.py:235-265`：覆盖跨来源 title 规范化 dedup key。

### 失败状态

- `apps/backend/app/services/literature_ingestion/__init__.py:94-97`：`finish()` 以 `error_count == 0` 判定 success。
- `apps/backend/app/services/literature_ingestion/orchestrator.py:193-198`：`session.flush()` 失败会增加 `error_count` 并写入 `Flush failed` 错误。
- `tests/unit/test_literature_ingestion_compliance.py:303-337`：覆盖 flush 失败时 job error 状态。

## 测试结果

### 必须命令

```bash
cd backend && uv run pytest
```

结果：

```text
835 passed, 13 skipped, 1 xfailed, 1 warning in 108.41s
```

说明：命令已不再收集 0 项测试。唯一 warning 是 `PytestUnknownMarkWarning: real_llm`，来源于 `backend/pyproject.toml` 未注册 marker；该 warning 未使测试失败，但建议后续补齐 marker 配置以保持与根目录 `pytest.ini` 一致。

### 采集器专项测试

```bash
uv run pytest tests/unit/test_literature_ingestion_metadata.py tests/unit/test_literature_ingestion_dedup.py tests/unit/test_literature_ingestion_compliance.py -q
```

结果：

```text
43 passed in 2.17s
```

### 仓库根全量测试

```bash
uv run pytest
```

结果：

```text
835 passed, 13 skipped, 1 deselected in 108.37s
```

## 已关闭阻塞项

### P0-1 `source_url` 未强制非空

已关闭。构造阶段、客户端 `try_create()` 路径和保存阶段均已有保护；非法或空 URL 不会入库。

### P0-2 去重不可靠

已关闭。DOI 使用大小写不敏感匹配；无 DOI 记录使用规范化 title/year，并在过滤阶段和保存阶段都执行检查。

### P1-1 CORE 保存 `downloadUrl` 为 `source_url`

已关闭。CORE 主来源 URL 改为 work/detail 页面；没有保存 downloadUrl。

### P1-2 指定测试入口错误

已关闭。`backend/pyproject.toml` 使 `cd backend && uv run pytest` 能发现并运行 `../tests`。

## 残余建议

1. `backend/pyproject.toml` 目前没有注册 `real_llm` marker，所以指定命令会出现 1 个 warning。建议后续补齐 markers 配置，保持与根目录 `pytest.ini` 一致。
2. `backend/pyproject.toml` 缺少 `requires-python`，`uv` 会提示默认 `>=3.13`。这不阻塞本轮验收，但建议补齐以减少环境歧义。

## 最终门禁

**PASS**

当前 accepted baseline 是本次 worktree 中的文献元数据采集器实现、`backend/pyproject.toml` 测试入口、以及 43 个采集器专项测试。后续不要继续改动采集器来源边界、`source_url` 强制校验、CORE URL 策略和去重逻辑，除非开启新的验收项。
