"""
Error types raised by toonpy.

This module defines custom exception classes for TOON parsing and validation
errors, providing detailed location information (line and column numbers)
for better error reporting.
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
    """Base class for all toonpy exceptions.
    
    All exceptions raised by toonpy inherit from this class, allowing
    users to catch all toonpy-related errors with a single except clause.
    """


class ToonSyntaxError(ToonError):
    """Raised when TOON input does not conform to the grammar.
    
    This exception is raised when the parser encounters syntax that
    violates the TOON SPEC v2.0 grammar. It includes location information
    (line and column numbers) to help identify the problematic code.
    
    Attributes:
        message: Error message describing the syntax violation
        line: Line number where the error occurred (1-indexed, or None)
        column: Column number where the error occurred (1-indexed, or None)
        
    Example:
        >>> try:
        ...     from_toon('invalid: syntax: here')
        ... except ToonSyntaxError as e:
        ...     print(f"Error at line {e.line}: {e.message}")
    """

    def __init__(self, message: str, line: int | None = None, column: int | None = None) -> None:
        """Initialize a ToonSyntaxError.
        
        Args:
            message: Error message describing the syntax violation
            line: Line number where error occurred (1-indexed, or None)
            column: Column number where error occurred (1-indexed, or None)
        """
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
    """Represents a validation finding emitted by :func:`validate_toon`.
    
    This class represents a single validation error or warning found
    during TOON validation. It includes location information and severity
    level for use in linting tools or validation reports.
    
    Attributes:
        message: Description of the validation issue
        line: Line number where issue occurred (1-indexed, or None)
        column: Column number where issue occurred (1-indexed, or None)
        severity: Severity level - "error" or "warning" (default: "error")
        
    Example:
        >>> valid, errors = validate_toon('invalid syntax')
        >>> if not valid:
        ...     for err in errors:
        ...         print(err)
        [error] line 1: Invalid syntax
    """

    message: str
    line: int | None
    column: int | None
    severity: Literal["error", "warning"] = "error"

    def __str__(self) -> str:
        """Format the validation error as a string.
        
        Returns:
            Formatted string with severity, location, and message
        """
        location = ""
        if self.line is not None:
            location = f"line {self.line}"
            if self.column is not None:
                location += f", column {self.column}"
        return f"[{self.severity}] {location}: {self.message}"

