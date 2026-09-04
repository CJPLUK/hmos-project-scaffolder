"""Validated user-facing scaffold configuration."""

from __future__ import annotations

import platform
import re
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from .errors import ConfigurationError

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MODULE_NAME = re.compile(r"^[a-z][A-Za-z0-9_]*$")
_BUNDLE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+$")
_CANGJIE_PACKAGE = re.compile(r"^[a-z][a-z0-9_]*$")
_CJC_VERSION = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._+-]*$")
_SDK_VERSION = re.compile(r"^\d+\.\d+\.\d+\((\d+)\)$")
_PERMISSION = re.compile(r"^ohos\.permission\.[A-Za-z][A-Za-z0-9_.]*$")
_SUPPORTED_DEVICE_TYPES = frozenset({"phone", "tablet"})
_WINDOWS_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
)
_CANGJIE_KEYWORDS = frozenset(
    """
    as abstract break Bool case catch class const continue Rune do else enum extend
    for func false finally foreign Float16 Float32 Float64 if in is init import
    interface Int8 Int16 Int32 Int64 IntNative let main macro match Nothing open
    operator override package private protected public redef return spawn static String
    struct super synchronized this This throw true try type UInt8 UInt16 UInt32 UInt64
    UIntNative Unit unsafe var VArray where while
    """.split()  # noqa: SIM905
)
_ARKTS_KEYWORDS = frozenset(
    """
    await break case catch class const continue debugger default delete do else enum
    export extends false finally for function if import in instanceof let new null
    return super switch this throw true try typeof var void while with yield implements
    interface package private protected public static
    """.split()  # noqa: SIM905
)


