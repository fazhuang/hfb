# Phase 2 学术增强 — 设计规格

**日期**: 2026-07-05
**状态**: 设计完成，待审阅
**原则**: 论文引擎驱动，KG 和 TEI 按需提供接口

---

## 1. 问题定义

将"皇甫谧数字人文平台"升级为学术可验证系统。

三个子系统：
1. **KG 升级** — 引入 evidence_level (0-4)、confidence_score、source_ref 绑定
2. **TEI 升级** — 版本树、异文系统、注疏层
3. **论文引擎** — 输入问题 + KG + TEI，输出纯数据的结构化论文

核心约束：
- 禁止纯 LLM 生成内容
- 禁止无引用输出
- 禁止无证据关系

---

## 2. 施工顺序

```
Phase 2a: KG 升级 (evidence_level + AcademicEdge 视图 + 多跳查询)
    │
Phase 2b: TEI 升级 (version_tree + variant 增强 + commentary_layer)
    │
Phase 2c: 论文引擎 (消费 2a + 2b 的接口，组装 8 模块输出)
```

---

## 3. Phase 2a: KG 升级

### 3.1 evidence_level 定义

| Level | 名称 | 必要条件 | Score |
|-------|------|---------|-------|
| 0 | 无来源 | 仅有 `claim_text`，无任何 evidence 字段 | — |
| 1 | 文献引用 | `evidence_document_id` 或 `evidence_citation`，但无 `evidence_passage_id` | — |
| 2 | 段落定位 | `evidence_version_id` + `evidence_passage_id` | 0.65 |
| 3 | 原文引证 | 满足 L2 + `evidence_quote`，且 quote 与 passage 文本可验证 | 0.85 |
| 4 | 对勘证据 | 满足 L3 + 存在关联 `TextualVariant` 记录 | 0.98 |

推导规则：纯函数，从字段存在性推导，确定性、可复现。

### 3.2 EntityRelation 模型变更

新增字段：
```python
evidence_level: Mapped[int] = mapped_column(
    Integer, nullable=False, default=0,
    server_default=sa_text("0"),
    comment="证据等级 0-4"
)
```

新增 CHECK 约束：
```sql
CHECK (evidence_level IN (0, 1, 2, 3, 4))
```

`_derive_evidence_level(entity_relation) -> int`：
1. L0 = 仅 claim_text，无 evidence_document_id、evidence_chunk_id、evidence_citation、evidence_passage_id
2. L1 = 有 evidence_document_id 或 evidence_citation，但无 evidence_passage_id
3. L2 = 有 evidence_version_id + evidence_passage_id
4. L3 = 满足 L2 + evidence_quote 非空 + 已有 verified 状态（quote 已被 verify_relation 验证过）
5. L4 = 满足 L3 + TextualVariant 表中存在关联记录（source/target version 对应）

### 3.3 AcademicEdge 视图

```sql
CREATE VIEW academic_edges AS
SELECT
    *,
    CASE evidence_level
        WHEN 2 THEN 0.65
        WHEN 3 THEN 0.85
        WHEN 4 THEN 0.98
    END AS confidence_score
FROM entity_relations
WHERE evidence_level >= 2
  AND evidence_status = 'verified'
  AND is_deleted = 0;
```

只读视图。写入仍走 `EntityRelation` + `GraphService`。

### 3.4 多跳查询 + evidence chain

新增 `GraphService.multi_hop_query`：
- 输入：起始实体 + 目标实体（可选）+ min_level + max_hops
- 仅遍历 AcademicEdge 视图中的边
- 每条边附带：`source_ref`（citation）、`evidence_level`、`confidence_score`
- 输出：`EvidenceChainPath[]`，每条路径包含有序边列表 + 每跳完整证据

新增 Schema：
```python
class EvidenceHop(BaseModel):
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relation_type: str
    evidence_level: int
    confidence_score: float
    citation: str
    exact_quote: str
    source_uri: str

class EvidenceChainPath(BaseModel):
    path_id: str  # sha256 of concatenated edge ids
    hops: list[EvidenceHop]
    total_confidence: float  # product of per-hop confidence
    min_evidence_level: int
```

API 端点：
- `POST /api/v2/graph/evidence-chains` — 多跳查询入口

