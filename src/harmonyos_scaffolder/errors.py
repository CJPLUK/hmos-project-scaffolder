"""Exceptions raised by the scaffolder."""


class ScaffoldError(Exception):
    """Base class for expected scaffolding errors."""


class ConfigurationError(ScaffoldError, ValueError):
    """A project configuration value is invalid."""


class TemplateNotFoundError(ScaffoldError, ValueError):
    """The requested template does not exist."""


class DestinationError(ScaffoldError, OSError):
    """The destination cannot be safely scaffolded."""
