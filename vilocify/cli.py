"""Cli to interact with Vilocify API."""

#  SPDX-FileCopyrightText: 2025 Siemens AG
#  SPDX-License-Identifier: MIT

import io
import json
import logging
import sys
import textwrap
from datetime import UTC, datetime, timedelta

import click
from click import BadParameter
from cyclonedx.model.bom import Bom
from cyclonedx.model.bom import Component as BomComponent

import vilocify
from vilocify.http import JSONAPIRequestError, RequestError
from vilocify.match import MissingPurlError, match_bom_component
from vilocify.models import (
    Component,
    ComponentRequest,
    MonitoringList,
    Notification,
    Vulnerability,
)

ComponentCache = dict[tuple[str, str], Component]

logger = logging.getLogger(__name__)

version_text = """Vilocify Python SDK, version %(version)s

Copyright (C) 2025 Siemens AG
MIT License
"""


class BadCycloneDXFileError(Exception):
    """Raised on unsupported file extensions of a CycloneDX file"""


@click.group()
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "ERROR"]), default="INFO")
@click.version_option(version=vilocify.__version__, message=version_text)
def cli(log_level: str):
    logging.basicConfig(format="%(levelname)s: %(message)s", level=log_level)


@cli.command()
@click.option("--for", "monitoring_list", required=True)
@click.option("--since", default=datetime.now(tz=UTC) - timedelta(days=1), type=click.DateTime())
def notifications(monitoring_list: str, since: datetime):
    """Print all notifications for the given monitoring list since a certain date."""
    ns = Notification.where("monitoringLists.id", "any", monitoring_list).where("createdAt", "after", since.isoformat())
    has_notifications = False
    for notification in ns:
        has_notifications = True
        print()
        print("---")
        print("Title:", notification.title)
        print("Description:")
        print(textwrap.indent(notification.description, "  "))
        print("Vulnerabilities:")
        for vuln in Vulnerability.where("id", "in", notification.vulnerabilities.ids()):
            print("  - CVE: ", vuln.cve)
            print("    CVSS: ", vuln.cvss)
            print("    Description: ", vuln.description)

    if not has_notifications:
        print(f"No new notifications for monitoringlist #{monitoring_list} since {since.isoformat()}.")


def _find_vilocify_component(cache: ComponentCache, bom_component: BomComponent) -> Component | None:
    vilocify_name, vilocify_version = match_bom_component(bom_component)
    if vilocify_name is not None and vilocify_version is not None:
        if (k := (vilocify_name, vilocify_version)) in cache:
            return cache[k]

        return (
            Component.where("name", "eq", vilocify_name)
            .where("version", "eq", vilocify_version)
            .where("active", "eq", "true")
            .first()
        )

    return None


def _load_bom(file: io.FileIO) -> Bom:
    if file.name.endswith(".json"):
        return Bom.from_json(data=json.load(file))  # type: ignore[attr-defined]

    if file.name.endswith(".xml"):
        return Bom.from_xml(data=file)  # type: ignore[attr-defined]

    raise BadCycloneDXFileError("The CyclondeDX file must end with .json or .xml.")


def _load_ml(name: str, comment: str) -> MonitoringList:
    ml = MonitoringList.where("name", "eq", name).where("comment", "eq", comment).first()
    if ml is None:
        logger.info("No monitoring list with given name and comment found. Creating new list.")
        ml = MonitoringList(name=name, comment=comment)
        ml.create()

    logger.info("Using monitoring list %s", ml.id)
    return ml


def _match_bom(cache: ComponentCache, bom: Bom) -> tuple[list[Component], list[BomComponent]]:
    components = []
    unidentified_components = []
    for bom_component in bom.components:
        try:
            c = _find_vilocify_component(cache, bom_component)
        except MissingPurlError:
            logger.warning("Ignoring BOM component %s due to missing PURL", bom_component.name)
        else:
            if c is not None:
                logger.info("Found component %s for %s", c.id, bom_component.purl)
                components.append(c)
            else:
                unidentified_components.append(bom_component)

    return components, unidentified_components


@cli.command()
@click.option("--name", required=True)
@click.option("--comment", default="")
@click.option("--yes", is_flag=True)
@click.option("--from-cyclonedx", type=click.File("rt"), required=True)
def monitoringlist(name: str, comment: str, yes: bool, from_cyclonedx: io.FileIO):
    """Creates or updates a monitoring list from a CycloneDX JSON or XML file.

    The monitoring list is identified by the given name and comment. Changing the name or comment between runs will
    create a new monitoring list. The JSON or XML filetype is identified by the filename ending.

    Some components might not be found on Vilocify. A ComponentRequest is created for components that cannot be
    identified. ComponentRequests might need several days to get processed and integrated into Vilocify. Running the
    same command repeatedly will update the monitoring list once the component requests are processed.
    """

    component_requests = []
    bom = _load_bom(from_cyclonedx)
    ml = _load_ml(name, comment)
    components_cache = {(c.name, c.version): c for c in ml.components}
    components, unidentified_components = _match_bom(components_cache, bom)

    for bom_component in unidentified_components:
        cr = ComponentRequest.where("componentUrl", "eq", str(bom_component.purl)).first()
        if cr is None:
            component_name, version = match_bom_component(bom_component)
            cr = ComponentRequest(
                name=component_name or bom_component.name,
                version=version or bom_component.version,
                component_url=str(bom_component.purl),
                comment="Auto-created by vilocify-sdk-python",
            )
            component_requests.append(cr)
        elif (c := cr.component) is not None:
            logger.info("Found component %s for %s through component request %s", c.id, bom_component.purl, cr.id)
            components.append(c)
        elif cr.state in ("unprocessed", "rejected"):
            logger.info("The component request %s for %s is %s", cr.id, bom_component.purl, cr.state)

    if component_requests:
        logger.info(
            "%d components could not be identified directly or through existing component requests.",
            len(component_requests),
        )
        if yes or click.prompt(f"\nCreate {len(component_requests)} component requests? (y/n)", type=bool):
            for cr in component_requests:
                cr.create()

    ml.components = components
    ml.update()
    logger.info("Finished updating monitoring list %s", ml.id)


@cli.command()
@click.option(
    "--state",
    type=click.Choice(["unprocessed", "rejected", "mapped"]),
    multiple=True,
    default=["unprocessed", "rejected", "mapped"],
)
def component_request(state: tuple[str]):
    """List component requests by processing state."""
    for cr in ComponentRequest.where("state", "in", list(state)):
        print("title:", cr.vendor, "-", cr.name, "-", cr.version)
        print("URL:", cr.component_url)
        print("state:", cr.state)
        print()


def main():
    try:
        exit_code = cli.main(standalone_mode=False)
        sys.exit(exit_code)
    except JSONAPIRequestError as e:
        logger.error("%s - %s", e.error_code, e.message)
        for error in e.errors:
            logger.error("%s. Detail: %s", error.title, error.detail)
        sys.exit(1)
    except RequestError as e:
        logger.error("%s - %s", e.error_code, e.message)
        sys.exit(1)
    except (BadCycloneDXFileError, FileNotFoundError, BadParameter) as e:
        logger.error("%s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unknown error occurred", exc_info=e)
        sys.exit(1)


if __name__ == "__main__":
    main()
