# HarmonyOS Project Scaffolder

`harmonyos-project-scaffolder` is an npm library for creating standalone
HarmonyOS projects from the two bundled Cangjie templates. It has no CLI.

The templates are rendered with strict missing-variable checks. Dynamic path
names are rendered, `.j2` is removed from rendered text files, binary assets
are copied unchanged, and intentional empty directories are retained.

## Templates

| Template | Output |
| --- | --- |
| `cangjie-empty-ability` | Stage-model application with a Cangjie `UIAbility`, ability stage, ArkUI view, local tests, and device tests. |
| `hybrid-cangjie-ability` | Stage-model ArkTS application whose page calls a Cangjie shared library, including type declarations and a backup extension. |

Both templates produce a complete application root rather than a module
overlay.

## Installation

```console
npm install harmonyos-project-scaffolder
```

Node.js 18 or newer is required.

## Usage

`scaffold` takes a template name, the exact destination directory, and project
options. It returns a promise.

```js
import {
  HostPlatform,
  scaffold,
} from "harmonyos-project-scaffolder";

await scaffold("cangjie-empty-ability", "./MyApplication", {
  projectName: "MyApplication",
  bundleName: "com.example.myapplication",
  permissions: [
    "ohos.permission.INTERNET",
    "ohos.permission.PRIVACY_WINDOW",
  ],
  hostPlatform: HostPlatform.MACOS_ARM64,
});
```

The destination is the generated project root; the project name is not
appended. A missing or empty destination is accepted. A non-empty destination
is rejected unless `overwrite: true` is supplied. Overwrite mode replaces
generated paths but does not delete unrelated files.

`listTemplates()` provides programmatic template discovery:

```js
import { listTemplates } from "harmonyos-project-scaffolder";

for (const template of listTemplates()) {
  console.log(template.name, template.description);
}
```

## Options

| Option | Required | Default | Meaning |
| --- | --- | --- | --- |
| `projectName` | Yes | - | Application display name written to `$string:app_name`. |
| `bundleName` | Yes | - | Dot-separated HarmonyOS bundle identifier. |
| `moduleName` | No | `entry` | Module identifier and output directory. |
| `abilityName` | No | `EntryAbility` | Main ability class and descriptor name. |
| `cangjiePackage` | No | `ohos_app_cangjie_<module>` | Cangjie package and shared-library base name. |
| `viewName` | No | `EntryView` | Root view class used by the Cangjie Empty template. |
| `backupAbilityName` | No | `EntryBackupAbility` | Backup extension class used by the Hybrid template. |
| `vendor` | No | `example` | Value written to `AppScope/app.json5`. |
| `targetSdkVersion` | No | `6.1.1(24)` | Target SDK in `major.minor.patch(api)` format. |
| `compatibleSdkVersion` | No | `6.1.1(24)` | Minimum compatible SDK in the same format. |
| `modelVersion` | No | `6.1.1` | Hvigor and root OHPM model version. |
| `cjcVersion` | No | `1.1.3` | Cangjie compiler version in each `cjpm.toml`. |
| `appVersionCode` | No | `1000000` | Positive numeric application version code. |
| `appVersionName` | No | `1.0.0` | Human-readable application version. |
| `appBuildVersion` | No | `1` | Application build version string. |
| `deviceTypes` | No | `["phone"]` | Array containing `phone`, `tablet`, or both. |
| `permissions` | No | `[]` | HarmonyOS permission names emitted into `requestPermissions`. |
| `hostPlatform` | No | `auto` | `auto`, `macos-arm64`, or `windows-x64`; controls CJPM host sections. |
| `installationFree` | No | `false` | Sets the module's `installationFree` field. |
| `exported` | No | `true` | Controls whether the main ability is exported. |
| `homeScreen` | No | `true` | Controls whether the launcher home-screen skill is emitted. |
| `overwrite` | No | `false` | Allows generated files to be merged into a non-empty directory. |

The compatible SDK must use API 22 or newer and cannot exceed the target SDK.
The source templates only define build-host dependencies for Windows x64 and
Apple Silicon macOS. On other systems, set `hostPlatform` explicitly to the
platform that will build the generated project.

Permissions must have the form `ohos.permission.PERMISSION_NAME`. This option
only emits name-based declarations. User-authorized permissions can also need
localized reason, use-scene metadata, and runtime authorization, which remain
the consuming application's responsibility.

The package includes TypeScript declarations for all exports and options.
Expected errors derive from `ScaffoldError`; more specific exported classes are
`ConfigurationError`, `TemplateNotFoundError`, and `DestinationError`.

## Removed Python Features

The Python command-line interface was intentionally not ported. Installed
DevEco SDK permission-catalog discovery (`list-permissions` / `list_permissions`)
was also removed because it only supported that interactive CLI workflow.
Callers provide the permission list directly through `permissions`.

## Development

```console
npm install
npm test
npm run check
npm pack --dry-run
```

## License And Template Attribution

This project is licensed under the Apache License 2.0. The bundled project
templates are modified derivatives of the Cangjie DevEco Studio plugin 6.1.1.280
templates, including Cangjie Empty Ability and Hybrid Cangjie Ability. See
[`NOTICE`](NOTICE) for attribution and the upstream Runtime Library Exception.
