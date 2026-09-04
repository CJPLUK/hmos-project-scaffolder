"""Template discovery and filesystem rendering."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateError

from .config import ProjectConfig
from .errors import DestinationError, ScaffoldError, TemplateNotFoundError

_TEMPLATE_SUFFIX = ".j2"
_KEEP_FILE = ".scaffold-keep"
_SOURCE_TEMPLATE_ROOT = Path(__file__).resolve().parent / "templates"


@dataclass(frozen=True, slots=True)
class TemplateInfo:
    """Metadata describing a bundled project template."""

    name: str
    display_name: str
    description: str


@dataclass(frozen=True, slots=True)
class ScaffoldResult:
    """The files and directories created by one scaffold operation."""

    template: TemplateInfo
    destination: Path
    files: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class _RenderedFile:
    path: PurePosixPath
    content: bytes


_TEMPLATES = {
    "cangjie-empty-ability": TemplateInfo(
        name="cangjie-empty-ability",
        display_name="Cangjie Empty Ability",
        description="A stage-model HarmonyOS app whose ability and ArkUI view use Cangjie.",
    ),
    "hybrid-cangjie-ability": TemplateInfo(
        name="hybrid-cangjie-ability",
        display_name="Hybrid Cangjie Ability",
        description="A stage-model ArkTS ability that calls a Cangjie shared library.",
    ),
}


def list_templates() -> tuple[TemplateInfo, ...]:
    """Return the bundled templates in stable CLI display order."""

    return tuple(_TEMPLATES.values())


def scaffold(
    template: str,
    destination: str | Path,
    config: ProjectConfig,
    *,
    overwrite: bool = False,
) -> ScaffoldResult:
    """Render ``template`` into the exact project root at ``destination``.

    Existing non-empty directories are rejected by default. With ``overwrite=True``,
    generated files are replaced while unrelated destination files are retained.
    """

    try:
        template_info = _TEMPLATES[template]
    except KeyError as error:
        choices = ", ".join(_TEMPLATES)
        raise TemplateNotFoundError(
            f"unknown template {template!r}; available templates: {choices}"
        ) from error

    destination_path = Path(destination).expanduser()
    _validate_destination(destination_path, overwrite=overwrite)

    environment = _create_environment()
    context = config.template_context()
    root = _template_root().joinpath(template, "project")
    try:
        rendered_files, rendered_directories = _render_tree(
            root,
            environment=environment,
            context=context,
        )
    except (TemplateError, UnicodeDecodeError) as error:
        raise ScaffoldError(f"failed to render {template!r}: {error}") from error

    for directory in sorted(rendered_directories, key=lambda item: (len(item.parts), item.parts)):
        (destination_path / Path(*directory.parts)).mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for rendered_file in sorted(rendered_files, key=lambda item: item.path.parts):
        output = destination_path / Path(*rendered_file.path.parts)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists() and output.is_dir():
            raise DestinationError(f"cannot replace directory with generated file: {output}")
        output.write_bytes(rendered_file.content)
        written.append(output)

    return ScaffoldResult(
        template=template_info,
        destination=destination_path,
        files=tuple(written),
    )


def _create_environment() -> Environment:
    environment = Environment(
        autoescape=False,
        keep_trailing_newline=True,
        lstrip_blocks=True,
        trim_blocks=True,
        undefined=StrictUndefined,
    )
    environment.filters["json"] = lambda value: json.dumps(value, ensure_ascii=False)
    return environment


def _template_root() -> Any:
    if _SOURCE_TEMPLATE_ROOT.is_dir():
        return _SOURCE_TEMPLATE_ROOT
    raise ScaffoldError("bundled project templates could not be located")


def _validate_destination(destination: Path, *, overwrite: bool) -> None:
    if destination.exists() and not destination.is_dir():
        raise DestinationError(f"destination is not a directory: {destination}")
    if destination.exists() and not overwrite and next(destination.iterdir(), None) is not None:
        raise DestinationError(
            f"destination is not empty: {destination}; pass overwrite=True to merge generated files"
        )


def _render_tree(
    root: Any,
    *,
    environment: Environment,
    context: dict[str, Any],
) -> tuple[list[_RenderedFile], set[PurePosixPath]]:
    files: list[_RenderedFile] = []
    directories: set[PurePosixPath] = {PurePosixPath()}

    for child in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).parts):
        source_relative = PurePosixPath(child.relative_to(root).as_posix())
        rendered_parts = []
        for source_name in source_relative.parts:
            rendered_name = environment.from_string(source_name).render(context)
            _validate_path_segment(rendered_name, source_name=source_name)
            rendered_parts.append(rendered_name)
        rendered_relative = PurePosixPath(*rendered_parts)

        if child.is_dir():
            directories.add(rendered_relative)
            continue
        if rendered_relative.name == _KEEP_FILE:
            directories.add(rendered_relative.parent)
            continue
        if rendered_relative.name.endswith(_TEMPLATE_SUFFIX):
            output_path = rendered_relative.with_name(
                rendered_relative.name[: -len(_TEMPLATE_SUFFIX)]
            )
            source = child.read_text(encoding="utf-8")
            content = environment.from_string(source).render(context).encode("utf-8")
        else:
            output_path = rendered_relative
            content = child.read_bytes()
        if any(existing.path == output_path for existing in files):
            raise ScaffoldError(f"template renders duplicate path: {output_path}")
        files.append(_RenderedFile(output_path, content))

    return files, directories


def _validate_path_segment(value: str, *, source_name: str) -> None:
    if not value or value in {".", ".."} or "/" in value or "\\" in value or "\0" in value:
        raise ScaffoldError(
            f"template path segment {source_name!r} rendered to unsafe value {value!r}"
        )
