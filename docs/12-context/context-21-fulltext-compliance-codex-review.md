# Context 21: 全文入库合规机制 Codex 验收

**验收日期:** 2026-07-10  
**验收范围:** 当前工作区 `/Users/likeming/Sites/hfb`  
**HEAD:** `5a09c0c`  
**结论:** **BLOCK_RELEASE**

## 总结

当前“外部文献元数据采集器”专项测试通过，能证明 OpenAlex/Crossref/CORE/PubMed/Internet Archive 采集器不主动下载 PDF/全文，且 `_save_items()` 不写入 `Paper.full_text`。

但这不能证明“全文入库机制”合规。当前仍存在可用全文入口 `IngestionService.ingest_text()` / `ingest_pdf()` / `POST /api/v1/search/ingest`，它们没有版权确认、`metadata_only`、`forbidden_fulltext`、checksum、持久审计、撤回清理门禁。实测未确认版权全文可以被保存到 `documents.content_text`，切块进入 `document_chunks`，并被检索/RAG 路径命中。

## 逐项验收

| 验收项 | 结论 | 证据 |
|---|---|---|
| 未确认版权全文是否无法进入 RAG | **FAIL** | `apps/backend/app/services/ingestion.py:62-125` 只校验文本非空和 passage 存在，然后保存 `content_text` 并创建 `DocumentChunk`；无版权状态判断。探针显示 `copyright_status=unknown` 语义的全文仍 `retrieval_hits=1`。 |
| `forbidden_fulltext` 是否被拒绝 | **FAIL** | `ingest_text()` 只允许 metadata 中的 `dynasty/category/source_url/raw_pdf_blob`，`forbidden_fulltext` 被静默丢弃；没有拒绝逻辑。探针显示 `forbidden_fulltext=True` 仍创建文档和 chunk。 |
| `metadata_only` 是否不能上传全文 | **FAIL** | API schema `apps/backend/app/schemas/chunk_search.py:68-76` 只有 `title/text/dynasty/category/max_chunk_chars`，没有 `metadata_only`/版权字段；服务层也没有该状态机。 |
| 撤回后是否从向量库移除 | **FAIL** | 当前没有真实向量库，`RAGService` 注释仍是 “Vector retrieval: reserved”。更严重的是 `RetrievalService.search()` 只过滤 `DocumentChunk.is_deleted`，不过滤父 `Document.is_deleted`（`apps/backend/app/services/retrieval.py:83-101`）。探针显示父文档软删除后仍可检索：`after_document_soft_delete_hits=1`；只有 chunk 自身软删除才为 `0`。 |
| 是否有审计日志 | **FAIL / partial** | 文献元数据采集器有内存态 `IngestionJob` dataclass（`apps/backend/app/services/literature_ingestion/__init__.py:75-97`），但不是持久表，也不覆盖全文入口。设计文档中的 `IngestionItem` 审计模型只在 `docs/03-data/...` 中存在，后端代码未落地。 |
| 是否有 checksum | **FAIL / partial** | `AcademicRAGResponse` 有 `corpus_sha256/output_sha256`，但全文入库对象 `Document`/`DocumentChunk` 没有 `checksum/content_hash/sha256` 字段；探针显示 `has_checksum_attr=False`。 |
| 是否测试通过 | **PARTIAL** | `uv run pytest tests/unit/test_literature_ingestion_compliance.py -q` 结果 `21 passed`；`uv run pytest tests/unit/test_day2_ingestion_search.py::TestIngestion::test_ingest_text_creates_document_and_chunks tests/unit/test_day2_ingestion_search.py::TestIngestion::test_pdf_raw_source_traceable tests/unit/test_day4_generation.py::test_deleted_chunk_not_returned_by_retrieval -q` 结果 `3 passed`。这些测试未覆盖版权门禁、metadata_only 拒绝、forbidden_fulltext 拒绝、父文档撤回清理和入库 checksum。 |

## 关键文件证据

- `apps/backend/app/models/document.py:35-37`: `Document` 直接包含 `content_text` 和 `raw_pdf_blob`，但没有 `copyright_status`、`authorization_basis`、`review_status`、`checksum`。
- `apps/backend/app/models/document_chunk.py:28-51`: `DocumentChunk` 存储可检索全文片段，但没有版权状态、撤回状态、checksum。
- `apps/backend/app/services/ingestion.py:24`: metadata 白名单只有 `dynasty/category/source_url/raw_pdf_blob`。
- `apps/backend/app/services/ingestion.py:107-125`: 任意非空文本会被写入 `content_text` 并切块。
- `apps/backend/app/services/ingestion.py:176-183`: PDF 默认保存 `raw_pdf_blob` 并转入 `ingest_text()`，无版权门禁。
- `apps/backend/app/api/v1/day2_search.py:117-136`: `/search/ingest` 只传 `title/text/dynasty/category/max_chunk_chars`，无授权字段。
- `tests/unit/test_literature_ingestion_compliance.py:149-258`: 现有测试证明“外部采集器不下载/不写入论文全文”，但不覆盖通用全文入库门禁。
- `docs/07-compliance/literature-source-policy.md:34-43`: 商业数据库仅可采集元数据，禁止下载、缓存或索引全文。
- `docs/07-compliance/literature-source-policy.md:90-105`: 存储审计要求包括采集时间、来源 URL、许可依据、审核状态、审核人等。
- `docs/03-data/huangfu-mi-literature-data-model.md:397-404`: 设计要求未知版权只能 metadata-only，`copyright_status` 非 `public_domain/licensed` 时全文字段必须为空。
- `docs/03-data/huangfu-mi-literature-data-model.md:994-1001`: 设计要求 `metadata_harvest` 与 `fulltext_download` 分离，全文下载前检查平台和版权判定，不满足则 `skipped` 并记录原因。

