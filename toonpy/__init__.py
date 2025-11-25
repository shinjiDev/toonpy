"""
toonpy – JSON/YAML ⇄ TOON conversion toolkit.

A production-quality Python library for converting between JSON, YAML and TOON
(Token-Oriented Object Notation) formats, fully conforming to TOON SPEC v2.0.

Main functions:
    - to_toon: Convert Python objects to TOON strings
    - from_toon: Parse TOON strings into Python objects
    - stream_to_toon: Stream JSON to TOON conversion for large files
    - suggest_tabular: Suggest whether arrays should use tabular format
    - validate_toon: Validate TOON syntax
    
YAML support (optional, requires PyYAML):
    - to_yaml_from_toon: Convert TOON to YAML
    - to_toon_from_yaml: Convert YAML to TOON
    - stream_yaml_to_toon: Stream YAML to TOON conversion
    - HAS_YAML: Flag indicating if YAML support is available

Example:
    >>> import toonpy
    >>> data = {"name": "Luz", "active": True}
    >>> toon = toonpy.to_toon(data)
    >>> parsed = toonpy.from_toon(toon)
    >>> parsed == data
    True
"""

from __future__ import annotations

from .api import (
    HAS_YAML,
    TabularSuggestion,
    from_toon,
    stream_to_toon,
    suggest_tabular,
    to_toon,
    validate_toon,
)

# YAML support (optional)
if HAS_YAML:
    from .api import (
        stream_yaml_to_toon,
        to_toon_from_yaml,
        to_yaml_from_toon,
    )
    
    __all__ = [
        "to_toon",
        "from_toon",
        "stream_to_toon",
        "suggest_tabular",
        "validate_toon",
        "TabularSuggestion",
        "HAS_YAML",
        "to_yaml_from_toon",
        "to_toon_from_yaml",
        "stream_yaml_to_toon",
    ]
else:
    __all__ = [
        "to_toon",
        "from_toon",
        "stream_to_toon",
        "suggest_tabular",
        "validate_toon",
        "TabularSuggestion",
        "HAS_YAML",
    ]

__version__ = "0.4.0"

