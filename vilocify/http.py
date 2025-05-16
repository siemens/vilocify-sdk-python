#  SPDX-FileCopyrightText: 2025 Siemens AG
#  SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

import requests

from vilocify import JSON, api_config

logger = logging.getLogger(__name__)


class RequestError(Exception):
    def __init__(self, error_code: int, message: str):
        self.error_code = error_code
        self.message = message


@dataclass
class JSONAPIError:
    title: str = ""
    detail: str = ""
    source: dict | None = None

    @staticmethod
    def from_dict(d: dict) -> "JSONAPIError":
        return JSONAPIError(d.get("title", ""), d.get("detail", ""), d.get("source"))


class JSONAPIRequestError(RequestError):
    def __init__(self, error_code: int, message: str, errors: list[JSONAPIError]):
        super().__init__(error_code, message)
        self.errors = errors

    @staticmethod
    def from_response(code: int, response_json: JSON) -> "JSONAPIRequestError":
        errors = []
        if isinstance(response_json, dict) and isinstance((raw_errors := response_json.get("errors")), list):
            errors = [JSONAPIError.from_dict(error) for error in raw_errors if isinstance(error, dict)]

        if errors:
            message = f"Encountered errors: {', '.join(f"'{e.title}'" for e in errors)}"
        else:
            message = "Encountered unknown error. No error details were provided from the server."
        return JSONAPIRequestError(code, message, errors)


def _request(verb: str, url: str, json: JSON = None, params: dict[str, str] | None = None) -> JSON:
    logger.debug("%s: url=%s, params=%s, json=%s", verb.upper(), url, params, json)
    response = api_config.client.request(
        verb, url, timeout=api_config.request_timeout_seconds, json=json, params=params
    )
    if response.content and not response.headers.get("Content-Type", "").startswith("application/vnd.api+json"):
        raise RequestError(response.status_code, "Unsupported content type in server response.")

    try:
        response_json = response.json()
    except requests.exceptions.JSONDecodeError:
        response_json = None

    logger.debug("status_code=%s response=%s", response.status_code, response_json)
    if "Server-Timing" in response.headers:
        logger.debug("server-timing: %s", response.headers["Server-Timing"])

    if not response.ok:
        raise JSONAPIRequestError.from_response(response.status_code, response_json)

    return response_json


def get(url: str, params: dict[str, str] | None = None) -> JSON:
    return _request("GET", url, params=params)


def post(url: str, json: JSON) -> JSON:
    return _request("POST", url, json=json)


def patch(url: str, json: JSON) -> JSON:
    return _request("PATCH", url, json=json)


def delete(url: str, json: JSON) -> JSON:
    return _request("DELETE", url, json=json)
