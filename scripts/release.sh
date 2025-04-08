#!/usr/bin/env sh

# SPDX-FileCopyrightText: 2025 Siemens AG
# SPDX-License-Identifier: MIT

set -e

actions="(patch|minor|major|prepatch|preminor|premajor|prerelease)"

usage() {
    cat << EOT
$0 $actions

Releases a new version according to bump rule.
Updates and commits pyproject.toml, tags and pushes the commit.

The CI then publishes a Python package to the package registry of
this project for tagged commits.

Note that the script must be run on the "main" branch.

EOT
}

if echo "$1" | grep -qvE "$actions"; then
    usage
    exit 1
fi

if [ "main" != "$(git branch --show-current)" ]; then
    echo "ERROR: Not on main branch!"
    exit 1
fi

version=$(poetry version --short -- "$1")

git diff pyproject.toml
echo
echo "commit, tag and push above changes? [y/N]"
read -r choice
if [ "$choice" = "y" ]; then
    git commit pyproject.toml -m "Release version $version"
    git tag "v$version"
    git push
    git push --tags
fi
