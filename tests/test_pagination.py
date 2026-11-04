# SPDX-FileCopyrightText: 2026 Umut Alisoglu
# SPDX-License-Identifier: MIT

import pytest
import requests_mock as rm

from vilocify import api_config
from vilocify.jsonapy import DeserializationError, JSONDict, Serializer
from vilocify.models import Component, MonitoringList


@pytest.mark.parametrize("related", [False, True])
@pytest.mark.parametrize(
    "last_links",
    [{}, {"links": {}}, {"links": {"self": "/api/v2/components"}}, {"links": {"next": None}}],
    ids=["no-links", "empty-links", "self-only", "null-next"],
)
def test_iteration_stops_at_last_page(requests_mock: rm.Mocker, related: bool, last_links: JSONDict) -> None:
    path = "/api/v2/monitoringLists/list/relationships/components" if related else "/api/v2/components"
    next_link = f"{path}?page[after]=first"
    headers = {"Content-Type": "application/vnd.api+json"}
    requests_mock.get(
        f"{api_config.api_host}{path}",
        json={"data": [{"type": "components", "id": "first"}], "links": {"next": next_link}},
        headers=headers,
    )
    requests_mock.get(
        f"{api_config.api_host}{next_link}",
        json={"data": [{"type": "components", "id": "second"}], **last_links},
        headers=headers,
    )

    components = MonitoringList(id="list").components if related else Component.iter()

    assert [component.id for component in components] == ["first", "second"]
    assert requests_mock.call_count == 2  # noqa: PLR2004
    assert requests_mock.last_request is not None
    assert requests_mock.last_request.qs["page[after]"] == ["first"]


@pytest.mark.parametrize("related", [False, True])
def test_empty_collection_without_links(requests_mock: rm.Mocker, related: bool) -> None:
    path = "/api/v2/monitoringLists/list/relationships/components" if related else "/api/v2/components"
    requests_mock.get(
        f"{api_config.api_host}{path}", json={"data": []}, headers={"Content-Type": "application/vnd.api+json"}
    )

    components = MonitoringList(id="list").components if related else Component.iter()

    assert list(components) == []
    assert requests_mock.call_count == 1


@pytest.mark.parametrize("response", [{"links": None}, {"links": []}, {"links": {"next": 1}}])
def test_invalid_pagination_links_raise_deserialization_error(response: JSONDict) -> None:
    with pytest.raises(DeserializationError):
        Serializer.deserialize_next_link(response)
