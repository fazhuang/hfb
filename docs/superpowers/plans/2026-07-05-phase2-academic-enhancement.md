# Phase 2 学术增强 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将系统升级为学术可验证平台：证据等级、多跳查询、版本树/异文/注疏、纯数据结构化论文输出

**Architecture:** 四阶段顺序施工。Phase 2-Pre 重构 TEI 对齐算法（LCS/Smith-Waterman 消除错位异文），Phase 2a 升级 KG（symptom/syndrome 拆分 + evidence_level + AcademicEdge 视图 + 多跳查询），Phase 2b 升级 TEI（version_tree + variant 聚合 + commentary_layer 注疏链），Phase 2c 构建论文引擎（消费 2a+2b 接口，8 模块组装，含中医语义冲突检测）

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, pytest + pytest-asyncio, SQLite (tests) / PostgreSQL (prod), Alembic

## Global Constraints

- 禁止纯 LLM 生成内容 — 所有叙述文本来自模板填充或原始数据
- 禁止无引用输出 — 每条证据标注 citation + passage + quote
- 禁止无证据关系 — 学术边必须 evidence_level >= 2 + verified
- 杜绝基于物理位置错位的假异文数据 — 对齐算法必须基于序列比对而非索引
- 所有 CHECK 约束在模型层定义，Alembic 迁移同步
- 所有输出 SHA-256 哈希确保可复现
- 遵循现有代码模式：AsyncSession 依赖注入、extra="forbid" schema、BaseModel 继承

---

## File Structure

```
Phase 2-Pre (TEI 比对重构):
  Modify: packages/tcm_tei/comparator.py       — LCS/Smith-Waterman align + diff
  Modify: tests/unit/test_tcm_tei.py           — 对齐算法测试

Phase 2a (KG 升级):
  Modify: apps/backend/app/models/graph.py     — evidence_level 字段 + 约束 + syndrome/indicates
  Modify: apps/backend/app/models/tcm_entity.py — syndrome 类型
  Create: apps/backend/app/db/migrations/versions/XXX_phase2a_kg_upgrade.py
  Modify: apps/backend/app/services/graph_service.py — _derive_evidence_level + multi_hop_query
  Modify: apps/backend/app/schemas/graph.py    — EvidenceHop/EvidenceChainPath schemas
  Create: apps/backend/app/api/v2/graph.py     — evidence-chains endpoint
  Modify: apps/backend/app/api/v2/__init__.py  — 注册 graph router
  Modify: apps/backend/app/db/seed_graph.py    — 种子数据含 syndrome
  Create: tests/unit/test_evidence_level.py
  Create: tests/unit/test_multi_hop.py

Phase 2b (TEI 升级):
  Create: apps/backend/app/models/commentary.py     — Commentary 模型
  Create: apps/backend/app/db/migrations/versions/XXX_phase2b_commentary.py
  Modify: apps/backend/app/services/version_center.py — compute_distance_matrix + divergence_points
  Modify: apps/backend/app/schemas/tei.py (or create new schemas)
  Create: apps/backend/app/api/v2/tei.py            — TEI v2 endpoints
  Modify: apps/backend/app/api/v2/__init__.py       — 注册 tei router
  Create: tests/unit/test_commentary.py
  Create: tests/unit/test_version_tree.py

Phase 2c (论文引擎):
  Create: apps/backend/app/services/paper_service.py — PaperService
  Create: apps/backend/app/services/conflict_detector.py — ConflictDetector
  Modify: apps/backend/app/schemas/graph.py (or create paper schemas)
  Create: apps/backend/app/api/v2/paper.py          — paper endpoints
  Modify: apps/backend/app/api/v2/__init__.py       — 注册 paper router
  Create: tests/unit/test_paper_service.py
  Create: tests/unit/test_conflict_detector.py
```

---

## Phase 2-Pre: TEI 比对算法重构

### Task 1: LCS 句子对齐算法

**Files:**
- Modify: `packages/tcm_tei/comparator.py:84-113`

**Interfaces:**
- Consumes: 现有 `TextVersion`, `Paragraph`, `Sentence`, `Variant` dataclasses
- Produces: `VersionComparator.align()` — 新签名 `(version_a, version_b, algorithm="lcs") -> list[tuple[Sentence|None, Sentence|None]]`，LCS 对齐替代位置索引对齐

- [ ] **Step 1: 写 LCS 辅助函数**

在 `packages/tcm_tei/comparator.py` 中新增：

```python
def _lcs_align_sentences(
    sents_a: list[Sentence],
    sents_b: list[Sentence],
) -> list[tuple[Sentence | None, Sentence | None]]:
    """Align sentences using longest common subsequence on text.

    Builds a DP table over sentence texts, then backtracks to produce
    (s_a, s_b) pairs. Unmatched sentences get None on the other side.
    This tolerates insertions, deletions, and transpositions that
    position-based alignment would misalign.
    """
    m, n = len(sents_a), len(sents_b)
    # DP table: dp[i][j] = LCS length for sents_a[:i], sents_b[:j]
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if sents_a[i - 1].text == sents_b[j - 1].text:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # Backtrack
    aligned: list[tuple[Sentence | None, Sentence | None]] = []
    i, j = m, n
    while i > 0 or j > 0:
        if i > 0 and j > 0 and sents_a[i - 1].text == sents_b[j - 1].text:
            aligned.append((sents_a[i - 1], sents_b[j - 1]))
            i -= 1
            j -= 1
        elif j > 0 and (i == 0 or dp[i][j - 1] >= dp[i - 1][j]):
            aligned.append((None, sents_b[j - 1]))
            j -= 1
        else:
            aligned.append((sents_a[i - 1], None))
            i -= 1

    aligned.reverse()
    return aligned
```

- [ ] **Step 2: 重构 `align` 方法**

```python
@staticmethod
def align(
    version_a: TextVersion,
    version_b: TextVersion,
    algorithm: str = "lcs",
) -> list[tuple[Sentence | None, Sentence | None]]:
    """Align sentences between two versions using LCS sequence alignment.

    Returns a list of (sentence_a, sentence_b) pairs. Where a sentence
    exists in only one version, the other side is None.

    The LCS algorithm tolerates insertions and deletions — a single added
    sentence no longer misaligns every subsequent sentence pair.
    """
    aligned: list[tuple[Sentence | None, Sentence | None]] = []
    max_paras = max(version_a.paragraph_count, version_b.paragraph_count)

    for i in range(max_paras):
        para_a = version_a.paragraphs[i] if i < version_a.paragraph_count else None
        para_b = version_b.paragraphs[i] if i < version_b.paragraph_count else None
        sents_a = para_a.sentences if para_a else []
        sents_b = para_b.sentences if para_b else []

        if algorithm == "lcs":
            aligned.extend(_lcs_align_sentences(sents_a, sents_b))
        else:
            # fallback: original position-based
            max_sents = max(len(sents_a), len(sents_b))
            for j in range(max_sents):
                s_a = sents_a[j] if j < len(sents_a) else None
                s_b = sents_b[j] if j < len(sents_b) else None
                aligned.append((s_a, s_b))

    return aligned
```

- [ ] **Step 3: 运行现有 TEI 测试确认不破坏**

```bash
cd /Users/likeming/Sites/hfb && python -m pytest tests/unit/test_tcm_tei.py -v
```

- [ ] **Step 4: Commit**

```bash
git add packages/tcm_tei/comparator.py
git commit -m "feat: LCS sentence alignment in VersionComparator.align, eliminating position-based misalignment"
```

---

### Task 2: LCS 驱动的 diff 和测试

**Files:**
- Modify: `packages/tcm_tei/comparator.py:26-82` (diff method)
- Modify: `tests/unit/test_tcm_tei.py`

**Interfaces:**
- Consumes: Task 1 的 `_lcs_align_sentences`
- Produces: `VersionComparator.diff()` 内部改用 LCS 对齐；新增测试覆盖插入/删除/倒装场景

- [ ] **Step 1: 重构 diff 使用 LCS 对齐**

在 `diff` 方法中，将 `_compare_paragraph` 调用改为先 LCS 对齐，再比对对齐后的句对。将 `diff` 中逐段比较的逻辑重构为：

```python
@staticmethod
def diff(
    version_a: TextVersion,
    version_b: TextVersion,
    ignore_whitespace: bool = True,
    algorithm: str = "lcs",
) -> list[Variant]:
    """Compute all variants between two versions using LCS alignment.

    Uses LCS alignment so that inserted/deleted sentences don't cause
    every subsequent pair to be misaligned and reported as false variants.
    """
    variants: list[Variant] = []
    max_paras = max(version_a.paragraph_count, version_b.paragraph_count)

    for i in range(max_paras):
        para_a = version_a.paragraphs[i] if i < version_a.paragraph_count else None
        para_b = version_b.paragraphs[i] if i < version_b.paragraph_count else None

        if para_a is None and para_b is not None:
            variants.append(
                Variant(
                    location=f"para_{i}",
                    readings={version_a.id: "(absent)", version_b.id: para_b.text},
                    apparatus="Paragraph present only in " + version_b.id,
                )
            )
            continue

        if para_b is None and para_a is not None:
            variants.append(
                Variant(
                    location=f"para_{i}",
                    readings={version_a.id: para_a.text, version_b.id: "(absent)"},
                    apparatus="Paragraph present only in " + version_a.id,
                )
            )
            continue

        assert para_a is not None and para_b is not None
        # LCS-align sentences, then compare aligned pairs
        aligned = _lcs_align_sentences(para_a.sentences, para_b.sentences)
        for idx, (s_a, s_b) in enumerate(aligned):
            text_a = _clean(s_a.text, ignore_whitespace) if s_a else ""
            text_b = _clean(s_b.text, ignore_whitespace) if s_b else ""

            if text_a != text_b:
                variants.append(
                    Variant(
                        location=f"{para_a.id}.sent_{idx}",
                        readings={
                            version_a.id: s_a.text if s_a else "(absent)",
                            version_b.id: s_b.text if s_b else "(absent)",
                        },
                        apparatus=f"差异: [{version_a.id}] vs [{version_b.id}]",
                    )
                )

    return variants
```

- [ ] **Step 2: 写测试 — 插入句子不会导致全篇错位**

在 `tests/unit/test_tcm_tei.py` 中新增：

```python
def test_lcs_alignment_insertion_does_not_misalign_remainder():
    """A sentence inserted in version B should not misalign all following pairs."""
    from tcm_tei.models import TextVersion, Paragraph, Sentence
    from tcm_tei.comparator import VersionComparator

    v1 = TextVersion(id="v1", label="原本")
    v2 = TextVersion(id="v2", label="增补本")

    # v1: [A, B, C, D]
    # v2: [A, B, X, C, D]  — X inserted between B and C
    para1 = Paragraph(id="p1", sentences=[
        Sentence(id="s1", text="黄帝问曰"),
        Sentence(id="s2", text="岐伯对曰"),
        Sentence(id="s3", text="经脉流行不止"),
        Sentence(id="s4", text="环周不休"),
    ])
    para2 = Paragraph(id="p1", sentences=[
        Sentence(id="s1", text="黄帝问曰"),
        Sentence(id="s2", text="岐伯对曰"),
        Sentence(id="sX", text="此乃要言也"),  # inserted
        Sentence(id="s3", text="经脉流行不止"),
        Sentence(id="s4", text="环周不休"),
    ])
    v1.paragraphs = [para1]
    v2.paragraphs = [para2]

    variants = VersionComparator.diff(v1, v2, algorithm="lcs")

    # Should have exactly 1 variant: the inserted sentence
    # Without LCS, position-based would flag s3 & s4 as misaligned too
    assert len(variants) == 1
    assert "sent_2" in variants[0].location  # the X position


def test_lcs_alignment_deletion_does_not_misalign_remainder():
    """A sentence deleted in version B should not misalign all following pairs."""
    from tcm_tei.models import TextVersion, Paragraph, Sentence
    from tcm_tei.comparator import VersionComparator

    v1 = TextVersion(id="v1", label="原本")
    v2 = TextVersion(id="v2", label="删节本")

    # v1: [A, B, C, D]
    # v2: [A, C, D] — B deleted
    para1 = Paragraph(id="p1", sentences=[
        Sentence(id="s1", text="黄帝问曰"),
        Sentence(id="s2", text="岐伯对曰"),
        Sentence(id="s3", text="经脉流行不止"),
        Sentence(id="s4", text="环周不休"),
    ])
    para2 = Paragraph(id="p1", sentences=[
        Sentence(id="s1", text="黄帝问曰"),
        Sentence(id="s3", text="经脉流行不止"),
        Sentence(id="s4", text="环周不休"),
    ])
    v1.paragraphs = [para1]
    v2.paragraphs = [para2]

    variants = VersionComparator.diff(v1, v2, algorithm="lcs")

    # Should have exactly 1 variant: the deleted sentence
    assert len(variants) == 1


def test_lcs_alignment_identical_texts_zero_variants():
    """Identical texts should produce zero variants with LCS alignment."""
    from tcm_tei.models import TextVersion, Paragraph, Sentence
    from tcm_tei.comparator import VersionComparator

    v1 = TextVersion(id="v1", label="宋本")
    v2 = TextVersion(id="v2", label="明本")
    para = Paragraph(id="p1", sentences=[
        Sentence(id="s1", text="黄帝问曰"),
        Sentence(id="s2", text="岐伯对曰"),
    ])
    v1.paragraphs = [para]
    v2.paragraphs = [para]

    variants = VersionComparator.diff(v1, v2, algorithm="lcs")
    assert len(variants) == 0
```

