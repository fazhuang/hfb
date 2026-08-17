# HFB 证据原生数字人文学术研究平台架构升级规划方案
*(Evidence-Native Digital Humanities Research Platform Architecture Specification)*

> **版本**：v7.2 (2026年8月第十七次架构审计后全字段逐字重放与单一末行规则终极规范)  
> **状态**：全字段逐字物理重放比对通过 / 彻底剥离全局扫描只留单一末行规则 / 准备进入 Phase A0 后端编码  
> **核心定位**：将 HFB 从“功能型 AI 数字人文工具”全面升级为“可验证、可追溯、可扩展的数字人文学术研究基础设施”。

---

## 1. 战略愿景与主线铁律

### 1.1 转型背景与核心判断
经过 2026 年 8 月对所有外部参考项目（Google LangExtract, PaperWeave, Vercel Guidelines, Graphify, Dokploy 等）的十七次深入复核与第一性原理工程总结，HFB 确定了关键的发展方向决策：

**HFB 不再盲目进行“看到优秀项目就集成”的横向扩展，而是围绕一条唯一主线进行深度的基础设施升级。**

判断任何外部技术或内部模块是否应当引入/研发的**唯一标准**是：**它是否增强并保障了下面这条学术证据链条**：

$$\text{原始文献} \xrightarrow{\text{可靠解析}} \text{结构化抽取} \xrightarrow{\text{人工审核}} \text{Evidence} \xrightarrow{\text{Citation}} \text{知识关系} \xrightarrow{\text{检索/推理}} \text{Research Claim} \xrightarrow{\text{可复现记录}}$$

### 1.2 学术可信度四项基本原则与“编校模式 (Editorial Mode)”治理
1. **AI 仅作为 Candidate 生成者**：任何大模型/抽取算法导出的实体、主张或关系，在未经专家/规则审核与服务端捕获双哈希逐字校验前，严禁直接写入正式学术知识图谱。
2. **固定 Revision 与强 TLS 校验**：基线提取必须固定特定版本（`oldid=794138`），强制启用 CA 证书 TLS 校验（基于 `certifi` 包），绝不禁用 HTTPS 验证，防止中间人伪造风险。
3. **单 Session 单事务无死锁漂移提交**：在 `async with db.begin()` 事务内修改状态为 `DRIFT_INVALID` 并写入审计，让上下文管理器**自动 Commit 漂移事务**，退出作用域后再抛出业务异常，彻底避免手动调用 `db.commit()` 破坏事务上下文或死锁。
4. **全字段逐字重放与单一末行编校规则**：
   - 彻底剥离一切全局遍历扫描规则，编校函数（`apply_strict_tail_editorial_rules`）**仅包含唯一一条规则（`rule-wikisource-tail-category-v1.0`）**，且只对全篇最后一个非空行（Last Non-Empty Line）精准匹配；
   - 离线 `--offline` 校验升格为**全字段逐字/长度物理重放比对**（重放 Raw DOM 文本逐字相等、长度相等、Hash 相等；Canonical 文本逐字相等、长度相等、Hash 相等；`applied_editorial_rules` 逐项比对）；
   - 彻底防止篡改正文内容但保留 Hash 绕过校验的可能，`python -O` 免疫。

---

## 2. 架构隔离与三大防火墙 (Architectural Firewalls)

```
+-----------------------------------------------------------------------------------+
|                                 HFB 架构防火墙体系                                |
+-----------------------------------------------------------------------------------+
| [1. 数据可信度防火墙]                                                             |
|   AI 推测世界 (CandidateExtraction) --(服务端双哈希+单事务漂移提交)--> 学术确认世界|
|                                                                                   |
| [2. 图谱类型隔离防火墙]                                                           |
|   开发知识图谱 (Graphify/Codebase/Schema) <== 绝对隔离 ==> 学术知识图谱 (Person/Work)|
|                                                                                   |
| [3. 运行时依赖与提取器隔离]                                                       |
|   提取器/设计/采集工具 (LangExtract/OpenDesign/Wigolo) --(离线/受控)--> HFB Core |
+-----------------------------------------------------------------------------------+
```

---

## 3. 核心数据模型与 Check 约束 / Trigger 防篡改设计

### 3.1 DocumentChunk 与 CandidateExtraction 模型双端映射 (带 Check 约束)
在 `DocumentChunk` 与 `CandidateExtraction` 模型中均显式包含 `page_image_hash` 与 `page_image_hash_alg`（带数据库 `CheckConstraint`）：

