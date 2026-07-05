"""Tests for Commentary model — 注疏链."""

import pytest
from app.models.commentary import Commentary
from tests.conftest_db import db_session  # noqa: F401


@pytest.mark.asyncio
async def test_create_commentary(db_session):
    """A basic commentary should be creatable."""
    c = Commentary(
        passage_id="pass-test-1",
        author_id="person-test-1",
        commentary_type="end_of_passage",
        layer="tang",
        content_text="此段论经脉流行之理。",
    )
    db_session.add(c)
    await db_session.flush()
    assert c.id is not None
    assert c.commentary_type == "end_of_passage"
    assert c.layer == "tang"


@pytest.mark.asyncio
async def test_commentary_self_reference_chain(db_session):
    """A sub-commentary should reference a parent commentary."""
    parent = Commentary(
        passage_id="pass-test-2",
        author_id="person-test-2",
        commentary_type="commentary_work",
        layer="tang",
        content_text="王冰注：此乃阴阳之道。",
    )
    db_session.add(parent)
    await db_session.flush()

    child = Commentary(
        passage_id="pass-test-2",
        author_id="person-test-3",
        commentary_type="sub_commentary",
        layer="ming",
        content_text="王注非也，应为阴阳离合论。",
        parent_id=parent.id,
        relation_type="refutes",
    )
    db_session.add(child)
    await db_session.flush()

    assert child.parent_id == parent.id
    assert child.relation_type == "refutes"


@pytest.mark.asyncio
async def test_commentary_invalid_type_raises(db_session):
    """Inserting an invalid commentary_type should fail at DB level."""
    c = Commentary(
        passage_id="pass-test-3",
        content_text="test",
        commentary_type="invalid_type",  # not in CHECK
        layer="modern",
    )
    db_session.add(c)
    with pytest.raises(Exception):
        await db_session.flush()