## 实测探针

### 1. 未确认/禁止/metadata-only 语义全文仍进入 RAG 检索

命令：

```bash
uv run python - <<'PY'
import asyncio, sys
sys.path.insert(0, 'apps/backend')
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.ingestion import IngestionService
from app.services.retrieval import RetrievalService

async def main():
    engine = create_async_engine('sqlite+aiosqlite://', echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        svc = IngestionService(session)
        result = await svc.ingest_text(
            title='forbidden_fulltext_probe',
            text='FORBIDDEN_FULLTEXT_SENTINEL 未确认版权全文内容，理论上不应进入 RAG。',
            metadata={
                'source_url': 'https://commercial.example/paid',
                'copyright_status': 'unknown',
                'fulltext_status': 'metadata_only',
                'forbidden_fulltext': True,
                'checksum': 'caller-supplied-ignored',
            },
            max_chunk_chars=200,
        )
        await session.flush()
        doc = (await session.execute(select(Document).where(Document.id == result.document_id))).scalar_one()
        chunks = (await session.execute(select(DocumentChunk).where(DocumentChunk.document_id == result.document_id))).scalars().all()
        search = await RetrievalService(session).search('FORBIDDEN_FULLTEXT_SENTINEL', top_k=5)
        print('created_document=', bool(doc.id))
        print('document_content_has_sentinel=', 'FORBIDDEN_FULLTEXT_SENTINEL' in (doc.content_text or ''))
        print('chunk_count=', len(chunks))
        print('retrieval_hits=', len(search.results))
        print('stored_source_url=', doc.source_url)
        print('has_copyright_attr=', hasattr(doc, 'copyright_status'))
        print('has_checksum_attr=', hasattr(doc, 'checksum') or hasattr(doc, 'content_hash') or hasattr(doc, 'sha256'))
        print('first_hit_content=', search.results[0].content if search.results else '')

asyncio.run(main())
PY
```

输出：

```text
created_document= True
document_content_has_sentinel= True
chunk_count= 1
retrieval_hits= 1
stored_source_url= https://commercial.example/paid
has_copyright_attr= False
has_checksum_attr= False
first_hit_content= FORBIDDEN_FULLTEXT_SENTINEL 未确认版权全文内容，理论上不应进入 RAG。
```

### 2. 父文档撤回后 chunk 仍可检索

输出：

```text
before_hits= 1
after_document_soft_delete_hits= 1
after_chunk_soft_delete_hits= 0
chunk_count= 1
```

含义：如果撤回只落到 `Document.is_deleted=True`，当前检索仍会返回全文 chunk；必须同步删除/软删除 chunks，且查询层也应过滤父文档状态。

## 测试结果

```text
$ uv run pytest tests/unit/test_literature_ingestion_compliance.py -q
21 passed in 1.28s

$ uv run pytest tests/unit/test_day2_ingestion_search.py::TestIngestion::test_ingest_text_creates_document_and_chunks tests/unit/test_day2_ingestion_search.py::TestIngestion::test_pdf_raw_source_traceable tests/unit/test_day4_generation.py::test_deleted_chunk_not_returned_by_retrieval -q
3 passed in 1.28s
```

## 最小阻塞集

1. 落地可执行的全文合规模型/字段：至少需要 `copyright_status`、`authorization_basis/license_basis`、`review_status`、`reviewed_by/reviewed_at`、`source_url`、`content_checksum/text_hash`，并用 DB check constraint 或服务层强门禁保证未知/未授权版权时全文字段为空。
2. 把 `metadata_harvest` 与 `fulltext_ingest/download` 分离。`metadata_only` 和 `forbidden_fulltext` 必须在 API schema、服务层和测试中显式表达并拒绝全文。
3. 全文进入 `DocumentChunk` / RAG / 后续向量索引前必须通过同一版权门禁；不能只让外部文献采集器不下载 PDF。
4. 实现持久审计日志，记录每条全文入库/拒绝/跳过/撤回的来源、许可依据、审核人、审核时间、checksum、结果实体。
5. 实现撤回/删除工作流：撤回全文时同步移除或软删除 chunks、向量索引项和缓存；检索层必须同时过滤 `Document.is_deleted` 与 `DocumentChunk.is_deleted`。
6. 补测试：未确认版权全文拒绝、`forbidden_fulltext` 拒绝、`metadata_only + text` 拒绝、授权全文成功、checksum 持久化且可复算、撤回后 RAG/检索/向量均不可命中、审计日志存在。

## 最终门禁

**BLOCK_RELEASE**

当前只能认为“外部文献元数据采集器不下载全文”局部通过；“全文入库机制合规”未通过，且未确认版权全文可以经现有通用全文入口进入 RAG 检索。
