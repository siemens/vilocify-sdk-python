"""Matches PURLs to vilocify component names and versions.

Vilocify currently does not support identifying components by PURLs directly. However, component naming in Vilocify
follows certain (undocumented) naming conventions. This module provides functions to map PURL information to names and
versions that can be used to identify components in Vilocify's component database.
"""

#  SPDX-FileCopyrightText: 2025 Siemens AG
#  SPDX-License-Identifier: MIT

from cyclonedx.model.bom import Component as BomComponent
from packageurl import PackageURL

Matcher = tuple[str | None, str | None]

PURL_TYPES = {
    "cargo": "Rust Crate",
    "composer": "PHP Package",
    "cpan": "Perl Module",
    "gem": "RubyGem",
    "golang": "Go Package",
    "hackage": "Haskell Package",
    "npm": "Node.js Package",
    "nuget": "NuGet Package",
    "pub": "Dart Package",
    "pypi": "Python Package",
    "swift": "Swift Package",
}

PURL_DISTROS: dict[str, dict[str, dict[str | None, str]]] = {
    "alpm": {"arch": {None: "Arch Linux Package"}},
    "apk": {
        "alpine": {
            None: "Alpine Package",
            "alpine-3.18": "Alpine 3.18 Package",
            "alpine-3.19": "Alpine 3.19 Package",
            "alpine-3.20": "Alpine 3.20 Package",
            "alpine-3.21": "Alpine 3.21 Package",
        },
        "openwrt": {
            None: "OpenWrt Package",
        },
    },
    "deb": {
        "debian": {
            None: "Debian Package",
            "debian-11": "Debian 11 Package",
            "bullseye": "Debian 11 Package",
            "debian-12": "Debian 12 Package",
            "bookworm": "Debian 12 Package",
        },
        "ubuntu": {
            None: "Ubuntu Package",
            "ubuntu-20.04": "Ubuntu 20.04 Package",
            "ubuntu-22.04": "Ubuntu 22.04 Package",
            "ubuntu-24.04": "Ubuntu 24.04 Package",
        },
    },
    "rpm": {
        "almalinux": {
            None: "AlmaLinux Package",
            "almalinux-8": "AlmaLinux 8 Package",
            "almalinux-9": "AlmaLinux 9 Package",
            "almalinux-10": "AlmaLinux 10 Package",
        },
        "amzn": {
            None: "Amazon Linux Package",
            "amzn-2018": "Amazon Linux Package",
            "amzn-2023": "Amazon Linux 2023 Package",
            "amzn-2": "Amazon Linux 2 Package",
        },
        "fedora": {
            None: "Fedora Package",
            "fedora-40": "Fedora 40 Package",
            "fedora-41": "Fedora 41 Package",
            "fedora-42": "Fedora 42 Package",
        },
        "opensuse": {
            None: "openSUSE Package",
        },
        "ol": {
            None: "Oracle Linux OS Package",
            "ol-7": "Oracle Linux OS 7 Package",
            "ol-8": "Oracle Linux OS 8 Package",
            "ol-9": "Oracle Linux OS 9 Package",
        },
        "redhat": {
            None: "RHEL Package",
            "rhel-7": "RHEL 7 Package",
            "rhel-8": "RHEL 8 Package",
            "rhel-9": "RHEL 9 Package",
        },
        "rocky": {
            None: "Rocky Linux Package",
            "rocky-8": "Rocky Linux 8 Package",
            "rocky-9": "Rocky Linux 9 Package",
        },
        "sles": {
            None: "SUSE Linux Enterprise Server Package",
            "sles-15.5": "SUSE Linux Enterprise Server 15 SP5 Package",
            "sles-15.6": "SUSE Linux Enterprise Server 15 SP6 Package",
            "sles-15.7": "SUSE Linux Enterprise Server 15 SP7 Package",
        },
    },
}


class MissingPurlError(Exception):
    """Raised when importing an SBOM component that has no PURL"""


def _match_purl_distro(purl: PackageURL) -> Matcher:
    distro_type = PURL_DISTROS.get(purl.type.lower())
    if distro_type is None:
        return None, None

    if purl.namespace is None:
        return None, None

    distro_namespace = distro_type.get(purl.namespace.lower())
    if distro_namespace is None:
        return None, None

    qualifier = None
    if isinstance(purl.qualifiers, dict):
        qualifier = purl.qualifiers.get("distro")
    if isinstance(qualifier, str):
        qualifier = qualifier.lower()

    for matcher, component_prefix in distro_namespace.items():
        if matcher is not None and qualifier is not None and qualifier.startswith(matcher):
            return f"{component_prefix}: {purl.name}", "All Versions"

    return f"{distro_namespace[None]}: {purl.name}", "All Versions"


def _match_purl_type(purl: PackageURL) -> Matcher:
    version = purl.version
    if version is not None:
        version = version.lstrip("v")
    return f"{PURL_TYPES[purl.type]}: {purl.namespace + '/' if purl.namespace else ''}{purl.name}", version


def match_purl(purl: PackageURL) -> Matcher:
    if purl.type in PURL_TYPES:
        return _match_purl_type(purl)

    return _match_purl_distro(purl)


def match_bom_component(bom_component: BomComponent) -> Matcher:
    purl = bom_component.purl
    if purl is None:
        raise MissingPurlError(f"purl is missing for BOM component {bom_component}")

    return match_purl(purl)
