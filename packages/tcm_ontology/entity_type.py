"""Entity type definitions and schemas for TCM ontology."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EntityType(StrEnum):
    """Core TCM entity types."""

    PERSON = "Person"
    TEXT = "Text"
    HERB = "Herb"
    PRESCRIPTION = "Prescription"
    MERIDIAN = "Meridian"
    SYMPTOM = "Symptom"


@dataclass
class RelationDef:
    """Definition of a valid outgoing relation from an entity type."""

    name: str  # e.g. "authored", "treats", "part_of"
    target_type: EntityType  # what type the relation points to


@dataclass
class EntitySchema:
    """Schema defining properties and valid relations for an entity type."""

    entity_type: EntityType
    properties: list[str] = field(default_factory=list)
    relations: list[RelationDef] = field(default_factory=list)
    description_zh: str = ""


# Standard TCM ontology schemas
ENTITY_SCHEMA: dict[EntityType, EntitySchema] = {
    EntityType.PERSON: EntitySchema(
        entity_type=EntityType.PERSON,
        properties=[
            "name",
            "name_zh",
            "courtesy_name",
            "pseudonym",
            "dynasty",
            "birth_year",
            "death_year",
            "birth_place",
            "biography",
            "expertise",
            "notable_works",
        ],
        relations=[
            RelationDef("authored", EntityType.TEXT),
            RelationDef("compiled", EntityType.TEXT),
            RelationDef("commented_on", EntityType.TEXT),
        ],
        description_zh="人物 — 医家、学者、历史人物",
    ),
    EntityType.TEXT: EntitySchema(
        entity_type=EntityType.TEXT,
        properties=[
            "title",
            "title_zh",
            "title_pinyin",
            "dynasty",
            "year",
            "category",
            "abstract",
            "language",
        ],
        relations=[
            RelationDef("authored_by", EntityType.PERSON),
            RelationDef("compiled_by", EntityType.PERSON),
            RelationDef("contains", EntityType.PRESCRIPTION),
            RelationDef("references", EntityType.TEXT),
            RelationDef("describes", EntityType.SYMPTOM),
            RelationDef("describes", EntityType.MERIDIAN),
        ],
        description_zh="文献 — 古籍、医书、经典",
    ),
    EntityType.HERB: EntitySchema(
        entity_type=EntityType.HERB,
        properties=[
            "name",
            "name_zh",
            "latin_name",
            "taste",
            "nature",
            "meridian_tropism",
            "dosage",
            "functions",
            "contraindications",
        ],
        relations=[
            RelationDef("part_of", EntityType.PRESCRIPTION),
            RelationDef("corresponds_to", EntityType.MERIDIAN),
            RelationDef("treats", EntityType.SYMPTOM),
        ],
        description_zh="药材 — 中药材、本草",
    ),
    EntityType.PRESCRIPTION: EntitySchema(
        entity_type=EntityType.PRESCRIPTION,
        properties=[
            "name",
            "name_zh",
            "composition",
            "indications",
            "contraindications",
            "preparation",
            "source_text",
            "category",
        ],
        relations=[
            RelationDef("contains", EntityType.HERB),
            RelationDef("treats", EntityType.SYMPTOM),
            RelationDef("variant_of", EntityType.PRESCRIPTION),
        ],
        description_zh="方剂 — 处方、方剂",
    ),
    EntityType.MERIDIAN: EntitySchema(
        entity_type=EntityType.MERIDIAN,
        properties=[
            "name",
            "name_zh",
            "category",
            "path_description",
            "acupoints",
            "related_organs",
        ],
        relations=[
            RelationDef("corresponds_to", EntityType.HERB),
            RelationDef("part_of", EntityType.TEXT),
        ],
        description_zh="经络 — 经脉、络脉、穴位",
    ),
    EntityType.SYMPTOM: EntitySchema(
        entity_type=EntityType.SYMPTOM,
        properties=[
            "name",
            "name_zh",
            "category",
            "location",
            "characteristics",
            "associated_pulse",
            "associated_tongue",
        ],
        relations=[
            RelationDef("treated_by", EntityType.HERB),
            RelationDef("treated_by", EntityType.PRESCRIPTION),
            RelationDef("part_of", EntityType.TEXT),
        ],
        description_zh="症候 — 症状、证候、临床表现",
    ),
}
