"""
toonpy – JSON ⇄ TOON conversion toolkit.

A production-quality Python library for converting between JSON and TOON
(Token-Oriented Object Notation) formats, fully conforming to TOON SPEC v2.0.

Main functions:
    - to_toon: Convert Python objects to TOON strings
    - from_toon: Parse TOON strings into Python objects
    - stream_to_toon: Stream JSON to TOON conversion for large files
    - suggest_tabular: Suggest whether arrays should use tabular format
    - validate_toon: Validate TOON syntax

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
    TabularSuggestion,
    from_toon,
    stream_to_toon,
    suggest_tabular,
    to_toon,
    validate_toon,
)

__all__ = [
    "to_toon",
    "from_toon",
    "stream_to_toon",
    "suggest_tabular",
    "validate_toon",
    "TabularSuggestion",
]

__version__ = "0.2.0"

