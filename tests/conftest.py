#  SPDX-FileCopyrightText: 2025 Siemens AG
#  SPDX-License-Identifier: MIT

import pytest

from vilocify import api_config


@pytest.fixture(autouse=True)
def _dummy_request_context():
    api_config.token = ""
