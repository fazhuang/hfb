"""JSON-LD schema loader for TCM ontology.

Loads and validates ontology definitions in JSON-LD format.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tcm_ontology.entity_type import ENTITY_SCHEMA, EntitySchema, EntityType, RelationDef


class SchemaLoader:
    """Load and validate TCM ontology schemas from JSON-LD files.

    JSON-LD format:
    {
        "@context": {"tcm": "https://huangfumi.org/ontology#"},
        "@graph": [
            {
                "@id": "tcm:Person",
                "@type": "tcm:EntityType",
                "tcm:properties": ["name", "name_zh", ...],
                "tcm:relations": [
                    {"name": "authored", "target": "tcm:Text"},
                    ...
                ]
            },
            ...
        ]
    }

    >>> loader = SchemaLoader()
    >>> schemas = loader.loads('''
    ... {"@context": {}, "@graph": [
    ...   {"@id": "tcm:Person", "@type": "tcm:EntityType",
    ...    "tcm:properties": ["name", "name_zh"],
    ...    "tcm:relations": [{"name": "authored", "target": "tcm:Text"}]}
    ... ]}''')
    >>> schemas[0].entity_type == EntityType.PERSON
    True
    """

    # Map JSON-LD type prefixes to EntityType
    _TYPE_MAP: dict[str, EntityType] = {
        "tcm:Person": EntityType.PERSON,
        "tcm:Text": EntityType.TEXT,
        "tcm:Herb": EntityType.HERB,
        "tcm:Prescription": EntityType.PRESCRIPTION,
        "tcm:Meridian": EntityType.MERIDIAN,
        "tcm:Symptom": EntityType.SYMPTOM,
    }

    def load_file(self, path: Path | str) -> list[EntitySchema]:
        """Load schemas from a JSON-LD file."""
        with open(path) as f:
            data = json.load(f)
        return self.loads(data)

    def loads(self, data: dict[str, Any] | str) -> list[EntitySchema]:
        """Load schemas from a JSON-LD dict or string."""
        if isinstance(data, str):
            data = json.loads(data)
        return self._parse_graph(data.get("@graph", []))

    def dump_file(self, path: Path | str, schemas: list[EntitySchema] | None = None) -> None:
        """Write built-in schemas (or given schemas) as JSON-LD."""
        if schemas is None:
            schemas = list(ENTITY_SCHEMA.values())
        doc = self.dumps(schemas)
        with open(path, "w") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

    def dumps(self, schemas: list[EntitySchema]) -> dict[str, Any]:
        """Serialize schemas to JSON-LD dict."""
        graph = []
        for s in schemas:
            node: dict[str, Any] = {
                "@id": f"tcm:{s.entity_type.value}",
                "@type": "tcm:EntityType",
                "tcm:properties": s.properties,
                "tcm:relations": [
                    {"name": r.name, "target": f"tcm:{r.target_type.value}"}
                    for r in s.relations
                ],
                "tcm:description_zh": s.description_zh,
            }
            graph.append(node)
        return {
            "@context": {"tcm": "https://huangfumi.org/ontology#"},
            "@graph": graph,
        }

    def _parse_graph(self, nodes: list[dict[str, Any]]) -> list[EntitySchema]:
        """Parse @graph nodes into EntitySchema objects."""
        schemas: list[EntitySchema] = []
        for node in nodes:
            type_id = node.get("@id", "")
            entity_type = self._TYPE_MAP.get(type_id)
            if entity_type is None:
                raise ValueError(f"Unknown entity type in JSON-LD: {type_id}")

            relations = []
            for r in node.get("tcm:relations", []):
                target_id = r.get("target", "")
                target_type = self._TYPE_MAP.get(target_id)
                if target_type is None:
                    raise ValueError(f"Unknown target type: {target_id}")
                relations.append(RelationDef(name=r["name"], target_type=target_type))

            schema = EntitySchema(
                entity_type=entity_type,
                properties=node.get("tcm:properties", []),
                relations=relations,
                description_zh=node.get("tcm:description_zh", ""),
            )
            schemas.append(schema)
        return schemas
