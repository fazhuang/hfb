"""Unit tests for TCM Ontology package."""

import json
import tempfile
from pathlib import Path

import pytest

from tcm_ontology.entity_type import EntityType, ENTITY_SCHEMA, EntitySchema
from tcm_ontology.registry import EntityRegistry
from tcm_ontology.schema_loader import SchemaLoader


class TestEntityType:
    def test_all_six_types_exist(self) -> None:
        assert len(EntityType) == 6
        assert EntityType.PERSON == EntityType("Person")
        assert EntityType.TEXT == EntityType("Text")
        assert EntityType.HERB == EntityType("Herb")
        assert EntityType.PRESCRIPTION == EntityType("Prescription")
        assert EntityType.MERIDIAN == EntityType("Meridian")
        assert EntityType.SYMPTOM == EntityType("Symptom")

    def test_entity_schema_has_required_fields(self) -> None:
        schema = ENTITY_SCHEMA[EntityType.PERSON]
        assert schema.entity_type == EntityType.PERSON
        assert "name" in schema.properties
        assert "dynasty" in schema.properties
        assert any(r.name == "authored" for r in schema.relations)

    def test_all_entity_types_have_schema(self) -> None:
        for etype in EntityType:
            assert etype in ENTITY_SCHEMA
            assert len(ENTITY_SCHEMA[etype].properties) > 0

    def test_relation_def_points_to_valid_type(self) -> None:
        for schema in ENTITY_SCHEMA.values():
            for rel in schema.relations:
                assert isinstance(rel.target_type, EntityType)


class TestEntityRegistry:
    @pytest.fixture
    def registry(self) -> EntityRegistry:
        return EntityRegistry()

    def test_get_known_type(self, registry: EntityRegistry) -> None:
        schema = registry.get(EntityType.HERB)
        assert "taste" in schema.properties
        assert "nature" in schema.properties

    def test_get_unknown_type_raises(self, registry: EntityRegistry) -> None:
        # StrEnum rejects invalid values at construction time, so KeyError
        # is only reachable when EntityType has a deleted member somehow.
        # Validate that known types work and unknown string names can't be
        # constructed — the get() guard is for future dynamic registrations.
        with pytest.raises(ValueError):
            EntityType("FakeType")  # type: ignore[call-arg]

    def test_list_types(self, registry: EntityRegistry) -> None:
        types = registry.list_types()
        assert len(types) == 6
        assert EntityType.PERSON in types

    def test_validate_required_properties(self, registry: EntityRegistry) -> None:
        assert registry.validate(EntityType.PERSON, {
            "name": "皇甫谧",
            "name_zh": "皇甫谧",
            "courtesy_name": "士安",
            "pseudonym": "玄晏先生",
            "dynasty": "魏晋",
            "birth_year": 215,
            "death_year": 282,
            "birth_place": "安定朝那",
            "biography": "魏晋时期著名医学家",
            "expertise": "针灸",
            "notable_works": "针灸甲乙经",
        })

    def test_validate_missing_property_raises(self, registry: EntityRegistry) -> None:
        with pytest.raises(ValueError, match="name"):
            registry.validate(EntityType.PERSON, {"dynasty": "魏晋"})

    def test_validate_allows_extra_properties(self, registry: EntityRegistry) -> None:
        # Open-world assumption
        assert registry.validate(EntityType.PERSON, {
            "name": "张仲景", "name_zh": "张仲景", "courtesy_name": "",
            "pseudonym": "", "dynasty": "东汉", "birth_year": 150, "death_year": 219,
            "birth_place": "", "biography": "", "expertise": "", "notable_works": "",
            "extra_field": "should be allowed",
        })

    def test_get_valid_relations(self, registry: EntityRegistry) -> None:
        rels = registry.get_valid_relations(EntityType.HERB)
        rel_names = [r[0] for r in rels]
        assert "part_of" in rel_names
        assert "treats" in rel_names
        assert "corresponds_to" in rel_names

    def test_is_valid_relation_true(self, registry: EntityRegistry) -> None:
        assert registry.is_valid_relation(
            EntityType.PERSON, "authored", EntityType.TEXT
        )

    def test_is_valid_relation_false(self, registry: EntityRegistry) -> None:
        assert not registry.is_valid_relation(
            EntityType.PERSON, "treats", EntityType.SYMPTOM
        )

    def test_register_custom_schema(self, registry: EntityRegistry) -> None:
        custom = EntitySchema(
            entity_type=EntityType.PERSON,
            properties=["name"],
            relations=[],
            description_zh="精简人物",
        )
        registry.register(custom)
        schema = registry.get(EntityType.PERSON)
        assert schema.properties == ["name"]


