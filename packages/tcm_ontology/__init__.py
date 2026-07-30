"""TCM Ontology — 中医本体系统.

Pure-Python ontology framework for Traditional Chinese Medicine entities.
Defines entity types, schemas, and relationships with JSON-LD support.
"""

from tcm_ontology.entity_type import (
    ENTITY_SCHEMA,
    EntitySchema,
    EntityType,
    RelationDef,
)
from tcm_ontology.registry import EntityRegistry
from tcm_ontology.schema_loader import SchemaLoader

__all__ = [
    "ENTITY_SCHEMA",
    "EntityRegistry",
    "EntitySchema",
    "EntityType",
    "RelationDef",
    "SchemaLoader",
]