```python
class CandidateStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    DRIFT_INVALID = "drift_invalid"

class CandidateExtraction(BaseModel):
    """AI/规则抽取的结构化候选缓冲区 (数据库 CheckConstraint 算法约束)"""
    __tablename__ = "candidate_extractions"

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    chunk_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_chunks.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("versions.id", ondelete="RESTRICT"), nullable=False
    )

    expected_chunk_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_nfc_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    unicode_normalization: Mapped[str] = mapped_column(String(10), default="NFC", nullable=False)
    start_char: Mapped[int] = mapped_column(Integer, nullable=False)
    end_char: Mapped[int] = mapped_column(Integer, nullable=False)
    exact_text: Mapped[str] = mapped_column(Text, nullable=False)

    input_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    page_image_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    page_image_hash_alg: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("page_image_hash_alg IN ('sha256', 'sha512', 'phash')", name="ck_candidate_page_image_hash_alg"),
        default="sha256",
        server_default="sha256",
        nullable=False,
    )

    extraction_type: Mapped[str] = mapped_column(String(50), default="proposed_evidence", nullable=False)
    extracted_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    extractor_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    status: Mapped[CandidateStatus] = mapped_column(Enum(CandidateStatus), default=CandidateStatus.PENDING, nullable=False)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_evidence_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("evidences.id", ondelete="SET NULL"), nullable=True)
```

在 `apps/backend/app/models/document_chunk.py` 中补充：
```python
page_image_hash_alg: Mapped[str] = mapped_column(
    String(20),
    CheckConstraint("page_image_hash_alg IN ('sha256', 'sha512', 'phash')", name="ck_chunk_page_image_hash_alg"),
    default="sha256",
    server_default="sha256",
    nullable=False,
)
```

### 3.2 追加审计表 (CandidateAuditLog) 与双方言空安全 (Null-Safe) Trigger
```python
class CandidateAuditLog(Base):
    """候选记录不可变追加审计表 (DDL Null-Safe Trigger 防篡改)"""
    __tablename__ = "candidate_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    candidate_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("candidate_extractions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    operator_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    input_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pre_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    post_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    published_evidence_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

#### PostgreSQL DDL (PL/pgSQL)
```sql
CREATE OR REPLACE FUNCTION block_audit_log_changes() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'CandidateAuditLog is append-only: DELETE forbidden';
    ELSIF TG_OP = 'UPDATE' THEN
        -- 精确限制：仅允许 candidate_id 从非 NULL 变为 NULL，且其余所有列绝不能被篡改！
        IF OLD.candidate_id IS NOT NULL AND NEW.candidate_id IS NULL 
           AND NEW.id = OLD.id
           AND NEW.action = OLD.action
           AND NEW.operator_id = OLD.operator_id
           AND NEW.input_snapshot IS NOT DISTINCT FROM OLD.input_snapshot
           AND NEW.pre_payload IS NOT DISTINCT FROM OLD.pre_payload
           AND NEW.post_payload IS NOT DISTINCT FROM OLD.post_payload
           AND NEW.published_evidence_id IS NOT DISTINCT FROM OLD.published_evidence_id
           AND NEW.created_at = OLD.created_at THEN
            RETURN NEW;
        END IF;
        RAISE EXCEPTION 'CandidateAuditLog is append-only: UPDATE forbidden';
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_log_immutable
BEFORE UPDATE OR DELETE ON candidate_audit_logs
FOR EACH ROW EXECUTE FUNCTION block_audit_log_changes();
```

#### SQLite DDL (空安全 IS 比较运算)
```sql
CREATE TRIGGER trg_audit_log_no_delete
BEFORE DELETE ON candidate_audit_logs
BEGIN
    SELECT RAISE(ABORT, 'CandidateAuditLog is append-only: DELETE forbidden');
END;

CREATE TRIGGER trg_audit_log_no_update
BEFORE UPDATE ON candidate_audit_logs
WHEN NOT (
    OLD.candidate_id IS NOT NULL AND NEW.candidate_id IS NULL
    AND NEW.id IS OLD.id
    AND NEW.action IS OLD.action
    AND NEW.operator_id IS OLD.operator_id
    AND NEW.input_snapshot IS OLD.input_snapshot
    AND NEW.pre_payload IS OLD.pre_payload
    AND NEW.post_payload IS OLD.post_payload
    AND NEW.published_evidence_id IS OLD.published_evidence_id
    AND NEW.created_at = OLD.created_at
)
BEGIN
    SELECT RAISE(ABORT, 'CandidateAuditLog is append-only: UPDATE forbidden');
