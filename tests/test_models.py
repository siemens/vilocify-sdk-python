#  SPDX-FileCopyrightText: 2025 Siemens AG
#  SPDX-License-Identifier: MIT

import pytest

from vilocify.models import Membership


def test_membership():
    m = Membership()
    m.role = "admin"
    assert m.role == "admin"

    m = Membership(role="admin")
    with pytest.raises(AttributeError) as e:
        m.role = "user"

    assert e.match("Cannot set write-once attribute")
