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

# Optional YAML support
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None  # type: ignore

# Optional TOML support
try:
    import tomli
    import tomli_w
    HAS_TOML = True
except ImportError:
    HAS_TOML = False
    tomli = None  # type: ignore
    tomli_w = None  # type: ignore

__all__ = [
    "to_toon",
    "from_toon",
    "stream_to_toon",
    "suggest_tabular",
    "validate_toon",
    "TabularSuggestion",
    # YAML support
    "to_yaml_from_toon",
    "to_toon_from_yaml",
    "stream_yaml_to_toon",
    "HAS_YAML",
    # TOML support
    "to_toml_from_toon",
    "to_toon_from_toml",
    "stream_toml_to_toon",
    "HAS_TOML",
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


def to_toon(
    obj: Any,
    *,
    indent: int = 2,
    mode: Literal["auto", "compact", "readable"] = "auto",
    delimiter: Literal["comma", "tab", "pipe"] = "comma",
    key_folding: Literal["off", "safe"] = "off",
    flatten_depth: int | float = float("inf"),
) -> str:
    """Convert a Python object to TOON format string.

    Args:
        obj: Python object compatible with JSON model (dict, list, scalar)
        indent: Spaces per indentation level (default: 2)
        mode: "auto" (default), "compact", or "readable"
        delimiter: "comma" (default), "tab", or "pipe"
        key_folding: "off" (default) or "safe" — fold single-key chains to dotted paths
        flatten_depth: Max depth for key folding (default: inf)

    Returns:
        TOON-formatted string
    """
    return _to_toon(
        obj,
        indent=indent,
        mode=mode,
        delimiter=delimiter,
        key_folding=key_folding,
        flatten_depth=flatten_depth,
    )


def from_toon(
    source: str,
    *,
    strict: bool = True,
    expand_paths: Literal["off", "safe"] = "off",
    spec: Literal["v2", "v3"] = "v3",
    permissive: bool = False,
    indent: int = 2,
) -> Any:
    """Parse a TOON string into a Python object.

    Args:
        source: TOON-formatted string to parse
        strict: Enforce strict v3 validation (default: True)
        expand_paths: "off" (default) or "safe" — expand dotted keys
        spec: "v3" (default) or "v2" — which spec version to use
        permissive: Relax identifier/numeric validation (v2 compat)
        indent: Expected indentation size for strict validation (default: 2)

    Returns:
        Python object (dict, list, or scalar value)

    Raises:
        ToonSyntaxError: If the TOON string is malformed
    """
    if spec == "v2":
        from ._parser_v2 import from_toon as _from_toon_v2
        return _from_toon_v2(source, permissive=permissive)
    return _from_toon(
        source,
        strict=strict,
        permissive=permissive,
        indent=indent,
        expand_paths=expand_paths,
    )


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
        _from_toon(source, strict=strict)
    except ToonSyntaxError as exc:
        return False, [ValidationError(str(exc), exc.line, exc.column)]
    return True, []


# ============================================================================
# YAML Support Functions
# ============================================================================


def to_yaml_from_toon(source: str, *, mode: Literal["strict", "permissive"] = "strict") -> str:
    """Convert TOON string to YAML string.
    
    Parses TOON format and converts it to YAML format. This is a convenience
    function that combines from_toon() and yaml.dump().
    
    Args:
        source: TOON-formatted string to convert
        mode: Parsing mode - "strict" or "permissive"
        
    Returns:
        YAML-formatted string
        
    Raises:
        ImportError: If PyYAML is not installed
        ToonSyntaxError: If TOON string is malformed
        
    Example:
        >>> toon = 'name: "Luz"\\nactive: true'
        >>> yaml_str = to_yaml_from_toon(toon)
        >>> 'name: Luz' in yaml_str
        True
        
    Note:
        Requires PyYAML to be installed: pip install toontools[yaml]
    """
    if not HAS_YAML:
        raise ImportError(
            "PyYAML is required for YAML support. "
            "Install it with: pip install toontools[yaml]"
        )
    data = from_toon(source, strict=(mode == "strict"), permissive=(mode == "permissive"))
    return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)


def to_toon_from_yaml(
    source: str,
    *,
    indent: int = 2,
    mode: Literal["auto", "compact", "readable"] = "auto"
) -> str:
    """Convert YAML string to TOON string.
    
    Parses YAML format and converts it to TOON format. This is a convenience
    function that combines yaml.safe_load() and to_toon().
    
    Args:
        source: YAML-formatted string to convert
        indent: Number of spaces per indentation level (default: 2)
        mode: Serialization mode - "auto", "compact", or "readable"
        
    Returns:
        TOON-formatted string
        
    Raises:
        ImportError: If PyYAML is not installed
        yaml.YAMLError: If YAML string is malformed
        
    Example:
        >>> yaml_str = 'name: Luz\\nactive: true'
        >>> toon = to_toon_from_yaml(yaml_str)
        >>> 'name: "Luz"' in toon or 'name: Luz' in toon
        True
        
    Note:
        Requires PyYAML to be installed: pip install toontools[yaml]
    """
    if not HAS_YAML:
        raise ImportError(
            "PyYAML is required for YAML support. "
            "Install it with: pip install toontools[yaml]"
        )
    data = yaml.safe_load(source)
    return to_toon(data, indent=indent, mode=mode)


