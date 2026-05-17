"""Path expansion post-processing for TOON v3 expandPaths='safe' option."""
from __future__ import annotations

from .errors import ToonSyntaxError
from .utils import is_identifier_segment


def expand_paths(obj: dict, *, strict: bool = True, quoted_keys: frozenset[str] = frozenset()) -> dict:
    """Expand dotted keys in obj to nested objects with deep-merge.

    Only expands keys where:
    - The key is not quoted (we receive it as a plain str from the parser)
    - All dot-separated segments are IdentifierSegments
    - No collision with existing sibling keys

    Quoted keys were parsed without modification and will not contain dots
    from path expansion — they remain as literal keys.

    Args:
        obj: Parsed TOON object (root dict)
        strict: If True, raise ToonSyntaxError on path conflicts.
                If False, last-write-wins (document order).

    Returns:
        New dict with paths expanded and deep-merged.
    """
    result: dict = {}
    for key, value in obj.items():
        segments = _try_split(key, quoted_keys)
        if segments is None:
            # Not expandable — insert as literal
            _merge_into(result, [key], value, strict=strict, original_key=key)
        else:
            _merge_into(result, segments, value, strict=strict, original_key=key)
    return result


def _try_split(key: str, quoted_keys: frozenset[str] = frozenset()) -> list[str] | None:
    """Return dot-split segments if all are valid IdentifierSegments, else None.

    Returns None for keys in quoted_keys (originally quoted in TOON — preserved as literals).
    """
    if key in quoted_keys:
        return None  # Quoted in source — never expand
    if "." not in key:
        return None
    parts = key.split(".")
    if all(is_identifier_segment(p) for p in parts):
        return parts
    return None


def _merge_into(target: dict, segments: list[str], value: object, *, strict: bool, original_key: str) -> None:
    """Deep-merge value at the path described by segments into target."""
    key = segments[0]
    if len(segments) == 1:
        if key in target:
            if strict:
                raise ToonSyntaxError(
                    f"Path expansion conflict: key '{original_key}' conflicts with existing key '{key}'"
                )
            # LWW: overwrite
        target[key] = value
        return

    # Need to recurse — target[key] must be a dict
    if key in target:
        existing = target[key]
        if not isinstance(existing, dict):
            if strict:
                raise ToonSyntaxError(
                    f"Path expansion conflict: '{key}' exists as non-object, cannot expand '{original_key}'"
                )
            # LWW: create new dict, overwrite
            target[key] = {}
    else:
        target[key] = {}

    _merge_into(target[key], segments[1:], value, strict=strict, original_key=original_key)
