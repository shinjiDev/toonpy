from __future__ import annotations

import pytest

from toonpy import from_toon
from toonpy.errors import ToonSyntaxError


def test_parse_object_and_array():
    text = """
title: "Glyphs"
items:
  - name: light
    power: 5
  - name: fire
    power: 9
"""
    data = from_toon(text)
    assert data["title"] == "Glyphs"
    assert len(data["items"]) == 2


def test_parse_table_block():
    text = """
crew[2]{id,name}:
  1,Luz
  2,Amity
"""
    data = from_toon(text)
    assert data["crew"][0]["name"] == "Luz"


def test_parse_table_length_validation():
    # Test that length mismatch raises error
    text = """
crew[2]{id,name}:
  1,Luz
"""
    with pytest.raises(ToonSyntaxError) as exc:
        from_toon(text)
    assert "declares 2 rows" in str(exc.value) and "found 1" in str(exc.value)
    
    # Test that extra rows also raise error
    text2 = """
crew[2]{id,name}:
  1,Luz
  2,Amity
  3,Extra
"""
    with pytest.raises(ToonSyntaxError) as exc:
        from_toon(text2)
    assert "declares 2 rows" in str(exc.value) and "found 3" in str(exc.value)


def test_multiline_string():
    text = """
entry:
  description: \"\"\"
line one
line two
\"\"\"
"""
    data = from_toon(text)
    assert data["entry"]["description"] == "line one\nline two"


def test_error_reports_line():
    # In v3, "key value" is a valid root primitive; use an actually invalid input
    text = '"unterminated'
    with pytest.raises(ToonSyntaxError) as exc:
        from_toon(text)
    assert "line" in str(exc.value)

