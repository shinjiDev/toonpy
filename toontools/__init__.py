"""
Compatibility layer exposing the public toonpy API under the expected toontools namespace.
"""

from __future__ import annotations

from toonpy import (
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

