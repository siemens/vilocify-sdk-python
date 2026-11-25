#  SPDX-FileCopyrightText: 2026 Umut Alisoglu
#  SPDX-License-Identifier: MIT

from datetime import UTC, date, datetime, timedelta, timezone
from typing import assert_type

import pytest
import requests_mock as rm

from vilocify.jsonapy import Action, Model, Serializer
from vilocify.models import (
    Component,
    ComponentRequest,
    Group,
    Membership,
    MonitoringList,
    Notification,
    Subscription,
)


@pytest.mark.parametrize(
    "model_type", [Component, ComponentRequest, Group, Membership, MonitoringList, Notification, Subscription]
)
@pytest.mark.parametrize(("attribute", "api_name"), [("created_at", "createdAt"), ("updated_at", "updatedAt")])
def test_model_timestamps(model_type: type[Model], attribute: str, api_name: str) -> None:
    obj = Serializer.deserialize_one(
        model_type,
        {"data": {"type": model_type.jsonapi_type_name(), "id": "1", "attributes": {api_name: "2026-10-01T12:30:45Z"}}},
    )

    assert obj is not None
    assert getattr(obj, attribute) == datetime(2026, 10, 1, 12, 30, 45, tzinfo=UTC)


@pytest.mark.parametrize(
    ("model_type", "attribute", "api_name", "value", "expected"),
    [
        (Component, "eol_on", "endOfLifeOn", "2026-10-01", date(2026, 10, 1)),
        (Component, "eol_on", "endOfLifeOn", None, None),
        (
            Component,
            "deactivated_at",
            "deactivatedAt",
            "2026-10-01T12:30:45Z",
            datetime(2026, 10, 1, 12, 30, 45, tzinfo=UTC),
        ),
        (Component, "deactivated_at", "deactivatedAt", None, None),
        (
            Membership,
            "expires_at",
            "expiresAt",
            "2026-10-01T12:30:45.123456+02:00",
            datetime(2026, 10, 1, 12, 30, 45, 123456, tzinfo=timezone(timedelta(hours=2))),
        ),
        (Membership, "expires_at", "expiresAt", None, None),
        (Notification, "third_party_published_on", "thirdPartyPublishedOn", "2026-10-01", date(2026, 10, 1)),
    ],
)
def test_date_fields(
    model_type: type[Model], attribute: str, api_name: str, value: str | None, expected: date | None
) -> None:
    obj = Serializer.deserialize_one(
        model_type, {"data": {"type": model_type.jsonapi_type_name(), "id": "1", "attributes": {api_name: value}}}
    )

    assert obj is not None
    assert getattr(obj, attribute) == expected


def test_assign_python_dates_and_keep_json_serializable() -> None:
    timestamp = datetime(2026, 10, 1, 12, 30, 45, tzinfo=UTC)
    component = Component(created_at=timestamp, eol_on=date(2027, 1, 1), deactivated_at=None)

    assert_type(component.created_at, datetime)
    assert_type(component.eol_on, date | None)
    assert_type(component.deactivated_at, datetime | None)
    assert component.created_at == timestamp
    assert component.eol_on == date(2027, 1, 1)
    assert component.deactivated_at is None
    assert Serializer.serialize_one(component, None, Action.CREATE) == {
        "data": {
            "type": "components",
            "attributes": {
                "createdAt": "2026-10-01T12:30:45+00:00",
                "endOfLifeOn": "2027-01-01",
                "deactivatedAt": None,
            },
        }
    }


def test_iso_strings_remain_accepted() -> None:
    component = Component(created_at="2026-10-01T12:30:45Z", eol_on="2027-01-01")

    assert component.created_at == datetime(2026, 10, 1, 12, 30, 45, tzinfo=UTC)
    assert component.eol_on == date(2027, 1, 1)
    assert Serializer.serialize_one(component, None, Action.UPDATE) == {
        "data": {"type": "components", "attributes": {"createdAt": "2026-10-01T12:30:45Z", "endOfLifeOn": "2027-01-01"}}
    }


def test_membership_date_create_update_and_refresh(requests_mock: rm.Mocker) -> None:
    url = "https://portal.vilocify.com/api/v2/memberships"
    response = {
        "data": {
            "type": "memberships",
            "id": "1",
            "attributes": {"expiresAt": "2026-12-01T00:00:00Z", "createdAt": "2026-10-01T12:30:45Z"},
        }
    }
    headers = {"Content-Type": "application/vnd.api+json"}
    requests_mock.post(url, json=response, headers=headers)
    membership = Membership(expires_at=datetime(2026, 12, 1, tzinfo=UTC))
    membership.create()

    assert requests_mock.last_request is not None
    assert requests_mock.last_request.json()["data"]["attributes"] == {"expiresAt": "2026-12-01T00:00:00+00:00"}
    assert_type(membership.expires_at, datetime | None)
    assert membership.expires_at == datetime(2026, 12, 1, tzinfo=UTC)
    assert membership.created_at == datetime(2026, 10, 1, 12, 30, 45, tzinfo=UTC)

    requests_mock.patch(f"{url}/1", status_code=204)
    membership.expires_at = None
    membership.update()

    assert requests_mock.last_request is not None
    assert requests_mock.last_request.json()["data"]["attributes"] == {"expiresAt": None}
    assert membership.expires_at is None

    requests_mock.get(f"{url}/1", json=response, headers=headers)
    membership.refresh()

    assert membership.expires_at == datetime(2026, 12, 1, tzinfo=UTC)
    assert [request.method for request in requests_mock.request_history] == ["POST", "PATCH", "GET"]


def test_date_fields_still_respect_read_only_attributes() -> None:
    with pytest.raises(AttributeError, match="Cannot set read-only attribute"):
        Membership().created_at = datetime(2026, 10, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    ("attribute", "value", "error"),
    [("created_at", "not-a-timestamp", "Invalid isoformat string"), ("eol_on", "2026-02-30", "day")],
)
def test_invalid_date_strings_raise(attribute: str, value: str, error: str) -> None:
    component = Component(**{attribute: value})

    with pytest.raises(ValueError, match=error):
        getattr(component, attribute)