def stream_yaml_to_toon(
    fileobj_in: TextIO,
    fileobj_out: TextIO,
    *,
    chunk_size: int = 65_536,
    indent: int = 2,
    mode: Literal["auto", "compact", "readable"] = "auto",
) -> int:
    """Stream YAML from input file to TOON output file.
    
    Reads YAML data from a text file object in chunks, parses it, converts
    to TOON format, and writes to an output file object. Useful for
    processing large files without loading everything into memory.
    
    Args:
        fileobj_in: Input file object containing YAML (must be opened in text mode)
        fileobj_out: Output file object for TOON (must be opened in text mode)
        chunk_size: Size of chunks to read from input (default: 65536 bytes)
        indent: Number of spaces per indentation level (default: 2)
        mode: Serialization mode - "auto", "compact", or "readable"
        
    Returns:
        Number of bytes written to output
        
    Raises:
        ImportError: If PyYAML is not installed
        yaml.YAMLError: If input is not valid YAML
        ToonSyntaxError: If conversion fails (should not occur)
        
    Example:
        >>> with open("input.yaml", "r") as fin, open("output.toon", "w") as fout:
        ...     bytes_written = stream_yaml_to_toon(fin, fout, mode="auto")
        
    Note:
        Requires PyYAML to be installed: pip install toontools[yaml]
    """
    if not HAS_YAML:
        raise ImportError(
            "PyYAML is required for YAML support. "
            "Install it with: pip install toontools[yaml]"
        )
    buffer = io.StringIO()
    while True:
        chunk = fileobj_in.read(chunk_size)
        if not chunk:
            break
        buffer.write(chunk)
    buffer.seek(0)
    data = yaml.safe_load(buffer)
    toon_text = to_toon(data, indent=indent, mode=mode)
    fileobj_out.write(toon_text)
    return len(toon_text)


# ─────────────────────────────────────────────────────────────────────────────
# TOML Support (Optional)
# ─────────────────────────────────────────────────────────────────────────────

def to_toml_from_toon(source: str) -> str:
    """Convert TOON format to TOML format string.
    
    Parses TOON format and converts it to TOML format. This is a convenience
    function that combines from_toon() and tomli_w.dumps().
    
    Args:
        source: TOON-formatted string to convert
        
    Returns:
        TOML-formatted string
        
    Raises:
        ImportError: If tomli/tomli_w are not installed
        ToonSyntaxError: If TOON string is malformed
        
    Example:
        >>> toon_str = 'name: "Luz"\\nactive: true'
        >>> toml = to_toml_from_toon(toon_str)
        >>> 'name = "Luz"' in toml
        True
        
    Note:
        Requires tomli/tomli_w to be installed: pip install toontools[toml]
    """
    if not HAS_TOML:
        raise ImportError(
            "tomli and tomli_w are required for TOML support. "
            "Install them with: pip install toontools[toml]"
        )
    data = from_toon(source)
    if not isinstance(data, dict):
        raise ValueError("TOML root must be a table (dictionary), got: " + type(data).__name__)
    return tomli_w.dumps(data)


def to_toon_from_toml(source: str, *, indent: int = 2, mode: Literal["auto", "compact", "readable"] = "auto") -> str:
    """Convert TOML format to TOON format string.
    
    Parses TOML format and converts it to TOON format. This is a convenience
    function that combines tomli.loads() and to_toon().
    
    Args:
        source: TOML-formatted string to convert
        indent: Number of spaces per indentation level (default: 2)
        mode: Serialization mode - "auto", "compact", or "readable"
        
    Returns:
        TOON-formatted string
        
    Raises:
        ImportError: If tomli is not installed
        tomli.TOMLDecodeError: If TOML string is malformed
        
    Example:
        >>> toml_str = 'name = "Luz"\\nactive = true'
        >>> toon = to_toon_from_toml(toml_str)
        >>> 'name: "Luz"' in toon or 'name: Luz' in toon
        True
        
    Note:
        Requires tomli to be installed: pip install toontools[toml]
    """
    if not HAS_TOML:
        raise ImportError(
            "tomli is required for TOML support. "
            "Install it with: pip install toontools[toml]"
        )
    data = tomli.loads(source)
    return to_toon(data, indent=indent, mode=mode)


def stream_toml_to_toon(
    fileobj_in: TextIO,
    fileobj_out: TextIO,
    *,
    chunk_size: int = 65_536,
    indent: int = 2,
    mode: Literal["auto", "compact", "readable"] = "auto",
) -> int:
    """Stream TOML from input file to TOON output file.
    
    Reads TOML data from a text file object in chunks, parses it, converts
    to TOON format, and writes to an output file object. Useful for
    processing large files without loading everything into memory.
    
    Args:
        fileobj_in: Input file object containing TOML (must be opened in text mode)
        fileobj_out: Output file object for TOON (must be opened in text mode)
        chunk_size: Size of chunks to read from input (default: 65536 bytes)
        indent: Number of spaces per indentation level (default: 2)
        mode: Serialization mode - "auto", "compact", or "readable"
        
    Returns:
        Number of bytes written to output
        
    Raises:
        ImportError: If tomli is not installed
        tomli.TOMLDecodeError: If input is not valid TOML
        ToonSyntaxError: If conversion fails (should not occur)
        
    Example:
        >>> with open("input.toml", "r") as fin, open("output.toon", "w") as fout:
        ...     bytes_written = stream_toml_to_toon(fin, fout, mode="auto")
        
    Note:
        Requires tomli to be installed: pip install toontools[toml]
    """
    if not HAS_TOML:
        raise ImportError(
            "tomli is required for TOML support. "
            "Install it with: pip install toontools[toml]"
        )
    buffer = io.StringIO()
    while True:
        chunk = fileobj_in.read(chunk_size)
        if not chunk:
            break
        buffer.write(chunk)
    buffer.seek(0)
    data = tomli.loads(buffer.getvalue())
    toon_text = to_toon(data, indent=indent, mode=mode)
    fileobj_out.write(toon_text)
    return len(toon_text)

