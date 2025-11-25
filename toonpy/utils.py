"""
Helper utilities shared between the parser and serializer.

This module provides utility functions for string formatting, number parsing,
tabular schema detection, and token counting used throughout toonpy.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from typing import List, Mapping, Sequence

SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_\-]*$")
NUMBER_RE = re.compile(r"""
    ^
    -?
    (?:
        0
        |
        [1-9][0-9]*
    )
    (?:
        \.[0-9]+
    )?
    (?:
        [eE][+-]?[0-9]+
    )?
    $
""", re.VERBOSE)

__all__ = [
    "TabularSchema",
    "escape_string",
    "format_key",
    "format_scalar",
    "guess_number",
    "is_safe_identifier",
    "split_escaped_row",
    "string_needs_quotes",
    "tabular_schema",
    "token_length",
]


@dataclass(slots=True)
class TabularSchema:
    """Schema information for tabular array format.
    
    Attributes:
        keys: Ordered list of field names for the table header
        savings: Estimated character/token savings from using tabular format
    """

    keys: List[str]
    savings: int


def is_safe_identifier(token: str) -> bool:
    """Check if a string is a safe unquoted identifier in TOON.
    
    Safe identifiers match the pattern: [A-Za-z_][A-Za-z0-9_-]*
    These can be used as keys or values without quotes in TOON.
    
    Args:
        token: String to check
        
    Returns:
        True if token is a safe identifier, False otherwise
        
    Example:
        >>> is_safe_identifier("name")
        True
        >>> is_safe_identifier("123abc")
        False
        >>> is_safe_identifier("my-key")
        True
    """
    return bool(SAFE_IDENTIFIER_RE.match(token))


def escape_string(value: str) -> str:
    r"""Escape a string for use in TOON format.
    
    Uses JSON escaping rules for full Unicode and control character support.
    Returns the escaped string without surrounding quotes.
    
    Args:
        value: String to escape
        
    Returns:
        Escaped string (without quotes)
        
    Example:
        >>> escape_string('Hello "World"')  # doctest: +SKIP
        'Hello \\"World\\"'
        >>> escape_string('Line 1\nLine 2')  # doctest: +SKIP
        'Line 1\\nLine 2'
    """
    # Delegate to json for full Unicode escape coverage, then strip quotes.
    return json.dumps(value)[1:-1]


def string_needs_quotes(value: str) -> bool:
    """Determine if a string value needs quotes in TOON format.
    
    Strings need quotes if they are empty, contain whitespace, or are not
    safe identifiers.
    
    Args:
        value: String to check
        
    Returns:
        True if quotes are required, False otherwise
        
    Example:
        >>> string_needs_quotes("name")
        False
        >>> string_needs_quotes("my name")
        True
        >>> string_needs_quotes("")
        True
    """
    # Optimization: Combined checks for better performance
    # Empty string check is fastest, do it first
    if not value:
        return True
    # is_safe_identifier already checks the pattern, includes whitespace check
    return not is_safe_identifier(value)


def format_key(key: str) -> str:
    """Format a dictionary key for TOON output.
    
    Returns the key as-is if it's a safe identifier, otherwise returns
    it as a JSON-quoted string.
    
    Args:
        key: Dictionary key to format
        
    Returns:
        Formatted key (unquoted if safe, quoted otherwise)
        
    Example:
        >>> format_key("name")
        'name'
        >>> format_key("my key")
        '"my key"'
    """
    if string_needs_quotes(key):
        return json.dumps(key)
    return key


def format_scalar(value: object) -> str:
    r"""Format a scalar value for TOON output.
    
    Converts Python scalar values (None, bool, int, float, str) to their
    TOON string representation. Handles special cases like multiline strings
    (uses triple quotes) and non-finite floats (raises error).
    
    Args:
        value: Scalar value to format (None, bool, int, float, or str)
        
    Returns:
        TOON-formatted string representation
        
    Raises:
        ValueError: If value is a non-finite float
        TypeError: If value is a mapping or sequence (not a scalar)
        
    Example:
        >>> format_scalar(42)
        '42'
        >>> format_scalar("hello")
        'hello'
        >>> format_scalar("hello world")
        '"hello world"'
        >>> # Multiline strings use triple quotes
    """
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        if isinstance(value, float):
            if math.isfinite(value):
                return repr(value)
            raise ValueError("TOON does not support non-finite floats")
        return str(value)
    if isinstance(value, str):
        if "\n" in value:
            escaped = escape_string(value)
            return f'"""{escaped}"""'
        if string_needs_quotes(value):
            return f"\"{escape_string(value)}\""
        return value
    if isinstance(value, Mapping):
        raise TypeError("format_scalar does not accept mappings")
    if isinstance(value, (list, tuple)):
        raise TypeError("format_scalar does not accept sequences")
    return json.dumps(value)


def guess_number(token: str) -> int | float | None:
    """Attempt to parse a token as a number.
    
    Optimized version using try/except which is faster than regex for valid numbers.
    Falls back to regex validation for edge cases.
    
    Args:
        token: String token to parse
        
    Returns:
        Parsed number (int or float) if valid, None otherwise
        
    Example:
        >>> guess_number("42")
        42
        >>> guess_number("3.14")
        3.14
        >>> guess_number("1e5")
        100000.0
        >>> guess_number("not_a_number")
        None
    """
    if not token:
        return None
    
    # Quick first character check (early rejection)
    first = token[0]
    if not (first.isdigit() or first == '-'):
        return None
    
    # Try direct parsing (faster than regex for valid cases)
    try:
        # Detect floats by presence of . or e/E
        if '.' in token or 'e' in token or 'E' in token:
            val = float(token)
            # Validate with regex to reject cases like "1.2.3" that float() partially accepts
            if not NUMBER_RE.match(token):
                return None
            return val
        return int(token)
    except ValueError:
        return None


def split_escaped_row(line: str, separator: str = "|") -> List[str]:
    """Split a table row line by separator, respecting string quotes and escapes.
    
    Optimized version using string slicing instead of character-by-character list building.
    
    Args:
        line: Table row line to split
        separator: Separator character (default: "|")
        
    Returns:
        List of cell values (stripped of whitespace)
        
    Example:
        >>> split_escaped_row("| 1 | Luz |")
        ['1', 'Luz']
        >>> split_escaped_row('| 1 | "Light glyph" |')
        ['1', '"Light glyph"']
        >>> split_escaped_row('| name | "value with | pipe" |')
        ['name', '"value with | pipe"']
    """
    # Early return for optimization
    if not line:
        return []
    
    if separator not in line:
        stripped = line.strip()
        return [stripped] if stripped else []
    
    parts: List[str] = []
    start = 0
    in_string = False
    i = 0
    line_len = len(line)
    
    while i < line_len:
        ch = line[i]
        
        # Handle escape: skip next character
        if ch == "\\" and i + 1 < line_len:
            i += 2
            continue
        
        if ch == "\"":
            in_string = not in_string
            i += 1
            continue
        
        if ch == separator and not in_string:
            # Use slicing instead of list construction
            part = line[start:i].strip().strip(separator).strip()
            if part:
                parts.append(part)
            start = i + 1
        
        i += 1
    
    # Process last part
    if start < line_len:
        part = line[start:].strip().strip(separator).strip()
        if part:
            parts.append(part)
    
    return parts if parts else [line.strip()]


def tabular_schema(rows: Sequence[Mapping[str, object]]) -> TabularSchema | None:
    """Detect if a sequence of mappings can use tabular format.
    
    Analyzes a sequence of dictionaries to determine if they all have
    the same keys in the same order, making them suitable for tabular
    format (key[N]{fields}:). Also estimates the character savings.
    
    Uses early exit optimization: stops checking as soon as a mismatch
    is found, avoiding processing the entire array when not uniform.
    
    Args:
        rows: Sequence of dictionaries to analyze
        
    Returns:
        TabularSchema with keys and savings if all rows have identical
        keys, None otherwise
        
    Example:
        >>> rows = [{"id": 1, "name": "Luz"}, {"id": 2, "name": "Amity"}]
        >>> schema = tabular_schema(rows)
        >>> schema.keys
        ['id', 'name']
        >>> schema.savings > 0
        True
    """
    if not rows:
        return None
    keys = list(rows[0].keys())
    if not keys:
        return None
    for row in rows[1:]:
        if list(row.keys()) != keys:
            return None
    linear = json.dumps(rows, separators=(",", ":"))
    table_rows = len(rows) + 1
    approx_table_len = sum(len(k) + 2 for k in keys) + table_rows * sum(len(str(v)) + 2 for v in rows[0].values())
    savings = len(linear) - approx_table_len
    return TabularSchema(keys=keys, savings=savings)


def token_length(text: str) -> int:
    """Estimate token count for a text string.
    
    Attempts to use tiktoken (OpenAI's tokenizer) to count tokens using
    the cl100k_base encoding. Falls back to character count if tiktoken
    is not available.
    
    Args:
        text: Text string to count tokens for
        
    Returns:
        Token count if tiktoken is available, character count otherwise
        
    Example:
        >>> token_length("Hello, world!")
        3
        >>> # Falls back to len() if tiktoken not installed
    """
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return len(text)

