# HarmonyOS Project Scaffolder

`harmonyos-project-scaffolder` is a pip-installable Python library and CLI for
creating standalone HarmonyOS projects from the Cangjie templates in this
repository.

The original FreeMarker recipes depended on DevEco Studio merge commands and
files outside this repository. They have been converted to complete Jinja
project trees. A template therefore looks nearly identical to its generated
project: dynamic text files only add a `.j2` suffix, dynamic directory and file
names use Jinja expressions, and binary assets are copied unchanged.

Jinja is used instead of a standard-library substitute because these templates
need strict missing-variable errors, conditionals, and templated path names.
Implementing those features locally would create a small, less-tested template
engine. Jinja also does not conflict with the `${...}` interpolation used by
Cangjie and `cjpm.toml`, so those expressions remain readable and unchanged.

## Templates

| Template | Output |
| --- | --- |
| `cangjie-empty-ability` | Stage-model application with a Cangjie `UIAbility`, ability stage, ArkUI view, local tests, and device tests. |
| `hybrid-cangjie-ability` | Stage-model ArkTS application whose page calls a Cangjie shared library, including type declarations and a backup extension. |

Both templates produce a complete application root, not a module overlay. The
generated shell is based on `example/MyApplication`; generated caches, lock
files, IDE metadata, local SDK paths, and compiler-generated Cangjie bridge
files are deliberately excluded.

The supported scope follows the templates' catalog metadata: Application,
Stage Model, and traditional Cangjie or ArkTS development. Dormant inherited
FreeMarker branches for FA Model, JS/HML, Atomic Service, and Super Visual were
not carried into the standalone generator because they were not advertised by
either template and several produced incomplete or non-hybrid output.

## Installation - End User

To install the CLI in an isolated environment with pipx (FUTURE add URL here instead when repo public):

```console
pipx install .
```

## Installation - Dev

Create the development environment and lock dependencies:

```console
uv sync
```

Run the CLI from the checkout:

```console
uv run harmonyos-scaffold list
```

Install the command as a tool:

```console
uv tool install .
```

The project is also installable with pip:

```console
python -m pip install .
```

## CLI

List the bundled templates:

```console
harmonyos-scaffold list
```

Create the same project shape and default values as the reference Cangjie Empty
Ability project:

```console
harmonyos-scaffold create cangjie-empty-ability ./MyApplication \
  --project-name MyApplication \
  --bundle-name com.example.myapplication
```

Create a hybrid project with explicit identifiers:

```console
harmonyos-scaffold create hybrid-cangjie-ability ./HybridApplication \
  --project-name HybridApplication \
  --bundle-name com.example.hybrid \
  --module-name entry \
  --ability-name EntryAbility \
  --cangjie-package ohos_app_cangjie_entry \
  --backup-ability-name EntryBackupAbility
```

`destination` is the exact project root. The CLI does not append the project
name. A missing or empty destination is accepted. A non-empty destination is
rejected unless `--overwrite` is supplied; overwrite mode replaces generated
paths but never deletes unrelated files.

### Create parameters

| Argument | Required | Default | Meaning |
| --- | --- | --- | --- |
| `template` | Yes | - | `cangjie-empty-ability` or `hybrid-cangjie-ability`. |
| `destination` | Yes | - | Exact directory that becomes the HarmonyOS project root. |
| `--project-name` | Yes | - | Application display name written to `$string:app_name`. |
| `--bundle-name` | Yes | - | Dot-separated HarmonyOS bundle identifier, such as `com.example.app`. |
| `--module-name` | No | `entry` | Module identifier and output directory. |
| `--ability-name` | No | `EntryAbility` | Main ability class and descriptor name. |
| `--cangjie-package` | No | `ohos_app_cangjie_<module>` | Cangjie package and shared-library base name. |
| `--view-name` | No | `EntryView` | Root view class used by the Cangjie Empty template. |
| `--backup-ability-name` | No | `EntryBackupAbility` | Backup extension class used by the Hybrid template. |
| `--vendor` | No | `example` | Value written to `AppScope/app.json5`. |
| `--target-sdk-version` | No | `6.1.1(24)` | Target SDK in `major.minor.patch(api)` format. |
| `--compatible-sdk-version` | No | `6.1.1(24)` | Minimum compatible SDK in `major.minor.patch(api)` format. |
| `--model-version` | No | `6.1.1` | Hvigor and root OHPM model version. |
| `--cjc-version` | No | `1.1.3` | Cangjie compiler version in each `cjpm.toml`. |
| `--app-version-code` | No | `1000000` | Positive numeric application version code. |
| `--app-version-name` | No | `1.0.0` | Human-readable application version. |
| `--app-build-version` | No | `1` | Application build version string. |
| `--device-type` | No | `phone` | `phone` or `tablet`; repeat the option to emit both. |
| `--permission` | No | - | HarmonyOS permission declared in the module manifest; repeat the option for multiple permissions. |
| `--host-platform` | No | `auto` | `auto`, `macos-arm64`, or `windows-x64`; controls the host section in CJPM manifests. |
| `--installation-free` | No | Off | Set the module's `installationFree` field. |
| `--not-exported` | No | Off | Omit `exported: true`; use with `--no-home-screen`. |
| `--no-home-screen` | No | Off | Omit the launcher home-screen skill. |
| `--overwrite` | No | Off | Replace generated files in an existing non-empty directory. |