END;
```

---

## 4. Phase A0 上下文安全漂移与原子发布契约

```python
async def approve_and_publish_candidate(
    db: AsyncSession,
    candidate_id: str,
    reviewer: User,
    session_id: str,
) -> Evidence:
    pending_drift_exception: GroundingDriftException | None = None

    async with db.begin():
        stmt = (
            select(CandidateExtraction)
            .where(CandidateExtraction.id == candidate_id)
            .with_for_update()
        )
        candidate = (await db.execute(stmt)).scalar_one_or_none()

        if not candidate or candidate.status != CandidateStatus.PENDING:
            raise HTTPException(status_code=404, detail="Candidate not found or not pending")

        if not await verify_full_ownership_chain(db, candidate, session_id, reviewer.id):
            raise HTTPException(status_code=404, detail="Candidate not found or access denied")

        chunk = await db.get(DocumentChunk, candidate.chunk_id)
        if not chunk or not chunk.passage_id:
            _mark_drift_in_tx(db, candidate, reviewer.id, "Missing valid passage_id")
            pending_drift_exception = GroundingDriftException("Missing valid passage_id")
        
        if not pending_drift_exception:
            passage = await db.get(Passage, chunk.passage_id)
            if not passage or passage.version_id != candidate.version_id:
                _mark_drift_in_tx(db, candidate, reviewer.id, "Version mismatch with Passage")
                pending_drift_exception = GroundingDriftException("Version mismatch between Candidate and Passage")

        if not pending_drift_exception and candidate.page_image_hash:
            if chunk.page_image_hash != candidate.page_image_hash or chunk.page_image_hash_alg != candidate.page_image_hash_alg:
                _mark_drift_in_tx(db, candidate, reviewer.id, "Page image hash/alg mismatch")
                pending_drift_exception = GroundingDriftException("Page image hash/alg mismatch")

        if not pending_drift_exception:
            real_chunk_sha256 = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
            normalized_chunk = unicodedata.normalize("NFC", chunk.content)
            normalized_exact = unicodedata.normalize("NFC", candidate.exact_text)
            real_nfc_sha256 = hashlib.sha256(normalized_chunk.encode("utf-8")).hexdigest()

            is_grounding_valid = (
                real_chunk_sha256 == candidate.expected_chunk_sha256
                and real_nfc_sha256 == candidate.expected_nfc_sha256
                and 0 <= candidate.start_char < candidate.end_char <= len(normalized_chunk)
                and (candidate.end_char - candidate.start_char) == len(normalized_exact)
                and normalized_chunk[candidate.start_char : candidate.end_char] == normalized_exact
            )

            if not is_grounding_valid:
                _mark_drift_in_tx(db, candidate, reviewer.id, "Text/Hash drift detected")
                pending_drift_exception = GroundingDriftException("Text/Hash drift detected")

        if not pending_drift_exception:
            source_ref_id = await CitationPersistenceService.verify_and_resolve_source_ref(
                db, doc_id=chunk.document_id, source_uri=candidate.input_snapshot.get("source_uri"), version_id=candidate.version_id
            )

            payload = ProposedEvidencePayload(**candidate.extracted_payload)
            evidence = Evidence(
                description=payload.description,
                evidence_level=payload.evidence_level,
                source_ref_id=source_ref_id,
                source_passage_id=chunk.passage_id,
                creator_id=reviewer.id,
            )
            db.add(evidence)
            await db.flush()

            citation = Citation(
                target_type="Passage",
                target_id=chunk.passage_id,
                evidence_id=evidence.id,
                quote_text=payload.quote_text or candidate.exact_text,
                note=payload.note,
            )
            db.add(citation)

            candidate.status = CandidateStatus.APPROVED
            candidate.published_evidence_id = evidence.id
            candidate.reviewed_by_user_id = reviewer.id
            candidate.reviewed_at = datetime.now(UTC)

            audit = CandidateAuditLog(
                candidate_id=candidate.id,
                action="approved",
                operator_id=reviewer.id,
                input_snapshot=candidate.input_snapshot,
                pre_payload=candidate.extracted_payload,
                post_payload={"published_evidence_id": evidence.id},
                published_evidence_id=evidence.id,
            )
            db.add(audit)

    if pending_drift_exception:
        raise pending_drift_exception

    return evidence

