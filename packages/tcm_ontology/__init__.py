"""TCM Ontology — 中医本体系统.

Pure-Python ontology framework for Traditional Chinese Medicine entities.
Defines entity types, schemas, and relationships with JSON-LD support.
"""

from tcm_ontology.entity_type import EntityType, ENTITY_SCHEMA, EntitySchema, RelationDef
from tcm_ontology.schema_loader import SchemaLoader
from tcm_ontology.registry import EntityRegistry

__all__ = [
    "EntityType",
    "ENTITY_SCHEMA",
    "EntitySchema",
    "RelationDef",
    "SchemaLoader",
    "EntityRegistry",
]