The source templates only define build-host dependencies for Windows x64 and
Apple Silicon macOS. `auto` detects those hosts. On another system, pass the
platform of the machine that will build the generated project explicitly.

The compatible SDK must be API 22 or newer, matching the modern source used by
the reference project, and cannot exceed the target SDK. API 20-21 generation
is intentionally rejected because the legacy source and hybrid interop APIs in
the original recipes do not form a buildable standalone project.

`--permission` declares name-only `system_grant` permissions in
`<module>/src/main/module.json5`. User-authorized permissions also require a
localized reason, use-scene metadata, and contextual runtime authorization;
those feature-specific values are not generated by this option.

Use `harmonyos-scaffold list-permissions` to list the permissions available to
normal applications in the installed DevEco SDK. The command labels
`system_basic` permissions that require ACL approval and includes grant mode
and minimum API level.

The same CLI is available through the module entry point:

```console
python -m harmonyos_scaffolder create --help
```

## Python API

`ProjectConfig` validates identifiers and derives the Cangjie package when it
is omitted. Pass the template name, exact destination, and configuration to
`scaffold`:

```python
from pathlib import Path

from harmonyos_scaffolder import HostPlatform, ProjectConfig, scaffold

config = ProjectConfig(
    project_name="MyApplication",
    bundle_name="com.example.myapplication",
    module_name="entry",
    ability_name="EntryAbility",
    view_name="EntryView",
    target_sdk_version="6.1.1(24)",
    compatible_sdk_version="6.1.1(24)",
    cjc_version="1.1.3",
    permissions=("ohos.permission.INTERNET",),
    host_platform=HostPlatform.MACOS_ARM64,
)

scaffold(
    "cangjie-empty-ability",
    Path("MyApplication"),
    config,
)

print("Created", Path("MyApplication"))
```

Use `list_templates()` for programmatic discovery:

```python
from harmonyos_scaffolder import list_templates

for template in list_templates():
    print(template.name, template.description)
```

The API raises subclasses of `ScaffoldError` for expected failures:

| Exception | Cause |
| --- | --- |
| `ConfigurationError` | Invalid identifier, API combination, version, device type, or host platform. |
| `TemplateNotFoundError` | Unknown template name. |
| `DestinationError` | Unsafe or non-empty destination without overwrite permission. |

`scaffold(..., overwrite=True)` has the same non-destructive merge behavior as
the CLI flag.

## Template layout

The source trees are under the repository's top-level `templates/` directory:

```text
templates/
├── cangjie-empty-ability/project/
└── hybrid-cangjie-ability/project/
```

The build embeds this directory as package data, so the same templates are
available to pip-installed wheels. Editable/source checkouts load the top-level
directory directly.

Everything below `project/` maps directly to the generated root. For example:

```text
project/
├── AppScope/
├── build-profile.json5.j2
├── code-linter.json5
├── hvigor/
├── oh-package.json5.j2
└── {{ module_name }}/
    ├── cjpm.toml.j2
    └── src/main/
```

The renderer applies these rules:

1. Jinja renders every path segment, allowing `{{ module_name }}` and ability-specific paths.
2. UTF-8 files ending in `.j2` are rendered with `StrictUndefined`, then the suffix is removed.
3. Other files, including PNG assets, are copied byte-for-byte.
4. `.scaffold-keep` records an intentional empty directory and is not emitted.
5. Rendered path segments are checked for traversal and separators before writing.

`${...}` expressions in Cangjie and CJPM files are runtime/build placeholders,
not Jinja expressions, and remain intact in generated projects.

## Development

```console
uv run ruff check .
uv run pytest
uv build
```
