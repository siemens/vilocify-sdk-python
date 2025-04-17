#  SPDX-FileCopyrightText: 2025 Siemens AG
#  SPDX-License-Identifier: MIT

import pytest
import requests_mock as rm

from vilocify import http
from vilocify.http import JSONAPIError, JSONAPIRequestError, RequestError


def test_invalid_content_type(requests_mock: rm.Mocker):
    url = "https://portal.vilocify.com/api/v2/componentRequests"
    requests_mock.get(url, headers={"Content-Type": "application/json"})
    with pytest.raises(RequestError) as e:
        http.get(url)

    assert e.value.message == "Unsupported content type in server response."


def test_unauthorized_error(requests_mock: rm.Mocker):
    url = "https://portal.vilocify.com/api/v2/componentRequests"
    requests_mock.get(
        url,
        status_code=401,
        headers={
            "Content-Type": "application/vnd.api+json;"
            ' profile="https://jsonapi.org/profiles/ethanresnick/cursor-pagination/"; charset=utf-8'
        },
        json={
            "jsonapi": {
                "version": "1.1",
                "ext": [],
                "profile": ["https://jsonapi.org/profiles/ethanresnick/cursor-pagination/"],
            },
            "errors": [
                {
                    "title": "Unauthorized - Missing Session or API Token",
                    "status": "401",
                    "detail": "Session and API Token are absent. Please log in or provide an API token.",
                }
            ],
        },
    )
    with pytest.raises(JSONAPIRequestError) as e:
        http.get(url)

    assert len(e.value.errors) == 1
    assert e.value.errors[0] == JSONAPIError(
        title="Unauthorized - Missing Session or API Token",
        detail="Session and API Token are absent. Please log in or provide an API token.",
        source=None,
    )
