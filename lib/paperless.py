#!/usr/bin/env python3
# Copyright 2023 John P. Lettman <the@johnlettman.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
from tempfile import NamedTemporaryFile
from urllib.request import urlopen
from os import environ
from platform import machine
from subprocess import check_call, CalledProcessError
from typing import Iterable, Union, List


gh_paperless_user = "paperless-ngx"
gh_paperless_repo = "paperless-ngx"


def apt_update() -> None:
    """Update the apt package cache."""
    cmd = ["apt-get", "update"]
    check_call(cmd, universal_newlines=True)


def apt_satisfy(packages: Union[Iterable[str], str]) -> None:
    """Satisfy package dependencies through apt."""
    if is_iterish(packages):
        packages = ", ".join(packages)

    cmd = ["apt", "satisfy", "-y", packages]
    env = {**environ, "DEBIAN_FRONTEND": "noninteractive"}
    check_call(cmd, universal_newlines=True, env=env)


def machine_is_arm() -> bool:
    """Check whether the CPU architecture is ARM-based."""
    # ARM architecture processors typically start with "ARM" or "AARCH"
    # Debian uses the following nomenclature: arm64, armel, armhf,...
    # Ubuntu uses the following nomenclature: arm32, aarch32, armhf32,...
    architecture = machine().lower()
    return architecture.startswith("arm") or architecture.startswith("aarch")


def is_iterish(obj: any) -> bool:
    """Check whether an object is strictly a list-like iterable."""
    try:
        iter(obj)  # Will raise TypeError if not iterable
        return not isinstance(obj, (str, bytes, bytearray))
    except TypeError:
        return False


# Credit: Przemyslaw Lal @przemeklal
# https://github.com/canonical/charm-local-juju-users/blob/e96fcd6319cda3743b237c8090deba3b32b37de0/lib/local_juju_users.py#L114
def linux_user_exists(user):
    """Return True if the user exists on the system."""
    cmd = ["getent", "passwd", user]
    try:
        check_call(cmd)
        return True
    except CalledProcessError:
        return False


def gh_list_releases(user: str, repo: str) -> List[str]:
    url = f"https://api.github.com/repos/{user}/{repo}/releases"

    with urlopen(url) as response:
        if response.status != 200:  # ruh-roh
            raise Exception(f"HTTP error {response.status}")

        data = response.read()
        releases = json.loads(data.decode("utf-8"))

    return [release["tag_name"] for release in releases]


def gh_download_release_asset(
    user: str,
    repo: str,
    tag: str,
    extension: str = ".tar.xz",
    destination: Union[str, None] = None,
) -> str:
    url = f"https://api.github.com/repos/{user}/{repo}/releases/tags/{tag}"

    with urlopen(url) as response:
        if response.status != 200:  # b0rked
            raise Exception(f"HTTP error {response.status}")

        data = response.read()
        release_info = json.loads(data.decode("utf-8"))

    # Find the specified asset
    asset_url = None
    for asset in release_info["assets"]:
        if asset["name"].endswith(extension):
            asset_url = asset["browser_download_url"]
            break

    if asset_url is None:
        raise Exception(f"No asset with extension {extension} found for release {tag}")

    # Download the asset
    with urlopen(asset_url) as response, open(
        destination, mode="wb"
    ) if destination else NamedTemporaryFile(
        mode="wb", suffix=extension, delete=False
    ) as output:
        output.write(response.read())
        return output.name


def list_paperless_versions() -> List[str]:
    return gh_list_releases(gh_paperless_user, gh_paperless_repo)


def download_paperless_archive(tag: str) -> str:
    return gh_download_release_asset(
        gh_paperless_user, gh_paperless_repo, tag, ".tar.xz"
    )



