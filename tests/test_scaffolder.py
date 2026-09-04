from __future__ import annotations

import json
from pathlib import Path

import pytest

from harmonyos_scaffolder import (
    DestinationError,
    HostPlatform,
    ProjectConfig,
    TemplateNotFoundError,
    list_templates,
    scaffold,
)


def config(**changes: object) -> ProjectConfig:
    values: dict[str, object] = {
        "project_name": "MyApplication",
        "bundle_name": "com.example.myapplication",
        "host_platform": HostPlatform.MACOS_ARM64,
    }
    values.update(changes)
    return ProjectConfig(**values)  # type: ignore[arg-type]


def test_lists_bundled_templates() -> None:
    assert [item.name for item in list_templates()] == [
        "cangjie-empty-ability",
        "hybrid-cangjie-ability",
    ]


def test_scaffolds_reference_empty_ability_shape(tmp_path: Path) -> None:
    destination = tmp_path / "MyApplication"

    result = scaffold("cangjie-empty-ability", destination, config())

    assert result.destination == destination
    assert len(result.files) == 35
    assert (destination / "entry/libs").is_dir()
    assert (destination / "entry/src/main/resources/rawfile").is_dir()
    assert not list(destination.rglob("*.j2"))
    assert not list(destination.rglob("*.ftl"))
    assert not list(destination.rglob(".scaffold-keep"))

    app = json.loads((destination / "AppScope/app.json5").read_text())
    assert app["app"]["bundleName"] == "com.example.myapplication"

    module = json.loads((destination / "entry/src/main/module.json5").read_text())
    assert module == {
        "module": {
            "name": "entry",
            "type": "entry",
            "description": "$string:module_desc",
            "mainElement": "EntryAbility",
            "deviceTypes": ["phone"],
            "deliveryWithInstall": True,
            "installationFree": False,
            "srcEntry": "ohos_app_cangjie_entry.MyAbilityStage",
            "abilities": [
                {
                    "name": "EntryAbility",
                    "srcEntry": "ohos_app_cangjie_entry.MainAbility",
                    "description": "$string:EntryAbility_desc",
                    "icon": "$media:layered_image",
                    "label": "$string:EntryAbility_label",
                    "startWindowIcon": "$media:startIcon",
                    "startWindowBackground": "$color:start_window_background",
                    "exported": True,
                    "skills": [
                        {
                            "entities": ["entity.system.home"],
                            "actions": ["action.system.home"],
                        }
                    ],
                }
            ],
        }
    }

    index_source = (destination / "entry/src/main/cangjie/index.cj").read_text()
    assert "package ohos_app_cangjie_entry" in index_source
    assert "import kit.ArkUI.Column" in index_source
    assert "class EntryView" in index_source

    manifest = (destination / "entry/cjpm.toml").read_text()
    assert "${COMPILE_CONDITION_ENTRY}" in manifest
    assert "${DEVECO_OH_NATIVE_HOME}" in manifest
    assert "[target.aarch64-apple-darwin]" in manifest
    assert "x86_64-w64-mingw32" not in manifest

    test_engine = (
        destination / "entry/src/ohosTest/cangjie/unittest_support/unittest_engine.cj"
    ).read_text()
    assert "${coveragePath}" in test_engine
    assert "import kit.TestKit.TestRunner" in test_engine


def test_scaffolds_hybrid_project_with_dynamic_paths(tmp_path: Path) -> None:
    destination = tmp_path / "Hybrid"
    project_config = config(
        project_name="Hybrid",
        bundle_name="org.example.hybrid",
        module_name="sample",
        ability_name="SampleAbility",
        cangjie_package="sample_cangjie",
        backup_ability_name="SampleBackup",
        device_types=("phone", "tablet"),
        host_platform=HostPlatform.WINDOWS_X64,
    )

    result = scaffold("hybrid-cangjie-ability", destination, project_config)

    assert len(result.files) == 31
    assert (destination / "sample/src/main/ets/sampleability/SampleAbility.ets").is_file()
    assert (destination / "sample/src/main/ets/samplebackup/SampleBackup.ets").is_file()
    assert (destination / "sample/src/main/cangjie/types/libsample_cangjie/Index.d.ts").is_file()

    module = json.loads((destination / "sample/src/main/module.json5").read_text())
    assert module["module"]["deviceTypes"] == ["phone", "tablet"]
    assert module["module"]["abilities"][0]["srcEntry"] == ("./ets/sampleability/SampleAbility.ets")
    assert module["module"]["extensionAbilities"][0]["name"] == "SampleBackup"

    package = json.loads((destination / "sample/oh-package.json5").read_text())
    assert package["dependencies"] == {
        "libsample_cangjie.so": "file:src/main/cangjie/types/libsample_cangjie"
    }

    page = (destination / "sample/src/main/ets/pages/Index.ets").read_text()
    assert "import { testCJ } from 'libsample_cangjie.so';" in page
    assert "this.message = testCJ('Cangjie');" in page

    manifest = (destination / "sample/cjpm.toml").read_text()
    assert "[target.x86_64-w64-mingw32.bin-dependencies]" in manifest
    assert "[target.aarch64-apple-darwin]" not in manifest


def test_renders_distinct_target_and_compatible_sdks(tmp_path: Path) -> None:
    destination = tmp_path / "SdkVersions"

    scaffold(
        "cangjie-empty-ability",
        destination,
        config(
            target_sdk_version="6.1.1(24)",
            compatible_sdk_version="6.0.2(22)",
        ),
    )

    build_profile = (destination / "build-profile.json5").read_text()
    index_source = (destination / "entry/src/main/cangjie/index.cj").read_text()
    assert '"targetSdkVersion": "6.1.1(24)"' in build_profile
    assert '"compatibleSdkVersion": "6.0.2(22)"' in build_profile
    assert "import kit.ArkUI.Column" in index_source


def test_refuses_non_empty_destination_and_overwrite_preserves_unrelated_file(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "existing"
    destination.mkdir()
    marker = destination / "user-file.txt"
    marker.write_text("keep me")

    with pytest.raises(DestinationError, match="not empty"):
        scaffold("cangjie-empty-ability", destination, config())

    scaffold("cangjie-empty-ability", destination, config(), overwrite=True)

    assert marker.read_text() == "keep me"
    assert (destination / "entry/src/main/cangjie/index.cj").is_file()


def test_rejects_unknown_template(tmp_path: Path) -> None:
    with pytest.raises(TemplateNotFoundError, match="unknown template"):
        scaffold("missing", tmp_path / "output", config())
