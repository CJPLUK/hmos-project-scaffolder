"""DevEco SDK permission catalog discovery."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .errors import ScaffoldError

_CATALOG_RELATIVE_PATH = Path("openharmony/toolchains/lib/PermissionDefinitions.json")


@dataclass(frozen=True, slots=True)
class PermissionInfo:
    """A permission available to a normal HarmonyOS application."""

    name: str
    grant_mode: str
    available_level: str
    since: int
    deprecated: str

    @property
    def requires_acl(self) -> bool:
        """Whether a normal application needs ACL approval to use the permission."""

        return self.available_level != "normal"


def list_permissions() -> tuple[PermissionInfo, ...]:
    """Return normal-app permissions from the installed DevEco SDK catalog."""

    try:
        catalog = json.loads(_find_catalog().read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ScaffoldError(f"could not read the DevEco permission catalog: {error}") from error

    return tuple(
        sorted(
            (
                PermissionInfo(
                    name=item["name"],
                    grant_mode=item["grantMode"],
                    available_level=item["availableLevel"],
                    since=item["since"],
                    deprecated=item.get("deprecated", ""),
                )
                for item in catalog["definePermissions"]
                if item["availableType"] == "NORMAL"
            ),
            key=lambda item: item.name,
        )
    )


def _find_catalog() -> Path:
    roots = [
        Path(value)
        for name in ("DEVECO_SDK_HOME", "HARMONYOS_SDK_HOME")
        if (value := os.environ.get(name))
    ]
    roots.extend(
        [
            Path.home() / "Library/Huawei/Sdk",
            Path("/Applications/DevEco-Studio.app/Contents/sdk/default"),
        ]
    )

    for root in roots:
        for path in (
            root / "toolchains/lib/PermissionDefinitions.json",
            root / _CATALOG_RELATIVE_PATH,
            root / "default" / _CATALOG_RELATIVE_PATH,
        ):
            if path.is_file():
                return path
    raise ScaffoldError(
        "could not find DevEco's PermissionDefinitions.json; set DEVECO_SDK_HOME to the "
        "SDK or OpenHarmony SDK directory"
    )
