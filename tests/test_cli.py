from __future__ import annotations

import json
from pathlib import Path

import pytest

from harmonyos_scaffolder.cli import main
from harmonyos_scaffolder.permissions import PermissionInfo


def test_cli_lists_templates(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["list"]) == 0

    output = capsys.readouterr().out
    assert "cangjie-empty-ability" in output
    assert "hybrid-cangjie-ability" in output


def test_cli_lists_normal_app_permissions(capsys, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "harmonyos_scaffolder.cli.list_permissions",
        lambda: (
            PermissionInfo("ohos.permission.CAMERA", "user_grant", "normal", 9, ""),
            PermissionInfo(
                "ohos.permission.SYSTEM_FLOAT_WINDOW",
                "system_grant",
                "system_basic",
                7,
                "",
            ),
        ),
    )

    assert main(["list-permissions"]) == 0

    output = capsys.readouterr().out
    assert "ohos.permission.CAMERA\tuser_grant, normal, API 9" in output
    assert (
        "ohos.permission.SYSTEM_FLOAT_WINDOW\tsystem_grant, system_basic, API 7, ACL required"
        in output
    )


def test_cli_creates_project(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    destination = tmp_path / "Demo"

    exit_code = main(
        [
            "create",
            "cangjie-empty-ability",
            str(destination),
            "--project-name",
            "Demo",
            "--bundle-name",
            "com.example.demo",
            "--host-platform",
            "macos-arm64",
            "--permission",
            "ohos.permission.INTERNET",
            "--permission",
            "ohos.permission.PRIVACY_WINDOW",
        ]
    )

    assert exit_code == 0
    assert "Created cangjie-empty-ability" in capsys.readouterr().out
    assert (destination / "entry/src/main/cangjie/index.cj").is_file()
    module = json.loads((destination / "entry/src/main/module.json5").read_text())
    assert module["module"]["requestPermissions"] == [
        {"name": "ohos.permission.INTERNET"},
        {"name": "ohos.permission.PRIVACY_WINDOW"},
    ]


def test_cli_reports_configuration_error(capsys) -> None:  # type: ignore[no-untyped-def]
    exit_code = main(
        [
            "create",
            "cangjie-empty-ability",
            "unused",
            "--project-name",
            "Demo",
            "--bundle-name",
            "invalid",
        ]
    )

    assert exit_code == 2
    assert "error: bundle_name" in capsys.readouterr().err
