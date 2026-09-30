#  SPDX-FileCopyrightText: 2026 Siemens AG
#  SPDX-License-Identifier: MIT

import json
from pathlib import Path

import pytest
import requests_mock as rm
from click.testing import CliRunner

from vilocify import api_config
from vilocify.cli import cli

ML_ID = "00000000-1111-2222-3333-444444444444"
CONTENT_TYPE = {"Content-Type": "application/vnd.api+json"}
USAGE_ERROR_EXIT_CODE = 2


@pytest.fixture
def sbom(tmp_path: Path) -> str:
    path = tmp_path / "sbom.json"
    path.write_text(json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1, "components": []}))
    return str(path)


@pytest.mark.parametrize("group", [None, "Engineering"])
@pytest.mark.parametrize("selector", [["--id", ML_ID], ["--name", "Existing", "--comment", "Keep this comment"]])
def test_import_existing_list(requests_mock: rm.Mocker, sbom: str, selector: list[str], group: str | None):
    url = f"{api_config.base_url}/monitoringLists"
    data = {
        "id": ML_ID,
        "type": "monitoringLists",
        "attributes": {"name": "Existing", "comment": "Keep this comment", "group": "Original"},
    }
    requests_mock.get(f"{url}/{ML_ID}", headers=CONTENT_TYPE, json={"data": data})
    requests_mock.get(url, headers=CONTENT_TYPE, json={"data": [data], "links": {"next": None}})
    requests_mock.get(
        f"{url}/{ML_ID}/relationships/components",
        headers=CONTENT_TYPE,
        json={"data": [], "links": {"next": None}},
    )
    requests_mock.patch(f"{url}/{ML_ID}", headers=CONTENT_TYPE, status_code=204)
    args = ["monitoringlist", "import", *selector, "--from-cyclonedx", sbom, "--yes"]
    if group is not None:
        args.extend(["--group", group])

    result = CliRunner().invoke(cli, args)

    assert result.exit_code == 0, result.output
    lookup = requests_mock.request_history[0]
    if selector[0] == "--id":
        assert lookup.url.split("?")[0] == f"{url}/{ML_ID}"
    else:
        assert lookup.qs["filter[name][eq]"] == ["existing"]
        assert lookup.qs["filter[comment][eq]"] == ["keep this comment"]
    update = requests_mock.request_history[-1].json()["data"]
    assert update["attributes"] == {
        "name": "Existing",
        "comment": "Keep this comment",
        "group": group or "Original",
    }
    assert update["relationships"]["components"]["data"] == []
    assert all(request.method != "POST" for request in requests_mock.request_history)


@pytest.mark.parametrize("group", [None, "Engineering"])
def test_import_creates_list(requests_mock: rm.Mocker, sbom: str, group: str | None):
    url = f"{api_config.base_url}/monitoringLists"
    requests_mock.get(url, headers=CONTENT_TYPE, json={"data": [], "links": {"next": None}})
    requests_mock.post(
        url,
        headers=CONTENT_TYPE,
        status_code=201,
        json={"data": {"id": ML_ID, "type": "monitoringLists", "attributes": {"name": "New", "comment": ""}}},
    )
    requests_mock.get(
        f"{url}/{ML_ID}/relationships/components",
        headers=CONTENT_TYPE,
        json={"data": [], "links": {"next": None}},
    )
    requests_mock.patch(f"{url}/{ML_ID}", headers=CONTENT_TYPE, status_code=204)
    args = ["monitoringlist", "import", "--name", "New", "--from-cyclonedx", sbom, "--yes"]
    if group is not None:
        args.extend(["--group", group])

    result = CliRunner().invoke(cli, args)

    assert result.exit_code == 0, result.output
    attributes = requests_mock.request_history[1].json()["data"]["attributes"]
    expected = {"name": "New", "comment": ""}
    if group is not None:
        expected["group"] = group
    assert attributes == expected


@pytest.mark.parametrize(
    ("selector", "message"),
    [
        ([], "Specify exactly one of --id or --name."),
        (["--id", ML_ID, "--name", "Existing"], "Specify exactly one of --id or --name."),
        (["--id", ML_ID, "--comment", "Comment"], "--comment can only be used with --name."),
        (["--id", ML_ID, "--comment", ""], "--comment can only be used with --name."),
    ],
)
def test_import_invalid_selector(requests_mock: rm.Mocker, sbom: str, selector: list[str], message: str):
    result = CliRunner().invoke(cli, ["monitoringlist", "import", *selector, "--from-cyclonedx", sbom])

    assert result.exit_code == USAGE_ERROR_EXIT_CODE
    assert message in result.output
    assert requests_mock.call_count == 0


def test_import_missing_id_does_not_create_list(requests_mock: rm.Mocker, sbom: str):
    requests_mock.get(
        f"{api_config.base_url}/monitoringLists/{ML_ID}", headers=CONTENT_TYPE, status_code=404, json={"errors": []}
    )

    result = CliRunner().invoke(cli, ["monitoringlist", "import", "--id", ML_ID, "--from-cyclonedx", sbom])

    assert result.exit_code != 0
    assert requests_mock.call_count == 1
    assert requests_mock.request_history[0].method == "GET"
