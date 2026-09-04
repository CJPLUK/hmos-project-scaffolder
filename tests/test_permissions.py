from __future__ import annotations

import json
from pathlib import Path

from harmonyos_scaffolder import permissions


def test_lists_only_normal_app_permissions(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    catalog = tmp_path / "PermissionDefinitions.json"
    catalog.write_text(
        json.dumps(
            {
                "definePermissions": [
                    {
                        "name": "ohos.permission.SYSTEM_FLOAT_WINDOW",
                        "grantMode": "system_grant",
                        "availableLevel": "system_basic",
                        "availableType": "NORMAL",
                        "since": 7,
                        "deprecated": "",
                    },
                    {
                        "name": "ohos.permission.CAMERA",
                        "grantMode": "user_grant",
                        "availableLevel": "normal",
                        "availableType": "NORMAL",
                        "since": 9,
                        "deprecated": "",
                    },
                    {
                        "name": "ohos.permission.SYSTEM_ONLY",
                        "grantMode": "system_grant",
                        "availableLevel": "system_basic",
                        "availableType": "SYSTEM",
                        "since": 7,
                        "deprecated": "",
                    },
                ]
            }
        )
    )
    monkeypatch.setattr(permissions, "_find_catalog", lambda: catalog)

    assert permissions.list_permissions() == (
        permissions.PermissionInfo("ohos.permission.CAMERA", "user_grant", "normal", 9, ""),
        permissions.PermissionInfo(
            "ohos.permission.SYSTEM_FLOAT_WINDOW",
            "system_grant",
            "system_basic",
            7,
            "",
        ),
    )