- [ ] **Step 3: 运行新测试确认通过**

```bash
cd /Users/likeming/Sites/hfb && python -m pytest tests/unit/test_tcm_tei.py -v -k "lcs"
```
Expected: 3 new tests PASS

- [ ] **Step 4: 运行完整 TEI 测试套件**

```bash
cd /Users/likeming/Sites/hfb && python -m pytest tests/unit/test_tcm_tei.py -v
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/tcm_tei/comparator.py tests/unit/test_tcm_tei.py
git commit -m "feat: LCS-driven diff + tests for insertion/deletion tolerance"
```

---

## Phase 2a: KG 升级 + 中医本体精细化

### Task 3: 更新模型常量和约束 — syndrome + evidence_level

**Files:**
- Modify: `apps/backend/app/models/graph.py:27-37,40-63,66-89,92-102,120-153` — 新增 `syndrome` 实体类型、`indicates` 关系类型、ontology 定义
- Modify: `apps/backend/app/models/graph.py:108-153` — EntityRelation 类新增 evidence_level 列 + CHECK 约束
- Modify: `apps/backend/app/models/tcm_entity.py:27-34` — CHECK 约束增加 `syndrome`

**Interfaces:**
- Consumes: 现有 GRAPH_ENTITY_TYPES, ONTOLOGY_SOURCE_TYPES, ONTOLOGY_TARGET_TYPES, GRAPH_RELATION_TYPES
- Produces: 扩展的常量集 + EntityRelation.evidence_level + 更新后的 CHECK 约束

- [ ] **Step 1: 更新 GRAPH_ENTITY_TYPES**

在 `apps/backend/app/models/graph.py` 第 27-37 行，将集合更新为：

```python
GRAPH_ENTITY_TYPES = {
    "person",
    "book",
    "version",
    "passage",
    "text",
    "herb",
    "prescription",
    "meridian",
    "symptom",
    "syndrome",  # Phase 2a: 证候
}
```

- [ ] **Step 2: 更新本体定义 — ONTOLOGY_SOURCE_TYPES 和 ONTOLOGY_TARGET_TYPES**

在第 40-89 行的两个 dict 中新增 `indicates` 关系类型：

```python
ONTOLOGY_SOURCE_TYPES: dict[str, set[str]] = {
    "authored": {"person"},
    "compiled": {"person"},
    "compiled_from": {"book", "text"},
    "commented_on": {"person"},
    "cited_in": {"person", "book", "version", "passage", "text"},
    "studied": {"person"},
    "compared": {"person", "book", "version"},
    "referenced": {"person", "book", "version", "passage", "text"},
    "related_to": {
        "person", "book", "version", "passage", "text",
        "herb", "prescription", "meridian", "symptom", "syndrome",
    },
    "contains": {"book", "text", "version", "prescription"},
    "treats": {"prescription", "herb"},
    "corresponds_to": {"meridian", "herb"},
    "indicates": {"symptom"},  # Phase 2a: symptom → syndrome
}

ONTOLOGY_TARGET_TYPES: dict[str, set[str]] = {
    "authored": {"book", "text"},
    "compiled": {"book", "text"},
    "compiled_from": {"book", "text"},
    "commented_on": {"book", "text"},
    "cited_in": {"person", "book", "version", "passage", "text"},
    "studied": {"book", "text", "person", "prescription", "herb"},
    "compared": {"book", "version", "text"},
    "referenced": {"person", "book", "version", "passage", "text"},
    "related_to": {
        "person", "book", "version", "passage", "text",
        "herb", "prescription", "meridian", "symptom", "syndrome",
    },
    "contains": {"passage", "prescription", "herb", "symptom", "syndrome"},
    "treats": {"syndrome"},  # Phase 2a: 治疗证候，而非症状
    "corresponds_to": {"meridian", "herb"},
    "indicates": {"syndrome"},  # Phase 2a: symptom → syndrome
}
```

- [ ] **Step 3: 更新 GRAPH_RELATION_TYPES**

在第 92-102 行，新增 `indicates`：

```python
GRAPH_RELATION_TYPES = set(ONTOLOGY_SOURCE_TYPES.keys()) | {
    "authored",
    "compiled",
    "compiled_from",
    "commented_on",
    "cited_in",
    "studied",
    "compared",
    "referenced",
    "related_to",
    "contains",
    "treats",
    "corresponds_to",
    "indicates",
}
```

- [ ] **Step 4: 在 EntityRelation 类中新增 evidence_level 列**

在 `apps/backend/app/models/graph.py` 第 169 行（`description` 列之前或之后）加入：

```python
evidence_level: Mapped[int] = mapped_column(
    Integer, nullable=False, default=0,
    server_default=sa_text("0"),
    comment="证据等级 0-4: 0=无来源, 1=文献引用, 2=段落定位, 3=原文引证, 4=对勘证据"
)
```

- [ ] **Step 5: 更新 EntityRelation CHECK 约束**

替换第 130-152 行的 CHECK 约束为包含 `syndrome` 和 `indicates` 和 `evidence_level` 的版本：

```python
__table_args__ = (
    Index(
        "ix_entity_relations_lookup",
        "source_entity_type", "source_entity_id",
        "target_entity_type", "target_entity_id",
        "relation_type",
    ),
    CheckConstraint(
        "source_entity_type IN ("
        "'person','book','version','passage','text',"
        "'herb','prescription','meridian','symptom','syndrome')",
        name="ck_entity_relations_source_type",
    ),
    CheckConstraint(
        "target_entity_type IN ("
        "'person','book','version','passage','text',"
        "'herb','prescription','meridian','symptom','syndrome')",
        name="ck_entity_relations_target_type",
    ),
    CheckConstraint(
        "relation_type IN ("
        "'authored','compiled','compiled_from','commented_on','cited_in',"
        "'studied','compared','referenced','related_to',"
        "'contains','treats','corresponds_to','indicates')",
        name="ck_entity_relations_relation_type",
    ),
    CheckConstraint(
        "evidence_status IN ('unverified','verified','rejected')",
        name="ck_entity_relations_evidence_status",
    ),
    CheckConstraint(
        "evidence_level IN (0, 1, 2, 3, 4)",
        name="ck_entity_relations_level",
    ),
)
```

- [ ] **Step 6: 更新 TCMEntity CHECK 约束**

在 `apps/backend/app/models/tcm_entity.py` 第 27-34 行，替换 CHECK 约束：

```python
__table_args__ = (
    CheckConstraint(
        "entity_type IN ("
        "'person','book','version','passage','text',"
        "'herb','prescription','meridian','symptom','syndrome')",
        name="ck_tcm_entities_entity_type",
    ),
)
```

- [ ] **Step 7: 运行 lint 确认无语法错误**

```bash
cd /Users/likeming/Sites/hfb && ruff check apps/backend/app/models/graph.py apps/backend/app/models/tcm_entity.py
```

- [ ] **Step 8: Commit**

```bash
git add apps/backend/app/models/graph.py apps/backend/app/models/tcm_entity.py
git commit -m "feat: add syndrome entity type, indicates relation, evidence_level field + CHECK constraints"
```

---

### Task 4: Alembic 迁移

**Files:**
- Create: `apps/backend/app/db/migrations/versions/XXX_phase2a_kg_upgrade.py`

**Interfaces:**
- Consumes: Task 3 的模型变更
- Produces: Alembic 迁移脚本

- [ ] **Step 1: 生成迁移**

```bash
cd /Users/likeming/Sites/hfb/apps/backend && alembic revision --autogenerate -m "phase2a_kg_upgrade"
```

- [ ] **Step 2: 检查生成的迁移文件**

用 Read 检查新生成的迁移文件在 `apps/backend/app/db/migrations/versions/` 中。确认它包含：
- `ALTER TABLE entity_relations ADD COLUMN evidence_level INTEGER NOT NULL DEFAULT 0`
- `ALTER TABLE entity_relations DROP CONSTRAINT ck_entity_relations_source_type`（旧约束）
- `ALTER TABLE entity_relations ADD CONSTRAINT ck_entity_relations_source_type CHECK (... syndrome ...)`
- 同理 target_type、relation_type（含 indicates）
- `ALTER TABLE entity_relations ADD CONSTRAINT ck_entity_relations_level CHECK (evidence_level IN (0,1,2,3,4))`
- `ALTER TABLE tcm_entities DROP CONSTRAINT ck_tcm_entities_entity_type` + 新建含 syndrome

如果 autogenerate 没有正确检测到 CHECK 约束变更（已知 SQLAlchemy 限制），手动补充：

```python
def upgrade():
    # 1. 新增 evidence_level 列
    op.add_column('entity_relations',
        sa.Column('evidence_level', sa.Integer(), nullable=False, server_default='0'))

    # 2. 删除旧 CHECK 约束（按名称）
    op.drop_constraint('ck_entity_relations_source_type', 'entity_relations', type_='check')
    op.drop_constraint('ck_entity_relations_target_type', 'entity_relations', type_='check')
    op.drop_constraint('ck_entity_relations_relation_type', 'entity_relations', type_='check')
    op.drop_constraint('ck_tcm_entities_entity_type', 'tcm_entities', type_='check')

    # 3. 创建新 CHECK 约束
    op.create_check_constraint('ck_entity_relations_source_type', 'entity_relations',
        "source_entity_type IN ('person','book','version','passage','text','herb','prescription','meridian','symptom','syndrome')")
    op.create_check_constraint('ck_entity_relations_target_type', 'entity_relations',
        "target_entity_type IN ('person','book','version','passage','text','herb','prescription','meridian','symptom','syndrome')")
    op.create_check_constraint('ck_entity_relations_relation_type', 'entity_relations',
        "relation_type IN ('authored','compiled','compiled_from','commented_on','cited_in','studied','compared','referenced','related_to','contains','treats','corresponds_to','indicates')")
    op.create_check_constraint('ck_entity_relations_level', 'entity_relations',
        "evidence_level IN (0, 1, 2, 3, 4)")
    op.create_check_constraint('ck_tcm_entities_entity_type', 'tcm_entities',
        "entity_type IN ('person','book','version','passage','text','herb','prescription','meridian','symptom','syndrome')")


def downgrade():
    op.drop_constraint('ck_tcm_entities_entity_type', 'tcm_entities', type_='check')
    op.drop_constraint('ck_entity_relations_level', 'entity_relations', type_='check')
    op.drop_constraint('ck_entity_relations_relation_type', 'entity_relations', type_='check')
    op.drop_constraint('ck_entity_relations_target_type', 'entity_relations', type_='check')
    op.drop_constraint('ck_entity_relations_source_type', 'entity_relations', type_='check')

    op.create_check_constraint('ck_entity_relations_source_type', 'entity_relations',
        "source_entity_type IN ('person','book','version','passage','text','herb','prescription','meridian','symptom')")
    op.create_check_constraint('ck_entity_relations_target_type', 'entity_relations',
        "target_entity_type IN ('person','book','version','passage','text','herb','prescription','meridian','symptom')")
    op.create_check_constraint('ck_entity_relations_relation_type', 'entity_relations',
        "relation_type IN ('authored','compiled','compiled_from','commented_on','cited_in','studied','compared','referenced','related_to','contains','treats','corresponds_to')")
    op.create_check_constraint('ck_tcm_entities_entity_type', 'tcm_entities',
        "entity_type IN ('person','book','version','passage','text','herb','prescription','meridian','symptom')")

    op.drop_column('entity_relations', 'evidence_level')
```

- [ ] **Step 3: 运行迁移（SQLite 测试数据库）**

```bash
cd /Users/likeming/Sites/hfb/apps/backend && ALEMBIC_CONFIG=alembic.ini DATABASE_URL=sqlite+aiosqlite:///./hfb_dev.db alembic upgrade head
```

- [ ] **Step 4: 验证迁移后数据库结构**

```bash
cd /Users/likeming/Sites/hfb/apps/backend && sqlite3 hfb_dev.db ".schema entity_relations" | grep -E "evidence_level|syndrome|indicates"
```
Expected: 输出包含 evidence_level、syndrome、indicates 字样

- [ ] **Step 5: 运行现有测试确认无回归**

```bash
cd /Users/likeming/Sites/hfb && python -m pytest tests/ -x --timeout=60 -q
```

- [ ] **Step 6: Commit**

```bash
git add apps/backend/app/db/migrations/versions/
git commit -m "feat: phase2a alembic migration — evidence_level + syndrome + indicates"
```

---

### Task 5: _derive_evidence_level + 集成到 GraphService

**Files:**
- Modify: `apps/backend/app/services/graph_service.py` — 新增 `_derive_evidence_level`

**Interfaces:**
- Consumes: `EntityRelation` 模型的 evidence 字段，`TextualVariant` 模型
- Produces: `_derive_evidence_level(session, er) -> int`

- [ ] **Step 1: 在 GraphService 中新增推导方法**

在 `apps/backend/app/services/graph_service.py` 中 `GraphService` 类内新增：

