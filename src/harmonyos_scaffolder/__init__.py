"""Public API for scaffolding HarmonyOS projects."""

from .config import HostPlatform, ProjectConfig
from .errors import (
    ConfigurationError,
    DestinationError,
    ScaffoldError,
    TemplateNotFoundError,
)
from .scaffolder import TemplateInfo, list_templates, scaffold

__all__ = [
    "ConfigurationError",
    "DestinationError",
    "HostPlatform",
    "ProjectConfig",
    "ScaffoldError",
    "TemplateInfo",
    "TemplateNotFoundError",
    "list_templates",
    "scaffold",
]