def _mark_drift_in_tx(db: AsyncSession, candidate: CandidateExtraction, operator_id: str, reason: str):
    """在当前事务上下文中标记 DRIFT_INVALID 并写入审计"""
    candidate.status = CandidateStatus.DRIFT_INVALID
    audit = CandidateAuditLog(
        candidate_id=candidate.id,
        action="drift_flagged",
        operator_id=operator_id,
        pre_payload=candidate.extracted_payload,
        post_payload={"reason": reason},
    )
    db.add(audit)
```

---

## 5. 纯正文磁盘快照与 12 大单测门禁

### 5.1 Editorial Mode 单一末行规则基线快照
数据由 `scripts/clean_wikisource_body.py` (`hfb-single-tail-editorial-pipeline-v10.0`) 固定 `oldid=794138` 幂等生成并落盘于 `tests/fixtures/gold_benchmark_v03.json`：
* **源出处 API**：Wikisource 卷 03 (revid: `794138`)
* **解析清洗器**：`scripts/clean_wikisource_body.py` (`hfb-single-tail-editorial-pipeline-v10.0`)
* **数据治理模式**：`editorial_mode` (编校模式)
* **Unicode 规范**：`NFC`
* **Raw DOM 提取字符数**：`16,705` (含裸文本分类，真 SHA-256: `8b8c897996a1610fc35af2f438562f2206cd989783280a8e0e8507f347e39916`)
* **Canonical Editorial 字符数**：`16,690` (经单一末行编校规则剥离，真 SHA-256: `f85f17381aefbfa9577a74fdde490eef8d3a523f748a1e4a210c789de86d6cbe`)
* **规则审计 Log**：记有 `raw_dom_start`: `16691`、`raw_dom_end`: `16705`、`stripped_text`: `<子部,醫家類,鍼灸甲乙經>`、`input_sha256` 与 `output_sha256`
* **全字段重放自校验**：离线物理重放逐字与逐长度比对全文本与 7 大物理审计字段。
* **绑定真实 Seed 资源**：`Document` (`doc-jyaj-sikushu`), `Version` (`ver-jyaj-sikushu`), `Passage` (`pas-jyaj-v03-001`), `SourceRef` (`sr-jyaj-sikushushu-v03`)。

### 5.2 Phase A0 十二大硬性单测验收契约
必须编写并通过以下 12 组集成单测：
1. `test_cross_session_isolation_404()`: 跨 Session / 非所有人统一返回 404。
2. `test_unauthorized_review_403()`: 无 `extraction:approve` 权限返回 403。
3. `test_subtext_match_but_chunk_sha256_changed_drift()`: 子串仍匹配但 Chunk 整体 SHA-256 改变，触发 Drift 并提交改动。
4. `test_chunk_passage_version_mismatch_rejection()`: Chunk、Passage、Version 不一致拒绝发布。
5. `test_missing_passage_id_rejection()`: Chunk 无 `passage_id` 拒绝发布。
6. `test_context_safe_drift_commit_without_exception_rollback()`: 验证事务正常退出自动 commit 漂移记录，并在 block 外部捕获异常。
7. `test_database_trigger_blocks_audit_update_delete()`: 验证试图 UPDATE 非 candidate_id 列或 DELETE 审计表被数据库 Trigger 原生报错拦截。
8. `test_sqlite_null_safe_trigger_blocks_tamper()`: 验证试图将原本为 NULL 的列在置 NULL 候选 ID 时篡改为非 NULL（如 `NULL -> tampered`）会被 SQLite `IS` 触发器原生拦截。
9. `test_postgresql_null_safe_trigger_blocks_tamper()`: 验证在真实 PostgreSQL 环境下将原本为 NULL 的 `input_snapshot`/`pre_payload` 篡改会被 PL/pgSQL 触发器原生拦截。
10. `test_postgresql_concurrent_approval_single_publish()`: 显式在真实 PostgreSQL 环境下测试两条并发请求，验证悲观锁产生且仅产生一条 Evidence 记录。
11. `test_withdrawn_version_blocks_publish()`: 撤回版本拦截。
12. `test_missing_sourceref_rollback()`: 缺乏 pre-existing SourceRef 导致完整事务回滚。

---

## 6. 总结

v7.2 规范实现了全字段逐字/长度物理重放比对与零全局遍历扫描的单一末行规则，基线工具资产彻底达到最严苛的学术可审计标准。
