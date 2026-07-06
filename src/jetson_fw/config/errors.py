"""Custom exceptions for configuration loading and validation."""

from __future__ import annotations


class BuildConfigError(Exception):
    """Base class for all config errors."""


class ConfigLoadError(BuildConfigError):
    """Raised when the YAML file cannot be loaded."""


class ConfigValidationError(BuildConfigError):
    """Raised when parsed YAML does not satisfy schema constraints."""

    def __init__(self, message: str, details: list[str] | None = None):
        super().__init__(message)
        self.details = details or []

    def __str__(self) -> str:
        if not self.details:
            return super().__str__()
        joined = "\n".join(f"- {detail}" for detail in self.details)
        return f"{super().__str__()}\n{joined}"
