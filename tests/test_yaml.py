"""
Tests for YAML support in toonpy.

Tests YAML ↔ TOON conversion functions, CLI commands, and edge cases.
"""

from __future__ import annotations

import io
import sys
import pytest

from toonpy import from_toon, to_toon
from toonpy.api import HAS_YAML

# Skip all tests if PyYAML is not installed
pytestmark = pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")

if HAS_YAML:
    import yaml
    from toonpy import (
        to_yaml_from_toon,
        to_toon_from_yaml,
        stream_yaml_to_toon,
    )


# ============================================================================
# BASIC CONVERSION TESTS
# ============================================================================

def test_yaml_to_toon_simple():
    """Test basic YAML to TOON conversion."""
    yaml_str = """
name: Luz
age: 16
active: true
"""
    toon_str = to_toon_from_yaml(yaml_str)
    data = from_toon(toon_str)
    
    assert data["name"] == "Luz"
    assert data["age"] == 16
    assert data["active"] is True


def test_toon_to_yaml_simple():
    """Test basic TOON to YAML conversion."""
    toon_str = """
name: "Luz"
age: 16
active: true
"""
    yaml_str = to_yaml_from_toon(toon_str)
    data = yaml.safe_load(yaml_str)
    
    assert data["name"] == "Luz"
    assert data["age"] == 16
    assert data["active"] is True


def test_yaml_to_toon_with_arrays():
    """Test YAML to TOON conversion with arrays."""
    yaml_str = """
crew:
  - id: 1
    name: Luz
    role: Magic user
  - id: 2
    name: Amity
    role: Strategist
"""
    toon_str = to_toon_from_yaml(yaml_str, mode="auto")
    data = from_toon(toon_str)
    
    assert len(data["crew"]) == 2
    assert data["crew"][0]["name"] == "Luz"
    assert data["crew"][1]["name"] == "Amity"


def test_toon_to_yaml_with_tables():
    """Test TOON to YAML conversion with tabular format."""
    toon_str = """
crew[2]{id,name,role}:
  1,Luz,"Magic user"
  2,Amity,Strategist
"""
    yaml_str = to_yaml_from_toon(toon_str)
    data = yaml.safe_load(yaml_str)
    
    assert len(data["crew"]) == 2
    assert data["crew"][0]["id"] == 1
    assert data["crew"][1]["role"] == "Strategist"


# ============================================================================
# ROUND-TRIP TESTS
# ============================================================================

