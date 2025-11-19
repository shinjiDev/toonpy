from __future__ import annotations

import io
import json

from toonpy import (
    from_toon,
    stream_to_toon,
    suggest_tabular,
    to_toon,
    validate_toon,
)


def test_validate_success_and_failure():
    ok, errors = validate_toon("key: 1")
    assert ok
    assert errors == []

    bad, errors = validate_toon("key value")
    assert not bad
    assert errors


def test_stream_to_toon(tmp_path):
    source = tmp_path / "data.json"
    source.write_text('{"x": [1, 2]}', encoding="utf-8")
    target = io.StringIO()
    with source.open("r", encoding="utf-8") as handle:
        bytes_written = stream_to_toon(handle, target)
    assert bytes_written == len(target.getvalue())
    assert from_toon(target.getvalue()) == {"x": [1, 2]}


def test_stream_to_toon_large(tmp_path):
    data = {"values": list(range(200))}
    source = tmp_path / "large.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    target = io.StringIO()
    with source.open("r", encoding="utf-8") as handle:
        stream_to_toon(handle, target, chunk_size=32)
    assert from_toon(target.getvalue()) == data


def test_suggest_tabular():
    crew = [
        {"id": 1, "name": "Luz"},
        {"id": 2, "name": "Amity"},
    ]
    suggestion = suggest_tabular(crew)
    assert suggestion.use_tabular
    assert suggestion.keys == ["id", "name"]

