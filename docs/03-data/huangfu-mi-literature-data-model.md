# 皇甫谧专题文献库 — 数据模型设计文档

**文档编号:** HFB-DESIGN-001
**版本:** 1.1
**日期:** 2026-07-10
**状态:** 设计草案（未执行）
**依赖:** 阶段 0 审计报告 (context-18)
**Codex 审查:** FAIL → 修订后待重新审查

---

## 目录

1. [SQLAlchemy 模型设计](#1-sqlalchemy-模型设计)
2. [Alembic 迁移草案](#2-alembic-迁移草案)
3. [API 设计草案](#3-api-设计草案)
4. [权限控制建议](#4-权限控制建议)
5. [与现有模型的关系](#5-与现有模型的关系)

---

## 1. SQLAlchemy 模型设计

所有新模型遵循现有代码规范：
- 继承 `BaseModel`（`id` UUID4 String(36) PK + `created_at` + `updated_at` + `deleted_at` + `is_deleted`）
- `mapped_column` + 中文 `comment`
- FK 使用 `ForeignKey("table.id", ondelete="...")` 模式
- `__tablename__` 使用复数 snake_case

### 1.1 SourcePlatform — 来源平台

```python
"""
SourcePlatform (来源平台) domain model.

记录文献数据的外部来源平台信息，包括平台名称、访问策略、
robots 协议、许可证说明等元数据。为合规采集提供平台级配置。

用于支撑：文献发现库、采集任务管理、版权合规审计。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class SourcePlatform(BaseModel):
    """外部数据来源平台注册表。"""

    __tablename__ = "source_platforms"

    name: Mapped[str] = mapped_column(
        String(200), nullable=False, unique=True, index=True, comment="平台名称"
    )
    url: Mapped[Optional[str]] = mapped_column(
        String(2000), nullable=True, comment="平台首页 URL"
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="web", server_default="web",
        comment="平台类型: web/library_api/academic_db/open_repository/digital_archive"
    )
    access_policy: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="访问策略说明（开放获取/注册访问/付费/IP限制）"
    )
    robots_policy: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="robots.txt 规则摘要及采集限制说明"
    )
    license_note: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="平台内容许可证说明（CC0/CC-BY/CC-BY-NC/自定义）"
    )
    is_allowed_for_metadata: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False,
        comment="是否允许采集元数据"
    )
    is_allowed_for_fulltext: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False,
        comment="是否允许采集全文。false 时 IngestionItem 不得执行 fulltext_download 或生成 FullTextDocument"
    )

    def __repr__(self) -> str:
        return f"<SourcePlatform id={self.id} name={self.name!r}>"
```

**字段说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | String(200) | ✅ | 平台名称，唯一索引 |
| `url` | String(2000) | | 平台首页 URL |
| `type` | String(50) | ✅ | web / library_api / academic_db / open_repository / digital_archive |
| `access_policy` | Text | | 访问策略说明 |
| `robots_policy` | Text | | robots.txt 规则摘要 |
| `license_note` | Text | | 平台内容许可证说明 |
| `is_allowed_for_metadata` | Boolean | ✅ | 是否允许采集元数据，默认 false |
| `is_allowed_for_fulltext` | Boolean | ✅ | 是否允许采集全文，默认 false。**这是全文采集的必要条件之一** |

**设计决策:**
- `type` 使用字符串而非枚举：外部平台类型会持续增长，字符串更灵活。ponytail: 如果平台类型超过 10 种且需要校验，再改为枚举。
- `robots_policy` 存文本摘要而非结构化规则：各平台 robots 格式差异大，摘要足够合规审计用。
- `is_allowed_for_*` 双重开关：允许元数据采集的平台未必允许全文采集（如 CNKI）。

---

### 1.2 LiteratureRecord — 文献记录

```python
"""
LiteratureRecord (文献记录) domain model.

统一的学术文献元数据记录，可表示期刊论文、会议论文、学位论文、
专著章节、预印本等多种出版类型。与 SourcePlatform 关联以追溯来源。

用于支撑：文献发现库、引文证据库。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.huangfu_meta import SourcePlatform
    from app.models.huangfu_meta import FullTextDocument


class LiteratureRecord(BaseModel):
    """学术文献元数据记录 — 统一的外部文献条目。"""

    __tablename__ = "literature_records"

    # --- 书目信息 ---
    title: Mapped[str] = mapped_column(
        String(1000), nullable=False, index=True, comment="文献标题"
    )
    original_title: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True, comment="原始语言标题（如英文文献的原题）"
    )
    authors: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="作者列表（JSON 数组字符串，含姓名+机构）。服务层必须校验 JSON 格式。推荐后续迁移到 JSONB。"
    )
    institutions: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="作者所属机构列表（JSON 数组字符串）。服务层必须校验 JSON 格式。推荐后续迁移到 JSONB。"
    )
    year: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="出版年份"
    )
    publication_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="journal_article", server_default="journal_article",
        comment="出版类型: journal_article/thesis/conference/book_chapter/preprint/report/other"
    )
    journal: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="期刊/会议/出版社名称"
    )
    publisher: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="出版社名称"
    )
    abstract: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="摘要"
    )
    keywords: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="关键词（JSON 数组字符串）"
    )

    # --- 标识符 ---
    doi: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, unique=True, index=True, comment="DOI 标识符"
    )
    external_id: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="外部系统 ID（如 PubMed ID、CNKI ID）"
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(2000), nullable=True, comment="来源 URL"
    )
    language: Mapped[str] = mapped_column(
        String(20), default="zh", server_default="zh", nullable=False, comment="文献语言"
    )

    # --- 来源追溯 ---
    source_platform_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("source_platforms.id", ondelete="SET NULL"), nullable=True,
        comment="来源平台 ID"
    )

    # --- 版权与状态 ---
    metadata_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft", server_default="draft",
        comment="元数据状态: draft/reviewed/approved/published/rejected"
    )
    copyright_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unknown", server_default="unknown",
        comment="版权状态: public_domain/in_copyright/orphan_work/licensed/unknown"
    )
    fulltext_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="none", server_default="none",
        comment="全文状态: none/metadata_only/abstract_only/open_access/authorized/embargoed"
    )

    # --- 关系 ---
    source_platform: Mapped[Optional["SourcePlatform"]] = relationship(
        "SourcePlatform", lazy="selectin"
    )
    full_text_documents: Mapped[list["FullTextDocument"]] = relationship(
        "FullTextDocument", back_populates="literature_record", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<LiteratureRecord id={self.id} title={self.title!r}>"
```

**字段说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | String(1000) | ✅ | 文献标题，索引 |
| `original_title` | String(1000) | | 原始语言标题 |
| `authors` | Text | | JSON 数组。服务层必须校验 JSON 格式；推荐后续迁移到 JSONB。 |
| `institutions` | Text | | JSON 数组。服务层必须校验 JSON 格式；推荐后续迁移到 JSONB。 |
| `year` | Integer | | 出版年份 |
| `publication_type` | String(50) | ✅ | journal_article/thesis/conference/book_chapter/preprint/report/other |
| `journal` | String(500) | | 期刊/会议/出版社名 |
| `publisher` | String(500) | | 出版社 |
| `abstract` | Text | | 摘要 |
| `keywords` | Text | | JSON 数组 |
| `doi` | String(500) | | 唯一索引 |
| `external_id` | String(500) | | 外部系统标识符 |
| `source_url` | String(2000) | | 来源链接 |
| `language` | String(20) | ✅ | 默认 "zh" |
| `source_platform_id` | FK | | → source_platforms.id |
| `metadata_status` | String(30) | ✅ | draft → reviewed → approved → published / rejected |
| `copyright_status` | String(50) | ✅ | public_domain / in_copyright / orphan_work / licensed / unknown |
| `fulltext_status` | String(30) | ✅ | none / metadata_only / abstract_only / open_access / authorized / embargoed |

**设计决策:**
- `authors` 存 JSON 字符串而非外键关联：外部文献的作者可能未在系统 Person 中注册，且批量导入时无需先创建 Person。ponytail: 需要作者实体关联时，通过 `authors` JSON 中的 name 匹配 Person 表。
- `metadata_status` 独立状态机：与 BaseModel 的软删除不同，这是学术审核流程的状态。
- `fulltext_status` 区分 6 种状态：embargoed（禁运期）和 authorized（授权访问）是不同的合规场景。
- `doi` 设唯一索引：天然的去重键。

---

### 1.3 VersionBibliography — 古籍版本目录学附属表

```python
"""
VersionBibliography (古籍版本目录学附属表) domain model.

**重要：这不是独立的古籍版本主表。** 系统的版本主数据仍然是 `Version` 模型。
VersionBibliography 是 Version 的 1:1 目录学扩展，记录与文本校勘无关的
馆藏信息、书影、公版状态、学术注记等版本目录学元数据。

版本谱系继续使用现有 VersionRelation。
段落对照继续使用现有 PassageMapping。
严禁新建第二套版本谱系或第二套古籍版本主路径。

用于支撑：版本目录库、馆藏管理、公版状态追踪。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.version import Version
    from app.models.huangfu_meta import FullTextDocument


class VersionBibliography(BaseModel):
    """Version 的 1:1 目录学扩展 — 不是独立版本主表。"""

    __tablename__ = "version_bibliographies"

    # --- 强制关联现有 Version ---
    version_id: Mapped[str] = mapped_column(
        ForeignKey("versions.id", ondelete="CASCADE"), nullable=False, unique=True,
        comment="关联的系统内 Version 记录 ID。NOT NULL + UNIQUE，确保 1:1 附属关系。"
    )

    # --- 馆藏信息 ---
    repository: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="收藏机构"
    )
    repository_location: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="收藏地（如'北京''上海'）"
    )
    shelf_mark: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="索书号"
    )

    # --- 数字化 ---
    source_url: Mapped[Optional[str]] = mapped_column(
        String(2000), nullable=True, comment="数字影像来源 URL"
    )
    image_url: Mapped[Optional[str]] = mapped_column(
        String(2000), nullable=True, comment="书影/卷端图片 URL"
    )
    ocr_text_available: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False,
        comment="是否已有 OCR 文本"
    )

    # --- 版权 ---
    public_domain_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="needs_investigation",
        server_default="needs_investigation",
        comment="公版状态: confirmed_public_domain/likely_public_domain/needs_investigation/in_copyright。"
                "默认 needs_investigation，人工确认后方可升级为 confirmed_public_domain。"
    )

    # --- 版权判定记录 ---
    copyright_decision: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="版权判定结论: public_domain/licensed/in_copyright/orphan_work/unknown"
    )
    copyright_decision_basis: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="版权判定依据（如'作者卒于1802年，超过70年'、'CC0 声明 URL'）"
    )
    copyright_reviewed_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        comment="版权判定审核人 ID"
    )
    copyright_reviewed_at: Mapped[Optional[str]] = mapped_column(
        nullable=True, comment="版权判定审核时间"
    )

    # --- 学术注记 ---
    citation_note: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="标准引文格式注记"
    )
    academic_note: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="学术考释注记（版本源流、校勘价值等）"
    )

    # --- 关系 ---
    version: Mapped["Version"] = relationship("Version")
    full_text_documents: Mapped[list["FullTextDocument"]] = relationship(
        "FullTextDocument", back_populates="version_bibliography", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<VersionBibliography id={self.id} version_id={self.version_id!r}>"
```

**字段说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `version_id` | FK | ✅ | → versions.id，**NOT NULL + UNIQUE**。强制 1:1 附属关系。这是关键约束。 |
| `repository` | String(500) | | 收藏机构 |
| `repository_location` | String(200) | | 收藏地 |
| `shelf_mark` | String(200) | | 索书号 |
| `source_url` | String(2000) | | 数字影像 URL |
| `image_url` | String(2000) | | 书影 URL |
| `ocr_text_available` | Boolean | ✅ | 默认 false |
| `public_domain_status` | String(50) | ✅ | **默认 `needs_investigation`**（不是 `confirmed_public_domain`）。人工确认后方可升级。 |
| `copyright_decision` | String(50) | | 版权判定结论 |
| `copyright_decision_basis` | Text | | 版权判定依据 |
| `copyright_reviewed_by` | FK | | → users.id |
| `copyright_reviewed_at` | String(100) | | 审核时间 |
| `citation_note` | Text | | 标准引文注记 |
| `academic_note` | Text | | 学术考释注记 |

**设计决策（P0-2 修订）:**
- **这是附属表，不是独立版本主表。** 系统的版本主数据仍然是 `Version`。`VersionBibliography` 只存储与文本校勘无关的目录学元数据。
- `version_id` 为 NOT NULL + UNIQUE，确保每条目录学记录必须对应一个现有 Version，且 1:1。
- **不再重复 Version 已有字段**（work_title、version_name、dynasty、year、edition_type 均在 Version 中）。
- 版本谱系继续使用现有 `VersionRelation`。
- 段落对照继续使用现有 `PassageMapping`。
- **严禁新建第二套版本谱系或第二套古籍版本主路径。**
- `public_domain_status` 默认改为 `needs_investigation`（P1 非阻塞修正），人工确认后方可升级为 `confirmed_public_domain`。
- 新增 `copyright_decision`、`copyright_decision_basis`、`copyright_reviewed_by`、`copyright_reviewed_at` 字段用于记录版权判定过程。

---

### 1.4 FullTextDocument — 合规全文

```python
"""
FullTextDocument (合规全文) domain model.

存储合规获取的全文文档，包括文件路径、文本内容、OCR 状态、
许可证、版权状态等合规元数据。

**版权门控（P0-1 修订）：**
- text_content 和 file_path 只有在 copyright_status IN ('public_domain', 'licensed')
  且 authorization_basis 非空时才允许非空。
- copyright_status IN ('unknown', 'in_copyright', 'orphan_work') 时，
  text_content 和 file_path 必须为 NULL —— 只能保存元数据、摘要、DOI、source_url。
- SourcePlatform.is_allowed_for_fulltext=false 时，采集任务不得生成 FullTextDocument。
- access_level 只是访问控制，不是入库许可。
- 未知版权来源只能创建 metadata-only 记录。

用于支撑：合规全文库、全文检索、引文证据提取。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, CheckConstraint, Float, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.huangfu_meta import LiteratureRecord
    from app.models.huangfu_meta import VersionBibliography
    from app.models.huangfu_meta import IngestionJob


class FullTextDocument(BaseModel):
    """合规全文文档记录。"""

    __tablename__ = "full_text_documents"

    __table_args__ = (
        # source FK: exactly one of literature_record_id / version_bibliography_id must be non-null
        CheckConstraint(
            "(literature_record_id IS NOT NULL AND version_bibliography_id IS NULL) OR "
            "(literature_record_id IS NULL AND version_bibliography_id IS NOT NULL)",
            name="ck_full_text_documents_exactly_one_source",
        ),
        # 版权门控：text_content 非空 → copyright_status 必须是 public_domain 或 licensed，且 authorization_basis 非空
        CheckConstraint(
            "text_content IS NULL OR ("
            "  copyright_status IN ('public_domain', 'licensed')"
            "  AND authorization_basis IS NOT NULL"
            ")",
            name="ck_full_text_documents_text_content_copyright_gate",
        ),
        # 版权门控：file_path 非空 → 同上
        CheckConstraint(
            "file_path IS NULL OR ("
            "  copyright_status IN ('public_domain', 'licensed')"
            "  AND authorization_basis IS NOT NULL"
            ")",
            name="ck_full_text_documents_file_path_copyright_gate",
        ),
    )

    # --- 关联 ---
    literature_record_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("literature_records.id", ondelete="SET NULL"), nullable=True,
        comment="关联的文献记录 ID（现代论文）"
    )
    version_bibliography_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("version_bibliographies.id", ondelete="SET NULL"), nullable=True,
        comment="关联的版本目录学记录 ID（古籍）"
    )
    ingestion_job_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("ingestion_jobs.id", ondelete="SET NULL"), nullable=True,
        comment="关联的采集任务 ID"
    )

    # --- 文件信息 ---
    file_path: Mapped[Optional[str]] = mapped_column(
        String(2000), nullable=True,
        comment="文件存储路径（MinIO object key）。受 ck_full_text_documents_file_path_copyright_gate 约束。"
    )
    file_format: Mapped[str] = mapped_column(
        String(20), nullable=False, default="txt", server_default="txt",
        comment="文件格式: txt/pdf/djvu/docx/html/markdown"
    )
    file_size: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="文件大小（字节）"
    )
    page_count: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="页数"
    )

    # --- 文本内容 ---
    text_content: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="全文文本内容（纯文本/OCR 结果）。受 ck_full_text_documents_text_content_copyright_gate 约束。"
    )
    text_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True, comment="文本内容 SHA-256 哈希"
    )

    # --- OCR ---
    ocr_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="none", server_default="none",
        comment="OCR 状态: none/pending/processing/done/manual_review/failed"
    )
    ocr_engine: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="OCR 引擎名称及版本"
    )
    ocr_confidence: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="OCR 平均置信度 (0.0-1.0)"
    )

    # --- 版权与许可证 ---
    license_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unknown", server_default="unknown",
        comment="许可证类型: cc0/cc_by/cc_by_nc/cc_by_nc_sa/custom/public_domain/unknown"
    )
    copyright_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unknown", server_default="unknown",
        comment="版权状态: public_domain/in_copyright/orphan_work/licensed/unknown。"
                "public_domain 或 licensed 才允许保存全文。"
    )
    authorization_basis: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="授权依据（如'CC0 声明 URL'、'与版权方签署的授权协议编号'、'公版确认依据'）。"
                "copyright_status IN ('public_domain','licensed') 时必填；是 text_content/file_path 非空的前提条件。"
    )
    access_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="restricted", server_default="restricted",
        comment="访问级别: open/registered/restricted/embargoed。"
                "注意：这只是访问控制，不是入库许可。入库许可由 copyright_status + authorization_basis 决定。"
    )

    # --- 采集 ---
    ingestion_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending", server_default="pending",
        comment="入库状态: pending/ingesting/ingested/verified/rejected"
    )

    # --- 关系 ---
    literature_record: Mapped[Optional["LiteratureRecord"]] = relationship(
        "LiteratureRecord", back_populates="full_text_documents"
    )
    version_bibliography: Mapped[Optional["VersionBibliography"]] = relationship(
        "VersionBibliography", back_populates="full_text_documents"
    )
    ingestion_job: Mapped[Optional["IngestionJob"]] = relationship(
        "IngestionJob", back_populates="full_text_documents", foreign_keys=[ingestion_job_id]
    )

    def __repr__(self) -> str:
        return f"<FullTextDocument id={self.id} format={self.file_format!r}>"
```

**字段说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `literature_record_id` | FK | | → literature_records.id。与 `version_bibliography_id` exactly one 互斥。 |
| `version_bibliography_id` | FK | | → version_bibliographies.id。与 `literature_record_id` exactly one 互斥。 |
| `ingestion_job_id` | FK | | → ingestion_jobs.id |
| `file_path` | String(2000) | | MinIO object key。受 copyright gate 约束。 |
| `file_format` | String(20) | ✅ | txt/pdf/djvu/docx/html/markdown |
| `file_size` | BigInteger | | 字节数 |
| `page_count` | Integer | | 页数 |
| `text_content` | Text | | 全文纯文本。受 copyright gate 约束。 |
| `text_hash` | String(64) | | SHA-256，索引（去重） |
| `ocr_status` | String(30) | ✅ | none → pending → processing → done → manual_review / failed |
| `ocr_engine` | String(100) | | 引擎名+版本 |
| `ocr_confidence` | Float | | 平均置信度 |
| `license_type` | String(50) | ✅ | cc0/cc_by/cc_by_nc/cc_by_nc_sa/custom/public_domain/unknown |
| `copyright_status` | String(50) | ✅ | public_domain/in_copyright/orphan_work/licensed/unknown |
| `authorization_basis` | Text | | **版权授权依据。copyright_status IN ('public_domain','licensed') 时必填。** |
| `access_level` | String(20) | ✅ | 访问控制，不是入库许可。默认 restricted。 |
| `ingestion_status` | String(30) | ✅ | pending → ingesting → ingested → verified / rejected |

**设计决策（P0-1 修订）:**

**入库版权门控（数据库层 + 服务层双重保障）:**

| copyright_status | authorization_basis | text_content | file_path | 允许的操作 |
|---|---|---|---|---|
| `public_domain` | 非空 | **允许** | **允许** | 全文存储、OCR、检索 |
| `licensed` | 非空 | **允许** | **允许** | 按许可证范围使用 |
| `unknown` | NULL | **必须 NULL** | **必须 NULL** | 仅元数据、摘要、DOI、source_url、版权判定记录 |
| `in_copyright` | NULL | **必须 NULL** | **必须 NULL** | 仅元数据、摘要、DOI、source_url |
| `orphan_work` | NULL | **必须 NULL** | **必须 NULL** | 仅元数据、摘要、DOI、source_url、孤儿作品判定记录 |

**数据库层约束：**
- `ck_full_text_documents_text_content_copyright_gate`: `text_content IS NULL OR (copyright_status IN ('public_domain','licensed') AND authorization_basis IS NOT NULL)`
- `ck_full_text_documents_file_path_copyright_gate`: `file_path IS NULL OR (copyright_status IN ('public_domain','licensed') AND authorization_basis IS NOT NULL)`

**服务层约束（补充，无法在 CHECK 中表达）：**
- `copyright_status = 'unknown'` 的记录，即使 `license_type`/`authorization_basis` 有值，也不得写入 `text_content` 或 `file_path`
- `SourcePlatform.is_allowed_for_fulltext = false` 时，采集任务不得为此来源创建任何 `FullTextDocument`
- `access_level` 只是访问控制，不作为入库许可依据

**来源 FK 约束（P1 修正）:**
- `ck_full_text_documents_exactly_one_source`: `literature_record_id` 和 `version_bibliography_id` exactly one 非空（XOR）

---

### 1.5 EvidenceCitation — 引文证据

```python
"""
EvidenceCitation (引文证据) domain model.

记录从全文中提取的引文证据，包含原文引用、标准化文本、
定位信息、引文格式、置信度评分。

与现有 Evidence / Citation 的强桥接（P0-3 修订）：
- 每条 EvidenceCitation 可以通过 evidence_id FK 直接绑定到现有 Evidence。
- 状态流：extracted → draft → reviewed → promoted_to_evidence / rejected
- reviewed 之前不得进入 RAG、Graph、AcademicRelation、Citation 证据链。
- 引文定位优先绑定 existing Passage / Version；页码、行号只是补充定位。

用于支撑：引文证据库、版本校勘引用、RAG 上下文溯源。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class EvidenceCitation(BaseModel):
    """全文引文证据提取记录。"""

    __tablename__ = "evidence_citations"

    # --- 来源 ---
    document_id: Mapped[str] = mapped_column(
        ForeignKey("full_text_documents.id", ondelete="CASCADE"), nullable=False, index=True,
        comment="来源全文文档 ID"
    )

    # --- 状态流 ---
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="extracted", server_default="extracted", index=True,
        comment="状态: extracted → draft → reviewed → promoted_to_evidence / rejected。"
                "只有 reviewed 及以上才允许进入 RAG/Graph/Evidence 链。"
    )

    # --- 定位（优先绑定现有 Passage / Version）---
    passage_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("passages.id", ondelete="SET NULL"), nullable=True,
        comment="优先定位：关联的系统内 Passage ID。如 OCR 文本已映射到 Passage。"
    )
    version_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("versions.id", ondelete="SET NULL"), nullable=True,
        comment="优先定位：关联的系统内 Version ID。"
    )
    # 以下为补充定位，在 passage_id/version_id 不可用时使用
    page_number: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="补充定位：页码"
    )
    paragraph_index: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="补充定位：段落序号（从 1 开始）"
    )
    line_range: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="补充定位：行范围（如 '3-5'）"
    )

    # --- 内容 ---
    quote_text: Mapped[str] = mapped_column(
        Text, nullable=False, comment="引文原文"
    )
    normalized_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="标准化/标点化后的文本"
    )
    # context_before / context_after 同样受版权规则限制：
    # 当来源 FullTextDocument.copyright_status IN ('unknown','in_copyright','orphan_work') 时，
    # context_before 和 context_after 必须为空 —— 只能保存 quote_text 本身（合理引用）。
    context_before: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="引文前文（上下文）。受版权规则限制：未知/受限版权来源不得保存上下文。"
    )
    context_after: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="引文后文（上下文）。受版权规则限制：未知/受限版权来源不得保存上下文。"
    )

    # --- 链接 ---
    source_url: Mapped[Optional[str]] = mapped_column(
        String(2000), nullable=True, comment="来源 URL"
    )
    citation_format: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="引文格式: gb7714/chicago/apa/mla"
    )
    formatted_citation: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="格式化后的引文字符串"
    )

    # --- 与现有 Evidence 的强桥接（P0-3）---
    evidence_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("evidences.id", ondelete="SET NULL"), nullable=True, unique=True,
        comment="桥接到现有 Evidence 模型。promoted_to_evidence 时创建 Evidence 并回写此 FK。"
               "UNIQUE 确保一条 EvidenceCitation 只生成一条 Evidence。"
    )

    # --- 质量 ---
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="提取置信度 (0.0-1.0)"
    )
    extraction_method: Mapped[str] = mapped_column(
        String(30), nullable=False, default="manual", server_default="manual",
        comment="提取方式: manual/ocr/regex/llm/hybrid"
    )
    reviewed_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        comment="审核人 ID"
    )
    reviewed_at: Mapped[Optional[str]] = mapped_column(
        nullable=True, comment="审核时间"
    )

    # --- 关系 ---
    document: Mapped["FullTextDocument"] = relationship("FullTextDocument")
    passage: Mapped[Optional["Passage"]] = relationship("Passage")
    version: Mapped[Optional["Version"]] = relationship("Version")
    evidence: Mapped[Optional["Evidence"]] = relationship("Evidence")

    def __repr__(self) -> str:
        preview = (self.quote_text[:50] + "...") if len(self.quote_text) > 50 else self.quote_text
        return f"<EvidenceCitation id={self.id} status={self.status!r} quote={preview!r}>"
```

**字段说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `document_id` | FK | ✅ | → full_text_documents.id，级联删除 |
| `status` | String(30) | ✅ | **extracted → draft → reviewed → promoted_to_evidence / rejected** |
| `passage_id` | FK | | **优先定位**：→ passages.id |
| `version_id` | FK | | **优先定位**：→ versions.id |
| `page_number` | Integer | | 补充定位 |
| `paragraph_index` | Integer | | 补充定位 |
| `line_range` | String(50) | | 补充定位 |
| `quote_text` | Text | ✅ | 引文原文 |
| `normalized_text` | Text | | 标准化文本 |
| `context_before` | Text | | 前文上下文。**受版权规则限制。** |
| `context_after` | Text | | 后文上下文。**受版权规则限制。** |
| `source_url` | String(2000) | | 来源 URL |
| `citation_format` | String(100) | | gb7714/chicago/apa/mla |
| `formatted_citation` | Text | | 格式化引文 |
| `evidence_id` | FK | | **桥接现有 Evidence。UNIQUE**。promoted_to_evidence 时回写。 |
| `confidence_score` | Float | | 0.0-1.0 |
| `extraction_method` | String(30) | ✅ | manual/ocr/regex/llm/hybrid |
| `reviewed_by` | FK | | → users.id |
| `reviewed_at` | String(100) | | 审核时间 |

**设计决策（P0-3 修订）:**

**状态流与门控:**

```
extracted ──→ draft ──→ reviewed ──→ promoted_to_evidence
  │                        │                │
  └──(任何阶段)──→ rejected                 │
                                ┌───────────┘
                                │ 系统自动创建 Evidence 记录
                                │ 回写 EvidenceCitation.evidence_id
                                │ Evidence 进入 RAG / Graph / AcademicRelation / Citation 证据链
                                ▼
                          Evidence (existing)
```

- `extracted`: 自动提取完成，待人工整理
- `draft`: 人工整理格式和定位
- `reviewed`: 人工审核通过，**此时才允许进入下游消费**
- `promoted_to_evidence`: 系统自动创建对应的 `Evidence` 记录，回写 `evidence_id` FK。该 Evidence 随后可被现有 `Citation`、`AcademicRelation`、RAG 等引用。
- `rejected`: 审核不通过，**不得进入任何证据链**

**门控规则:**
- `status NOT IN ('reviewed', 'promoted_to_evidence')` → 不得进入 RAG、Graph、AcademicRelation、Citation 证据链
- `context_before`/`context_after` 受版权规则限制：当 `FullTextDocument.copyright_status IN ('unknown','in_copyright','orphan_work')` 时，服务层必须拒绝保存上下文，仅允许 `quote_text` 本身（合理引用）

**定位优先级:**
1. `passage_id` + `version_id`（优先：绑定系统内 Passage/Version）
2. `page_number` + `paragraph_index` + `line_range`（补充：物理页码定位）

---

### 1.6 IngestionJob — 采集任务（批次级）

```python
"""
IngestionJob (采集任务) domain model.

记录文献采集批次的执行信息，包括任务类型、查询参数、
来源平台、执行状态、结果统计。

每条采集目标的详细审计使用 IngestionItem（见 1.7）。

用于支撑：采集任务管理、批量导入追踪、错误重试。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.huangfu_meta import FullTextDocument
    from app.models.huangfu_meta import IngestionItem
    from app.models.user import User


class IngestionJob(BaseModel):
    """文献采集批次记录。"""

    __tablename__ = "ingestion_jobs"

    # --- 任务定义 ---
    job_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="任务类型: metadata_harvest/fulltext_download/ocr_pipeline/citation_extract/bulk_import"
    )
    query: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="查询参数/搜索词（JSON 字符串）"
    )
    source_platform_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("source_platforms.id", ondelete="SET NULL"), nullable=True,
        comment="来源平台 ID"
    )

    # --- 执行状态 ---
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending", server_default="pending", index=True,
        comment="批次状态: pending/running/completed/failed/cancelled/partial"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="开始时间"
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="完成时间"
    )

    # --- 结果统计（汇总自 IngestionItem）---
    result_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False, comment="成功采集条数"
    )
    error_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False, comment="错误条数"
    )
    skipped_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False, comment="跳过条数（重复/不符合条件）"
    )

    # --- 日志 ---
    log: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="执行日志（摘要或关键错误）"
    )

    # --- 操作人 ---
    created_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="创建人 ID"
    )

    # --- 关系 ---
    source_platform: Mapped[Optional["SourcePlatform"]] = relationship("SourcePlatform")
    creator: Mapped[Optional["User"]] = relationship("User")
    items: Mapped[list["IngestionItem"]] = relationship(
        "IngestionItem", back_populates="job", lazy="selectin"
    )
    full_text_documents: Mapped[list["FullTextDocument"]] = relationship(
        "FullTextDocument", back_populates="ingestion_job",
        foreign_keys="FullTextDocument.ingestion_job_id", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<IngestionJob id={self.id} type={self.job_type!r} status={self.status!r}>"
```

### 1.7 IngestionItem — 采集任务明细（P1-1 新增）

```python
"""
IngestionItem (采集任务明细) domain model.

每条采集目标的独立审计记录。一个 IngestionJob 包含多条 IngestionItem。

metadata_harvest 成功不代表 fulltext_download 可执行。
fulltext_download 必须依赖 SourcePlatform.is_allowed_for_fulltext 和版权判定结果。

用于支撑：item-level 采集审计、版权判定追踪、错误重试。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class IngestionItem(BaseModel):
    """采集任务明细 — 单条采集目标的完整审计记录。"""

    __tablename__ = "ingestion_items"

    # --- 关联 ---
    ingestion_job_id: Mapped[str] = mapped_column(
        ForeignKey("ingestion_jobs.id", ondelete="CASCADE"), nullable=False, index=True,
        comment="所属采集批次 ID"
    )
    source_platform_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("source_platforms.id", ondelete="SET NULL"), nullable=True,
        comment="来源平台 ID（可覆盖 Job 级设置）"
    )

    # --- 目标标识 ---
    target_url: Mapped[Optional[str]] = mapped_column(
        String(2000), nullable=True, comment="采集目标 URL"
    )
    target_identifier: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="采集目标标识符（DOI/ISBN/索书号）"
    )
    harvest_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="采集类型: metadata/fulltext/ocr/citation_extract。"
                "metadata 成功不等于 fulltext 可执行。"
    )

    # --- 执行状态 ---
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending", server_default="pending", index=True,
        comment="明细状态: pending/running/completed/failed/skipped/cancelled"
    )
    error_detail: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="结构化错误详情"
    )
    skipped_reason: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True,
        comment="跳过原因（如'重复DOI'、'平台不允许全文采集'、'版权不明'、'不在公版范围'）"
    )

    # --- 结果 ---
    result_entity_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="生成实体类型: literature_record/full_text_document/evidence_citation/none"
    )
    result_entity_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="生成实体 ID"
    )

    # --- 版权判定 ---
    copyright_decision: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="版权判定结论: public_domain/licensed/in_copyright/orphan_work/unknown/skipped"
    )
    copyright_decision_basis: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="版权判定依据（如'来源平台声明CC0'、'作者卒年>70年'、'未找到版权信息'）"
    )

    # --- 审核 ---
    reviewed_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="审核人 ID"
    )
    reviewed_at: Mapped[Optional[str]] = mapped_column(
        nullable=True, comment="审核时间"
    )

    # --- 关系 ---
    job: Mapped["IngestionJob"] = relationship("IngestionJob", back_populates="items")
    source_platform: Mapped[Optional["SourcePlatform"]] = relationship("SourcePlatform")

    def __repr__(self) -> str:
        return f"<IngestionItem id={self.id} type={self.harvest_type!r} status={self.status!r}>"
```

**字段说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `ingestion_job_id` | FK | ✅ | → ingestion_jobs.id，级联删除 |
| `source_platform_id` | FK | | → source_platforms.id |
| `target_url` | String(2000) | | 采集目标 URL |
| `target_identifier` | String(500) | | DOI/ISBN/索书号 |
| `harvest_type` | String(30) | ✅ | **metadata / fulltext / ocr / citation_extract** |
| `status` | String(30) | ✅ | pending → running → completed / failed / skipped / cancelled |
| `error_detail` | JSON | | 结构化错误 |
| `skipped_reason` | String(500) | | 跳过原因 |
| `result_entity_type` | String(50) | | 生成实体类型 |
| `result_entity_id` | String(36) | | 生成实体 ID |
| `copyright_decision` | String(50) | | 版权判定结论 |
| `copyright_decision_basis` | Text | | 版权判定依据 |
| `reviewed_by` | FK | | → users.id |
| `reviewed_at` | String(100) | | 审核时间 |

**设计决策（P1-1 修订）:**

- **metadata_harvest 与 fulltext_download 分离状态机：**
  - `metadata_harvest` 成功 → 生成 LiteratureRecord（status=completed），但 **不自动触发 fulltext_download**
  - `fulltext_download` 必须是独立的 IngestionItem，且执行前必须检查：
    1. `SourcePlatform.is_allowed_for_fulltext == true`
    2. `LiteratureRecord.copyright_status IN ('public_domain', 'licensed')`
    3. 版权判定结果允许全文采集
    4. 以上任一不满足 → `status='skipped'` + `skipped_reason` 记录原因
- `copyright_decision` 字段记录每条采集目标的版权判定结论和依据，形成可审计的决策链。
- `error_detail` 使用 PostgreSQL JSON 列类型，支持结构化错误信息。

---

### 1.8 模型文件组织

```
apps/backend/app/models/huangfu_meta.py
```

所有 7 个模型放在 **一个文件** 中，因为：
1. 它们紧密相关（通过 FK 互相关联）
2. 导入关系简洁 — 只需在 `__init__.py` 加一行

ponytail: 当单个文件超过 400 行或需要独立 Service 时再拆分。

### 1.9 `__init__.py` 注册

```python
# 在 app/models/__init__.py 末尾添加:

from app.models.huangfu_meta import (
    EvidenceCitation,
    FullTextDocument,
    IngestionItem,
    IngestionJob,
    LiteratureRecord,
    SourcePlatform,
    VersionBibliography,
)

# 在 __all__ 中添加:
    "EvidenceCitation",
    "FullTextDocument",
    "IngestionItem",
    "IngestionJob",
    "LiteratureRecord",
    "SourcePlatform",
    "VersionBibliography",
```

---

## 2. Alembic 迁移草案

### 2.1 迁移文件命名

```
apps/backend/app/db/migrations/versions/
  <rev_id>_huangfu_mi_literature_ingestion.py
```

### 2.2 迁移操作清单

```python
"""皇甫谧专题文献采集库 — 初始模型（Codex 修订版）

Revision ID: <auto-generated>
Revises: 291a1dce8d65  # Phase 2b: commentary
Create Date: 2026-07-10

新增 7 张表:
  - source_platforms
  - literature_records
  - version_bibliographies
  - full_text_documents (含 copyright gate check constraints)
  - evidence_citations (含 evidence_id FK 桥接)
  - ingestion_jobs
  - ingestion_items
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '<auto-generated>'
down_revision: Union[str, None] = '291a1dce8d65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. source_platforms ---
    op.create_table(
        'source_platforms',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('url', sa.String(2000), nullable=True),
        sa.Column('type', sa.String(50), nullable=False, server_default='web'),
        sa.Column('access_policy', sa.Text(), nullable=True),
        sa.Column('robots_policy', sa.Text(), nullable=True),
        sa.Column('license_note', sa.Text(), nullable=True),
        sa.Column('is_allowed_for_metadata', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_allowed_for_fulltext', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_index('ix_source_platforms_name', 'source_platforms', ['name'], unique=True)

    # --- 2. literature_records ---
    op.create_table(
        'literature_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(1000), nullable=False),
        sa.Column('original_title', sa.String(1000), nullable=True),
        sa.Column('authors', sa.Text(), nullable=True),
        sa.Column('institutions', sa.Text(), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('publication_type', sa.String(50), nullable=False, server_default='journal_article'),
        sa.Column('journal', sa.String(500), nullable=True),
        sa.Column('publisher', sa.String(500), nullable=True),
        sa.Column('abstract', sa.Text(), nullable=True),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column('doi', sa.String(500), nullable=True, unique=True),
        sa.Column('external_id', sa.String(500), nullable=True),
        sa.Column('source_url', sa.String(2000), nullable=True),
        sa.Column('language', sa.String(20), nullable=False, server_default='zh'),
        sa.Column('source_platform_id', sa.String(36), nullable=True),
        sa.Column('metadata_status', sa.String(30), nullable=False, server_default='draft'),
        sa.Column('copyright_status', sa.String(50), nullable=False, server_default='unknown'),
        sa.Column('fulltext_status', sa.String(30), nullable=False, server_default='none'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_index('ix_literature_records_title', 'literature_records', ['title'])
    op.create_foreign_key(
        'fk_literature_records_source_platform',
        'literature_records', 'source_platforms',
        ['source_platform_id'], ['id'], ondelete='SET NULL',
    )

    # --- 3. version_bibliographies ---
    op.create_table(
        'version_bibliographies',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('version_id', sa.String(36), nullable=False),
        sa.Column('repository', sa.String(500), nullable=True),
        sa.Column('repository_location', sa.String(200), nullable=True),
        sa.Column('shelf_mark', sa.String(200), nullable=True),
        sa.Column('source_url', sa.String(2000), nullable=True),
        sa.Column('image_url', sa.String(2000), nullable=True),
        sa.Column('ocr_text_available', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('public_domain_status', sa.String(50), nullable=False, server_default='needs_investigation'),
        sa.Column('copyright_decision', sa.String(50), nullable=True),
        sa.Column('copyright_decision_basis', sa.Text(), nullable=True),
        sa.Column('copyright_reviewed_by', sa.String(36), nullable=True),
        sa.Column('copyright_reviewed_at', sa.String(100), nullable=True),
        sa.Column('citation_note', sa.Text(), nullable=True),
        sa.Column('academic_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_unique_constraint('uq_version_bibliographies_version_id', 'version_bibliographies', ['version_id'])
    op.create_foreign_key(
        'fk_version_bibliographies_version',
        'version_bibliographies', 'versions',
        ['version_id'], ['id'], ondelete='CASCADE',
    )

    # --- 4. ingestion_jobs ---
    op.create_table(
        'ingestion_jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('job_type', sa.String(50), nullable=False, index=True),
        sa.Column('query', sa.Text(), nullable=True),
        sa.Column('source_platform_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending', index=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skipped_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('log', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_foreign_key(
        'fk_ingestion_jobs_source_platform',
        'ingestion_jobs', 'source_platforms',
        ['source_platform_id'], ['id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_ingestion_jobs_created_by',
        'ingestion_jobs', 'users',
        ['created_by'], ['id'], ondelete='SET NULL',
    )

    # --- 5. full_text_documents ---
    op.create_table(
        'full_text_documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('literature_record_id', sa.String(36), nullable=True),
        sa.Column('version_bibliography_id', sa.String(36), nullable=True),
        sa.Column('ingestion_job_id', sa.String(36), nullable=True),
        sa.Column('file_path', sa.String(2000), nullable=True),
        sa.Column('file_format', sa.String(20), nullable=False, server_default='txt'),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('text_hash', sa.String(64), nullable=True),
        sa.Column('ocr_status', sa.String(30), nullable=False, server_default='none'),
        sa.Column('ocr_engine', sa.String(100), nullable=True),
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
        sa.Column('license_type', sa.String(50), nullable=False, server_default='unknown'),
        sa.Column('copyright_status', sa.String(50), nullable=False, server_default='unknown'),
        sa.Column('authorization_basis', sa.Text(), nullable=True),
        sa.Column('access_level', sa.String(20), nullable=False, server_default='restricted'),
        sa.Column('ingestion_status', sa.String(30), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_index('ix_full_text_documents_text_hash', 'full_text_documents', ['text_hash'])
    op.create_foreign_key(
        'fk_full_text_documents_literature_record',
        'full_text_documents', 'literature_records',
        ['literature_record_id'], ['id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_full_text_documents_version_bibliography',
        'full_text_documents', 'version_bibliographies',
        ['version_bibliography_id'], ['id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_full_text_documents_ingestion_job',
        'full_text_documents', 'ingestion_jobs',
        ['ingestion_job_id'], ['id'], ondelete='SET NULL',
    )
    # source FK: exactly one
    op.create_check_constraint(
        'ck_full_text_documents_exactly_one_source',
        'full_text_documents',
        '(literature_record_id IS NOT NULL AND version_bibliography_id IS NULL) OR '
        '(literature_record_id IS NULL AND version_bibliography_id IS NOT NULL)',
    )
    # copyright gate: text_content
    op.create_check_constraint(
        'ck_full_text_documents_text_content_copyright_gate',
        'full_text_documents',
        "text_content IS NULL OR ("
        "  copyright_status IN ('public_domain', 'licensed')"
        "  AND authorization_basis IS NOT NULL"
        ")",
    )
    # copyright gate: file_path
    op.create_check_constraint(
        'ck_full_text_documents_file_path_copyright_gate',
        'full_text_documents',
        "file_path IS NULL OR ("
        "  copyright_status IN ('public_domain', 'licensed')"
        "  AND authorization_basis IS NOT NULL"
        ")",
    )

    # --- 6. evidence_citations ---
    op.create_table(
        'evidence_citations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('document_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='extracted'),
        sa.Column('passage_id', sa.String(36), nullable=True),
        sa.Column('version_id', sa.String(36), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('paragraph_index', sa.Integer(), nullable=True),
        sa.Column('line_range', sa.String(50), nullable=True),
        sa.Column('quote_text', sa.Text(), nullable=False),
        sa.Column('normalized_text', sa.Text(), nullable=True),
        sa.Column('context_before', sa.Text(), nullable=True),
        sa.Column('context_after', sa.Text(), nullable=True),
        sa.Column('source_url', sa.String(2000), nullable=True),
        sa.Column('citation_format', sa.String(100), nullable=True),
        sa.Column('formatted_citation', sa.Text(), nullable=True),
        sa.Column('evidence_id', sa.String(36), nullable=True, unique=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('extraction_method', sa.String(30), nullable=False, server_default='manual'),
        sa.Column('reviewed_by', sa.String(36), nullable=True),
        sa.Column('reviewed_at', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_index('ix_evidence_citations_document_id', 'evidence_citations', ['document_id'])
    op.create_index('ix_evidence_citations_status', 'evidence_citations', ['status'])
    op.create_foreign_key(
        'fk_evidence_citations_document',
        'evidence_citations', 'full_text_documents',
        ['document_id'], ['id'], ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_evidence_citations_passage',
        'evidence_citations', 'passages',
        ['passage_id'], ['id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_evidence_citations_version',
        'evidence_citations', 'versions',
        ['version_id'], ['id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_evidence_citations_evidence',
        'evidence_citations', 'evidences',
        ['evidence_id'], ['id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_evidence_citations_reviewed_by',
        'evidence_citations', 'users',
        ['reviewed_by'], ['id'], ondelete='SET NULL',
    )

    # --- 7. ingestion_items ---
    op.create_table(
        'ingestion_items',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('ingestion_job_id', sa.String(36), nullable=False),
        sa.Column('source_platform_id', sa.String(36), nullable=True),
        sa.Column('target_url', sa.String(2000), nullable=True),
        sa.Column('target_identifier', sa.String(500), nullable=True),
        sa.Column('harvest_type', sa.String(30), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'),
        sa.Column('error_detail', sa.JSON(), nullable=True),
        sa.Column('skipped_reason', sa.String(500), nullable=True),
        sa.Column('result_entity_type', sa.String(50), nullable=True),
        sa.Column('result_entity_id', sa.String(36), nullable=True),
        sa.Column('copyright_decision', sa.String(50), nullable=True),
        sa.Column('copyright_decision_basis', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.String(36), nullable=True),
        sa.Column('reviewed_at', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_index('ix_ingestion_items_job_id', 'ingestion_items', ['ingestion_job_id'])
    op.create_index('ix_ingestion_items_status', 'ingestion_items', ['status'])
    op.create_foreign_key(
        'fk_ingestion_items_job',
        'ingestion_items', 'ingestion_jobs',
        ['ingestion_job_id'], ['id'], ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_ingestion_items_source_platform',
        'ingestion_items', 'source_platforms',
        ['source_platform_id'], ['id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_ingestion_items_reviewed_by',
        'ingestion_items', 'users',
        ['reviewed_by'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_table('ingestion_items')
    op.drop_table('evidence_citations')
    op.drop_table('full_text_documents')
    op.drop_table('ingestion_jobs')
    op.drop_table('version_bibliographies')
    op.drop_table('literature_records')
    op.drop_table('source_platforms')
```

### 2.3 执行命令

```bash
cd apps/backend
alembic revision --autogenerate -m "huangfu_mi_literature_ingestion"
alembic upgrade head
```

---

## 3. API 设计草案

### 3.1 设计原则

- 遵循现有 `_make_crud()` 工厂模式为标准 CRUD
- 特殊操作用手动路由
- 权限检查使用 `require_permission(resource, action)`
- 响应格式使用 `api_response()`

### 3.2 路由文件

```
apps/backend/app/api/v1/huangfu_meta.py
```

挂载在 `APIRouter(prefix="/api/v1")` 下。

### 3.3 端点清单

#### SourcePlatform — `/api/v1/source-platforms`

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/source-platforms` | `source_platform.read` | 列表（分页 + 搜索） |
| POST | `/source-platforms` | `source_platform.create` | 创建平台 |
| GET | `/source-platforms/{id}` | `source_platform.read` | 获取详情 |
| PATCH | `/source-platforms/{id}` | `source_platform.update` | 更新平台 |
| DELETE | `/source-platforms/{id}` | `source_platform.delete` | 软删除 |
| POST | `/source-platforms/{id}/check-policy` | `source_platform.read` | 检查平台访问策略是否允许采集 |

#### LiteratureRecord — `/api/v1/literature-records`

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/literature-records` | `literature_record.read` | 列表（分页 + 搜索 + 筛选） |
| POST | `/literature-records` | `literature_record.create` | 创建记录（metadata-only 入口） |
| GET | `/literature-records/{id}` | `literature_record.read` | 获取详情 |
| PATCH | `/literature-records/{id}` | `literature_record.update` | 更新记录 |
| DELETE | `/literature-records/{id}` | `literature_record.delete` | 软删除 |
| POST | `/literature-records/bulk-import` | `literature_record.create` | 批量导入（CSV/JSON） |
| POST | `/literature-records/{id}/approve` | `literature_record.review` | 审核通过 |
| POST | `/literature-records/{id}/reject` | `literature_record.review` | 审核退回 |
| GET | `/literature-records/check-duplicate` | `literature_record.read` | 查重（按 title + year 相似度） |

#### VersionBibliography — `/api/v1/version-bibliographies`

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/version-bibliographies` | `version_bibliography.read` | 列表（分页 + 搜索） |
| POST | `/version-bibliographies` | `version_bibliography.create` | 为已有 Version 创建目录学扩展 |
| GET | `/version-bibliographies/{id}` | `version_bibliography.read` | 获取详情 |
| PATCH | `/version-bibliographies/{id}` | `version_bibliography.update` | 更新 |
| DELETE | `/version-bibliographies/{id}` | `version_bibliography.delete` | 软删除 |
| GET | `/versions/{version_id}/bibliography` | `version_bibliography.read` | 获取某 Version 的目录学扩展 |

#### FullTextDocument — `/api/v1/full-text-documents`

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/full-text-documents` | `full_text_document.read` | 列表（分页 + 筛选） |
| POST | `/full-text-documents/upload` | `full_text_document.create` | 上传文件（multipart/form-data → MinIO） |
| GET | `/full-text-documents/{id}` | `full_text_document.read` | 获取详情 |
| GET | `/full-text-documents/{id}/content` | `full_text_document.read` | 获取文本内容（access_level + copyright_status 双重门控） |
| PATCH | `/full-text-documents/{id}` | `full_text_document.update` | 更新元数据 |
| DELETE | `/full-text-documents/{id}` | `full_text_document.delete` | 软删除 |
| POST | `/full-text-documents/{id}/ocr` | `full_text_document.update` | 触发 OCR 管道 |
| GET | `/full-text-documents/{id}/ocr-status` | `full_text_document.read` | 查询 OCR 状态 |

#### EvidenceCitation — `/api/v1/evidence-citations`

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/evidence-citations` | `evidence_citation.read` | 列表（分页 + 按文档/状态筛选） |
| POST | `/evidence-citations` | `evidence_citation.create` | 手动创建引文 |
| GET | `/evidence-citations/{id}` | `evidence_citation.read` | 获取详情 |
| PATCH | `/evidence-citations/{id}` | `evidence_citation.update` | 更新引文 |
| DELETE | `/evidence-citations/{id}` | `evidence_citation.delete` | 软删除 |
| POST | `/evidence-citations/extract` | `evidence_citation.create` | 从全文自动提取引文（regex/LLM） |
| POST | `/evidence-citations/{id}/review` | `evidence_citation.review` | 人工审核 → status=reviewed |
| POST | `/evidence-citations/{id}/promote` | `evidence_citation.review` | **提升为 Evidence：创建 Evidence 记录 + 回写 evidence_id** |
| POST | `/evidence-citations/{id}/reject` | `evidence_citation.review` | 退回 → status=rejected |

#### IngestionJob — `/api/v1/ingestion-jobs`

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/ingestion-jobs` | `ingestion_job.read` | 列表（分页 + 按状态/类型筛选） |
| POST | `/ingestion-jobs` | `ingestion_job.create` | 创建采集任务（自动生成 IngestionItems） |
| GET | `/ingestion-jobs/{id}` | `ingestion_job.read` | 获取详情（含 items 列表） |
| PATCH | `/ingestion-jobs/{id}` | `ingestion_job.update` | 更新任务（如取消） |
| POST | `/ingestion-jobs/{id}/run` | `ingestion_job.execute` | 执行任务 |

#### IngestionItem — `/api/v1/ingestion-items`

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/ingestion-items` | `ingestion_job.read` | 列表（分页 + 按 job/状态/类型筛选） |
| GET | `/ingestion-items/{id}` | `ingestion_job.read` | 获取详情（含错误和版权判定） |
| POST | `/ingestion-items/{id}/retry` | `ingestion_job.execute` | 重试单条 |
| POST | `/ingestion-items/{id}/skip` | `ingestion_job.update` | 标记跳过 + skipped_reason |
| POST | `/ingestion-items/{id}/review` | `ingestion_job.review` | 人工审核 by reviewed_by |

### 3.4 路由伪代码

```python
# apps/backend/app/api/v1/huangfu_meta.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.middleware.auth import require_permission

router = APIRouter(tags=["皇甫谧专题文献库"])

# --- SourcePlatform: 标准 CRUD ---
_make_crud("source_platform", SourcePlatformService, ...)

# --- LiteratureRecord: 标准 CRUD + 扩展 ---
_make_crud("literature_record", LiteratureRecordService, ...)

# --- VersionBibliography: 手动路由（version_id 从 /versions/{version_id}/bibliography 获取）---
...

# --- FullTextDocument: 手动路由（版权门控 + access_level 门控）---
@router.post("/full-text-documents/upload", dependencies=[Depends(require_permission("full_text_document", "create"))])
async def upload_full_text(file: UploadFile = File(...), ...):
    """
    上传前必须通过版权门控检查：
    1. copyright_status IN ('public_domain', 'licensed')
    2. authorization_basis 非空
    3. SourcePlatform.is_allowed_for_fulltext == true
    以上任意不满足 → 400，不创建 FullTextDocument。
    未知版权只能创建 metadata-only 记录。
    """

@router.get("/full-text-documents/{id}/content", dependencies=[Depends(require_permission("full_text_document", "read"))])
async def get_full_text_content(id: str, ...):
    """
    双重门控：
    1. copyright_status 检查（public_domain/licensed 才返回全文）
    2. access_level 检查（open/registered/restricted/embargoed）
    """

# --- EvidenceCitation: promotion 端点 ---
@router.post("/evidence-citations/{id}/promote", dependencies=[Depends(require_permission("evidence_citation", "review"))])
async def promote_to_evidence(id: str, ...):
    """
    status=reviewed → promoted_to_evidence:
    1. 创建 Evidence 记录（绑定 SourceRef + Passage）
    2. 回写 EvidenceCitation.evidence_id
    3. Evidence 进入 RAG / Graph / AcademicRelation / Citation 证据链
    """
```

### 3.5 Pydantic Schema 草案（关键字段）

```python
# apps/backend/app/schemas/huangfu_meta.py

# SourcePlatform
class SourcePlatformCreate(BaseModel):
    name: str = Field(..., max_length=200)
    url: str | None = None
    type: str = "web"
    access_policy: str | None = None
    robots_policy: str | None = None
    license_note: str | None = None
    is_allowed_for_metadata: bool = False
    is_allowed_for_fulltext: bool = False

# LiteratureRecord — 默认 metadata-only
class LiteratureRecordCreate(BaseModel):
    title: str = Field(..., max_length=1000)
    original_title: str | None = None
    authors: str | None = None          # JSON array string，服务层校验格式
    year: int | None = None
    publication_type: str = "journal_article"
    journal: str | None = None
    doi: str | None = None
    source_platform_id: str | None = None
    # metadata_status defaults to "draft", copyright_status to "unknown"
    # 不包含 text_content 或 file 字段 — metadata-only 入口

# FullTextDocument upload — 版权门控严格
class FullTextUploadRequest(BaseModel):
    literature_record_id: str | None = Field(default=None, description="与 version_bibliography_id 二选一")
    version_bibliography_id: str | None = Field(default=None, description="与 literature_record_id 二选一")
    copyright_status: str = Field(..., description="必须为 public_domain 或 licensed")
    authorization_basis: str = Field(..., min_length=1, description="授权依据，必填")
    license_type: str = Field(..., description="许可证类型")
    access_level: str = "restricted"

    @model_validator(mode="after")
    def validate_source_exactly_one(self):
        if (self.literature_record_id is None) == (self.version_bibliography_id is None):
            raise ValueError("exactly one of literature_record_id / version_bibliography_id required")
        return self

    @model_validator(mode="after")
    def validate_copyright_for_fulltext(self):
        if self.copyright_status not in ("public_domain", "licensed"):
            raise ValueError("copyright_status must be public_domain or licensed to upload full text. "
                             "Unknown/in_copyright/orphan_work → use metadata-only endpoint.")
        return self
```

---

## 4. 权限控制建议

### 4.1 新增资源类型

扩展现有 RBAC 体系，在 `permissions` 表中注册以下新资源：

| 资源 | 操作 | 权限码 |
|------|------|--------|
| `source_platform` | create, read, update, delete | `source_platform.{action}` |
| `literature_record` | create, read, update, delete, review, export | `literature_record.{action}` |
| `version_bibliography` | create, read, update, delete | `version_bibliography.{action}` |
| `full_text_document` | create, read, update, delete, upload | `full_text_document.{action}` |
| `evidence_citation` | create, read, update, delete, review, extract | `evidence_citation.{action}` |
| `ingestion_job` | create, read, update, delete, execute, review | `ingestion_job.{action}` |
| `ingestion_item` | read, update, execute, review | `ingestion_item.{action}` |

### 4.2 角色-权限映射建议

| 角色 | 新增权限 |
|------|---------|
| **平台管理员** (Platform Admin) | 全部资源的全部操作 |
| **学术管理员** (Academic Admin) | 全部资源的 read + review + export；literature_record.create/update；full_text_document.upload |
| **研究负责人** (Research Leader) | 全部资源的 read；literature_record.create；evidence_citation.create/extract/review |
| **研究员** (Researcher) | 全部资源的 read；evidence_citation.create |
| **审核员** (Reviewer) | 全部资源的 read + review |
| **学生** (Student) | 全部资源的 read（full_text_document 受 access_level 限制） |
| **访客** (Visitor) | open access_level 资源的 read |

### 4.3 access_level 中间件

```python
# 建议在 middleware/auth.py 中增加:

def require_document_access(document_id_param: str = "id"):
    """Factory: check copyright_status + access_level on FullTextDocument.

    版权门控:
    - copyright_status IN ('public_domain', 'licensed') → 可以访问全文
    - copyright_status = 'unknown' → 只能访问元数据
    - copyright_status = 'in_copyright' → 访问拒绝（仅管理员可预览元数据）

    access_level 门控:
    - open → 任何人
    - registered → 登录用户
    - restricted → 有 full_text_document.read 权限
    - embargoed → 仅管理员
    """
    async def checker(
        request: Request,
        user_id: Annotated[str | None, Depends(OptionalUser())],
        auth_svc: Annotated[AuthService, Depends(get_auth_service)],
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> str:
        document_id = request.path_params.get(document_id_param)
        doc = await session.get(FullTextDocument, document_id)
        if doc is None:
            raise HTTPException(status_code=404)

        # Copyright gate
        if doc.copyright_status not in ('public_domain', 'licensed'):
            if doc.copyright_status == 'unknown':
                raise HTTPException(status_code=403, detail="Copyright status unknown — full text not available. Use metadata endpoint.")
            raise HTTPException(status_code=403, detail="Full text not available due to copyright restrictions.")

        # Access level gate
        level = doc.access_level
        if level == "open":
            return document_id
        if level == "registered" and user_id is not None:
            return document_id
        if level == "restricted":
            if user_id is not None and await auth_svc.has_permission(user_id, "full_text_document", "read"):
                return document_id
        if level == "embargoed":
            if user_id is not None and await auth_svc.has_permission(user_id, "full_text_document", "read"):
                # additional admin check
                ...
        raise HTTPException(status_code=403, detail="Access restricted")
    return checker
```

### 4.4 种子数据

```python
# 在 db/seed_rbac.py 中添加新权限的种子数据

HUANGFU_MI_PERMISSIONS = [
    # Source Platform
    ("source_platform", "create"),
    ("source_platform", "read"),
    ("source_platform", "update"),
    ("source_platform", "delete"),
    # Literature Record
    ("literature_record", "create"),
    ("literature_record", "read"),
    ("literature_record", "update"),
    ("literature_record", "delete"),
    ("literature_record", "review"),
    ("literature_record", "export"),
    # Version Bibliography
    ("version_bibliography", "create"),
    ("version_bibliography", "read"),
    ("version_bibliography", "update"),
    ("version_bibliography", "delete"),
    # Full Text Document
    ("full_text_document", "create"),
    ("full_text_document", "read"),
    ("full_text_document", "update"),
    ("full_text_document", "delete"),
    ("full_text_document", "upload"),
    # Evidence Citation
    ("evidence_citation", "create"),
    ("evidence_citation", "read"),
    ("evidence_citation", "update"),
    ("evidence_citation", "delete"),
    ("evidence_citation", "review"),
    ("evidence_citation", "extract"),
    # Ingestion Job
    ("ingestion_job", "create"),
    ("ingestion_job", "read"),
    ("ingestion_job", "update"),
    ("ingestion_job", "delete"),
    ("ingestion_job", "execute"),
    ("ingestion_job", "review"),
    # Ingestion Item
    ("ingestion_item", "read"),
    ("ingestion_item", "update"),
    ("ingestion_item", "execute"),
    ("ingestion_item", "review"),
]
```

---

## 5. 与现有模型的关系

### 5.1 与现有实体的桥接

```
┌─────────────────────────────────────────────────────────────────┐
│                      现有系统 (Existing)                         │
│                                                                  │
│  Book ──→ Version ──→ Chapter ──→ Passage                       │
│                  │                    ↑                          │
│                  │ (1:1)              │                          │
│                  ▼                    │                          │
│  VersionBibliography (NEW) ──────────┘ (passage_id FK)           │
│  (附属表，非独立版本主表)                                        │
│                                                                  │
│  Document ──→ DocumentChunk ──────────┘  (passage_id FK)         │
│                                                                  │
│  Person ←── Book.author_id                                       │
│  Person ←── Document.author_id                                   │
│                                                                  │
│  EntityRelation ──→ Evidence ←── EvidenceCitation (NEW)          │
│                        ↑              │                          │
│                        │    evidence_id FK (UNIQUE)              │
│                        │              │                          │
│                     Citation ─────────┘ (通过 Evidence 间接引用)  │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                      新模块 (Huangfu Mi)                         │
│                                                                  │
│  SourcePlatform ──→ LiteratureRecord ──→ FullTextDocument        │
│                           │                    ↑      ↓          │
│                           │              EvidenceCitation        │
│                           │                    │                 │
│  VersionBibliography ────┘                    │                 │
│        │                                      │                 │
│        └── version_id (NOT NULL, UNIQUE)      │                 │
│             → Version (existing)              │                 │
│                                               │                 │
│  IngestionJob ──→ IngestionItem ──→ FullTextDocument             │
│       │                                   / LiteratureRecord     │
│       └── (1:N item-level 审计)                                   │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                        桥接关系 (修订后)                          │
│                                                                  │
│  VersionBibliography.version_id → Version.id (NOT NULL, UNIQUE)  │
│    (1:1 附属表 — 不是独立版本主表)                                │
│    (版本谱系 → VersionRelation, 段落对照 → PassageMapping)       │
│                                                                  │
│  EvidenceCitation.evidence_id → Evidence.id (UNIQUE FK)          │
│    (promoted_to_evidence 时创建 Evidence 并回写 FK)              │
│    (EvidenceCitation 通过 Evidence 进入 Citation/RAG/Graph)      │
│                                                                  │
│  EvidenceCitation.passage_id → Passage.id                        │
│  EvidenceCitation.version_id → Version.id                        │
│    (优先定位 — Passage/Version 绑定优先于页码/行号)              │
│                                                                  │
│  LiteratureRecord.authors (JSON) ↔ Person.name (匹配)            │
│    (外部文献作者 ↔ 系统内人物实体)                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 数据流（修订后）

```
外部数据源 (ctext.org / CrossRef / OpenAlex / ...)
        │
        ▼
  IngestionJob (采集批次)
        │
        └──→ IngestionItem (逐条审计)
                │
                ├── harvest_type=metadata
                │   ├── 成功 → LiteratureRecord (元数据 + 版权状态判定)
                │   └── 不自动触发 fulltext_download
                │
                ├── harvest_type=fulltext (前置条件检查)
                │   ├── SourcePlatform.is_allowed_for_fulltext? ──No──→ skipped
                │   ├── copyright_status IN (public_domain, licensed)? ──No──→ skipped
                │   ├── authorization_basis 非空? ──No──→ skipped
                │   └── 全部通过 → FullTextDocument
                │                      │
                │                      └──→ EvidenceCitation (引文提取)
                │                              │
                │               extracted → draft → reviewed → promoted_to_evidence
                │                              │                    │
                │                     rejected (不进证据链)    Evidence (existing)
                │                                                   │
                │                                        RAG / Graph / Citation
                │
                ├── harvest_type=ocr
                │   └── 已有 FullTextDocument + 公版 → OCR 管道
                │
                └── harvest_type=citation_extract
                    └── 已有 FullTextDocument → EvidenceCitation 批量提取

  VersionBibliography (附属表)
        │
        └── version_id (NOT NULL, UNIQUE) → Version (existing)
               │
               ├── 版本谱系 → VersionRelation (existing)
               └── 段落对照 → PassageMapping (existing)
```

### 5.3 不重复造轮子（修订后）

| 能力 | 使用现有 | 不使用新的 | 原因 |
|------|---------|-----------|------|
| 人物管理 | `Person` | 不在 LiteratureRecord 外键关联作者 | 外部文献作者可能不在系统中 |
| **古籍版本** | **`Version`（主轴）** | **VersionBibliography 只是附属扩展** | **Version 是唯一版本主数据** |
| 版本谱系 | `VersionRelation` | 不新建第二套谱系 | 现有系统已成熟 |
| 段落对照 | `PassageMapping` | 不新建第二套对照 | 现有系统已成熟 |
| **引文证据链** | **`Evidence` + `Citation`** | **EvidenceCitation 通过 evidence_id FK 接入** | **强桥接，非应用层** |
| 知识图谱关系 | `EntityRelation` | 不新建关系表 | 现有图谱系统可表达所有关系类型 |
| 文档分块 | `DocumentChunk` | FullTextDocument 只存全文 | 分块由现有 chunking.py 处理 |
| RBAC | `User` + `Role` + `Permission` | 不新建权限系统 | 扩展现有体系即可 |

---

## 附录：文件清单

执行本设计将创建/修改以下文件：

**新建:**
- `apps/backend/app/models/huangfu_meta.py` — 7 个 SQLAlchemy 模型
- `apps/backend/app/schemas/huangfu_meta.py` — Pydantic 校验模型
- `apps/backend/app/services/huangfu_meta.py` — 业务逻辑服务（含版权门控）
- `apps/backend/app/repositories/huangfu_meta.py` — 数据访问层
- `apps/backend/app/api/v1/huangfu_meta.py` — API 路由
- `apps/backend/app/db/migrations/versions/<rev>_huangfu_mi_literature_ingestion.py` — 迁移

**修改:**
- `apps/backend/app/models/__init__.py` — 注册新模型
- `apps/backend/app/db/seed_rbac.py` — 添加新权限种子
- `apps/backend/app/api/v1/__init__.py` — 注册新路由

---

*本设计文档为阶段 1 的规划产物，不包含任何可执行代码变更。所有模型、迁移、API 设计需经审核后方可进入实施。*

**修订历史:**
- v1.0 (2026-07-10): 初始设计草案
- v1.1 (2026-07-10): Codex 审查修订 — 5 项阻塞修正

READY_FOR_CODEX_REAUDIT
