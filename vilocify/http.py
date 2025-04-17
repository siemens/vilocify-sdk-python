#  SPDX-FileCopyrightText: 2025 Siemens AG
#  SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

import requests

from vilocify import JSON, api_config


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
    def from_response(response: requests.Response) -> "JSONAPIRequestError":
        errors = [JSONAPIError.from_dict(error) for error in response.json()["errors"]]
        if errors:
            message = f"Encountered errors: {', '.join(f"'{e.title}'" for e in errors)}"
        else:
            message = "Encountered unknown error. No error details were provided from the REST API."
        return JSONAPIRequestError(response.status_code, message, errors)


def _request(verb: str, url: str, json: JSON = None, params: dict[str, str] | None = None) -> JSON:
    logging.debug("%s: url=%s, params=%s, json=%s", verb.upper(), url, params, json)
    response = api_config.client.request(
        verb, url, timeout=api_config.request_timeout_seconds, json=json, params=params
    )
    if not response.headers.get("Content-Type", "").startswith("application/vnd.api+json"):
        raise RequestError(response.status_code, "Unsupported content type in server response.")

    if not response.ok:
        raise JSONAPIRequestError.from_response(response)

    response_json = response.json() if response.text else None
    logging.debug("status_code=%s response=%s", response.status_code, response_json)
    if "Server-Timing" in response.headers:
        logging.debug("server-timing: %s", response.headers["Server-Timing"])

    return response_json


def get(url: str, params: dict[str, str] | None = None) -> JSON:
    return _request("GET", url, params=params)


def post(url: str, json: JSON) -> JSON:
    return _request("POST", url, json=json)


def patch(url: str, json: JSON) -> JSON:
    return _request("PATCH", url, json=json)


def delete(url: str, json: JSON) -> JSON:
    return _request("DELETE", url, json=json)
