#  SPDX-FileCopyrightText: 2025 Siemens AG
#  SPDX-License-Identifier: MIT

import logging

from vilocify import JSON, api_config


class RequestError(Exception):
    def __init__(self, error_code: int, message: str):
        self.error_code = error_code
        self.message = message


def _request(verb: str, url: str, json: JSON = None, params: dict[str, str] | None = None) -> JSON:
    logging.debug("%s: url=%s, params=%s, json=%s", verb.upper(), url, params, json)
    response = api_config.client.request(
        verb, url, timeout=api_config.request_timeout_seconds, json=json, params=params
    )
    if not response.ok:
        raise RequestError(response.status_code, response.text)
    response_json = response.json() if response.text else None
    logging.debug("status_code=%s response=%s", response.status_code, response_json)
    logging.debug("server-timing: %s", response.headers.get("Server-Timing", "n/a"))
    return response_json


def get(url: str, params: dict[str, str] | None = None) -> JSON:
    return _request("GET", url, params=params)


def post(url: str, json: JSON) -> JSON:
    return _request("POST", url, json=json)


def patch(url: str, json: JSON) -> JSON:
    return _request("PATCH", url, json=json)


def delete(url: str, json: JSON) -> JSON:
    return _request("DELETE", url, json=json)
