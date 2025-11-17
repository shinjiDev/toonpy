"""
toonpy – JSON ⇄ TOON conversion toolkit.
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

__version__ = "0.1.0"

