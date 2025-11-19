"""
Public API surface for toonpy.

This module provides the main user-facing functions for converting between
JSON and TOON formats, as well as utility functions for validation and
tabular format suggestions.
"""

from __future__ import annotations

from dataclasses import dataclass
import io
import json
from typing import Any, BinaryIO, Iterable, List, Literal, Sequence, TextIO

from .errors import ToonSyntaxError, ValidationError
from .parser import from_toon as _from_toon
from .serializer import to_toon as _to_toon
from .utils import TabularSchema, tabular_schema, token_length

__all__ = [
    "to_toon",
    "from_toon",
    "stream_to_toon",
    "suggest_tabular",
    "validate_toon",
    "TabularSuggestion",
]


@dataclass(slots=True)
class TabularSuggestion:
    """Suggestion result for whether to use tabular format for an array.
    
    Attributes:
        use_tabular: Whether tabular format would be beneficial
        estimated_savings: Estimated token/character savings if tabular format is used
        keys: List of field names that would be used in the table header
    """

    use_tabular: bool
    estimated_savings: int
    keys: List[str]


def to_toon(obj: Any, *, indent: int = 2, mode: Literal["auto", "compact", "readable"] = "auto") -> str:
    """Convert a Python object to TOON format string.
    
    Converts any JSON-compatible Python object (dict, list, scalar) into
    a TOON-formatted string according to TOON SPEC v2.0.
    
    Args:
        obj: Python object compatible with JSON model (dict, list, scalar)
        indent: Number of spaces per indentation level (default: 2)
        mode: Serialization mode:
            - "auto": Automatically choose compact or readable based on content
            - "compact": Minimize output size
            - "readable": Prefer human-readable formatting
            
    Returns:
        TOON-formatted string
        
    Example:
        >>> data = {"crew": [{"id": 1, "name": "Luz"}]}
        >>> toon = to_toon(data, mode="auto")
        >>> "crew[1]{id,name}:" in toon
        True
    """
    return _to_toon(obj, indent=indent, mode=mode)


def from_toon(source: str, *, mode: Literal["strict", "permissive"] = "strict") -> Any:
    """Parse a TOON string into a Python object.
    
    Converts a TOON-formatted string into a Python object (dict, list, scalar)
    according to TOON SPEC v2.0.
    
    Args:
        source: TOON-formatted string to parse
        mode: Parsing mode:
            - "strict": Enforce strict TOON grammar compliance
            - "permissive": Allow minor deviations (e.g., trailing commas)
            
    Returns:
        Python object (dict, list, or scalar value)
        
    Raises:
        ToonSyntaxError: If the TOON string is malformed
        
    Example:
        >>> toon = 'name: "Luz"\\nactive: true'
        >>> data = from_toon(toon)
        >>> data == {"name": "Luz", "active": True}
        True
    """
    return _from_toon(source, permissive=(mode == "permissive"))


def stream_to_toon(
    fileobj_in: TextIO,
    fileobj_out: TextIO,
    *,
    chunk_size: int = 65_536,
    indent: int = 2,
    mode: Literal["auto", "compact", "readable"] = "auto",
) -> int:
    """Stream JSON from input file to TOON output file.
    
    Reads JSON data from a text file object in chunks, parses it, converts
    to TOON format, and writes to an output file object. Useful for
    processing large files without loading everything into memory.
    
    Args:
        fileobj_in: Input file object containing JSON (must be opened in text mode)
        fileobj_out: Output file object for TOON (must be opened in text mode)
        chunk_size: Size of chunks to read from input (default: 65536 bytes)
        indent: Number of spaces per indentation level (default: 2)
        mode: Serialization mode - "auto", "compact", or "readable"
        
    Returns:
        Number of bytes written to output
        
    Raises:
        json.JSONDecodeError: If input is not valid JSON
        ToonSyntaxError: If conversion fails (should not occur)
        
    Example:
        >>> with open("input.json", "r") as fin, open("output.toon", "w") as fout:
        ...     bytes_written = stream_to_toon(fin, fout, mode="auto")
    """
    buffer = io.StringIO()
    while True:
        chunk = fileobj_in.read(chunk_size)
        if not chunk:
            break
        buffer.write(chunk)
    buffer.seek(0)
    data = json.load(buffer)
    toon_text = to_toon(data, indent=indent, mode=mode)
    fileobj_out.write(toon_text)
    return len(toon_text)


def suggest_tabular(obj: Sequence[Any]) -> TabularSuggestion:
    """Suggest whether an array should use tabular format.
    
    Analyzes a sequence of objects to determine if tabular format
    (key[N]{fields}:) would be more efficient than standard array format.
    Only suggests tabular format if all items are dicts with identical keys.
    
    Args:
        obj: Sequence to analyze (list, tuple, etc.)
        
    Returns:
        TabularSuggestion with recommendation and estimated savings
        
    Example:
        >>> crew = [{"id": 1, "name": "Luz"}, {"id": 2, "name": "Amity"}]
        >>> suggestion = suggest_tabular(crew)
        >>> suggestion.use_tabular
        True
        >>> suggestion.keys
        ['id', 'name']
    """
    if not isinstance(obj, Sequence) or isinstance(obj, (str, bytes, bytearray)):
        return TabularSuggestion(False, 0, [])
    mappings = [item for item in obj if isinstance(item, dict)]
    if len(mappings) != len(obj):
        return TabularSuggestion(False, 0, [])
    schema = tabular_schema(mappings)
    if not schema:
        return TabularSuggestion(False, 0, [])
    # Calculate savings: compare JSON vs TOON tabular format
    linear = json.dumps(obj, separators=(",", ":"))
    serializer_text = _to_toon(obj, indent=2, mode="compact")
    savings = token_length(linear) - token_length(serializer_text)
    # For small arrays, schema.savings might be more accurate than token comparison
    # Use schema.savings if token comparison shows no savings but schema suggests savings
    if savings <= 0 and schema.savings > 0:
        savings = schema.savings
    return TabularSuggestion(savings > 0, savings, schema.keys)


def validate_toon(source: str, *, strict: bool = True) -> tuple[bool, List[ValidationError]]:
    """Validate a TOON string for syntax errors.
    
    Attempts to parse the TOON string and returns validation results.
    Useful for checking TOON files before processing or for linting tools.
    
    Args:
        source: TOON-formatted string to validate
        strict: If True, use strict parsing mode; if False, use permissive mode
        
    Returns:
        Tuple of (is_valid, list_of_errors):
        - is_valid: True if TOON is valid, False otherwise
        - list_of_errors: List of ValidationError objects (empty if valid)
        
    Example:
        >>> valid, errors = validate_toon('name: "Luz"\\nactive: true')
        >>> valid
        True
        >>> errors
        []
        
        >>> valid, errors = validate_toon('name: "Luz"\\ninvalid syntax')
        >>> valid
        False
        >>> len(errors) > 0
        True
    """
    try:
        _from_toon(source, permissive=not strict)
    except ToonSyntaxError as exc:
        return False, [ValidationError(str(exc), exc.line, exc.column)]
    return True, []

