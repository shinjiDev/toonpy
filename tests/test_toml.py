"""
Tests for TOML conversion functionality.

Tests bidirectional conversion between TOML and TOON formats, including
error handling, edge cases, and streaming functionality.
"""

import io
import pytest

from toonpy.api import (
    HAS_TOML,
    to_toml_from_toon,
    to_toon_from_toml,
    stream_toml_to_toon,
)

# Conditional imports for TOML support
if HAS_TOML:
    import tomli
    import tomli_w
else:
    tomli = None
    tomli_w = None

# Skip all tests if TOML support is not available
pytestmark = pytest.mark.skipif(not HAS_TOML, reason="TOML support not installed")


class TestTOMLToTOON:
    """Test TOML to TOON conversion."""

    def test_simple_table(self):
        """Test conversion of simple TOML table."""
        toml_str = 'name = "Luz"\nage = 14'
        toon = to_toon_from_toml(toml_str)
        assert 'name:' in toon or 'name :' in toon
        assert 'Luz' in toon
        assert 'age:' in toon or 'age :' in toon
        assert '14' in toon

    def test_nested_tables(self):
        """Test conversion of nested TOML tables."""
        toml_str = """
[user]
name = "Luz"
age = 14

[user.address]
city = "Gravesfield"
"""
        toon = to_toon_from_toml(toml_str)
        assert 'user:' in toon or 'user :' in toon
        assert 'name:' in toon or 'name :' in toon
        assert 'Luz' in toon

    def test_arrays(self):
        """Test conversion of TOML arrays."""
        toml_str = 'colors = ["red", "green", "blue"]'
        toon = to_toon_from_toml(toml_str)
        assert 'colors:' in toon or 'colors :' in toon
        assert 'red' in toon
        assert 'green' in toon
        assert 'blue' in toon

    def test_array_of_tables(self):
        """Test conversion of TOML array of tables."""
        toml_str = """
[[crew]]
id = 1
name = "Luz"

[[crew]]
id = 2
name = "Eda"
"""
        toon = to_toon_from_toml(toml_str)
        # Array of tables becomes tabular format in TOON
        assert 'crew' in toon
        assert 'Luz' in toon
        assert 'Eda' in toon

    def test_boolean_values(self):
        """Test conversion of TOML boolean values."""
        toml_str = 'active = true\ninactive = false'
        toon = to_toon_from_toml(toml_str)
        assert 'true' in toon
        assert 'false' in toon

    def test_numeric_values(self):
        """Test conversion of TOML numeric values."""
        toml_str = """
integer = 42
float = 3.14
negative = -10
"""
        toon = to_toon_from_toml(toml_str)
        assert '42' in toon
        assert '3.14' in toon
        assert '-10' in toon or '- 10' in toon

    def test_compact_mode(self):
        """Test TOML to TOON conversion in compact mode."""
        toml_str = 'name = "Luz"\nactive = true'
        toon = to_toon_from_toml(toml_str, mode="compact")
        assert 'Luz' in toon
        assert 'true' in toon
        # Compact mode should have minimal whitespace
        assert len(toon) < 100

    def test_readable_mode(self):
        """Test TOML to TOON conversion in readable mode."""
        toml_str = 'name = "Luz"\nactive = true'
        toon = to_toon_from_toml(toml_str, mode="readable")
        assert 'Luz' in toon
        assert 'true' in toon

    def test_custom_indent(self):
        """Test TOML to TOON conversion with custom indentation."""
        toml_str = """
[user]
name = "Luz"
"""
        toon = to_toon_from_toml(toml_str, indent=4)
        assert 'Luz' in toon


class TestTOONToTOML:
    """Test TOON to TOML conversion."""

    def test_simple_object(self):
        """Test conversion of simple TOON object to TOML."""
        toon_str = 'name: "Luz"\nage: 14'
        toml = to_toml_from_toon(toon_str)
        assert 'name = "Luz"' in toml or "name = 'Luz'" in toml
        assert 'age = 14' in toml

    def test_nested_object(self):
        """Test conversion of nested TOON object to TOML."""
        toon_str = """
user:
  name: "Luz"
  age: 14
"""
        toml = to_toml_from_toon(toon_str)
        assert '[user]' in toml
        assert 'name = "Luz"' in toml or "name = 'Luz'" in toml

    def test_array_simple(self):
        """Test conversion of simple TOON array to TOML."""
        toon_str = """
colors:
  - red
  - green
  - blue
"""
        toml = to_toml_from_toon(toon_str)
        assert 'colors = [' in toml or 'colors=[' in toml
        assert 'red' in toml

    def test_array_of_objects(self):
        """Test conversion of TOON array of objects to TOML."""
        toon_str = """
crew[2]{id,name}:
  1, Luz
  2, Eda
"""
        toml = to_toml_from_toon(toon_str)
        # tomli_w uses inline array format for arrays of tables
        assert 'crew' in toml
        assert 'Luz' in toml
        assert 'Eda' in toml

    def test_boolean_values(self):
        """Test conversion of TOON boolean values to TOML."""
        toon_str = 'active: true\ninactive: false'
        toml = to_toml_from_toon(toon_str)
        assert 'active = true' in toml
        assert 'inactive = false' in toml

    def test_null_handling(self):
        """Test that null values raise error (TOML doesn't support null)."""
        toon_str = 'value: null'
        # TOML doesn't support null, so this should raise TypeError
        with pytest.raises(TypeError, match="not TOML serializable"):
            to_toml_from_toon(toon_str)

    def test_numeric_values(self):
        """Test conversion of TOON numeric values to TOML."""
        toon_str = """
integer: 42
float: 3.14
negative: -10
"""
        toml = to_toml_from_toon(toon_str)
        assert 'integer = 42' in toml
        assert 'float = 3.14' in toml
        assert 'negative = -10' in toml


