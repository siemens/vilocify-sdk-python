#  SPDX-FileCopyrightText: 2025 Siemens AG
#  SPDX-License-Identifier: MIT

from typing import assert_type

import pytest
import requests_mock as rm

from vilocify.models import Component, ComponentRequest, Membership, MonitoringList


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


def test_monitoring_list_component_deletion(requests_mock: rm.Mocker) -> None:
    ml_id = "c95b8d2a-d113-41e8-8b8a-909aabbe5ff5"
    requests_mock.delete(
        f"https://portal.vilocify.com/api/v2/monitoringLists/{ml_id}/relationships/components",
        status_code=204,
    )
    ml = MonitoringList(id=ml_id, name="test_monitoring_list_component_deletion")
    ml.components.delete(Component(id="1337"))
