"""Template discovery and filesystem rendering."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError

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
) -> None:
    """Render ``template`` into the exact project root at ``destination``.

    Existing non-empty directories are rejected by default. With ``overwrite=True``,
    generated files are replaced while unrelated destination files are retained.
    """

    if template not in _TEMPLATES:
        choices = ", ".join(_TEMPLATES)
        raise TemplateNotFoundError(
            f"unknown template {template!r}; available templates: {choices}"
        )

    destination_path = Path(destination).expanduser()
    # Validate the destination path
    if destination_path.exists() and not destination_path.is_dir():
        raise DestinationError(f"destination is not a directory: {destination_path}")
    if destination_path.exists() and not overwrite and any(destination_path.iterdir()):
        raise DestinationError(
            f"destination is not empty: {destination_path}; pass overwrite=True to "
            "merge generated files"
        )

    context = config.template_context()
    root = _SOURCE_TEMPLATE_ROOT.joinpath(template, "project")
    environment = Environment(
        autoescape=False,
        keep_trailing_newline=True,
        lstrip_blocks=True,
        trim_blocks=True,
        loader=FileSystemLoader(root),
        undefined=StrictUndefined,
    )
    environment.filters["json"] = lambda value: json.dumps(value, ensure_ascii=False)

    try:
        _render_tree(
            root,
            destination=destination_path,
            environment=environment,
            context=context,
        )
    except (TemplateError, UnicodeDecodeError) as error:
        raise ScaffoldError(f"failed to render {template!r}: {error}") from error


def _render_tree(
    root: Any,
    *,
    destination: Path,
    environment: Environment,
    context: dict[str, Any],
) -> None:
    destination.mkdir(parents=True, exist_ok=True)

    def render_name(source_name: str) -> str:
        rendered_name = environment.from_string(source_name).render(context)
        _validate_path_segment(rendered_name, source_name=source_name)
        return rendered_name

    for current_root, dir_names, file_names in os.walk(root, topdown=True):
        relative_root = PurePosixPath(Path(current_root).relative_to(root).as_posix())
        rendered_root = PurePosixPath(*(render_name(part) for part in relative_root.parts))
        rendered_children: set[PurePosixPath] = set()

        for name in dir_names:
            output_path = rendered_root / render_name(name)
            if output_path in rendered_children:
                raise ScaffoldError(f"template renders duplicate path: {output_path}")
            rendered_children.add(output_path)
            destination.joinpath(*output_path.parts).mkdir(parents=True, exist_ok=True)

        for name in (name for name in file_names if name != _KEEP_FILE):
            child = Path(current_root) / name
            rendered_relative = rendered_root / render_name(name)

            if rendered_relative.name.endswith(_TEMPLATE_SUFFIX):
                output_path = rendered_relative.with_name(
                    rendered_relative.name[: -len(_TEMPLATE_SUFFIX)]
                )
                template_name = (relative_root / name).as_posix()
            else:
                output_path = rendered_relative
                template_name = None
            if output_path in rendered_children:
                raise ScaffoldError(f"template renders duplicate path: {output_path}")
            rendered_children.add(output_path)
            output = destination.joinpath(*output_path.parts)
            if output.exists() and output.is_dir():
                raise DestinationError(f"cannot replace directory with generated file: {output}")
            if template_name is None:
                shutil.copyfile(child, output)
            else:
                with output.open("wb", encoding="utf-8") as stream:
                    environment.get_template(template_name).stream(context).dump(stream)

def _validate_path_segment(value: str, *, source_name: str) -> None:
    if not value or value in {".", ".."} or "/" in value or "\\" in value or "\0" in value:
        raise ScaffoldError(
            f"template path segment {source_name!r} rendered to unsafe value {value!r}"
        )
