"""Command-line interface for the HarmonyOS project scaffolder."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .config import HostPlatform, ProjectConfig
from .errors import ScaffoldError
from .scaffolder import list_templates, scaffold


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harmonyos-scaffold",
        description="Scaffold a standalone HarmonyOS Cangjie project.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="list bundled templates")

    create = subparsers.add_parser("create", help="create a project from a template")
    create.add_argument("template", choices=[item.name for item in list_templates()])
    create.add_argument("destination", type=Path, help="exact output project directory")
    create.add_argument("--project-name", required=True, help="application display name")
    create.add_argument("--bundle-name", required=True, help="HarmonyOS bundle identifier")
    create.add_argument("--module-name", default="entry")
    create.add_argument("--ability-name", default="EntryAbility")
    create.add_argument(
        "--cangjie-package",
        help="Cangjie package name (default: ohos_app_cangjie_<module-name>)",
    )
    create.add_argument("--view-name", default="EntryView", help="Cangjie Empty view class")
    create.add_argument(
        "--backup-ability-name",
        default="EntryBackupAbility",
        help="Hybrid template backup extension class",
    )
    create.add_argument("--vendor", default="example")
    create.add_argument("--target-sdk-version", default="6.1.1(24)")
    create.add_argument("--compatible-sdk-version", default="6.1.1(24)")
    create.add_argument("--model-version", default="6.1.1")
    create.add_argument("--cjc-version", default="1.1.3")
    create.add_argument("--app-version-code", default=1_000_000, type=int)
    create.add_argument("--app-version-name", default="1.0.0")
    create.add_argument("--app-build-version", default="1")
    create.add_argument(
        "--device-type",
        action="append",
        dest="device_types",
        help="target device type; repeat for multiple values (default: phone)",
    )
    create.add_argument(
        "--host-platform",
        choices=[item.value for item in HostPlatform],
        default=HostPlatform.AUTO.value,
    )
    create.add_argument("--installation-free", action="store_true")
    create.add_argument(
        "--not-exported",
        action="store_false",
        dest="exported",
        help="do not export the main ability",
    )
    create.add_argument(
        "--no-home-screen",
        action="store_false",
        dest="home_screen",
        help="omit the home-screen launch skill",
    )
    create.add_argument(
        "--overwrite",
        action="store_true",
        help="replace generated paths in a non-empty destination without deleting other files",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)

    if arguments.command == "list":
        for template in list_templates():
            print(f"{template.name}\t{template.description}")
        return 0

    try:
        config = ProjectConfig(
            project_name=arguments.project_name,
            bundle_name=arguments.bundle_name,
            module_name=arguments.module_name,
            ability_name=arguments.ability_name,
            cangjie_package=arguments.cangjie_package,
            view_name=arguments.view_name,
            backup_ability_name=arguments.backup_ability_name,
            vendor=arguments.vendor,
            target_sdk_version=arguments.target_sdk_version,
            compatible_sdk_version=arguments.compatible_sdk_version,
            model_version=arguments.model_version,
            cjc_version=arguments.cjc_version,
            app_version_code=arguments.app_version_code,
            app_version_name=arguments.app_version_name,
            app_build_version=arguments.app_build_version,
            device_types=tuple(arguments.device_types or ("phone",)),
            installation_free=arguments.installation_free,
            exported=arguments.exported,
            home_screen=arguments.home_screen,
            host_platform=arguments.host_platform,
        )
        result = scaffold(
            arguments.template,
            arguments.destination,
            config,
            overwrite=arguments.overwrite,
        )
    except ScaffoldError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(f"Created {result.template.display_name} at {result.destination}")
    return 0
