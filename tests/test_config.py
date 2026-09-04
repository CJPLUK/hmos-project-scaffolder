from __future__ import annotations

import pytest

from harmonyos_scaffolder import ConfigurationError, HostPlatform, ProjectConfig


def test_config_derives_cangjie_package_and_context() -> None:
    config = ProjectConfig(
        project_name="Demo",
        bundle_name="com.example.demo",
        module_name="feature",
        ability_name="DemoAbility",
        backup_ability_name="DemoBackupAbility",
        host_platform=HostPlatform.WINDOWS_X64,
        device_types=("phone", "tablet"),
        permissions=["ohos.permission.INTERNET"],  # type: ignore[arg-type]
    )

    context = config.template_context()

    assert config.cangjie_package == "ohos_app_cangjie_feature"
    assert context["module_name_upper"] == "FEATURE"
    assert context["ability_name_lower"] == "demoability"
    assert context["backup_ability_name_lower"] == "demobackupability"
    assert context["host_platform"] == "windows-x64"
    assert context["device_types"] == ("phone", "tablet")
    assert context["permissions"] == ("ohos.permission.INTERNET",)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"bundle_name": "not-a-bundle"}, "bundle_name"),
        ({"module_name": "../entry"}, "module_name"),
        ({"ability_name": "Bad/Ability"}, "ability_name"),
        ({"cangjie_package": "bad.package"}, "cangjie_package"),
        ({"compatible_sdk_version": "6.0.0(21)"}, "API 22 or newer"),
        ({"target_sdk_version": "6.0.2(22)"}, "greater than or equal"),
        ({"cjc_version": "1.2\\"}, "cjc_version"),
        ({"device_types": ()}, "device_types"),
        ({"device_types": "phone"}, "sequence"),
        ({"device_types": ("toaster",)}, "only supports"),
        ({"permissions": "ohos.permission.INTERNET"}, "sequence"),
        ({"permissions": ("ohos.permission.INTERNET", "ohos.permission.INTERNET")}, "duplicates"),
        ({"permissions": ("android.permission.INTERNET",)}, "ohos.permission"),
        ({"permissions": (1,)}, "ohos.permission"),
        ({"ability_name": "class"}, "ArkTS keyword"),
        ({"ability_name": "Foo", "backup_ability_name": "foo"}, "case-insensitively"),
        ({"exported": False}, "home_screen requires"),
    ],
)
def test_config_rejects_invalid_values(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "project_name": "Demo",
        "bundle_name": "com.example.demo",
        "host_platform": HostPlatform.MACOS_ARM64,
    }
    values.update(changes)

    with pytest.raises(ConfigurationError, match=message):
        ProjectConfig(**values)  # type: ignore[arg-type]