---

## 4. Phase 2b: TEI 升级

### 4.1 version_tree

**无新模型**。基于现有 `VersionRelation` + `PassageMapping` + `VersionDiff`。

新增 API：

`GET /api/v2/tei/version-tree/{version_id}`
```json
{
  "root_version": {"id": "...", "name": "...", "era": "...", "year": 0},
  "tree": [{"parent_id": "...", "child_id": "...", "relation_type": "...", "distance": 0.0}],
  "distance_matrix": {"v1-v2": 0.12, "v1-v3": 0.35, ...},
  "closest_to": [{"version_id": "...", "name": "...", "distance": 0.0}],
  "divergence_points": [{"passage_id": "...", "passage_text": "...", "diff_summary": "...", "variant_count": 0}]
}
```

距离计算：Jaccard 距离 = lines_changed / total_lines（从 VersionDiff.diff_data 推导）。
距离矩阵 lazily 计算和缓存。

### 4.2 variant system（增强）

基于现有 `TextualVariant` 模型，新增聚合 API：

`GET /api/v2/tei/passage/{id}/variants`
- 该 passage 在所有版本中的所有 variant，按 apparatus 分组

`GET /api/v2/tei/version/{source_id}/variants?target_version={target_id}`
- 两版本间所有 variant

`GET /api/v2/tei/apparatus?passage_id={id}&source_version={id}&target_version={id}`
- 返回 TEI XML critical apparatus（复用 `TEISerializer`）

### 4.3 commentary_layer（注疏链）

**新建模型**：

```python
class Commentary(BaseModel):
    __tablename__ = "commentaries"

    passage_id: Mapped[str]       # FK passage，所注段落
    version_id: Mapped[Optional[str]]  # FK version，所注版本（可空）
    author_id: Mapped[str]        # FK person，注者
    commentary_type: Mapped[str]  # interlinear_gloss | end_of_passage | commentary_work | critique
    layer: Mapped[str]            # 年代层：han, tang, song, ming, qing, modern
    content_text: Mapped[str]     # 注文
    target_position_start: Mapped[Optional[int]]  # 段落中起始字符偏移
    target_position_end: Mapped[Optional[int]]    # 段落中结束字符偏移
    parent_id: Mapped[Optional[str]]   # 自引用 FK — 回应另一条注疏
    relation_type: Mapped[Optional[str]]  # supplements | refutes | expands | annotates

    __table_args__ = (
        CheckConstraint(
            "commentary_type IN ('interlinear_gloss', 'end_of_passage', 'commentary_work', 'critique')",
            name="ck_commentaries_type",
        ),
        CheckConstraint(
            "layer IN ('han', 'tang', 'song', 'ming', 'qing', 'modern')",
            name="ck_commentaries_layer",
        ),
        CheckConstraint(
            "relation_type IS NULL OR relation_type IN ('supplements', 'refutes', 'expands', 'annotates')",
            name="ck_commentaries_relation",
        ),
    )
```

**注疏作为证据**：Commentary 不存储在 EntityRelation 中。但当一条 AcademicEdge 的 `evidence_passage_id` 指向有 Commentary 的段落时，Commentary 作为补充证据链暴露。

**注疏图谱**：当 Commentary A 的 `parent_id` 指向 Commentary B，且 `relation_type = 'refutes'`，生成一条注释辩论边（可在 KG 中遍历）。

API 端点：
- `GET /api/v2/tei/passage/{id}/commentaries?layer={layer}`
- `GET /api/v2/tei/commentary/{id}/chain` — 完整注疏链
- `POST /api/v2/tei/commentary`
- `GET /api/v2/tei/commentary-graph?passage_id={id}` — 注疏间的辩论/补充关系图谱

---

## 5. Phase 2c: 论文引擎

### 5.1 核心原则

- 零 LLM 叙述生成：所有文本来自模板填充或原始数据
- 所有输出可追溯到 source（citation + passage + quote）
- 每条证据标注 evidence_level
- SHA-256 输出哈希确保复现性

### 5.2 架构