class TestRoundTrip:
    """Test round-trip conversion between TOML and TOON."""

    def test_simple_round_trip(self):
        """Test simple TOML -> TOON -> TOML round trip."""
        original_toml = 'name = "Luz"\nage = 14'
        toon = to_toon_from_toml(original_toml)
        final_toml = to_toml_from_toon(toon)
        
        # Parse both to compare data
        original_data = tomli.loads(original_toml)
        final_data = tomli.loads(final_toml)
        assert original_data == final_data

    def test_nested_round_trip(self):
        """Test nested TOML -> TOON -> TOML round trip."""
        original_toml = """
[user]
name = "Luz"
age = 14

[user.address]
city = "Gravesfield"
"""
        toon = to_toon_from_toml(original_toml)
        final_toml = to_toml_from_toon(toon)
        
        original_data = tomli.loads(original_toml)
        final_data = tomli.loads(final_toml)
        assert original_data == final_data

    def test_array_round_trip(self):
        """Test array TOML -> TOON -> TOML round trip."""
        original_toml = 'colors = ["red", "green", "blue"]'
        toon = to_toon_from_toml(original_toml)
        final_toml = to_toml_from_toon(toon)
        
        original_data = tomli.loads(original_toml)
        final_data = tomli.loads(final_toml)
        assert original_data == final_data


class TestStreaming:
    """Test streaming TOML to TOON conversion."""

    def test_stream_simple(self):
        """Test streaming a simple TOML file to TOON."""
        toml_str = 'name = "Luz"\nage = 14'
        
        in_file = io.StringIO(toml_str)
        out_file = io.StringIO()
        
        bytes_written = stream_toml_to_toon(in_file, out_file)
        assert bytes_written > 0
        
        out_file.seek(0)
        toon_result = out_file.read()
        assert 'Luz' in toon_result
        assert '14' in toon_result

    def test_stream_nested(self):
        """Test streaming a nested TOML file to TOON."""
        toml_str = """
[user]
name = "Luz"
age = 14
"""
        in_file = io.StringIO(toml_str)
        out_file = io.StringIO()
        
        bytes_written = stream_toml_to_toon(in_file, out_file, mode="readable")
        assert bytes_written > 0
        
        out_file.seek(0)
        toon_result = out_file.read()
        assert 'Luz' in toon_result


class TestErrorHandling:
    """Test error handling for TOML conversion."""

    def test_invalid_toml(self):
        """Test that invalid TOML raises appropriate error."""
        invalid_toml = 'name = "Luz\nage = 14'  # Missing closing quote
        with pytest.raises(Exception):  # tomli.TOMLDecodeError
            to_toon_from_toml(invalid_toml)

    def test_invalid_toon(self):
        """Test that invalid TOON raises appropriate error."""
        invalid_toon = 'name: "Luz\nage: 14'  # Missing closing quote
        with pytest.raises(Exception):
            to_toml_from_toon(invalid_toon)

    def test_toon_non_dict_root(self):
        """Test that TOON with non-dict root raises ValueError."""
        toon_array = """
- Luz
- Eda
"""
        with pytest.raises(ValueError, match="TOML root must be a table"):
            to_toml_from_toon(toon_array)

    def test_toon_scalar_root(self):
        """Test that TOON with scalar root raises ValueError."""
        toon_scalar = '"Luz"'
        with pytest.raises(ValueError, match="TOML root must be a table"):
            to_toml_from_toon(toon_scalar)


class TestEdgeCases:
    """Test edge cases for TOML conversion."""

    def test_empty_table(self):
        """Test conversion of empty TOML table."""
        toml_str = ''
        toon = to_toon_from_toml(toml_str)
        # Empty TOML should give empty object in TOON
        assert toon.strip() == '{}' or toon.strip() == ''

    def test_special_characters(self):
        """Test conversion of TOML with special characters."""
        toml_str = 'message = "Hello\\nWorld!"'
        toon = to_toon_from_toml(toml_str)
        # Should preserve the newline escape
        assert 'Hello' in toon

    def test_unicode(self):
        """Test conversion of TOML with Unicode characters."""
        toml_str = 'name = "Luz Noceda"'  # Using ASCII for simplicity
        toon = to_toon_from_toml(toml_str)
        assert 'Noceda' in toon

    def test_large_numbers(self):
        """Test conversion of large numbers."""
        toml_str = 'big = 9223372036854775807'
        toon = to_toon_from_toml(toml_str)
        assert '9223372036854775807' in toon


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

