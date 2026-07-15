# Claude 实施专属：皇甫谧数字人文平台重构执行手册

本手册为具体负责代码实施的 Agent (Claude) 准备。通过本手册，可以直接进行数据库迁移、API 路由开发、可信度算法实现以及闭环测试的落地。

---

## 1. 当前 codebase 状态说明 (已完成部分)

重构的 **第一阶段（模型层声明）** 已经执行完毕：
* 💡 [models/__init__.py](file:///Users/likeming/Sites/hfb/apps/backend/app/models/__init__.py) 已正确导入并导出所有重构模型。
* 💡 [passage.py](file:///Users/likeming/Sites/hfb/apps/backend/app/models/passage.py) 已扩展 `sentences` 关联。
* 💡 新增的 3 个模型文件已就绪：
  * [version_criticism.py](file:///Users/likeming/Sites/hfb/apps/backend/app/models/version_criticism.py)：断句 `Sentence`、词元 `Token`、异文 `Variant`。
  * [academic_evidence.py](file:///Users/likeming/Sites/hfb/apps/backend/app/models/academic_evidence.py)：物理出处 `SourceRef`、证据 `Evidence`、引文 `Citation`。
  * [academic_relation.py](file:///Users/likeming/Sites/hfb/apps/backend/app/models/academic_relation.py)：学术实体 `AcademicEntity`、学术命题关系 `AcademicRelation`、关系置信度 `RelationConfidence`。

---

## 2. 实施步骤一：数据库 Alembic 迁移

### 执行任务
1. **生成迁移脚本**：
   在 backend 开发环境下运行以下命令生成 Alembic 迁移脚本：
   ```bash
   poetry run alembic revision --autogenerate -m "add_academic_and_version_criticism_models"
   ```
2. **校验迁移文件**：
   确保生成的迁移文件中正确包含了新创建的 `sentences`、`tokens`、`variants`、`source_refs`、`evidences`、`citations`、`academic_entities` , `academic_relations`、`relation_evidences` 和 `relation_confidences` 10张表，以及正确设置了 `ondelete="CASCADE"` 和索引。
3. **应用迁移**：
   ```bash
   poetry run alembic upgrade head
   ```

---

## 3. 实施步骤二：最小 API 路由实现 (FastAPI)

请在 `apps/backend/app/api/v1/` 目录下创建或修改对应的路由。

### 3.1 段落与异文详情路由 (`passages.py`)
* **路径**：`GET /api/v1/passages/{id}`
* **逻辑**：加载 `Passage` 时，必须使用 SQLAlchemy `selectinload` 加载 `sentences.tokens` 和关联的 `variants`。
* **Pydantic Schema 结构**：
  ```python
  class TokenResponse(BaseModel):
      id: str
      char_text: str
      position: int

  class SentenceResponse(BaseModel):
      id: str
      content_text: str
      order: int
      tokens: list[TokenResponse]

  class VariantResponse(BaseModel):
      id: str
      base_token_id: str
      compare_token: Optional[TokenResponse]
      variant_type: str
      description: Optional[str]
  ```

### 3.2 学术证据录入路由 (`evidences.py`)
* **路径**：`POST /api/v1/evidences`
* **逻辑**：
  1. 若 Payload 中含有 `source_ref` 字典，先创建 `SourceRef` 记录并保存。
  2. 创建 `Evidence` 记录，并绑定 `source_ref_id`。
  3. 返回创建好的 `Evidence` 详情。

### 3.3 学术关系置信度计算服务 (`relations.py`)
* **路径**：`POST /api/v1/relations/{id}/calculate-confidence`
* **置信度运算核心逻辑（请直接转译为 Python 代码）**：
  ```python
  async def calculate_relation_confidence(session: AsyncSession, relation_id: str) -> float:
      # 1. 查找学术关系及其关联的证据
      result = await session.execute(
          select(AcademicRelation)
          .options(selectinload(AcademicRelation.evidences))
          .filter(AcademicRelation.id == relation_id)
      )
      relation = result.scalar_one_or_none()
      if not relation or not relation.evidences:
          return 0.0
      
      # 2. 证据等级对应的可信度系数
      level_weights = {
          EvidenceLevel.LEVEL_1: 1.0,  # 出土实物
          EvidenceLevel.LEVEL_2: 0.9,  # 传世善本/校勘本
          EvidenceLevel.LEVEL_3: 0.6,  # 旁证/转引注疏
          EvidenceLevel.LEVEL_4: 0.3   # 现代推论
      }
      
      # 3. 累积可信度公式：1 - 乘积(1 - W_i)
      weights = [level_weights.get(ev.evidence_level, 0.1) for ev in relation.evidences]
      combined_score = 1.0
      for w in weights:
          combined_score *= (1.0 - w)
      score = round(1.0 - combined_score, 3)
      
      # 4. 一致性逻辑校验（防止中医药理悖论）
      # 读取该关系源实体（腧穴）与靶实体（病症）是否存在逆命题冲突
      # 如：商阳穴主治齿痛 vs. 商阳穴禁刺齿痛
      # 若冲突，score = score * 0.5 (扣减一半分数) 并记录逻辑异常
      
      # 5. 更新或创建 RelationConfidence
      conf_result = await session.execute(
          select(RelationConfidence).filter(RelationConfidence.relation_id == relation_id)
      )
      confidence = conf_result.scalar_one_or_none()
      if not confidence:
          confidence = RelationConfidence(relation_id=relation_id)
          session.add(confidence)
      
      confidence.calculated_score = score
      confidence.calculation_log = f"Evidences weight: {weights}."
      await session.commit()
      return score
  ```

---

## 4. 实施步骤三：闭环测试用例编写

请在 `tests/unit/test_academic_loop.py` 中编写以下自动化测试用例，运行 `pytest` 进行验证。

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import (
    Book, Version, Chapter, Passage, Sentence, Token, 
    Variant, VariantType, SourceRef, Evidence, EvidenceLevel,
    AcademicEntity, AcademicEntityType, AcademicRelation, RelationConfidence
)

@pytest.mark.asyncio
async def test_academic_minimal_viable_loop(db_session: AsyncSession):
    # 1. 初始化书籍与版本
    book = Book(title="针灸甲乙经", dynasty="晋", year=282)
    db_session.add(book)
    await db_session.flush()

    v_song = Version(book_id=book.id, version_name="宋校本", era="北宋")
    v_ming = Version(book_id=book.id, version_name="明抄本", era="明代")
    db_session.add_all([v_song, v_ming])
    await db_session.flush()

    # 2. 章节：卷十一
    chapter = Chapter(book_id=book.id, title="卷十一·大肠腑病第八", chapter_number=11)
    db_session.add(chapter)
    await db_session.flush()

    # 3. 宋校本 Passage
    p_song = Passage(chapter_id=chapter.id, edition_id=v_song.id, content_text="齿痛，商阳主之。", order=1)
    db_session.add(p_song)
    await db_session.flush()

    s_song = Sentence(passage_id=p_song.id, content_text="齿痛，商阳主之。", order=1)
    db_session.add(s_song)
    await db_session.flush()

    t_yang = Token(sentence_id=s_song.id, char_text="阳", position=4)
    db_session.add(t_yang)
    await db_session.flush()

    # 4. 明抄本 Passage
    p_ming = Passage(chapter_id=chapter.id, edition_id=v_ming.id, content_text="齿痛，商阴主之。", order=1)
    db_session.add(p_ming)
    await db_session.flush()

    s_ming = Sentence(passage_id=p_ming.id, content_text="齿痛，商阴主之。", order=1)
    db_session.add(s_ming)
    await db_session.flush()

    t_yin = Token(sentence_id=s_ming.id, char_text="阴", position=4)
    db_session.add(t_yin)
    await db_session.flush()

    # 5. 创建异文记录（宋校本的 阳 ↔ 明抄本的 阴）
    variant = Variant(
        base_token_id=t_yang.id, 
        compare_token_id=t_yin.id, 
        variant_type=VariantType.SUBSTITUTION,
        description="宋校本作阳，明抄本作阴。"
    )
    db_session.add(variant)
    await db_session.flush()

    # 6. 物理出处的学术证据
    ref = SourceRef(title="宋刻针灸甲乙经", author="高保衡等校", page_location="卷十一 p245")
    db_session.add(ref)
    await db_session.flush()

    evidence = Evidence(
        description="宋校本《针灸甲乙经》原字为阳", 
        evidence_level=EvidenceLevel.LEVEL_2,
        source_ref_id=ref.id,
        source_passage_id=p_song.id
    )
    db_session.add(evidence)
    await db_session.flush()

    # 7. 学术命题 (商阳穴, 主治, 齿痛)
    entity_acupoint = AcademicEntity(name="商阳", entity_type=AcademicEntityType.ACUPOINT)
    entity_disease = AcademicEntity(name="齿痛", entity_type=AcademicEntityType.DISEASE)
    db_session.add_all([entity_acupoint, entity_disease])
    await db_session.flush()

    relation = AcademicRelation(
        source_entity_id=entity_acupoint.id,
        target_entity_id=entity_disease.id,
        relation_type="TREAT",
        description="商阳穴主治齿痛"
    )
    db_session.add(relation)
    await db_session.flush()

    # 关联证据
    relation.evidences.append(evidence)
    await db_session.flush()

    # 8. 执行置信度计算
    from app.services.relations import calculate_relation_confidence # 假设在service层实现
    score = await calculate_relation_confidence(db_session, relation.id)

    # 9. 闭环断言校验
    assert score >= 0.89  # 对应 Level 2 证据
    assert variant.variant_type == VariantType.SUBSTITUTION
    assert variant.base_token.char_text == "阳"
    assert variant.compare_token.char_text == "阴"
    
    print("✅ 最低学术闭环自动测试全部通过！")
```