class HostPlatform(str, Enum):
    """Host target emitted into the Cangjie package manifest."""

    AUTO = "auto"
    MACOS_ARM64 = "macos-arm64"
    WINDOWS_X64 = "windows-x64"


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """Values shared by the bundled standalone project templates.

    ``cangjie_package`` defaults to ``ohos_app_cangjie_<module_name>`` to match
    DevEco Studio's Cangjie Empty Ability naming convention.
    """

    project_name: str
    bundle_name: str
    module_name: str = "entry"
    ability_name: str = "EntryAbility"
    cangjie_package: str | None = None
    view_name: str = "EntryView"
    backup_ability_name: str = "EntryBackupAbility"
    vendor: str = "example"
    target_sdk_version: str = "6.1.1(24)"
    compatible_sdk_version: str = "6.1.1(24)"
    model_version: str = "6.1.1"
    cjc_version: str = "1.1.3"
    app_version_code: int = 1_000_000
    app_version_name: str = "1.0.0"
    app_build_version: str = "1"
    device_types: tuple[str, ...] = ("phone",)
    permissions: tuple[str, ...] = ()
    installation_free: bool = False
    exported: bool = True
    home_screen: bool = True
    host_platform: HostPlatform | str = HostPlatform.AUTO

    def __post_init__(self) -> None:
        if self.cangjie_package is None:
            object.__setattr__(
                self,
                "cangjie_package",
                f"ohos_app_cangjie_{self.module_name}",
            )
        if isinstance(self.host_platform, str):
            try:
                object.__setattr__(self, "host_platform", HostPlatform(self.host_platform))
            except ValueError as error:
                choices = ", ".join(item.value for item in HostPlatform)
                raise ConfigurationError(f"host_platform must be one of: {choices}") from error
        if isinstance(self.device_types, str):
            raise ConfigurationError("device_types must be a sequence, not a string")
        if not isinstance(self.device_types, tuple):
            try:
                object.__setattr__(self, "device_types", tuple(self.device_types))
            except TypeError as error:
                raise ConfigurationError("device_types must be an iterable of strings") from error
        if isinstance(self.permissions, str):
            raise ConfigurationError("permissions must be a sequence, not a string")
        if not isinstance(self.permissions, tuple):
            try:
                object.__setattr__(self, "permissions", tuple(self.permissions))
            except TypeError as error:
                raise ConfigurationError("permissions must be an iterable of strings") from error
        self._validate()

    def _validate(self) -> None:
        if not self.project_name.strip():
            raise ConfigurationError("project_name must not be empty")
        if any(character in self.project_name for character in "\r\n\0"):
            raise ConfigurationError("project_name must not contain control characters")
        if not _BUNDLE_NAME.fullmatch(self.bundle_name):
            raise ConfigurationError(
                "bundle_name must contain at least two dot-separated identifier segments"
            )
        if not _MODULE_NAME.fullmatch(self.module_name):
            raise ConfigurationError(
                "module_name must start with a lowercase letter and contain only letters, "
                "digits, and underscores"
            )
        self._validate_path_name(self.module_name, field_name="module_name")
        for field_name in ("ability_name", "view_name", "backup_ability_name"):
            value = getattr(self, field_name)
            if not _IDENTIFIER.fullmatch(value):
                raise ConfigurationError(f"{field_name} must be a valid source identifier")
        if self.view_name in _CANGJIE_KEYWORDS:
            raise ConfigurationError("view_name must not be a Cangjie keyword")
        for field_name in ("ability_name", "backup_ability_name"):
            if getattr(self, field_name) in _ARKTS_KEYWORDS:
                raise ConfigurationError(f"{field_name} must not be an ArkTS keyword")
            self._validate_path_name(getattr(self, field_name), field_name=field_name)
        if self.ability_name.casefold() == self.backup_ability_name.casefold():
            raise ConfigurationError(
                "ability_name and backup_ability_name must differ when compared case-insensitively"
            )
        if not _CANGJIE_PACKAGE.fullmatch(self.cangjie_package or ""):
            raise ConfigurationError(
                "cangjie_package must start with a lowercase letter and contain only lowercase "
                "letters, digits, and underscores"
            )
        if self.cangjie_package in _CANGJIE_KEYWORDS:
            raise ConfigurationError("cangjie_package must not be a Cangjie keyword")
        self._validate_path_name(self.cangjie_package or "", field_name="cangjie_package")
        if not self.vendor.strip() or any(character in self.vendor for character in "\r\n\0"):
            raise ConfigurationError("vendor must be a non-empty single-line value")
        for field_name in (
            "model_version",
            "app_version_name",
            "app_build_version",
        ):
            value = getattr(self, field_name)
            if not value or any(character in value for character in '"\r\n\0'):
                raise ConfigurationError(f"{field_name} must be a non-empty quoted-string value")
        if not _CJC_VERSION.fullmatch(self.cjc_version):
            raise ConfigurationError(
                "cjc_version may contain only letters, digits, dots, underscores, pluses, "
                "and hyphens"
            )
        target_api = self._parse_sdk_api(self.target_sdk_version, field_name="target_sdk_version")
        compatible_api = self._parse_sdk_api(
            self.compatible_sdk_version,
            field_name="compatible_sdk_version",
        )
        if compatible_api < 22:
            raise ConfigurationError("compatible_sdk_version must use API 22 or newer")
        if target_api < compatible_api:
            raise ConfigurationError(
                "target_sdk_version API must be greater than or equal to compatible_sdk_version API"
            )
        if self.app_version_code < 1:
            raise ConfigurationError("app_version_code must be positive")
        if self.home_screen and not self.exported:
            raise ConfigurationError("home_screen requires exported=True")
        if not self.device_types:
            raise ConfigurationError("device_types must contain at least one device type")
        unsupported_device_types = set(self.device_types) - _SUPPORTED_DEVICE_TYPES
        if unsupported_device_types:
            raise ConfigurationError(
                "device_types only supports: " + ", ".join(sorted(_SUPPORTED_DEVICE_TYPES))
            )
        if len(set(self.device_types)) != len(self.device_types):
            raise ConfigurationError("device_types must not contain duplicates")
        for permission in self.permissions:
            if not isinstance(permission, str) or not _PERMISSION.fullmatch(permission):
                raise ConfigurationError(
                    "permissions must use the form ohos.permission.PERMISSION_NAME"
                )
        if len(set(self.permissions)) != len(self.permissions):
            raise ConfigurationError("permissions must not contain duplicates")

    @staticmethod
    def _parse_sdk_api(value: str, *, field_name: str) -> int:
        match = _SDK_VERSION.fullmatch(value)
        if match is None:
            raise ConfigurationError(f"{field_name} must use the format major.minor.patch(api)")
        return int(match.group(1))

    @staticmethod
    def _validate_path_name(value: str, *, field_name: str) -> None:
        if value.upper() in _WINDOWS_RESERVED_NAMES:
            raise ConfigurationError(f"{field_name} must not be a Windows-reserved path name")

    def template_context(self) -> dict[str, Any]:
        """Return a complete Jinja context with derived template values."""

        context = asdict(self)
        context["host_platform"] = self.resolved_host_platform.value
        context["module_name_upper"] = self.module_name.upper()
        context["ability_name_lower"] = self.ability_name.lower()
        context["backup_ability_name_lower"] = self.backup_ability_name.lower()
        return context

    @property
    def resolved_host_platform(self) -> HostPlatform:
        """Resolve ``auto`` to one of the host targets supported by the source templates."""

        host_platform = HostPlatform(self.host_platform)
        if host_platform is not HostPlatform.AUTO:
            return host_platform
        if sys.platform == "win32":
            return HostPlatform.WINDOWS_X64
        machine = platform.machine().lower()
        if sys.platform == "darwin" and machine in {"arm64", "aarch64"}:
            return HostPlatform.MACOS_ARM64
        raise ConfigurationError(
            "host_platform could not be detected as windows-x64 or macos-arm64; "
            "pass it explicitly for the machine that will build the project"
        )
