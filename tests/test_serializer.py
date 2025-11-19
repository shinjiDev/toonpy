from __future__ import annotations

from toonpy import to_toon, from_toon


def test_round_trip_simple():
    payload = {"a": 1, "b": True, "c": None, "d": ["x", "y"]}
    toon = to_toon(payload)
    assert from_toon(toon) == payload


def test_tabular_mode_auto():
    crew = [
        {"id": 1, "name": "Luz"},
        {"id": 2, "name": "Amity"},
    ]
    toon = to_toon({"crew": crew}, mode="auto")
    # Check for spec-compliant syntax: key[N]{fields}:
    assert "crew[2]{id,name}:" in toon
    assert from_toon(toon)["crew"] == crew

