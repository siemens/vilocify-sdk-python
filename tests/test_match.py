#  SPDX-FileCopyrightText: 2025 Siemens AG
#  SPDX-License-Identifier: MIT

import pytest
from packageurl import PackageURL

from vilocify.match import match_purl

distro_purls = [
    ("pkg:deb/debian/base-files@12.4%2Bdeb12u10?arch=amd64&distro=debian-12", "Debian 12 Package: base-files"),
    ("pkg:deb/debian/openssl@1.1.1f?distro=ubuntu-20.04", "Debian Package: openssl"),
    ("pkg:deb/debian/bash@4.12", "Debian Package: bash"),
    ("pkg:apk/alpine/musl", "Alpine Package: musl"),
    ("pkg:apk/alpine/musl@1.2.5-r9?distro=alpine-3.21.3", "Alpine 3.21 Package: musl"),
    (
        "pkg:rpm/redhat/acl@2.2.53-3.el8?arch=x86_64&distro=rhel-8.10&upstream=acl-2.2.53-3.el8.src.rpm",
        "RHEL 8 Package: acl",
    ),
    (
        "pkg:rpm/sles/aaa_base@84.87%2Bgit20180409.04c9dae-150300.10.28.2?arch=x86_64&distro=sles-15.6",
        "SUSE Linux Enterprise Server 15 SP6 Package: aaa_base",
    ),
    ("pkg:rpm/amzn/basesystem@10.0-7.amzn2.0.1?arch=noarch&distro=amzn-2", "Amazon Linux 2 Package: basesystem"),
    ("pkg:rpm/amzn/bzip2-libs@1.0.6-8.12.amzn1?arch=x86_64&distro=amzn-2018.03", "Amazon Linux Package: bzip2-libs"),
    (
        "pkg:rpm/amzn/alternatives@1.15-2.amzn2023.0.2?arch=x86_64&distro=amzn-2023",
        "Amazon Linux 2023 Package: alternatives",
    ),
]

package_purls = [
    ("pkg:npm/%40angular/animations@19.2.2", "Node.js Package: @angular/animations", "19.2.2"),
    (
        "pkg:golang/github.com/Azure/azure-sdk-for-go/sdk/azcore@v1.18.0?type=module",
        "Go Package: github.com/Azure/azure-sdk-for-go/sdk/azcore",
        "1.18.0",
    ),
    ("pkg:gem/actionpack@7.2.2.1", "RubyGem: actionpack", "7.2.2.1"),
    ("pkg:composer/composer/pcre@3.3.1", "PHP Package: composer/pcre", "3.3.1"),
]

github_purls = [
    ("pkg:github/package-url/purl-spec@244fd47e07d", "244fd47e07d", "https://github.com/package-url/purl-spec"),
    ("pkg:github/curl/curl@8.4.0", "8.4.0", "https://github.com/curl/curl"),
]

unknown_purls = [
    "pkg:conan/openssl@3.0.3",
    "pkg:deb/bash@4.12",
    "pkg:android/com.android.dialer@35",
]


@pytest.mark.parametrize(("purl", "expected"), distro_purls)
def test_match_distro_purl(purl: str, expected: str):
    name, version, url = match_purl(PackageURL.from_string(purl))
    assert name == expected
    assert version == "All Versions"
    assert url is None


@pytest.mark.parametrize(("purl", "expected_name", "expected_version"), package_purls)
def test_match_package_purls(purl: str, expected_name: str, expected_version: str):
    name, version, url = match_purl(PackageURL.from_string(purl))
    assert name == expected_name
    assert version == expected_version
    assert url is None


@pytest.mark.parametrize(("purl", "expected_version", "expected_url"), github_purls)
def test_match_github_purls(purl: str, expected_version: str, expected_url: str):
    name, version, url = match_purl(PackageURL.from_string(purl))
    assert name is None
    assert version == expected_version
    assert url == expected_url


@pytest.mark.parametrize("purl", unknown_purls)
def test_match_unknown_purl(purl: str):
    name, version, url = match_purl(PackageURL.from_string(purl))
    assert name is None
    assert version is None
    assert url is None