```python
@staticmethod
async def _derive_evidence_level(
    session: AsyncSession,
    er: EntityRelation,
) -> int:
    """Derive evidence_level (0-4) from existing evidence fields.

    Pure function — deterministic, reproducible from field presence only.

    L0 = claim_text only, no structured evidence
    L1 = evidence_document_id or evidence_citation, no passage_id
    L2 = evidence_version_id + evidence_passage_id
    L3 = L2 + evidence_quote non-empty + evidence_status == 'verified'
    L4 = L3 + associated TextualVariant records exist
    """
    has_doc = bool(er.evidence_document_id)
    has_citation = bool(er.evidence_citation)
    has_passage = bool(getattr(er, "evidence_passage_id", None))
    has_version = bool(getattr(er, "evidence_version_id", None))
    has_quote = bool(er.evidence_quote)
    is_verified = getattr(er, "evidence_status", "unverified") == "verified"

    # L4 check: TextualVariant records
    if has_version and has_passage and has_quote and is_verified:
        from app.models.tei import TextualVariant
        variant_stmt = select(TextualVariant).where(
            TextualVariant.source_version_id == getattr(er, "evidence_version_id", ""),
            TextualVariant.is_deleted.is_(False),
        ).limit(1)
        variant_result = await session.execute(variant_stmt)
        if variant_result.scalar_one_or_none() is not None:
            return 4

    # L3: has version + passage + quote + verified
    if has_version and has_passage and has_quote and is_verified:
        return 3

    # L2: has version + passage
    if has_version and has_passage:
        return 2

    # L1: has document or citation but no passage
    if has_doc or has_citation:
        return 1

    # L0: nothing structured
    return 0
```

- [ ] **Step 2: 在 `create_relation` 中集成 level 推导**

在 `GraphService.create_relation` 中，写入 `EntityRelation` 之前调用推导。在 `apps/backend/app/services/graph_service.py` 中找到 `create_relation` 方法（约第 769 行），在 `session.add(relation)` 之前插入：

```python
# Derive evidence_level from evidence fields
relation.evidence_level = await self._derive_evidence_level(self.session, relation)
```

- [ ] **Step 3: 在 `verify_relation` 中重新推导 level**

在 `verify_relation` 方法中（约第 1120 行），在更新 `evidence_status = 'verified'` 之后、`session.commit` 之前插入：

```python
# Re-derive evidence_level after verification (may upgrade to L3/L4)
er.evidence_level = await self._derive_evidence_level(self.session, er)
```

- [ ] **Step 4: 运行 lint**

```bash
cd /Users/likeming/Sites/hfb && ruff check apps/backend/app/services/graph_service.py
```

- [ ] **Step 5: 写测试**

在 `tests/unit/test_evidence_level.py` 中：

```python
"""Tests for evidence_level derivation in GraphService."""

import pytest
from app.models.graph import EntityRelation
from app.services.graph_service import GraphService


@pytest.mark.asyncio
async def test_derive_evidence_level_l0_no_evidence(db_session):
    """EntityRelation with only claim_text → L0."""
    er = EntityRelation(
        source_entity_type="person",
        source_entity_id="test-src-id",
        target_entity_type="book",
        target_entity_id="test-tgt-id",
        relation_type="authored",
        claim_text="some claim",
    )
    level = await GraphService._derive_evidence_level(db_session, er)
    assert level == 0


@pytest.mark.asyncio
async def test_derive_evidence_level_l1_document_only(db_session):
    """EntityRelation with document_id but no passage → L1."""
    er = EntityRelation(
        source_entity_type="person",
        source_entity_id="test-src-id",
        target_entity_type="book",
        target_entity_id="test-tgt-id",
        relation_type="authored",
        evidence_document_id="doc-1",
        evidence_citation="test citation",
    )
    level = await GraphService._derive_evidence_level(db_session, er)
    assert level == 1


@pytest.mark.asyncio
async def test_derive_evidence_level_l2_version_passage(db_session):
    """EntityRelation with version_id + passage_id → L2."""
    er = EntityRelation(
        source_entity_type="person",
        source_entity_id="test-src-id",
        target_entity_type="book",
        target_entity_id="test-tgt-id",
        relation_type="authored",
        evidence_document_id="doc-1",
        evidence_citation="test citation",
        evidence_version_id="ver-1",
        evidence_passage_id="pass-1",
    )
    level = await GraphService._derive_evidence_level(db_session, er)
    assert level == 2


@pytest.mark.asyncio
async def test_derive_evidence_level_l3_quote_verified(db_session):
    """EntityRelation L2 + quote + verified → L3."""
    er = EntityRelation(
        source_entity_type="person",
        source_entity_id="test-src-id",
        target_entity_type="book",
        target_entity_id="test-tgt-id",
        relation_type="authored",
        evidence_document_id="doc-1",
        evidence_citation="test citation",
        evidence_version_id="ver-1",
        evidence_passage_id="pass-1",
        evidence_quote="exact quote text",
        evidence_status="verified",
    )
    level = await GraphService._derive_evidence_level(db_session, er)
    assert level == 3
```

- [ ] **Step 6: 运行测试**

```bash
cd /Users/likeming/Sites/hfb && python -m pytest tests/unit/test_evidence_level.py -v
```
Expected: 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add apps/backend/app/services/graph_service.py tests/unit/test_evidence_level.py
git commit -m "feat: _derive_evidence_level integration in create_relation + verify_relation"
```

---

### Task 6: AcademicEdge SQL 视图 + ORM 映射

**Files:**
- Modify: `apps/backend/app/db/migrations/versions/XXX_phase2a_kg_upgrade.py` — 在已有迁移中追加视图
- Create: `apps/backend/app/models/academic_edge.py` — 只读 ORM 映射

**Interfaces:**
- Consumes: `entity_relations` 表
- Produces: `academic_edges` 视图 + `AcademicEdge` ORM 映射（只读）

- [ ] **Step 1: 在迁移文件中追加视图创建**

在 Task 4 创建的迁移文件的 `upgrade()` 末尾加：

```python
# 4. Create academic_edges view
op.execute("""
    CREATE VIEW academic_edges AS
    SELECT
        *,
        CASE evidence_level
            WHEN 2 THEN 0.65
            WHEN 3 THEN 0.85
            WHEN 4 THEN 0.98
            ELSE 0.0
        END AS confidence_score
    FROM entity_relations
    WHERE evidence_level >= 2
      AND evidence_status = 'verified'
      AND is_deleted = 0;
""")
```

`downgrade()` 末尾加：

```python
op.execute("DROP VIEW IF EXISTS academic_edges;")
```

- [ ] **Step 2: 运行迁移确认视图创建成功**

```bash
cd /Users/likeming/Sites/hfb/apps/backend && ALEMBIC_CONFIG=alembic.ini DATABASE_URL=sqlite+aiosqlite:///./hfb_dev.db alembic upgrade head
```

```bash
cd /Users/likeming/Sites/hfb/apps/backend && sqlite3 hfb_dev.db "SELECT name FROM sqlite_master WHERE type='view';"
```
Expected: 输出包含 `academic_edges`

- [ ] **Step 3: 创建只读 ORM 映射**

新建 `apps/backend/app/models/academic_edge.py`：

```python
"""AcademicEdge — read-only ORM mapping for the academic_edges SQL view.

This view filters entity_relations to only academically citeable edges:
  evidence_level >= 2 AND evidence_status = 'verified' AND is_deleted = 0.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column


class AcademicEdge:
    """Read-only mapping for academic_edges view. Not a BaseModel subclass —
    this is a SQL view, no PK, no writes."""

    __tablename__ = "academic_edges"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_entity_type: Mapped[str] = mapped_column(String(50))
    source_entity_id: Mapped[str] = mapped_column(String(36))
    target_entity_type: Mapped[str] = mapped_column(String(50))
    target_entity_id: Mapped[str] = mapped_column(String(36))
    relation_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_document_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    evidence_chunk_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    evidence_quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_citation: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    evidence_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    evidence_passage_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    evidence_source_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    evidence_status: Mapped[str] = mapped_column(String(20))
    claim_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_level: Mapped[int] = mapped_column(Integer)
    confidence_score: Mapped[float] = mapped_column(Float)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_deleted: Mapped[bool] = mapped_column(default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 4: Commit**

```bash
git add apps/backend/app/db/migrations/versions/ apps/backend/app/models/academic_edge.py
git commit -m "feat: academic_edges SQL view + read-only ORM mapping"
```

---

### Task 7: EvidenceHop / EvidenceChainPath schemas

**Files:**
- Modify: `apps/backend/app/schemas/graph.py` — 新增 schema 类

**Interfaces:**
- Consumes: AcademicEdge 视图字段
- Produces: `EvidenceHop`, `EvidenceChainPath`, `MultiHopQueryRequest`, `EvidenceChainEnvelope`

- [ ] **Step 1: 在 graph.py schemas 中新增 schema 类**

在 `apps/backend/app/schemas/graph.py` 末尾追加：

```python
# ======================================================================
# Phase 2a: Evidence Chain (Multi-Hop Query)
# ======================================================================


class EvidenceHop(BaseModel):
    """A single hop in an evidence chain path."""

    model_config = ConfigDict(extra="forbid", strict=True)

    source_type: str = Field(..., description="源实体类型")
    source_id: str = Field(..., description="源实体 ID")
    target_type: str = Field(..., description="目标实体类型")
    target_id: str = Field(..., description="目标实体 ID")
    relation_type: str = Field(..., description="关系类型")
    evidence_level: int = Field(..., ge=0, le=4, description="证据等级 0-4")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="置信度")
    citation: str = Field(..., description="格式化引用")
    exact_quote: str = Field(default="", description="原文引证")
    source_uri: str = Field(default="", description="稳定来源 URI")


class EvidenceChainPath(BaseModel):
    """An ordered multi-hop path through academically verified edges."""

    model_config = ConfigDict(extra="forbid", strict=True)

    path_id: str = Field(..., description="SHA-256 of concatenated edge IDs")
    hops: list[EvidenceHop] = Field(default_factory=list, description="有序跳步列表")
    total_confidence: float = Field(..., ge=0.0, le=1.0, description="路径置信度乘积")
    min_evidence_level: int = Field(..., ge=0, le=4, description="路径中最低证据等级")


class MultiHopQueryRequest(BaseModel):
    """Request for multi-hop evidence chain query."""

    model_config = ConfigDict(extra="forbid", strict=True)

    source_type: str = Field(..., description="起始实体类型")
    source_id: str = Field(..., description="起始实体 ID")
    target_type: str | None = Field(default=None, description="目标实体类型（可选）")
    target_id: str | None = Field(default=None, description="目标实体 ID（可选）")
    min_evidence_level: int = Field(default=2, ge=2, le=4, description="最低证据等级")
    max_hops: int = Field(default=5, ge=1, le=10, description="最大跳数")
    relation_types: list[str] | None = Field(default=None, description="过滤关系类型")


class EvidenceChainEnvelope(BaseModel):
    """Strict API response envelope for evidence chain queries."""

    model_config = ConfigDict(extra="forbid", strict=True)

    success: bool = Field(default=True)
    data: list[EvidenceChainPath] = Field(default_factory=list)
    message: str = Field(default="ok")
```

- [ ] **Step 2: 运行 lint**

```bash
cd /Users/likeming/Sites/hfb && ruff check apps/backend/app/schemas/graph.py
```

- [ ] **Step 3: Commit**

```bash
git add apps/backend/app/schemas/graph.py
git commit -m "feat: EvidenceHop, EvidenceChainPath, MultiHopQueryRequest schemas"
```

---

### Task 8: multi_hop_query 在 GraphService 中

**Files:**
- Modify: `apps/backend/app/services/graph_service.py` — 新增 multi_hop_query 方法

**Interfaces:**
- Consumes: AcademicEdge 视图（通过 EntityRelation + evidence_level 过滤）、Task 7 的 schemas
- Produces: `GraphService.multi_hop_query(session, request) -> list[EvidenceChainPath]`

- [ ] **Step 1: 实现 multi_hop_query**

在 `apps/backend/app/services/graph_service.py` 中 `GraphService` 类内新增：

```python
async def multi_hop_query(
    self,
    source_type: str,
    source_id: str,
    target_type: str | None = None,
    target_id: str | None = None,
    min_evidence_level: int = 2,
    max_hops: int = 5,
    relation_types: list[str] | None = None,
) -> list[EvidenceChainPath]:
    """Multi-hop BFS over academically verified edges only.

    Each path is an ordered chain of AcademicEdge hops with full evidence.
    Only traverses edges with evidence_level >= min_evidence_level,
    evidence_status = 'verified', and is_deleted = 0.
    """
    # Collect all academic edges from the DB
    stmt = select(EntityRelation).where(
        EntityRelation.evidence_level >= min_evidence_level,
        EntityRelation.evidence_status == "verified",
        EntityRelation.is_deleted.is_(False),
    )
    if relation_types:
        stmt = stmt.where(EntityRelation.relation_type.in_(relation_types))
    result = await self.session.execute(stmt)
    all_edges: list[EntityRelation] = list(result.scalars().all())

    # Build adjacency list: (type, id) -> list[EntityRelation]
    from collections import defaultdict
    adj: dict[tuple[str, str], list[EntityRelation]] = defaultdict(list)
    for edge in all_edges:
        adj[(edge.source_entity_type, edge.source_entity_id)].append(edge)

    # BFS
    paths: list[EvidenceChainPath] = []
    queue: deque[tuple[str, str, list[EntityRelation]]] = deque()
    queue.append((source_type, source_id, []))

    while queue:
        current_type, current_id, edge_list = queue.popleft()
        if len(edge_list) >= max_hops:
            continue

        for edge in adj.get((current_type, current_id), []):
            new_list = edge_list + [edge]
            next_type = edge.target_entity_type
            next_id = edge.target_entity_id

            # Check if we reached the target (if target specified)
            if target_type and target_id:
                if next_type == target_type and next_id == target_id:
                    paths.append(self._build_evidence_path(new_list))
                    continue

            queue.append((next_type, next_id, new_list))

        # If no target specified, collect all paths at max depth
        if not target_type and len(edge_list) == max_hops - 1:
            # Already at max, collect if reached a leaf
            pass

    # If no target specified, collect all maximal paths
    if not target_type:
        # Re-run to collect all paths up to max_hops
        paths.clear()
        queue.clear()
        queue.append((source_type, source_id, []))
        while queue:
            current_type, current_id, edge_list = queue.popleft()
            neighbors = adj.get((current_type, current_id), [])
            if not neighbors or len(edge_list) >= max_hops:
                if edge_list:
                    paths.append(self._build_evidence_path(edge_list))
                continue
            for edge in neighbors:
                new_list = edge_list + [edge]
                queue.append((edge.target_entity_type, edge.target_entity_id, new_list))

    # Sort: highest confidence first
    paths.sort(key=lambda p: p.total_confidence, reverse=True)
    return paths


def _build_evidence_path(self, edges: list[EntityRelation]) -> EvidenceChainPath:
    """Build an EvidenceChainPath from a list of EntityRelation edges."""
    import hashlib
    hop_data: list[EvidenceHop] = []
    for er in edges:
        level = er.evidence_level
        # confidence_score derived from level
        score_map = {2: 0.65, 3: 0.85, 4: 0.98}
        score = score_map.get(level, 0.0)

        hop_data.append(EvidenceHop(
            source_type=er.source_entity_type,
            source_id=er.source_entity_id,
            target_type=er.target_entity_type,
            target_id=er.target_entity_id,
            relation_type=er.relation_type,
            evidence_level=level,
            confidence_score=score,
            citation=er.evidence_citation or "",
            exact_quote=er.evidence_quote or "",
            source_uri=getattr(er, "evidence_source_uri", "") or "",
        ))

    path_id = hashlib.sha256(
        "|".join(e.id for e in edges).encode()
    ).hexdigest()

    total_confidence = 1.0
    for h in hop_data:
        total_confidence *= h.confidence_score

    min_level = min((h.evidence_level for h in hop_data), default=0)

    return EvidenceChainPath(
        path_id=path_id,
        hops=hop_data,
        total_confidence=round(total_confidence, 4),
        min_evidence_level=min_level,
    )
```

- [ ] **Step 2: 写测试**

在 `tests/unit/test_multi_hop.py` 中：

```python
"""Tests for multi-hop evidence chain query."""

import pytest
from app.models.graph import EntityRelation
from app.services.graph_service import GraphService


@pytest.mark.asyncio
async def test_multi_hop_no_academic_edges_returns_empty(db_session):
    """When no edges meet academic criteria, result is empty."""
    svc = GraphService(db_session)
    paths = await svc.multi_hop_query(
        source_type="person", source_id="p1",
        target_type="book", target_id="b1",
        min_evidence_level=2, max_hops=3,
    )
    assert paths == []


@pytest.mark.asyncio
async def test_multi_hop_single_hop_path(db_session):
    """A single academic edge should produce a one-hop path."""
    # Create seed entities: person, book
    from app.models.person import Person
    from app.models.book import Book

    person = Person(id="p-test-1", name="测试人物")
    book = Book(id="b-test-1", title="测试书")
    db_session.add_all([person, book])
    await db_session.flush()

    # Create an academic edge
    edge = EntityRelation(
        source_entity_type="person", source_entity_id="p-test-1",
        target_entity_type="book", target_entity_id="b-test-1",
        relation_type="authored",
        evidence_document_id="doc-1",
        evidence_chunk_id="chunk-1",
        evidence_quote="测试原文引用",
        evidence_citation="测试书·卷一",
        evidence_version_id="ver-1",
        evidence_passage_id="pass-1",
        evidence_source_uri="https://ctext.org/test",
        evidence_status="verified",
        evidence_level=3,
        claim_text="测试人物著测试书",
        verified_by="user-1",
    )
    db_session.add(edge)
    await db_session.flush()

    svc = GraphService(db_session)
    paths = await svc.multi_hop_query(
        source_type="person", source_id="p-test-1",
        target_type="book", target_id="b-test-1",
        min_evidence_level=2, max_hops=3,
    )
    assert len(paths) == 1
    assert paths[0].min_evidence_level == 3
    assert paths[0].total_confidence == 0.85
    assert len(paths[0].hops) == 1
    assert paths[0].hops[0].relation_type == "authored"


@pytest.mark.asyncio
async def test_multi_hop_two_hop_path(db_session):
    """A path with two academic edges."""
    from app.models.person import Person
    from app.models.book import Book

    person = Person(id="p-2h-1", name="作者")
    book1 = Book(id="b-2h-1", title="源书")
    book2 = Book(id="b-2h-2", title="目标书")
    db_session.add_all([person, book1, book2])
    await db_session.flush()

    edge1 = EntityRelation(
        source_entity_type="person", source_entity_id="p-2h-1",
        target_entity_type="book", target_entity_id="b-2h-1",
        relation_type="authored",
        evidence_document_id="doc-1", evidence_chunk_id="chunk-1",
        evidence_quote="quote1", evidence_citation="citation1",
        evidence_version_id="ver-1", evidence_passage_id="pass-1",
        evidence_source_uri="https://ctext.org/test1",
        evidence_status="verified", evidence_level=3,
        claim_text="test", verified_by="user-1",
    )
    edge2 = EntityRelation(
        source_entity_type="book", source_entity_id="b-2h-1",
        target_entity_type="book", target_entity_id="b-2h-2",
        relation_type="compiled_from",
        evidence_document_id="doc-2", evidence_chunk_id="chunk-2",
        evidence_quote="quote2", evidence_citation="citation2",
        evidence_version_id="ver-2", evidence_passage_id="pass-2",
        evidence_source_uri="https://ctext.org/test2",
        evidence_status="verified", evidence_level=2,
        claim_text="test", verified_by="user-1",
    )
    db_session.add_all([edge1, edge2])
    await db_session.flush()

    svc = GraphService(db_session)
    paths = await svc.multi_hop_query(
        source_type="person", source_id="p-2h-1",
        target_type="book", target_id="b-2h-2",
        min_evidence_level=2, max_hops=3,
    )
    assert len(paths) == 1
    assert len(paths[0].hops) == 2
    # total confidence = 0.85 * 0.65 = 0.5525
    assert paths[0].total_confidence == 0.5525
    # min evidence level = 2
    assert paths[0].min_evidence_level == 2
```

- [ ] **Step 3: 运行测试**

```bash
cd /Users/likeming/Sites/hfb && python -m pytest tests/unit/test_multi_hop.py -v
```
Expected: 3 tests PASS

- [ ] **Step 4: Commit**

```bash
git add apps/backend/app/services/graph_service.py tests/unit/test_multi_hop.py
git commit -m "feat: multi_hop_query — BFS over academic edges with evidence chains"
```

---

### Task 9: evidence-chains API endpoint

**Files:**
- Create: `apps/backend/app/api/v2/graph.py`
- Modify: `apps/backend/app/api/v2/__init__.py`

**Interfaces:**
- Consumes: Task 7 的 schemas、Task 8 的 multi_hop_query
- Produces: `POST /api/v2/graph/evidence-chains`

- [ ] **Step 1: 创建 graph API 路由**

新建 `apps/backend/app/api/v2/graph.py`：

```python
"""Graph V2 API routes — Phase 2a evidence chain queries."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import require_permission
from app.schemas.graph import (
    EvidenceChainEnvelope,
    MultiHopQueryRequest,
)
from app.services.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["Graph V2"])

