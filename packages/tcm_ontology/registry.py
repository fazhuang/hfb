"""Ontology registry — manage entity types and validate instances."""

from __future__ import annotations

from typing import Any

from tcm_ontology.entity_type import ENTITY_SCHEMA, EntitySchema, EntityType


class EntityRegistry:
    """Registry for TCM entity types, schemas, and validation.

    >>> reg = EntityRegistry()
    >>> reg.get(EntityType.PERSON).properties[:2]
    ['name', 'name_zh']
    >>> reg.validate(EntityType.PERSON, {"name": "皇甫谧", "dynasty": "魏晋"})
    True
    """

    def __init__(self) -> None:
        self._schemas: dict[EntityType, EntitySchema] = dict(ENTITY_SCHEMA)

    def register(self, schema: EntitySchema) -> None:
        """Register or override a schema for an entity type."""
        self._schemas[schema.entity_type] = schema

    def get(self, entity_type: EntityType) -> EntitySchema:
        """Get schema for an entity type. Raises KeyError if not found."""
        if entity_type not in self._schemas:
            raise KeyError(f"Unknown entity type: {entity_type}")
        return self._schemas[entity_type]

    def list_types(self) -> list[EntityType]:
        """Return all registered entity types."""
        return list(self._schemas.keys())

    def has_type(self, entity_type: EntityType) -> bool:
        """Check if an entity type is registered."""
        return entity_type in self._schemas

    def validate(self, entity_type: EntityType, properties: dict[str, Any]) -> bool:
        """Validate that properties match the schema for a given entity type.

        Returns True if all required properties are present. Extra properties
        beyond the schema are allowed (open-world assumption).
        """
        schema = self.get(entity_type)
        for prop in schema.properties:
            if prop not in properties:
                raise ValueError(
                    f"Missing required property '{prop}' for {entity_type.value}"
                )
        return True

    def get_valid_relations(
        self, entity_type: EntityType
    ) -> list[tuple[str, EntityType]]:
        """Return list of (relation_name, target_type) valid for this entity."""
        schema = self.get(entity_type)
        return [(r.name, r.target_type) for r in schema.relations]

    def is_valid_relation(
        self, source_type: EntityType, relation: str, target_type: EntityType
    ) -> bool:
        """Check if a relation is valid between two entity types."""
        schema = self.get(source_type)
        for r_def in schema.relations:
            if r_def.name == relation and r_def.target_type == target_type:
                return True
        return False
