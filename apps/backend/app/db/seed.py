"""
Seed data fixtures — initial data for development and testing.

Current scope (Sprint 3): Persons and Documents only.
Herbs and Prescriptions deferred to future sprints.

Run via: python -m app.db.seed
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.person import Person

# ============================================================
# Sample People (人物)
# ============================================================

SEED_PERSONS = [
    {
        "name": "皇甫谧",
        "name_pinyin": "Huangfu Mi",
        "name_zh": "皇甫謐",
        "courtesy_name": "士安",
        "dynasty": "西晋",
        "birth_year": 215,
        "death_year": 282,
        "birth_place": "安定朝那 (今甘肃灵台)",
        "biography": "皇甫谧，字士安，号玄晏先生，西晋著名医学家、史学家。著有《针灸甲乙经》，是中国现存最早的针灸学专著，系统整理了魏晋以前的针灸学成就。",
        "notable_works": "针灸甲乙经, 帝王世纪, 高士传",
        "expertise": "针灸学, 史学",
        "external_ref": "https://baike.baidu.com/item/皇甫谧",
    },
    {
        "name": "张仲景",
        "name_pinyin": "Zhang Zhongjing",
        "name_zh": "張仲景",
        "courtesy_name": "仲景",
        "dynasty": "东汉",
        "birth_year": 150,
        "death_year": 219,
        "birth_place": "南阳郡涅阳 (今河南南阳)",
        "biography": "张仲景，名机，字仲景，东汉著名医学家，被誉为'医圣'。著有《伤寒杂病论》，是中医临床医学的奠基之作。",
        "notable_works": "伤寒杂病论",
        "expertise": "伤寒学, 方剂学",
        "external_ref": "https://baike.baidu.com/item/张仲景",
    },
    {
        "name": "李时珍",
        "name_pinyin": "Li Shizhen",
        "name_zh": "李時珍",
        "courtesy_name": "东璧",
        "dynasty": "明",
        "birth_year": 1518,
        "death_year": 1593,
        "birth_place": "蕲州 (今湖北蕲春)",
        "biography": "李时珍，字东璧，号濒湖山人，明代著名医学家、药学家。历时27年编成《本草纲目》，收载药物1892种，是中国古代最伟大的药学著作。",
        "notable_works": "本草纲目, 濒湖脉学, 奇经八脉考",
        "expertise": "本草学, 脉学",
        "external_ref": "https://baike.baidu.com/item/李时珍",
    },
]

# ============================================================
# Sample Documents (文献)
# ============================================================

SEED_DOCUMENTS = [
    {
        "title": "针灸甲乙经",
        "title_pinyin": "Zhen Jiu Jia Yi Jing",
        "title_english": "The Systematic Classic of Acupuncture and Moxibustion",
        "dynasty": "西晋",
        "year": 282,
        "category": "针灸",
        "abstract": "《针灸甲乙经》是皇甫谧编撰的针灸学专著，共12卷128篇。系统整理了魏晋以前的针灸学成就，记载349个腧穴，对后世针灸学发展影响深远。",
        "language": "zh",
    },
    {
        "title": "伤寒杂病论",
        "title_pinyin": "Shang Han Za Bing Lun",
        "title_english": "Treatise on Cold Damage and Miscellaneous Diseases",
        "dynasty": "东汉",
        "year": 210,
        "category": "方剂",
        "abstract": "《伤寒杂病论》为张仲景所著，确立了六经辨证体系，载方269首，被誉为'方书之祖'。",
        "language": "zh",
    },
    {
        "title": "本草纲目",
        "title_pinyin": "Ben Cao Gang Mu",
        "title_english": "Compendium of Materia Medica",
        "dynasty": "明",
        "year": 1578,
        "category": "本草",
        "abstract": "《本草纲目》为李时珍所著，共52卷，收载药物1892种，附方11096首，是中国古代药物学的集大成之作。",
        "language": "zh",
    },
]


async def seed_all(session: AsyncSession) -> dict[str, int]:
    """Insert seed data into the database.

    Returns counts of inserted records per model.
    """
    from sqlalchemy import select as sa_select

    counts: dict[str, int] = {}

    # Persons
    person_count = 0
    for data in SEED_PERSONS:
        existing = await session.execute(
            sa_select(Person).where(Person.name == data["name"])
        )
        if existing.scalar_one_or_none() is None:
            session.add(Person(**data))
            person_count += 1
    counts["persons"] = person_count

    # Documents
    doc_count = 0
    for data in SEED_DOCUMENTS:
        existing = await session.execute(
            sa_select(Document).where(Document.title == data["title"])
        )
        if existing.scalar_one_or_none() is None:
            session.add(Document(**data))
            doc_count += 1
    counts["documents"] = doc_count

    await session.flush()
    return counts