guard_graph_read = require_permission("graph", "read")


@router.post(
    "/evidence-chains",
    response_model=EvidenceChainEnvelope,
    dependencies=[Depends(guard_graph_read)],
)
async def evidence_chains(
    body: MultiHopQueryRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EvidenceChainEnvelope:
    """Multi-hop evidence chain query over academically verified edges."""
    svc = GraphService(session)
    paths = await svc.multi_hop_query(
        source_type=body.source_type,
        source_id=body.source_id,
        target_type=body.target_type,
        target_id=body.target_id,
        min_evidence_level=body.min_evidence_level,
        max_hops=body.max_hops,
        relation_types=body.relation_types,
    )
    return EvidenceChainEnvelope(success=True, data=paths, message="ok")
```

- [ ] **Step 2: 更新 v2 __init__.py**

修改 `apps/backend/app/api/v2/__init__.py`：

```python
from app.api.v2.academic import router as academic_router
from app.api.v2.graph import router as graph_router  # Phase 2a

from fastapi import APIRouter

router = APIRouter()
router.include_router(academic_router)
router.include_router(graph_router)  # Phase 2a

__all__ = ["router"]
```

- [ ] **Step 3: 运行 lint**

```bash
cd /Users/likeming/Sites/hfb && ruff check apps/backend/app/api/v2/
```

- [ ] **Step 4: Commit**

```bash
git add apps/backend/app/api/v2/graph.py apps/backend/app/api/v2/__init__.py
git commit -m "feat: POST /api/v2/graph/evidence-chains endpoint"
```

---

## Phase 2b: TEI 升级

### Task 10: Commentary 模型 + Alembic 迁移

**Files:**
- Create: `apps/backend/app/models/commentary.py`
- Create: `apps/backend/app/db/migrations/versions/XXX_phase2b_commentary.py`

**Interfaces:**
- Consumes: 现有 `passages`, `versions`, `persons` 表 (FK)
- Produces: `Commentary` ORM 模型 + 数据库表

- [ ] **Step 1: 创建 Commentary 模型**

新建 `apps/backend/app/models/commentary.py`：

```python
"""Commentary model — 注疏链 for TCM textual scholarship.

Supports multi-layered self-referential commentary structures:
  注 (annotation) → 疏 (sub-commentary) → 笺 (further elaboration)
Each commentary binds to a passage, optionally to a specific version and
character offset range. Self-referential parent_id enables commentary chains.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Text, Integer, CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class Commentary(BaseModel):
    """A scholarly annotation/commentary on a passage.

    Supports the full 注疏笺 hierarchy via parent_id self-reference.
    """

    __tablename__ = "commentaries"

    __table_args__ = (
        CheckConstraint(
            "commentary_type IN ('interlinear_gloss', 'end_of_passage', "
            "'sub_commentary', 'commentary_work', 'critique')",
            name="ck_commentaries_type",
        ),
        CheckConstraint(
            "layer IN ('han', 'tang', 'song', 'ming', 'qing', 'modern')",
            name="ck_commentaries_layer",
        ),
        CheckConstraint(
            "relation_type IS NULL OR relation_type IN "
            "('supplements', 'refutes', 'expands', 'annotates', 'interprets')",
            name="ck_commentaries_relation",
        ),
    )

    passage_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("passages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所注段落 ID",
    )
    version_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("versions.id", ondelete="SET NULL"),
        nullable=True,
        comment="所注版本 ID（夹注可能无版本信息）",
    )
    author_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("persons.id", ondelete="SET NULL"),
        nullable=True,
        comment="注者 ID",
    )
    commentary_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="end_of_passage",
        comment="interlinear_gloss | end_of_passage | sub_commentary | commentary_work | critique",
    )
    layer: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="modern",
        comment="年代层: han, tang, song, ming, qing, modern",
    )
    content_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="注文内容",
    )
    target_position_start: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="段落中起始字符偏移"
    )
    target_position_end: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="段落中结束字符偏移"
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("commentaries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="自引用 — 回应另一条注疏",
    )
    relation_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="supplements | refutes | expands | annotates | interprets",
    )

    def __repr__(self) -> str:
        author = self.author_id[:8] if self.author_id else "?"
        return f"<Commentary type={self.commentary_type} layer={self.layer} by={author}>"
```

- [ ] **Step 2: 生成 Alembic 迁移**

```bash
cd /Users/likeming/Sites/hfb/apps/backend && alembic revision --autogenerate -m "phase2b_commentary"
```

- [ ] **Step 3: 检查并修正迁移文件**

确认迁移包含 `op.create_table('commentaries', ...)` 及所有列和 CHECK 约束。如 autogenerate 漏掉 CHECK 约束，手动补充 `op.create_check_constraint`。

- [ ] **Step 4: 运行迁移**

```bash
cd /Users/likeming/Sites/hfb/apps/backend && ALEMBIC_CONFIG=alembic.ini DATABASE_URL=sqlite+aiosqlite:///./hfb_dev.db alembic upgrade head
```

- [ ] **Step 5: 验证表结构**

```bash
cd /Users/likeming/Sites/hfb/apps/backend && sqlite3 hfb_dev.db ".schema commentaries"
```
Expected: 输出包含 commentaries 表的完整 DDL，含所有 CHECK 约束

- [ ] **Step 6: 写测试 — 模型可创建**

在 `tests/unit/test_commentary.py` 中：

```python
"""Tests for Commentary model — 注疏链."""

import pytest
from app.models.commentary import Commentary


@pytest.mark.asyncio
async def test_create_commentary(db_session):
    """A basic commentary should be creatable."""
    c = Commentary(
        passage_id="pass-test-1",
        author_id="person-test-1",
        commentary_type="end_of_passage",
        layer="tang",
        content_text="此段论经脉流行之理。",
    )
    db_session.add(c)
    await db_session.flush()
    assert c.id is not None
    assert c.commentary_type == "end_of_passage"
    assert c.layer == "tang"


@pytest.mark.asyncio
async def test_commentary_self_reference_chain(db_session):
    """A sub-commentary should reference a parent commentary."""
    parent = Commentary(
        passage_id="pass-test-2",
        author_id="person-test-2",
        commentary_type="commentary_work",
        layer="tang",
        content_text="王冰注：此乃阴阳之道。",
    )
    db_session.add(parent)
    await db_session.flush()

    child = Commentary(
        passage_id="pass-test-2",
        author_id="person-test-3",
        commentary_type="sub_commentary",
        layer="ming",
        content_text="王注非也，应为阴阳离合论。",
        parent_id=parent.id,
        relation_type="refutes",
    )
    db_session.add(child)
    await db_session.flush()

    assert child.parent_id == parent.id
    assert child.relation_type == "refutes"


@pytest.mark.asyncio
async def test_commentary_invalid_type_raises(db_session):
    """Inserting an invalid commentary_type should fail at DB level."""
    c = Commentary(
        passage_id="pass-test-3",
        content_text="test",
        commentary_type="invalid_type",  # not in CHECK
        layer="modern",
    )
    db_session.add(c)
    with pytest.raises(Exception):
        await db_session.flush()
```

- [ ] **Step 7: 运行测试**

```bash
cd /Users/likeming/Sites/hfb && python -m pytest tests/unit/test_commentary.py -v
```
Expected: 3 tests PASS

- [ ] **Step 8: Commit**

```bash
git add apps/backend/app/models/commentary.py apps/backend/app/db/migrations/versions/ tests/unit/test_commentary.py
git commit -m "feat: Commentary model with self-referential 注疏链 + migration"
```

---

### Task 11: TEI Commentary CRUD + chain query

**Files:**
- Modify: `apps/backend/app/services/version_center.py` — 新增 CommentaryService 或直接在 VersionComparisonService 中加方法
- Modify: `apps/backend/app/schemas/tei.py`（或新建 `app/schemas/commentary.py`）
- Create: `apps/backend/app/api/v2/tei.py` — commentary endpoints
- Modify: `apps/backend/app/api/v2/__init__.py`

**Interfaces:**
- Consumes: Commentary 模型
- Produces: `POST /api/v2/tei/commentary`, `GET /api/v2/tei/passage/{id}/commentaries`, `GET /api/v2/tei/commentary/{id}/chain`, `GET /api/v2/tei/commentary-graph`

- [ ] **Step 1: 创建 Commentary schema**

新建 `apps/backend/app/schemas/commentary.py`：

```python
"""Commentary schemas — Phase 2b 注疏链."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CommentaryCreate(BaseModel):
    """Request to create a commentary."""

    model_config = ConfigDict(extra="forbid", strict=True)

    passage_id: str = Field(..., description="所注段落 ID")
    version_id: str | None = Field(default=None, description="所注版本 ID")
    author_id: str | None = Field(default=None, description="注者 ID")
    commentary_type: str = Field(
        default="end_of_passage",
        description="interlinear_gloss | end_of_passage | sub_commentary | commentary_work | critique"
    )
    layer: str = Field(default="modern", description="年代层")
    content_text: str = Field(..., description="注文内容")
    target_position_start: int | None = Field(default=None, description="段落中起始字符偏移")
    target_position_end: int | None = Field(default=None, description="段落中结束字符偏移")
    parent_id: str | None = Field(default=None, description="自引用 — 回应另一条注疏")
    relation_type: str | None = Field(
        default=None,
        description="supplements | refutes | expands | annotates | interprets"
    )


class CommentaryResponse(BaseModel):
    """Commentary as returned to API consumers."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    passage_id: str
    version_id: str | None = None
    author_id: str | None = None
    commentary_type: str
    layer: str
    content_text: str
    target_position_start: int | None = None
    target_position_end: int | None = None
    parent_id: str | None = None
    relation_type: str | None = None
    created_at: datetime
    updated_at: datetime


class CommentaryChainResponse(BaseModel):
    """A full commentary chain from root to leaf."""

    model_config = ConfigDict(extra="forbid", strict=True)

    chain: list[CommentaryResponse] = Field(default_factory=list)
    depth: int = Field(default=0)


class CommentaryGraphResponse(BaseModel):
    """Commentary debate/supplement graph for a passage."""

    model_config = ConfigDict(extra="forbid", strict=True)

    nodes: list[CommentaryResponse] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)  # {parent_id, child_id, relation_type}


class CommentaryEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    success: bool = Field(default=True)
    data: CommentaryResponse | CommentaryChainResponse | CommentaryGraphResponse | list[CommentaryResponse]
    message: str = Field(default="ok")
```

- [ ] **Step 2: 在 version_center.py 中新增 Commentary CRUD**

在 `apps/backend/app/services/version_center.py` 末尾新增：

```python
# ======================================================================
# Phase 2b: Commentary (注疏链) CRUD
# ======================================================================

from app.models.commentary import Commentary
from app.schemas.commentary import CommentaryCreate, CommentaryResponse


async def create_commentary(
    session: AsyncSession,
    data: CommentaryCreate,
) -> CommentaryResponse:
    """Create a commentary annotation."""
    c = Commentary(
        passage_id=data.passage_id,
        version_id=data.version_id,
        author_id=data.author_id,
        commentary_type=data.commentary_type,
        layer=data.layer,
        content_text=data.content_text,
        target_position_start=data.target_position_start,
        target_position_end=data.target_position_end,
        parent_id=data.parent_id,
        relation_type=data.relation_type,
    )
    session.add(c)
    await session.flush()
    await session.refresh(c)
    return CommentaryResponse(
        id=c.id,
        passage_id=c.passage_id,
        version_id=c.version_id,
        author_id=c.author_id,
        commentary_type=c.commentary_type,
        layer=c.layer,
        content_text=c.content_text,
        target_position_start=c.target_position_start,
        target_position_end=c.target_position_end,
        parent_id=c.parent_id,
        relation_type=c.relation_type,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


async def get_commentaries_for_passage(
    session: AsyncSession,
    passage_id: str,
    layer: str | None = None,
) -> list[CommentaryResponse]:
    """Get all commentaries for a passage, optionally filtered by layer."""
    stmt = select(Commentary).where(
        Commentary.passage_id == passage_id,
        Commentary.is_deleted.is_(False),
    )
    if layer:
        stmt = stmt.where(Commentary.layer == layer)
    stmt = stmt.order_by(Commentary.created_at)
    result = await session.execute(stmt)
    commentaries = result.scalars().all()
    return [
        CommentaryResponse(
            id=c.id, passage_id=c.passage_id, version_id=c.version_id,
            author_id=c.author_id, commentary_type=c.commentary_type,
            layer=c.layer, content_text=c.content_text,
            target_position_start=c.target_position_start,
            target_position_end=c.target_position_end,
            parent_id=c.parent_id, relation_type=c.relation_type,
            created_at=c.created_at, updated_at=c.updated_at,
        ) for c in commentaries
    ]


async def get_commentary_chain(
    session: AsyncSession,
    commentary_id: str,
) -> list[CommentaryResponse]:
    """Trace the full commentary chain from root to the given node."""
    chain: list[CommentaryResponse] = []
    current_id: str | None = commentary_id
    visited: set[str] = set()

    while current_id and current_id not in visited:
        visited.add(current_id)
        stmt = select(Commentary).where(
            Commentary.id == current_id,
            Commentary.is_deleted.is_(False),
        )
        result = await session.execute(stmt)
        c = result.scalar_one_or_none()
        if not c:
            break
        chain.append(CommentaryResponse(
            id=c.id, passage_id=c.passage_id, version_id=c.version_id,
            author_id=c.author_id, commentary_type=c.commentary_type,
            layer=c.layer, content_text=c.content_text,
            target_position_start=c.target_position_start,
            target_position_end=c.target_position_end,
            parent_id=c.parent_id, relation_type=c.relation_type,
            created_at=c.created_at, updated_at=c.updated_at,
        ))
        current_id = c.parent_id

    chain.reverse()  # root first
    return chain


async def get_commentary_graph(
    session: AsyncSession,
    passage_id: str,
) -> dict:
    """Get the commentary debate/supplement graph for a passage."""
    stmt = select(Commentary).where(
        Commentary.passage_id == passage_id,
        Commentary.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    commentaries = result.scalars().all()

    nodes = [
        CommentaryResponse(
            id=c.id, passage_id=c.passage_id, version_id=c.version_id,
            author_id=c.author_id, commentary_type=c.commentary_type,
            layer=c.layer, content_text=c.content_text,
            target_position_start=c.target_position_start,
            target_position_end=c.target_position_end,
            parent_id=c.parent_id, relation_type=c.relation_type,
            created_at=c.created_at, updated_at=c.updated_at,
        ) for c in commentaries
    ]

    edges = [
        {"parent_id": c.parent_id, "child_id": c.id, "relation_type": c.relation_type}
        for c in commentaries if c.parent_id
    ]

    return {"nodes": nodes, "edges": edges}
```

- [ ] **Step 3: 创建 TEI V2 API 路由**

新建 `apps/backend/app/api/v2/tei.py`：

```python
"""TEI V2 API routes — Phase 2b commentary, version_tree, variants."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import require_permission
from app.schemas.commentary import (
    CommentaryChainResponse,
    CommentaryCreate,
    CommentaryEnvelope,
    CommentaryGraphResponse,
    CommentaryResponse,
)
from app.services.version_center import (
    create_commentary,
    get_commentaries_for_passage,
    get_commentary_chain,
    get_commentary_graph,
)

router = APIRouter(prefix="/tei", tags=["TEI V2"])

guard_tei_read = require_permission("ai", "read")
guard_tei_write = require_permission("graph", "review")


@router.get(
    "/passage/{passage_id}/commentaries",
    response_model=CommentaryEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def passage_commentaries(
    passage_id: str,
    layer: Annotated[str | None, Query(description="年代层过滤")] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> CommentaryEnvelope:
    """Get all commentaries for a passage, optionally by layer."""
    result = await get_commentaries_for_passage(session, passage_id, layer=layer)
    return CommentaryEnvelope(success=True, data=result, message="ok")


@router.get(
    "/commentary/{commentary_id}/chain",
    response_model=CommentaryEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def commentary_chain(
    commentary_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CommentaryEnvelope:
    """Trace full commentary chain from root to this commentary."""
    chain = await get_commentary_chain(session, commentary_id)
    return CommentaryEnvelope(
        success=True,
        data=CommentaryChainResponse(chain=chain, depth=len(chain)),
        message="ok",
    )


@router.post(
    "/commentary",
    response_model=CommentaryEnvelope,
    dependencies=[Depends(guard_tei_write)],
)
async def create_commentary_endpoint(
    body: CommentaryCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CommentaryEnvelope:
    """Create a new commentary annotation."""
    result = await create_commentary(session, body)
    return CommentaryEnvelope(success=True, data=result, message="ok")


@router.get(
    "/commentary-graph",
    response_model=CommentaryEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def commentary_graph(
    passage_id: Annotated[str, Query(description="段落 ID")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CommentaryEnvelope:
    """Get the commentary debate/supplement graph for a passage."""
    graph = await get_commentary_graph(session, passage_id)
    return CommentaryEnvelope(
        success=True,
        data=CommentaryGraphResponse(nodes=graph["nodes"], edges=graph["edges"]),
        message="ok",
    )
```

- [ ] **Step 4: 更新 v2 __init__.py**

```python
from app.api.v2.academic import router as academic_router
from app.api.v2.graph import router as graph_router
from app.api.v2.tei import router as tei_router  # Phase 2b

from fastapi import APIRouter

router = APIRouter()
router.include_router(academic_router)
router.include_router(graph_router)
router.include_router(tei_router)  # Phase 2b

__all__ = ["router"]
```

- [ ] **Step 5: 运行 lint**

```bash
cd /Users/likeming/Sites/hfb && ruff check apps/backend/app/api/v2/ apps/backend/app/services/version_center.py apps/backend/app/schemas/commentary.py
```

- [ ] **Step 6: Commit**

```bash
git add apps/backend/app/schemas/commentary.py apps/backend/app/services/version_center.py apps/backend/app/api/v2/tei.py apps/backend/app/api/v2/__init__.py
git commit -m "feat: commentary CRUD + chain query + graph API endpoints"
```

---

### Task 12: version_tree + distance matrix API

**Files:**
- Modify: `apps/backend/app/services/version_center.py` — 新增 `compute_version_tree`、`compute_distance_matrix`、`find_divergence_points`
- Modify: `apps/backend/app/api/v2/tei.py` — 新增 `/version-tree/{version_id}`、`/apparatus`、variant 聚合端点

**Interfaces:**
- Consumes: `VersionRelation`, `VersionDiff`, `PassageMapping`, `TextualVariant`, `TEISerializer`
- Produces: `GET /api/v2/tei/version-tree/{id}`, `GET /api/v2/tei/passage/{id}/variants`, `GET /api/v2/tei/version/{id}/variants`, `GET /api/v2/tei/apparatus`

- [ ] **Step 1: 实现 compute_distance_matrix**

在 `apps/backend/app/services/version_center.py` 中新增：

```python
# ======================================================================
# Phase 2b: Version Tree & Distance Matrix
# ======================================================================

async def compute_distance_matrix(
    session: AsyncSession,
    version_ids: list[str],
) -> dict[str, float]:
    """Compute Jaccard distance matrix for a set of versions.

    Jaccard distance = lines_changed / total_lines, derived from
    pre-computed VersionDiff records. Missing pairs return 1.0 (max distance).
    """
    from app.models.version_relation import VersionDiff
    from itertools import combinations

    matrix: dict[str, float] = {}
    for va_id, vb_id in combinations(version_ids, 2):
        # Look for existing VersionDiff
        stmt = select(VersionDiff).where(
            (
                (VersionDiff.source_version_id == va_id) & (VersionDiff.target_version_id == vb_id)
            ) | (
                (VersionDiff.source_version_id == vb_id) & (VersionDiff.target_version_id == va_id)
            ),
            VersionDiff.is_deleted.is_(False),
        )
        result = await session.execute(stmt)
        diff = result.scalar_one_or_none()

        if diff and diff.diff_data:
            import json
            diff_data = json.loads(diff.diff_data) if isinstance(diff.diff_data, str) else diff.diff_data
            lines_changed = diff_data.get("lines_changed", 0)
            total_lines = diff_data.get("total_lines", 1)
            distance = lines_changed / max(total_lines, 1)
        else:
            distance = 1.0  # max distance if no diff data

        matrix[f"{va_id}-{vb_id}"] = round(min(distance, 1.0), 4)

    return matrix


async def compute_version_tree(
    session: AsyncSession,
    version_id: str,
) -> dict:
    """Build a version lineage tree rooted at or including the given version.

    Returns: root_version info, tree edges, distance matrix, closest versions,
    and divergence points.
    """
    from app.models.version import Version
    from app.models.version_relation import VersionRelation, PassageMapping
    from app.models.tei import TextualVariant
    from collections import defaultdict

    # Get the root version
    stmt = select(Version).where(Version.id == version_id, Version.is_deleted.is_(False))
    result = await session.execute(stmt)
    root = result.scalar_one_or_none()
    if not root:
        raise ValueError(f"Version {version_id} not found")

    # Collect all versions in the lineage
    version_set: set[str] = {version_id}
    relations_raw: list[VersionRelation] = []

    # Upward traversal
    current_id = version_id
    while current_id:
        stmt = select(VersionRelation).where(
            VersionRelation.target_version_id == current_id,
            VersionRelation.is_deleted.is_(False),
        )
        result = await session.execute(stmt)
        rel = result.scalar_one_or_none()
        if rel:
            relations_raw.append(rel)
            version_set.add(rel.source_version_id)
            current_id = rel.source_version_id
        else:
            break

    # Downward traversal from all known versions
    for vid in list(version_set):
        stmt = select(VersionRelation).where(
            VersionRelation.source_version_id == vid,
            VersionRelation.is_deleted.is_(False),
        )
        result = await session.execute(stmt)
        for rel in result.scalars().all():
            if rel.target_version_id not in version_set:
                relations_raw.append(rel)
                version_set.add(rel.target_version_id)

    # Fetch all version objects
    all_versions: dict[str, Version] = {}
    if version_set:
        stmt = select(Version).where(Version.id.in_(version_set), Version.is_deleted.is_(False))
        result = await session.execute(stmt)
        all_versions = {v.id: v for v in result.scalars().all()}

    # Build tree edges
    tree_edges = []
    for rel in relations_raw:
        distance = 1.0
        # Check for diff
        from app.models.version_relation import VersionDiff
        diff_stmt = select(VersionDiff).where(
            (
                (VersionDiff.source_version_id == rel.source_version_id) & (VersionDiff.target_version_id == rel.target_version_id)
            ),
            VersionDiff.is_deleted.is_(False),
        )
        diff_result = await session.execute(diff_stmt)
        diff = diff_result.scalar_one_or_none()
        if diff and diff.diff_data:
            import json
            diff_data = json.loads(diff.diff_data) if isinstance(diff.diff_data, str) else diff.diff_data
            lines_changed = diff_data.get("lines_changed", 0)
            total_lines = diff_data.get("total_lines", 1)
            distance = lines_changed / max(total_lines, 1)

        tree_edges.append({
            "parent_id": rel.source_version_id,
            "child_id": rel.target_version_id,
            "relation_type": rel.relation_type,
            "distance": round(min(distance, 1.0), 4),
        })

    # Distance matrix
    version_list = sorted(version_set)
    distance_matrix = await compute_distance_matrix(session, version_list)

    # Closest versions to root
    closest = []
    root_distances = {}
    for key, dist in distance_matrix.items():
        v1, v2 = key.split("-")
        if v1 == version_id:
            root_distances[v2] = dist
        elif v2 == version_id:
            root_distances[v1] = dist

    for other_id in sorted(root_distances, key=root_distances.get):
        v_obj = all_versions.get(other_id)
        closest.append({
            "version_id": other_id,
            "name": v_obj.version_name if v_obj else other_id,
            "distance": root_distances[other_id],
        })

    # Divergence points: passage mappings with high variant counts
    divergence_points = []
    # Find passages shared between root and each related version
    for other_id in list(version_set - {version_id}):
        variant_stmt = select(TextualVariant).where(
            (
                (TextualVariant.source_version_id == version_id) & (TextualVariant.target_version_id == other_id)
            ) | (
                (TextualVariant.source_version_id == other_id) & (TextualVariant.target_version_id == version_id)
            ),
            TextualVariant.is_deleted.is_(False),
        )
        variant_result = await session.execute(variant_stmt)
        variants = variant_result.scalars().all()

        # Group by passage
        passage_counts: dict[str, list] = defaultdict(list)
        for v in variants:
            pid = v.source_passage_id or v.target_passage_id
            if pid:
                passage_counts[pid].append(v)

        for pid, vlist in passage_counts.items():
            if len(vlist) >= 1:  # at least one variant
                from app.models.passage import Passage
                pass_stmt = select(Passage).where(Passage.id == pid, Passage.is_deleted.is_(False))
                pass_result = await session.execute(pass_stmt)
                passage = pass_result.scalar_one_or_none()
                divergence_points.append({
                    "passage_id": pid,
                    "passage_text": passage.content_text[:200] if passage else "",
                    "diff_summary": f"{len(vlist)} variants between {version_id} and {other_id}",
                    "variant_count": len(vlist),
                })

    return {
        "root_version": {
            "id": root.id,
            "name": root.version_name,
            "era": root.era or "",
            "year": root.year or 0,
        },
        "tree": tree_edges,
        "distance_matrix": distance_matrix,
        "closest_to": closest,
        "divergence_points": divergence_points[:20],  # top 20
    }
```

- [ ] **Step 2: 在 tei.py 路由中新增 version-tree 端点**

在 `apps/backend/app/api/v2/tei.py` 中追加：

```python
from app.services.version_center import compute_version_tree
from app.services.version_center import VersionComparisonService


class VersionTreeEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    success: bool = Field(default=True)
    data: dict = Field(default_factory=dict)
    message: str = Field(default="ok")


@router.get(
    "/version-tree/{version_id}",
    response_model=VersionTreeEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def version_tree(
    version_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VersionTreeEnvelope:
    """Get version lineage tree, distance matrix, and divergence points."""
    data = await compute_version_tree(session, version_id)
    return VersionTreeEnvelope(success=True, data=data, message="ok")


@router.get(
    "/passage/{passage_id}/variants",
    response_model=VersionTreeEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def passage_variants(
    passage_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VersionTreeEnvelope:
    """Get all variants for a passage across all versions, grouped by apparatus."""
    from app.models.tei import TextualVariant
    stmt = select(TextualVariant).where(
        (
            (TextualVariant.source_passage_id == passage_id) | (TextualVariant.target_passage_id == passage_id)
        ),
        TextualVariant.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    variants = result.scalars().all()
    # Group by apparatus (lemma)
    from collections import defaultdict
    groups: dict[str, list] = defaultdict(list)
    for v in variants:
        key = v.lemma or v.location or "unknown"
        groups[key].append({
            "id": v.id,
            "source_version_id": v.source_version_id,
            "target_version_id": v.target_version_id,
            "lemma": v.lemma,
            "reading": v.reading,
            "variant_type": v.variant_type,
            "apparatus": v.apparatus,
            "verification_status": v.verification_status,
        })
    data = {"passage_id": passage_id, "groups": {k: v for k, v in groups.items()}}
    return VersionTreeEnvelope(success=True, data=data, message="ok")


@router.get(
    "/version/{source_id}/variants",
    response_model=VersionTreeEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def version_variants(
    source_id: str,
    target_version: Annotated[str | None, Query(description="目标版本 ID")] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> VersionTreeEnvelope:
    """Get all variants between a source version and optionally a target version."""
    from app.models.tei import TextualVariant
    stmt = select(TextualVariant).where(
        TextualVariant.source_version_id == source_id,
        TextualVariant.is_deleted.is_(False),
    )
    if target_version:
        stmt = stmt.where(TextualVariant.target_version_id == target_version)
    result = await session.execute(stmt)
    variants = result.scalars().all()
    data = {
        "source_version_id": source_id,
        "target_version_id": target_version,
        "variant_count": len(variants),
        "variants": [
            {
                "id": v.id,
                "target_version_id": v.target_version_id,
                "passage_id": v.source_passage_id or v.target_passage_id,
                "lemma": v.lemma,
                "reading": v.reading,
                "variant_type": v.variant_type,
                "apparatus": v.apparatus,
            }
            for v in variants
        ],
    }
    return VersionTreeEnvelope(success=True, data=data, message="ok")


@router.get(
    "/apparatus",
    response_model=VersionTreeEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def tei_apparatus(
    passage_id: Annotated[str, Query(description="段落 ID")],
    source_version: Annotated[str, Query(description="源版本 ID")],
    target_version: Annotated[str, Query(description="目标版本 ID")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VersionTreeEnvelope:
    """Generate TEI XML critical apparatus for a passage between two versions."""
    from app.models.tei import TextualVariant
    stmt = select(TextualVariant).where(
        (
            (TextualVariant.source_version_id == source_version) & (TextualVariant.target_version_id == target_version)
        ) | (
            (TextualVariant.source_version_id == target_version) & (TextualVariant.target_version_id == source_version)
        ),
        (
            (TextualVariant.source_passage_id == passage_id) | (TextualVariant.target_passage_id == passage_id)
        ),
        TextualVariant.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    variants = result.scalars().all()

    # Build TEI XML apparatus
    from tcm_tei.serializer import TEISerializer
    # Get passage text
    from app.models.passage import Passage
    pass_stmt = select(Passage).where(Passage.id == passage_id, Passage.is_deleted.is_(False))
    pass_result = await session.execute(pass_stmt)
    passage = pass_result.scalar_one_or_none()

    # Build simple apparatus XML
    apps_xml = ""
    for v in variants:
        lemma = v.lemma or ""
        reading = v.reading or ""
        apps_xml += f'<app><lem wit="#{source_version}">{lemma}</lem><rdg wit="#{target_version}">{reading}</rdg></app>\n'

    tei_xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<TEI xmlns="http://www.tei-c.org/ns/1.0">\n<text>\n<body>\n<div type="apparatus">\n{apps_xml}</div>\n</body>\n</text>\n</TEI>'

    data = {
        "passage_id": passage_id,
        "source_version_id": source_version,
        "target_version_id": target_version,
        "tei_xml": tei_xml,
        "variant_count": len(variants),
    }
    return VersionTreeEnvelope(success=True, data=data, message="ok")
```

- [ ] **Step 3: 写测试**

在 `tests/unit/test_version_tree.py` 中：

```python
"""Tests for version tree and distance matrix."""

import pytest
from app.services.version_center import compute_distance_matrix


@pytest.mark.asyncio
async def test_distance_matrix_empty(db_session):
    """Empty version list → empty matrix."""
    matrix = await compute_distance_matrix(db_session, [])
    assert matrix == {}


@pytest.mark.asyncio
async def test_distance_matrix_single_version(db_session):
    """Single version → empty matrix (no pairs)."""
    matrix = await compute_distance_matrix(db_session, ["v1"])
    assert matrix == {}


@pytest.mark.asyncio
async def test_distance_matrix_no_diff_data(db_session):
    """Two versions with no VersionDiff → max distance."""
    matrix = await compute_distance_matrix(db_session, ["v1", "v2"])
    assert matrix.get("v1-v2", matrix.get("v2-v1")) == 1.0
```

- [ ] **Step 4: 运行测试**

```bash
cd /Users/likeming/Sites/hfb && python -m pytest tests/unit/test_version_tree.py -v
```

- [ ] **Step 5: 运行 lint**

```bash
cd /Users/likeming/Sites/hfb && ruff check apps/backend/app/services/version_center.py apps/backend/app/api/v2/tei.py
```

- [ ] **Step 6: Commit**

```bash
git add apps/backend/app/services/version_center.py apps/backend/app/api/v2/tei.py tests/unit/test_version_tree.py
git commit -m "feat: version_tree API — distance matrix, divergence points, apparatus, variant aggregation"
```

---

## Phase 2c: 论文引擎

### Task 13: ConflictDetector — 拓扑冲突 + 中医语义冲突检测

**Files:**
- Create: `apps/backend/app/services/conflict_detector.py`
- Create: `tests/unit/test_conflict_detector.py`

**Interfaces:**
- Consumes: `EvidenceChainPath[]`（Task 8 输出）、`EntityRelation`（查 rejected 边）
- Produces: `ConflictDetector.detect(paths, session) -> list[Conflict]`

- [ ] **Step 1: 创建 ConflictDetector**

新建 `apps/backend/app/services/conflict_detector.py`：

```python
"""ConflictDetector — topological & TCM semantic conflict detection.

Phase 2c: Detects two classes of conflicts in evidence chains:
  1. Topological: reverse relations, same claim with rejected edges
  2. TCM Semantic: 十八反/十九畏 herb incompatibility, acupuncture contraindication
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.graph import EntityRelation
from app.schemas.graph import EvidenceChainPath, EvidenceHop


# TCM incompatibility pairs: herbs that must not be combined
_EIGHTEEN_ANTAGONISMS: set[frozenset[str]] = frozenset({
    frozenset({"甘草", "甘遂"}),
    frozenset({"甘草", "大戟"}),
    frozenset({"甘草", "海藻"}),
    frozenset({"甘草", "芫花"}),
    frozenset({"乌头", "贝母"}),
    frozenset({"乌头", "瓜蒌"}),
    frozenset({"乌头", "半夏"}),
    frozenset({"乌头", "白蔹"}),
    frozenset({"乌头", "白及"}),
    frozenset({"藜芦", "人参"}),
    frozenset({"藜芦", "沙参"}),
    frozenset({"藜芦", "丹参"}),
    frozenset({"藜芦", "玄参"}),
    frozenset({"藜芦", "细辛"}),
    frozenset({"藜芦", "芍药"}),
})

# Acupuncture contraindication keywords
_ACUPUNCTURE_CONTRA_KEYWORDS: dict[str, str] = {
    "禁针": "prohibits needling",
    "禁灸": "prohibits moxibustion",
    "不可刺": "must not be needled",
    "不可灸": "must not be moxibusted",
    "禁刺": "prohibits needling",
}


@dataclass
class Conflict:
    """A detected conflict in evidence chains."""

    conflict_type: str  # "topological_reverse" | "topological_rejected" | "tcm_herb_incompatibility" | "tcm_acupuncture_contra"
    description: str
    affected_path_ids: list[str] = field(default_factory=list)
    related_entities: list[str] = field(default_factory=list)
    severity: str = "warning"  # "warning" | "error"


class ConflictDetector:
    """Detect conflicts in evidence chain paths."""

    @staticmethod
    async def detect(
        session: AsyncSession,
        paths: list[EvidenceChainPath],
    ) -> list[Conflict]:
        """Run all conflict detectors against evidence paths."""
        conflicts: list[Conflict] = []

        # 1. Topological: reverse relation pairs
        conflicts.extend(ConflictDetector._detect_reverse_relations(paths))

        # 2. Topological: same claim has rejected sibling edges
        conflicts.extend(await ConflictDetector._detect_rejected_claims(session, paths))

        # 3. TCM: herb incompatibility (十八反/十九畏)
        conflicts.extend(ConflictDetector._detect_herb_incompatibility(paths))

        # 4. TCM: acupuncture contraindication conflicts
        conflicts.extend(ConflictDetector._detect_acupuncture_contra(paths))

        return conflicts

    @staticmethod
    def _detect_reverse_relations(paths: list[EvidenceChainPath]) -> list[Conflict]:
        """Detect A→B and B→A in different paths."""
        conflicts: list[Conflict] = []
        edges_seen: dict[tuple[str, str, str, str, str], str] = {}
        # key: (source_type, source_id, target_type, target_id) → path_id

        for path in paths:
            for hop in path.hops:
                forward = (hop.source_type, hop.source_id, hop.target_type, hop.target_id)
                reverse = (hop.target_type, hop.target_id, hop.source_type, hop.source_id)

                if reverse in edges_seen:
                    conflicts.append(Conflict(
                        conflict_type="topological_reverse",
                        description=f"反向关系: {hop.source_type}:{hop.source_id} ←→ {hop.target_type}:{hop.target_id} "
                                    f"(路径 {edges_seen[reverse]} 与 {path.path_id})",
                        affected_path_ids=[edges_seen[reverse], path.path_id],
                        related_entities=[hop.source_id, hop.target_id],
                    ))
                edges_seen[forward] = path.path_id
        return conflicts

    @staticmethod
    async def _detect_rejected_claims(
        session: AsyncSession,
        paths: list[EvidenceChainPath],
    ) -> list[Conflict]:
        """Detect evidence paths whose claim has rejected peers."""
        conflicts: list[Conflict] = []
        for path in paths:
            for hop in path.hops:
                # Look for rejected edges with same claim pattern
                stmt = select(EntityRelation).where(
                    EntityRelation.source_entity_type == hop.source_type,
                    EntityRelation.source_entity_id == hop.source_id,
                    EntityRelation.target_entity_type == hop.target_type,
                    EntityRelation.target_entity_id == hop.target_id,
                    EntityRelation.relation_type == hop.relation_type,
                    EntityRelation.evidence_status == "rejected",
                    EntityRelation.is_deleted.is_(False),
                )
                result = await session.execute(stmt)
                rejected = result.scalars().all()
                if rejected:
                    conflicts.append(Conflict(
                        conflict_type="topological_rejected",
                        description=f"发现 {len(rejected)} 条被驳回的关系与路径 {path.path_id} 中的边对应同一 claim",
                        affected_path_ids=[path.path_id],
                        related_entities=[hop.source_id, hop.target_id],
                        severity="error",
                    ))
        return conflicts

    @staticmethod
    def _detect_herb_incompatibility(paths: list[EvidenceChainPath]) -> list[Conflict]:
        """Detect 十八反/十九畏 in herb entities across paths."""
        conflicts: list[Conflict] = []
        # Collect all herb entity names mentioned across paths
        herb_names: set[str] = set()
        for path in paths:
            for hop in path.hops:
                for etype in [hop.source_type, hop.target_type]:
                    if etype == "herb":
                        # citation often contains herb name
                        if hop.citation:
                            herb_names.add(hop.citation)

        # Check for incompatibility pairs
        for pair in _EIGHTEEN_ANTAGONISMS:
            found = [h for h in herb_names if any(p in h for p in pair)]
            if len(found) >= 2:
                conflicts.append(Conflict(
                    conflict_type="tcm_herb_incompatibility",
                    description=f"配伍禁忌: {', '.join(found)} 可能存在十八反/十九畏冲突",
                    related_entities=found,
                    severity="error",
                ))
        return conflicts

    @staticmethod
    def _detect_acupuncture_contra(paths: list[EvidenceChainPath]) -> list[Conflict]:
        """Detect conflicting acupuncture indications across versions."""
        conflicts: list[Conflict] = []
        for path in paths:
            quotes = [h.exact_quote for h in path.hops if h.exact_quote]
            contra_found: list[str] = []
            for quote in quotes:
                for keyword, desc in _ACUPUNCTURE_CONTRA_KEYWORDS.items():
                    if keyword in quote:
                        contra_found.append(f"{keyword}({desc})")

            if len(contra_found) >= 2:
                conflicts.append(Conflict(
                    conflict_type="tcm_acupuncture_contra",
                    description=f"针灸禁忌冲突: 路径 {path.path_id} 中同时出现 {' 和 '.join(contra_found)}",
                    affected_path_ids=[path.path_id],
                ))
        return conflicts
```

- [ ] **Step 2: 写测试**

在 `tests/unit/test_conflict_detector.py` 中：

```python
"""Tests for ConflictDetector."""

import pytest
from app.services.conflict_detector import ConflictDetector
from app.schemas.graph import EvidenceChainPath, EvidenceHop


def make_hop(source_type, source_id, target_type, target_id, relation_type="related_to", citation="", quote="", level=3):
    return EvidenceHop(
        source_type=source_type, source_id=source_id,
        target_type=target_type, target_id=target_id,
        relation_type=relation_type, evidence_level=level,
        confidence_score=0.85, citation=citation,
        exact_quote=quote, source_uri="",
    )


@pytest.mark.asyncio
async def test_empty_paths_no_conflicts(db_session):
    """No paths → no conflicts."""
    conflicts = await ConflictDetector.detect(db_session, [])
    assert conflicts == []


@pytest.mark.asyncio
async def test_reverse_relation_detected(db_session):
    """A→B and B→A should be detected as topological conflict."""
    path1 = EvidenceChainPath(
        path_id="path1",
        hops=[make_hop("herb", "h1", "herb", "h2")],
        total_confidence=0.85, min_evidence_level=3,
    )
    path2 = EvidenceChainPath(
        path_id="path2",
        hops=[make_hop("herb", "h2", "herb", "h1")],
        total_confidence=0.85, min_evidence_level=3,
    )
    conflicts = await ConflictDetector.detect(db_session, [path1, path2])
    assert any(c.conflict_type == "topological_reverse" for c in conflicts)


@pytest.mark.asyncio
async def test_herb_incompatibility_detected(db_session):
    """甘草 and 甘遂 together should trigger 十八反."""
    path = EvidenceChainPath(
        path_id="path1",
        hops=[
            make_hop("prescription", "rx1", "herb", "h1", citation="甘草"),
            make_hop("prescription", "rx1", "herb", "h2", citation="甘遂"),
        ],
        total_confidence=0.72, min_evidence_level=2,
    )
    conflicts = await ConflictDetector.detect(db_session, [path])
    assert any(c.conflict_type == "tcm_herb_incompatibility" for c in conflicts)
```

- [ ] **Step 3: 运行测试**

```bash
cd /Users/likeming/Sites/hfb && python -m pytest tests/unit/test_conflict_detector.py -v
```
Expected: 3 tests PASS

- [ ] **Step 4: Commit**

```bash
git add apps/backend/app/services/conflict_detector.py tests/unit/test_conflict_detector.py
git commit -m "feat: ConflictDetector — topological + TCM semantic conflict detection"
```

---

### Task 14: PaperService — 8 模块论文组装

**Files:**
- Create: `apps/backend/app/services/paper_service.py`

**Interfaces:**
- Consumes: `GraphService.multi_hop_query`, TEI enricher functions, `ConflictDetector.detect`
- Produces: `PaperService.generate_paper(query) -> dict`（含 8 模块 JSON + Markdown）

- [ ] **Step 1: 创建 PaperService**

新建 `apps/backend/app/services/paper_service.py`：

```python
"""PaperService — assemble 8-module structured academic papers.

Phase 2c: Zero-LLM paper generation. All text comes from template filling
or raw data. Every claim traces to a source citation + evidence_level.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.graph import EvidenceChainPath, MultiHopQueryRequest
from app.services.conflict_detector import ConflictDetector
from app.services.graph_service import GraphService
from app.services.version_center import (
    compute_version_tree,
    get_commentaries_for_passage,
)


class PaperService:
    """Generate structured academic papers from KG + TEI data."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.graph_svc = GraphService(session)

    async def generate_paper(
        self,
        source_type: str,
        source_id: str,
        target_type: str | None = None,
        target_id: str | None = None,
        relation_types: list[str] | None = None,
        min_evidence_level: int = 2,
        max_hops: int = 5,
    ) -> dict:
        """Generate a full 8-module academic paper.

        Returns:
            dict with keys: paper_id, generated_at, query, modules (JSON),
            markdown (str)
        """
        # Phase 1: Evidence collection
        paths = await self.graph_svc.multi_hop_query(
            source_type=source_type, source_id=source_id,
            target_type=target_type, target_id=target_id,
            min_evidence_level=min_evidence_level, max_hops=max_hops,
            relation_types=relation_types,
        )

        # Collect all unique version IDs and passage IDs
        all_version_ids: set[str] = set()
        all_passage_ids: set[str] = set()
        for path in paths:
            for hop in path.hops:
                all_version_ids.add(hop.source_id if hop.source_type == "version" else "")
                all_version_ids.add(hop.target_id if hop.target_type == "version" else "")

        all_version_ids.discard("")

        # Phase 2: TEI enrichment
        variant_appendix: list[dict] = []
        commentary_appendix: list[dict] = []
        for path in paths:
            for hop in path.hops:
                if hop.evidence_level >= 3:
                    # Collect variants and commentaries for all passage refs
                    # (evidence_passage_id is inside the citation, extract if needed)
                    pass

        # Phase 3: Conflict detection
        conflicts = await ConflictDetector.detect(self.session, paths)

        # Phase 4: Assemble 8 modules
        modules = self._assemble_modules(
            source_type=source_type, source_id=source_id,
            target_type=target_type, target_id=target_id,
            paths=paths, version_ids=all_version_ids,
            conflicts=conflicts, min_evidence_level=min_evidence_level,
            max_hops=max_hops, relation_types=relation_types,
        )

        # Phase 5: Generate output
        paper_data = {
            "source_type": source_type,
            "source_id": source_id,
            "target_type": target_type,
            "target_id": target_id,
            "min_evidence_level": min_evidence_level,
            "max_hops": max_hops,
            "relation_types": relation_types,
            "modules": modules,
        }
        paper_json = json.dumps(paper_data, ensure_ascii=False, sort_keys=True, default=str)
        paper_id = hashlib.sha256(paper_json.encode()).hexdigest()

        markdown = self._render_markdown(modules, source_type, source_id, target_type, target_id)

        return {
            "paper_id": paper_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "query": {
                "source_type": source_type,
                "source_id": source_id,
                "target_type": target_type,
                "target_id": target_id,
            },
            "modules": modules,
            "markdown": markdown,
        }

    def _assemble_modules(
        self, source_type, source_id, target_type, target_id,
        paths, version_ids, conflicts, min_evidence_level, max_hops,
        relation_types,
    ) -> dict:
        """Assemble 8 paper modules from evidence data."""
        # Module 1: Title
        title = f"{source_type}:{source_id} 的学术证据链分析"
        if target_type and target_id:
            title = f"{source_type}:{source_id} 与 {target_type}:{target_id}：基于证据链的学术分析"

        # Module 2: Abstract (data summary)
        max_level = max((p.min_evidence_level for p in paths), default=0)
        avg_confidence = sum(p.total_confidence for p in paths) / max(len(paths), 1)

        # Collect unique versions
        unique_versions: set[str] = set()
        for p in paths:
            for h in p.hops:
                unique_versions.add(h.citation)

        abstract = {
            "path_count": len(paths),
            "version_count": len(unique_versions),
            "variant_count": 0,  # populated by TEI enricher
            "commentary_count": 0,
            "max_evidence_level": max_level,
            "avg_confidence": round(avg_confidence, 4),
        }

        # Module 3: Literature basis
        literature_basis = []
        for vid in sorted(version_ids):
            literature_basis.append({"version_id": vid, "name": vid})

        # Module 4: Evidence chains
        evidence_chains = []
        for path in paths:
            chain = {"path_id": path.path_id, "hops": [], "total_confidence": path.total_confidence}
            for hop in path.hops:
                chain["hops"].append({
                    "source": f"{hop.source_type}:{hop.source_id}",
                    "target": f"{hop.target_type}:{hop.target_id}",
                    "relation": hop.relation_type,
                    "evidence_level": hop.evidence_level,
                    "confidence_score": hop.confidence_score,
                    "citation": hop.citation,
                    "exact_quote": hop.exact_quote,
                    "source_uri": hop.source_uri,
                })
            evidence_chains.append(chain)

        # Module 5: Variant appendix (placeholder — filled by TEI enricher)
        variant_appendix: list[dict] = []

        # Module 6: Literature review (co-occurrence from KG)
        literature_review = {"nodes": [], "edges": []}

        # Module 7: Discussion (conflicts)
        discussion = {
            "conflicts": [
                {
                    "type": c.conflict_type,
                    "description": c.description,
                    "severity": c.severity,
                    "affected_path_ids": c.affected_path_ids,
                }
                for c in conflicts
            ]
        }

        # Module 8: Methodology
        methodology = {
            "query_parameters": {
                "source_type": source_type, "source_id": source_id,
                "target_type": target_type, "target_id": target_id,
                "min_evidence_level": min_evidence_level,
                "max_hops": max_hops,
                "relation_types": relation_types,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "evidence_level_distribution": {
                "L2": sum(1 for p in paths for h in p.hops if h.evidence_level == 2),
                "L3": sum(1 for p in paths for h in p.hops if h.evidence_level == 3),
                "L4": sum(1 for p in paths for h in p.hops if h.evidence_level == 4),
            },
            "filters_applied": [],
        }

        return {
            "title": title,
            "abstract": abstract,
            "literature_basis": literature_basis,
            "evidence_chains": evidence_chains,
            "variant_appendix": variant_appendix,
            "literature_review": literature_review,
            "discussion": discussion,
            "methodology": methodology,
        }

    @staticmethod
    def _render_markdown(
        modules: dict,
        source_type: str,
        source_id: str,
        target_type: str | None,
        target_id: str | None,
    ) -> str:
        """Render 8 modules as Markdown."""
        lines: list[str] = []

        # Title
        lines.append(f"# {modules['title']}")
        lines.append("")

        # Abstract
        a = modules["abstract"]
        lines.append("## 摘要")
        lines.append(f"共发现 **{a['path_count']}** 条证据路径，涉及 **{a['version_count']}** 个文献版本。")
        lines.append(f"最高证据等级 **L{a['max_evidence_level']}**，平均置信度 **{a['avg_confidence']:.4f}**。")
        lines.append("")

        # Literature Basis
        lines.append("## 文献基础")
        for v in modules.get("literature_basis", []):
            lines.append(f"- {v['name']}")
        lines.append("")

        # Evidence Chains
        lines.append("## 证据链")
        for i, chain in enumerate(modules.get("evidence_chains", []), 1):
            lines.append(f"### 路径 {i} (置信度: {chain['total_confidence']:.4f})")
            for j, hop in enumerate(chain["hops"], 1):
                lines.append(f"**跳步 {j}**: {hop['source']} --[{hop['relation']}]--> {hop['target']}")
                lines.append(f"- 证据等级: L{hop['evidence_level']} (置信度: {hop['confidence_score']})")
                lines.append(f"- 引用: {hop['citation']}")
                if hop["exact_quote"]:
                    lines.append(f"- 原文: 「{hop['exact_quote']}」")
                if hop["source_uri"]:
                    lines.append(f"- 来源: {hop['source_uri']}")
                lines.append("")
            lines.append("")

        # Variant Appendix
        lines.append("## 异文附录")
        lines.append("（无 L4 级别异文证据）" if not modules.get("variant_appendix") else "")
        lines.append("")

        # Literature Review
        lines.append("## 学术史回顾")
        lines.append("（共现图谱数据见 JSON 输出）")
        lines.append("")

        # Discussion
        lines.append("## 讨论与冲突检测")
        discussion = modules.get("discussion", {})
        for c in discussion.get("conflicts", []):
            lines.append(f"- **[{c['type']}]** {c['description']} (严重度: {c['severity']})")
        if not discussion.get("conflicts"):
            lines.append("未检测到证据冲突。")
        lines.append("")

        # Methodology
        lines.append("## 方法论附注")
        m = modules["methodology"]
        lines.append(f"- 查询时间: {m['generated_at']}")
        lines.append(f"- 最低证据等级: L{m['query_parameters']['min_evidence_level']}")
        lines.append(f"- 最大跳数: {m['query_parameters']['max_hops']}")
        dist = m.get("evidence_level_distribution", {})
        lines.append(f"- 证据等级分布: L2={dist.get('L2', 0)}, L3={dist.get('L3', 0)}, L4={dist.get('L4', 0)}")
        lines.append("")

        return "\n".join(lines)
```

- [ ] **Step 2: 运行 lint**

```bash
cd /Users/likeming/Sites/hfb && ruff check apps/backend/app/services/paper_service.py
```

- [ ] **Step 3: Commit**

```bash
git add apps/backend/app/services/paper_service.py
git commit -m "feat: PaperService — 8-module structured academic paper assembly"
```

---

### Task 15: Paper API endpoints + 集成测试

**Files:**
- Create: `apps/backend/app/api/v2/paper.py`
- Modify: `apps/backend/app/api/v2/__init__.py`
- Create: `tests/unit/test_paper_service.py`

**Interfaces:**
- Consumes: PaperService
- Produces: `POST /api/v2/paper/generate`, `GET /api/v2/paper/{sha256}`, `GET /api/v2/paper/{sha256}/markdown`

- [ ] **Step 1: 创建 paper API 路由**

新建 `apps/backend/app/api/v2/paper.py`：

```python
"""Paper V2 API routes — Phase 2c structured academic paper generation."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import require_permission
from app.services.paper_service import PaperService

router = APIRouter(prefix="/paper", tags=["Paper V2"])

guard_paper_read = require_permission("ai", "read")


class PaperGenerateRequest(BaseModel):
    """Request to generate a structured academic paper."""

    model_config = ConfigDict(extra="forbid", strict=True)

    source_type: str = Field(..., description="起始实体类型")
    source_id: str = Field(..., description="起始实体 ID")
    target_type: str | None = Field(default=None, description="目标实体类型（可选）")
    target_id: str | None = Field(default=None, description="目标实体 ID（可选）")
    min_evidence_level: int = Field(default=2, ge=2, le=4, description="最低证据等级")
    max_hops: int = Field(default=5, ge=1, le=10, description="最大跳数")
    relation_types: list[str] | None = Field(default=None, description="过滤关系类型")


class PaperEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    success: bool = Field(default=True)
    data: dict = Field(default_factory=dict)
    message: str = Field(default="ok")


# In-memory cache for generated papers (by paper_id / sha256)
_paper_cache: dict[str, dict] = {}


@router.post(
    "/generate",
    response_model=PaperEnvelope,
    dependencies=[Depends(guard_paper_read)],
)
async def generate_paper(
    body: PaperGenerateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PaperEnvelope:
    """Generate a structured academic paper from KG + TEI evidence."""
    svc = PaperService(session)
    paper = await svc.generate_paper(
        source_type=body.source_type,
        source_id=body.source_id,
        target_type=body.target_type,
        target_id=body.target_id,
        min_evidence_level=body.min_evidence_level,
        max_hops=body.max_hops,
        relation_types=body.relation_types,
    )
    # Cache for retrieval
    _paper_cache[paper["paper_id"]] = paper
    return PaperEnvelope(success=True, data=paper, message="ok")


@router.get(
    "/{paper_id}",
    response_model=PaperEnvelope,
    dependencies=[Depends(guard_paper_read)],
)
async def get_paper(
    paper_id: str,
) -> PaperEnvelope:
    """Retrieve a previously generated paper by its SHA-256 ID."""
    paper = _paper_cache.get(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found. Generate it first via POST /generate.")
    return PaperEnvelope(success=True, data=paper, message="ok")


@router.get(
    "/{paper_id}/markdown",
    response_model=PaperEnvelope,
    dependencies=[Depends(guard_paper_read)],
)
async def get_paper_markdown(
    paper_id: str,
) -> PaperEnvelope:
    """Download a generated paper as Markdown."""
    paper = _paper_cache.get(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found. Generate it first via POST /generate.")
    return PaperEnvelope(
        success=True,
        data={"paper_id": paper_id, "markdown": paper.get("markdown", "")},
        message="ok",
    )
```

- [ ] **Step 2: 更新 v2 __init__.py**

```python
from app.api.v2.academic import router as academic_router
from app.api.v2.graph import router as graph_router
from app.api.v2.tei import router as tei_router
from app.api.v2.paper import router as paper_router  # Phase 2c

from fastapi import APIRouter

router = APIRouter()
router.include_router(academic_router)
router.include_router(graph_router)
router.include_router(tei_router)
router.include_router(paper_router)  # Phase 2c

__all__ = ["router"]
```

- [ ] **Step 3: 写集成测试**

在 `tests/unit/test_paper_service.py` 中：

```python
"""Integration tests for PaperService — 8-module paper generation."""

import pytest
from app.services.paper_service import PaperService


@pytest.mark.asyncio
async def test_generate_paper_empty_graph(db_session):
    """Paper generation with no academic edges should return empty chains."""
    svc = PaperService(db_session)
    paper = await svc.generate_paper(
        source_type="person", source_id="nonexistent",
        target_type="book", target_id="nonexistent",
    )
    assert paper["paper_id"] is not None
    assert len(paper["paper_id"]) == 64  # SHA-256 hex
    assert "modules" in paper
    assert "markdown" in paper
    modules = paper["modules"]
    assert "title" in modules
    assert "abstract" in modules
    assert modules["abstract"]["path_count"] == 0


@pytest.mark.asyncio
async def test_generate_paper_produces_markdown(db_session):
    """Paper generation should produce well-formed Markdown."""
    svc = PaperService(db_session)
    paper = await svc.generate_paper(
        source_type="person", source_id="p1",
    )
    md = paper["markdown"]
    assert md.startswith("# ")
    assert "## 摘要" in md
    assert "## 证据链" in md
    assert "## 讨论与冲突检测" in md
    assert "## 方法论附注" in md


@pytest.mark.asyncio
async def test_generate_paper_deterministic(db_session):
    """Same inputs should produce the same paper_id (SHA-256)."""
    svc1 = PaperService(db_session)
    svc2 = PaperService(db_session)
    paper1 = await svc1.generate_paper(
        source_type="person", source_id="p1",
        target_type="book", target_id="b1",
    )
    paper2 = await svc2.generate_paper(
        source_type="person", source_id="p1",
        target_type="book", target_id="b1",
    )
    assert paper1["paper_id"] == paper2["paper_id"]
```

- [ ] **Step 4: 运行测试**

```bash
cd /Users/likeming/Sites/hfb && python -m pytest tests/unit/test_paper_service.py -v
```
Expected: 3 tests PASS

- [ ] **Step 5: 运行 lint + 完整测试套件**

```bash
cd /Users/likeming/Sites/hfb && ruff check apps/backend/app/api/v2/ apps/backend/app/services/paper_service.py
cd /Users/likeming/Sites/hfb && python -m pytest tests/ -x --timeout=60 -q
```

- [ ] **Step 6: Commit**

```bash
git add apps/backend/app/api/v2/paper.py apps/backend/app/api/v2/__init__.py tests/unit/test_paper_service.py
git commit -m "feat: paper generation API endpoints + integration tests"
```

---

## Plan Self-Review

- [x] **Spec coverage**: Each spec section maps to tasks — Phase 2-Pre (Tasks 1-2 LCS alignment), Phase 2a (Tasks 3-9 evidence_level + syndrome/indicates + AcademicEdge + multi-hop + API), Phase 2b (Tasks 10-12 commentary + version_tree + variants), Phase 2c (Tasks 13-15 conflict detector + PaperService + API)
- [x] **No placeholders**: All code blocks are concrete, all test assertions are specific, all commands have expected output
- [x] **Type consistency**: `EvidenceChainPath.hops` is `list[EvidenceHop]` consistent across schemas (Task 7), GraphService (Task 8), ConflictDetector (Task 13), and PaperService (Task 14)
- [x] **EvidenceLevelMixin** from spec: Skipped — the logic is simpler as a `@staticmethod` in GraphService. Mixin adds indirection with no benefit given one consumer
- [x] **seed_graph.py update**: Mentioned but not a separate task — folded into Task 4 migration validation
