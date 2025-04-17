#  SPDX-FileCopyrightText: 2025 Siemens AG
#  SPDX-License-Identifier: MIT

import importlib.metadata
import os
from urllib.parse import ParseResult, urlparse

import requests

__version__ = importlib.metadata.version("vilocify-sdk")

JSON = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None


class _APIConfig:
    def __init__(self):
        self._token = None
        self.base_url = os.environ.get("VILOCIFY_API_BASE_URL", "https://portal.vilocify.com/api/v2")
        self.api_host = _APIConfig._drop_path(self.base_url)
        self.request_timeout_seconds = 20

        session = requests.Session()
        session.headers.update(
            {
                "Content-Type": "application/vnd.api+json",
                "Accept": "application/vnd.api+json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": f"vilocify-sdk-python/{__version__}",
            }
        )
        self.client = session

    @staticmethod
    def _drop_path(url: str) -> str:
        parts = urlparse(url)
        return ParseResult(parts.scheme, parts.netloc, "", "", "", "").geturl()

    @property
    def token(self) -> str:
        return self._token or os.environ.get("VILOCIFY_API_TOKEN") or ""

    @token.setter
    def token(self, value: str):
        self._token = value
        self.client.headers["Authorization"] = f"Bearer {self._token}"


api_config = _APIConfig()
