#  SPDX-FileCopyrightText: 2025 Siemens AG
#  SPDX-License-Identifier: MIT

from typing import assert_type

import pytest

from vilocify.models import ComponentRequest, Membership


def test_membership() -> None:
    m = Membership()
    m.role = "admin"
    assert m.role == "admin"

    m = Membership(role="admin")
    with pytest.raises(AttributeError) as e:
        m.role = "user"

    assert e.match("Cannot set write-once attribute")


def test_type_annotation() -> None:
    cr = ComponentRequest(name=1, prioritized=True)
    assert_type(cr.name, str)  # typechecker result
    assert type(cr.name) is int  # actual dynamic type

    assert_type(cr.prioritized, bool)
    assert type(cr.prioritized) is bool
