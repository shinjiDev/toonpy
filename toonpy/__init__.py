"""
toonpy – JSON/YAML/TOML ⇄ TOON conversion toolkit.

A production-quality Python library for converting between JSON, YAML, TOML and TOON
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

TOML support (optional, requires tomli/tomli_w):
    - to_toml_from_toon: Convert TOON to TOML
    - to_toon_from_toml: Convert TOML to TOON
    - stream_toml_to_toon: Stream TOML to TOON conversion
    - HAS_TOML: Flag indicating if TOML support is available

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
    HAS_TOML,
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

# TOML support (optional)
if HAS_TOML:
    from .api import (
        stream_toml_to_toon,
        to_toon_from_toml,
        to_toml_from_toon,
    )

# Build __all__ dynamically based on available features
__all__ = [
    "to_toon",
    "from_toon",
    "stream_to_toon",
    "suggest_tabular",
    "validate_toon",
    "TabularSuggestion",
    "HAS_YAML",
    "HAS_TOML",
]

if HAS_YAML:
    __all__.extend([
        "to_yaml_from_toon",
        "to_toon_from_yaml",
        "stream_yaml_to_toon",
    ])

if HAS_TOML:
    __all__.extend([
        "to_toml_from_toon",
        "to_toon_from_toml",
        "stream_toml_to_toon",
    ])

__version__ = "0.6.0"