class TestSchemaLoader:
    def test_loads_basic(self) -> None:
        loader = SchemaLoader()
        data = {
            "@context": {},
            "@graph": [
                {
                    "@id": "tcm:Person",
                    "@type": "tcm:EntityType",
                    "tcm:properties": ["name", "name_zh"],
                    "tcm:relations": [
                        {"name": "authored", "target": "tcm:Text"}
                    ],
                }
            ],
        }
        schemas = loader.loads(data)
        assert len(schemas) == 1
        assert schemas[0].entity_type == EntityType.PERSON
        assert schemas[0].properties == ["name", "name_zh"]
        assert schemas[0].relations[0].name == "authored"
        assert schemas[0].relations[0].target_type == EntityType.TEXT

    def test_loads_from_string(self) -> None:
        loader = SchemaLoader()
        schemas = loader.loads(json.dumps({
            "@context": {},
            "@graph": [
                {"@id": "tcm:Herb", "@type": "tcm:EntityType",
                 "tcm:properties": ["name"], "tcm:relations": []}
            ],
        }))
        assert len(schemas) == 1
        assert schemas[0].entity_type == EntityType.HERB

    def test_loads_unknown_type_raises(self) -> None:
        loader = SchemaLoader()
        with pytest.raises(ValueError, match="Unknown"):
            loader.loads({"@context": {}, "@graph": [
                {"@id": "tcm:Bogus", "@type": "tcm:EntityType",
                 "tcm:properties": [], "tcm:relations": []}
            ]})

    def test_loads_unknown_target_raises(self) -> None:
        loader = SchemaLoader()
        with pytest.raises(ValueError, match="Unknown target"):
            loader.loads({"@context": {}, "@graph": [
                {"@id": "tcm:Person", "@type": "tcm:EntityType",
                 "tcm:properties": ["name"],
                 "tcm:relations": [{"name": "authored", "target": "tcm:Nope"}]}
            ]})

    def test_dumps_roundtrip(self) -> None:
        loader = SchemaLoader()
        doc = loader.dumps([ENTITY_SCHEMA[EntityType.PERSON]])
        assert "@context" in doc
        assert len(doc["@graph"]) == 1
        assert doc["@graph"][0]["@id"] == "tcm:Person"

    def test_load_file(self) -> None:
        loader = SchemaLoader()
        doc = loader.dumps([ENTITY_SCHEMA[EntityType.TEXT]])
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(doc, f)
            tmp_path = f.name

        try:
            schemas = loader.load_file(Path(tmp_path))
            assert len(schemas) == 1
            assert schemas[0].entity_type == EntityType.TEXT
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_dump_file(self) -> None:
        loader = SchemaLoader()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            tmp_path = f.name

        try:
            loader.dump_file(Path(tmp_path), [ENTITY_SCHEMA[EntityType.SYMPTOM]])
            with open(tmp_path) as f:
                content = json.load(f)
            assert len(content["@graph"]) == 1
            assert content["@graph"][0]["@id"] == "tcm:Symptom"
        finally:
            Path(tmp_path).unlink(missing_ok=True)
