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
    # SUPPRESS is used for defaults because default values for ProjectConfig members are
    # sorted by the class itself
    create.add_argument("--module-name", default=argparse.SUPPRESS)
    create.add_argument("--ability-name", default=argparse.SUPPRESS)
    create.add_argument(
        "--cangjie-package",
        default=argparse.SUPPRESS,
        help="Cangjie package name (default: ohos_app_cangjie_<module-name>)",
    )
    create.add_argument(
        "--view-name",
        default=argparse.SUPPRESS,
        help="Cangjie Empty view class",
    )
    create.add_argument(
        "--backup-ability-name",
        default=argparse.SUPPRESS,
        help="Hybrid template backup extension class",
    )
    create.add_argument("--vendor", default=argparse.SUPPRESS)
    create.add_argument("--target-sdk-version", default=argparse.SUPPRESS)
    create.add_argument("--compatible-sdk-version", default=argparse.SUPPRESS)
    create.add_argument("--model-version", default=argparse.SUPPRESS)
    create.add_argument("--cjc-version", default=argparse.SUPPRESS)
    create.add_argument("--app-version-code", default=argparse.SUPPRESS, type=int)
    create.add_argument("--app-version-name", default=argparse.SUPPRESS)
    create.add_argument("--app-build-version", default=argparse.SUPPRESS)
    create.add_argument(
        "--device-type",
        action="append",
        dest="device_types",
        default=argparse.SUPPRESS,
        help="target device type; repeat for multiple values (default: phone)",
    )
    create.add_argument(
        "--host-platform",
        choices=[item.value for item in HostPlatform],
        default=argparse.SUPPRESS,
    )
    create.add_argument(
        "--installation-free",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    create.add_argument(
        "--not-exported",
        action="store_false",
        dest="exported",
        default=argparse.SUPPRESS,
        help="do not export the main ability",
    )
    create.add_argument(
        "--no-home-screen",
        action="store_false",
        dest="home_screen",
        default=argparse.SUPPRESS,
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
        config_values = {
            name: value
            for name, value in vars(arguments).items()
            if name not in {"command", "template", "destination", "overwrite"}
        }
        if "device_types" in config_values:
            config_values["device_types"] = tuple(config_values["device_types"])
        config = ProjectConfig(**config_values)
        scaffold(
            arguments.template,
            arguments.destination,
            config,
            overwrite=arguments.overwrite,
        )
    except ScaffoldError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(f"Created {arguments.template} at {arguments.destination}")
    return 0