```
Query (NL 或结构化)
    │
    ▼
QueryParser ─── 解析为实体 + 关系 + 约束
    │
    ▼
EvidenceCollector ─── 多跳 BFS，仅走 AcademicEdge
    │
    ▼
TEIEnricher ─── L3+ 路径补充 variant、commentary、version_tree
    │
    ▼
Assembler ─── 8 模块模板填充 → JSON + Markdown
```

### 5.3 8 模块

| # | 模块 | 数据源 | 产出 |
|---|------|--------|------|
| 1 | 标题 | QueryParser 实体名 + 关系类型 | 模板：`{源} 与 {目标}：基于 {关系} 的证据链分析` |
| 2 | 摘要 | EvidenceCollector 统计 | 路径数、版本数、异文数、注疏数、最高 L、平均置信度 |
| 3 | 文献基础 | TEIEnricher 版本信息 | 所有涉及版本 + 馆藏/年代/编者 + 版本谱系子树 |
| 4 | 证据链 | EvidenceCollector + TEIEnricher | 每条多跳路径展开为独立章节，每跳附 level + citation + quote + variant_count + commentary_count |
| 5 | 异文附录 | TEIEnricher | 所有 L4 路径关联的 TextualVariant，按 passage 分组，含 lem/rdg |
| 6 | 学术史回顾 | KG 共现查询 | 与 query 实体相关的其他研究关系的共现图谱 |
| 7 | 讨论 | 冲突检测 | 证据路径矛盾标注（反向关系、同一 claim 有 rejected 边） |
| 8 | 方法论附注 | 全链路追踪 | 查询参数 + 时间戳 + SHA-256 + evidence_level 分布 + 过滤条件 |

### 5.4 输出格式

**JSON**（程序消费）：8 模块的结构化数据

**Markdown**（人类阅读）：
- 8 个 `##` 章节
- 引用：`[citation]` 脚注式展平
- 异文表格：| 版本 | 读法 | apparatus |

### 5.5 API

- `POST /api/v2/paper/generate` — 生成论文
- `GET /api/v2/paper/{sha256}` — 按 hash 检索
- `GET /api/v2/paper/{sha256}/markdown` — 下载 Markdown

### 5.6 服务层

新建 `PaperService`，组合现有 `GraphService` + `VersionComparisonService`：
- `generate_paper(query) -> Paper`
- Paper 按需生成，不持久化（SHA-256 确保复现）

---

## 6. 数据结构汇总

### 新增模型
- `EvidenceLevelMixin` — 可复用的 evidence_level + _derive 逻辑
- `Commentary` — 注疏实体

### 新增视图
- `academic_edges` — 只读 SQL 视图

### 新增 Schema
- `EvidenceHop` / `EvidenceChainPath` / `MultiHopQueryRequest`
- `VersionTreeResponse` / `DistanceMatrix` / `DivergencePoint`
- `CommentaryResponse` / `CommentaryChainResponse` / `CommentaryGraphResponse`
- `PaperGenerateRequest` / `PaperResponse` / `PaperModule`

### 新增 API
- Phase 2a: `POST /api/v2/graph/evidence-chains`
- Phase 2b: `GET /api/v2/tei/version-tree/{id}`, `GET /api/v2/tei/passage/{id}/variants`, `GET /api/v2/tei/version/{id}/variants`, `GET /api/v2/tei/apparatus`, `GET /api/v2/tei/passage/{id}/commentaries`, `GET /api/v2/tei/commentary/{id}/chain`, `POST /api/v2/tei/commentary`, `GET /api/v2/tei/commentary-graph`
- Phase 2c: `POST /api/v2/paper/generate`, `GET /api/v2/paper/{sha256}`, `GET /api/v2/paper/{sha256}/markdown`

### 新增服务
- ` _derive_evidence_level()` — 在 `GraphService` 中
- `multi_hop_query()` — 在 `GraphService` 中
- `compute_distance_matrix()` — 在 `VersionComparisonService` 中
- `PaperService` — 新建

---

## 7. Spec 自检

- [x] 无 TBD / TODO 占位符
- [x] evidence_level 定义与现有 P0 字段一一对应，无歧义
- [x] 三个子系统边界清晰，Phase 2a → 2b → 2c 依赖明确
- [x] 施工范围聚焦：无新依赖、无架构重构、无前端变更
- [x] 所有输出可追溯、引用可验证