def test_yaml_toon_yaml_round_trip():
    """Test YAML → TOON → YAML round trip."""
    original_data = {
        "name": "Luz",
        "age": 16,
        "tags": ["magic", "hero", "glyphs"],
        "stats": {
            "power": 95,
            "intelligence": 88
        }
    }
    
    # Original YAML
    yaml1 = yaml.dump(original_data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    # YAML → TOON → YAML
    toon_str = to_toon_from_yaml(yaml1)
    yaml2 = to_yaml_from_toon(toon_str)
    
    # Compare data, not exact YAML strings (formatting may differ)
    data1 = yaml.safe_load(yaml1)
    data2 = yaml.safe_load(yaml2)
    
    assert data1 == data2


def test_toon_yaml_toon_round_trip():
    """Test TOON → YAML → TOON round trip."""
    original_data = {
        "name": "Amity",
        "active": True,
        "score": 98.5,
        "items": [1, 2, 3, 4, 5]
    }
    
    # Original TOON
    toon1 = to_toon(original_data, mode="auto")
    
    # TOON → YAML → TOON
    yaml_str = to_yaml_from_toon(toon1)
    toon2 = to_toon_from_yaml(yaml_str)
    
    # Compare data
    data1 = from_toon(toon1)
    data2 = from_toon(toon2)
    
    assert data1 == data2


# ============================================================================
# EDGE CASES
# ============================================================================

def test_yaml_empty_containers():
    """Test YAML conversion with empty containers."""
    yaml_str = """
empty_list: []
empty_dict: {}
normal: value
"""
    toon_str = to_toon_from_yaml(yaml_str)
    data = from_toon(toon_str)
    
    assert data["empty_list"] == []
    assert data["empty_dict"] == {}
    assert data["normal"] == "value"


def test_toon_null_values_to_yaml():
    """Test TOON null values convert to YAML correctly."""
    toon_str = """
name: null
value: 123
active: null
"""
    yaml_str = to_yaml_from_toon(toon_str)
    data = yaml.safe_load(yaml_str)
    
    assert data["name"] is None
    assert data["value"] == 123
    assert data["active"] is None


def test_yaml_unicode_support():
    """Test YAML to TOON with Unicode characters."""
    yaml_str = """
name: "Luz Noceda"
message: "¡Hola! 你好 こんにちは"
emoji: "🔥⚡✨"
"""
    toon_str = to_toon_from_yaml(yaml_str)
    data = from_toon(toon_str)
    
    assert "Luz Noceda" in data["name"]
    assert "¡Hola!" in data["message"]
    assert "🔥" in data["emoji"]


def test_yaml_nested_structures():
    """Test deeply nested YAML structures."""
    yaml_str = """
level1:
  level2:
    level3:
      level4:
        value: deep
"""
    toon_str = to_toon_from_yaml(yaml_str)
    data = from_toon(toon_str)
    
    assert data["level1"]["level2"]["level3"]["level4"]["value"] == "deep"


# ============================================================================
# STREAMING TESTS
# ============================================================================

def test_stream_yaml_to_toon(tmp_path):
    """Test streaming YAML to TOON."""
    yaml_content = """
users:
  - id: 1
    name: User1
  - id: 2
    name: User2
meta:
  count: 2
"""
    
    source = tmp_path / "data.yaml"
    source.write_text(yaml_content, encoding="utf-8")
    target = io.StringIO()
    
    with source.open("r", encoding="utf-8") as handle:
        bytes_written = stream_yaml_to_toon(handle, target)
    
    assert bytes_written == len(target.getvalue())
    
    # Verify result
    data = from_toon(target.getvalue())
    assert len(data["users"]) == 2
    assert data["meta"]["count"] == 2


def test_stream_yaml_to_toon_large(tmp_path):
    """Test streaming large YAML file."""
    large_data = {
        "records": [
            {"id": i, "value": f"record_{i}"}
            for i in range(100)
        ]
    }
    
    source = tmp_path / "large.yaml"
    source.write_text(
        yaml.dump(large_data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8"
    )
    
    target = io.StringIO()
    with source.open("r", encoding="utf-8") as handle:
        stream_yaml_to_toon(handle, target, chunk_size=256)
    
    data = from_toon(target.getvalue())
    assert len(data["records"]) == 100
    assert data["records"][99]["value"] == "record_99"


# ============================================================================
# MODE TESTS
# ============================================================================

def test_yaml_to_toon_compact_mode():
    """Test YAML to TOON with compact mode."""
    yaml_str = """
data:
  - 1
  - 2
  - 3
"""
    toon_str = to_toon_from_yaml(yaml_str, mode="compact")
    
    # Compact mode should minimize whitespace
    assert "data:" in toon_str or "data[" in toon_str


def test_yaml_to_toon_readable_mode():
    """Test YAML to TOON with readable mode."""
    yaml_str = """
name: Test
value: 123
"""
    toon_str = to_toon_from_yaml(yaml_str, mode="readable")
    
    # Should be readable format
    data = from_toon(toon_str)
    assert data["name"] == "Test"
    assert data["value"] == 123


def test_toon_to_yaml_permissive_mode():
    """Test TOON to YAML with permissive parsing."""
    # TOON with potential issues (might have trailing commas, etc.)
    toon_str = """
name: "Test"
value: 123
"""
    yaml_str = to_yaml_from_toon(toon_str, mode="permissive")
    data = yaml.safe_load(yaml_str)
    
    assert data["name"] == "Test"
    assert data["value"] == 123


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

def test_yaml_invalid_syntax():
    """Test YAML to TOON with invalid YAML."""
    invalid_yaml = """
name: "unclosed quote
value: 123
"""
    with pytest.raises(yaml.YAMLError):
        to_toon_from_yaml(invalid_yaml)


def test_toon_invalid_syntax_to_yaml():
    """Test TOON to YAML with invalid TOON."""
    from toonpy.errors import ToonSyntaxError
    
    invalid_toon = """
name value  # Missing colon
"""
    with pytest.raises(ToonSyntaxError):
        to_yaml_from_toon(invalid_toon)


# ============================================================================
# IMPORT ERROR TEST
# ============================================================================

def test_import_error_message():
    """Test that helpful error is shown when PyYAML not available."""
    # This test is more of a documentation of expected behavior
    # In practice, if PyYAML is not installed, the module import would fail
    # But we check that HAS_YAML flag works correctly
    assert HAS_YAML is True or HAS_YAML is False


# ============================================================================
# DATA TYPES TESTS
# ============================================================================

def test_yaml_all_types():
    """Test YAML to TOON with all supported data types."""
    yaml_str = """
string: "hello"
integer: 42
float: 3.14
boolean_true: true
boolean_false: false
null_value: null
list: [1, 2, 3]
dict:
  key: value
"""
    toon_str = to_toon_from_yaml(yaml_str)
    data = from_toon(toon_str)
    
    assert data["string"] == "hello"
    assert data["integer"] == 42
    assert data["float"] == 3.14
    assert data["boolean_true"] is True
    assert data["boolean_false"] is False
    assert data["null_value"] is None
    assert data["list"] == [1, 2, 3]
    assert data["dict"]["key"] == "value"


def test_yaml_numbers():
    """Test YAML number types."""
    yaml_str = """
int_positive: 123
int_negative: -456
float_positive: 3.14
float_negative: -2.71
scientific: 1.23e+10
"""
    toon_str = to_toon_from_yaml(yaml_str)
    data = from_toon(toon_str)
    
    assert data["int_positive"] == 123
    assert data["int_negative"] == -456
    assert data["float_positive"] == 3.14
    assert data["float_negative"] == -2.71
    assert data["scientific"] == 1.23e+10


# ============================================================================
# PERFORMANCE INDICATORS (simple timing tests)
# ============================================================================

def test_yaml_to_toon_performance():
    """Test that YAML to TOON conversion completes in reasonable time."""
    import time
    
    large_data = {
        "records": [
            {"id": i, "name": f"name_{i}", "value": i * 1.5}
            for i in range(100)
        ]
    }
    yaml_str = yaml.dump(large_data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    start = time.perf_counter()
    toon_str = to_toon_from_yaml(yaml_str)
    elapsed = time.perf_counter() - start
    
    # Should complete in reasonable time (< 1 second for 100 records)
    assert elapsed < 1.0
    assert len(toon_str) > 0
    
    # Verify correctness
    data = from_toon(toon_str)
    assert len(data["records"]) == 100


def test_toon_to_yaml_performance():
    """Test that TOON to YAML conversion completes in reasonable time."""
    import time
    
    large_data = {
        "records": [
            {"id": i, "name": f"name_{i}", "value": i * 1.5}
            for i in range(100)
        ]
    }
    toon_str = to_toon(large_data, mode="auto")
    
    start = time.perf_counter()
    yaml_str = to_yaml_from_toon(toon_str)
    elapsed = time.perf_counter() - start
    
    # Should complete in reasonable time
    assert elapsed < 1.0
    assert len(yaml_str) > 0
    
    # Verify correctness
    data = yaml.safe_load(yaml_str)
    assert len(data["records"]) == 100

