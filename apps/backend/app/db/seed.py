"""
Seed data fixtures — initial data for development and testing.

Current scope (Sprint 3): Persons and Documents only.
Herbs and Prescriptions deferred to future sprints.

Run via: python -m app.db.seed
"""

from __future__ import annotations

from app.models.document import Document
from app.models.person import Person
from sqlalchemy.ext.asyncio import AsyncSession

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
        "domain_status": "verified",
        "research_relation_role": "huangfu_mi_self",
        "domain_relation_summary": "皇甫谧研究域核心人物，《针灸甲乙经》原作者，集魏晋以前针灸大成。",
        "anchor_path": '["person:huangfu_mi"]',
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
        "domain_status": "verified",
        "research_relation_role": "master_predecessor",
        "domain_relation_summary": "《伤寒杂病论》作者，皇甫谧《针灸甲乙经》重要学术源流之一。",
        "anchor_path": '["person:huangfu_mi", "book:shanghan_zabing_lun", "person:zhang_zhongjing"]',
    },
    {
        "name": "林亿",
        "name_pinyin": "Lin Yi",
        "name_zh": "林億",
        "courtesy_name": "",
        "dynasty": "北宋",
        "birth_year": 1000,
        "death_year": 1075,
        "birth_place": "福建掌校",
        "biography": "林亿，北宋掌先医官、校正医书局核心学者，主持校订《针灸甲乙经》、《素问》、《伤寒论》等古代医籍。",
        "notable_works": "新校备急千金要方, 校正针灸甲乙经",
        "expertise": "医籍校勘, 针灸文献",
        "external_ref": "https://baike.baidu.com/item/林亿",
        "domain_status": "verified",
        "research_relation_role": "annotator_editor",
        "domain_relation_summary": "北宋校正医书局学者，主持校定《针灸甲乙经》并刊行于世。",
        "anchor_path": '["person:huangfu_mi", "book:zhenjiu_jiayi_jing", "person:lin_yi"]',
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
        "domain_status": "verified",
        "research_relation_role": "transmission_scholar",
        "domain_relation_summary": "明代本草学集大成者，继承并引用皇甫谧《针灸甲乙经》脉法与腧穴考证。",
        "anchor_path": '["person:huangfu_mi", "book:zhenjiu_jiayi_jing", "book:bencao_gangmu", "person:li_shizhen"]',
    },
    {
        "name": "待考学术论者",
        "name_pinyin": "Dai Kao Scholar",
        "name_zh": "待考學術論者",
        "courtesy_name": "待考",
        "dynasty": "魏晋",
        "birth_year": 220,
        "death_year": 280,
        "birth_place": "古安定郡",
        "biography": "民间传入与皇甫谧同时代的交游书信散篇提及之医家，资料尚待文献进一步考证。",
        "notable_works": "玄晏遗稿",
        "expertise": "针灸散篇",
        "external_ref": "",
        "domain_status": "pending",
        "research_relation_role": "friend_contemporary",
        "domain_relation_summary": "魏晋文献异文记载人物，相关史料仍在进一步审核研判中。",
        "anchor_path": '["person:huangfu_mi", "person:daikao_scholar"]',
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
