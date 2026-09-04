from __future__ import annotations

from pathlib import Path

from harmonyos_scaffolder.cli import main


def test_cli_lists_templates(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["list"]) == 0

    output = capsys.readouterr().out
    assert "cangjie-empty-ability" in output
    assert "hybrid-cangjie-ability" in output


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
        ]
    )

    assert exit_code == 0
    assert "Wrote 35 files" in capsys.readouterr().out
    assert (destination / "entry/src/main/cangjie/index.cj").is_file()


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
