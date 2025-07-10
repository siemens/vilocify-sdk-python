#  SPDX-FileCopyrightText: 2025 Siemens AG
#  SPDX-License-Identifier: MIT

import os

import pytest

from vilocify import api_config
from vilocify.jsonapy import (
    Attribute,
    IllegalSortError,
    Model,
    RelationshipToMany,
    RelationshipToOne,
    UnmappedModelError,
)


def test_create_attribute_assign_through_constructor_and_direct_assignment():
    class Test(Model):
        a1 = Attribute("a1")

    t1 = Test(a1=1)
    t2 = Test()
    t2.a1 = 1
    assert t1 == t2


def test_raise_writing_read_only_attribute():
    class Test(Model):
        created_at = Attribute("created_at", serialize_on=())

    t = Test()
    with pytest.raises(AttributeError):
        t.created_at = "today"


def test_assign_unknown_attribute():
    class Test(Model):
        attr = Attribute("attr")

    with pytest.raises(AttributeError):
        Test(abc=2)

    assert Test(attr="asdf").attr == "asdf"


def test_page_size_must_be_greater_than_zero():
    class Test(Model):
        attr = Attribute("attr")

    with pytest.raises(ValueError, match="Page size must be at least 1"):
        Test().asc("attr").page_size(0)

    with pytest.raises(ValueError, match="Page size must be at least 1"):
        Test().asc("attr").page_size(-10)


def test_default_model_eq():
    class Test(Model):
        a1 = Attribute("a1")
        a2 = Attribute("a2")

    assert Test(a1=1, a2=2) == Test(a1=1, a2=2)
    assert Test(a1=1, a2=1) != Test(a1=1, a2=2)
    # assert Test(a1=1) != Test(a1=1, a2=2)


def test_default_model_eq_ignores_relationships():
    class Test(Model):
        a1 = Attribute("a1")
        a2 = Attribute("a2")
        r1 = RelationshipToOne("Test")

    t1 = Test(a1=1, a2=2)
    t2 = Test(a1=1, a2=2)
    t1.r1 = Test()
    assert t1 == t2


def test_unmapped_model_delete_raises():
    class Test(Model):
        a1 = Attribute("a1")

    t = Test(a1=1)
    with pytest.raises(UnmappedModelError):
        t.delete()


def test_unmapped_model_update_raises():
    class Test(Model):
        a1 = Attribute("a1")

    t = Test(a1=1)
    with pytest.raises(UnmappedModelError):
        t.update()


def test_unmapped_model_relationship_update_raises():
    class Test(Model):
        a1 = Attribute("a1")
        r1 = RelationshipToMany("Test")

    t = Test(a1=1)
    with pytest.raises(UnmappedModelError):
        t.r1.extend(Test(a1=2))


def test_repr():
    class Test(Model):
        a1 = Attribute("a1")
        a2 = Attribute("a2")
        a3 = Attribute("a3")
        a4 = Attribute("a4")

    m = Test(a1=1, a2=2, a4=3)
    assert repr(m) == "<Test(_id=None, _json_api_attributes={'a1': 1, 'a2': 2, 'a4': 3})>"

    m = Test(a1=1, a2=2, a3=3, a4=4)
    assert repr(m) == "<Test(_id=None, _json_api_attributes={'a1': 1, 'a2': 2, 'a3': 3, ...})>"


def test_api_token_config():
    if "VILOCIFY_API_TOKEN" in os.environ:
        del os.environ["VILOCIFY_API_TOKEN"]
    assert api_config.token == ""

    os.environ["VILOCIFY_API_TOKEN"] = "abc"  # noqa: S105
    assert api_config.token == "abc"  # noqa: S105

    api_config.token = "def"  # noqa: S105
    assert api_config.token == "def"  # noqa: S105


def test_illegal_sort():
    class Test(Model):
        a1 = Attribute("a1")

    t = Test.asc("a1")
    with pytest.raises(IllegalSortError):
        t.desc("a1")
