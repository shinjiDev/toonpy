"""
Error types raised by toonpy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = [
    "ToonError",
    "ToonSyntaxError",
    "ValidationError",
]


class ToonError(Exception):
    """Base class for all toonpy exceptions."""


class ToonSyntaxError(ToonError):
    """Raised when TOON input does not conform to the grammar."""

    def __init__(self, message: str, line: int | None = None, column: int | None = None) -> None:
        prefix = ""
        if line is not None and column is not None:
            prefix = f"(line {line}, column {column}) "
        elif line is not None:
            prefix = f"(line {line}) "
        super().__init__(f"{prefix}{message}")
        self.message = message
        self.line = line
        self.column = column


@dataclass(slots=True)
class ValidationError:
    """Represents a validation finding emitted by :func:`validate_toon`."""

    message: str
    line: int | None
    column: int | None
    severity: Literal["error", "warning"] = "error"

    def __str__(self) -> str:
        location = ""
        if self.line is not None:
            location = f"line {self.line}"
            if self.column is not None:
                location += f", column {self.column}"
        return f"[{self.severity}] {location}: {self.message}"

