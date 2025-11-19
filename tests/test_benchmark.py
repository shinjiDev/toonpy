"""
Performance benchmarks for toonpy.

These tests measure the speed of JSON ↔ TOON conversion operations
to demonstrate the library's performance characteristics.
"""

from __future__ import annotations

import json
import time
from typing import Any

import pytest

from toonpy import from_toon, to_toon


def generate_large_data(size: int = 1000) -> dict[str, Any]:
    """Generate a large dataset for benchmarking."""
    return {
        "users": [
            {
                "id": i,
                "name": f"User{i}",
                "email": f"user{i}@example.com",
                "active": i % 2 == 0,
                "score": i * 1.5,
            }
            for i in range(size)
        ],
        "metadata": {
            "total": size,
            "version": "1.0.0",
            "tags": ["test", "benchmark", "performance"],
        },
    }


def generate_nested_data(depth: int = 5, width: int = 10) -> dict[str, Any]:
    """Generate deeply nested data for benchmarking."""
    result: dict[str, Any] = {}
    current = result
    for i in range(depth):
        current[f"level{i}"] = {}
        current = current[f"level{i}"]
        for j in range(width):
            current[f"item{j}"] = f"value{i}_{j}"
    return result


class TestPerformance:
    """Performance benchmarks for toonpy operations."""

    def test_serialize_small_data(self):
        """Benchmark serialization of small data structures."""
        data = {"name": "Luz", "age": 16, "active": True}
        
        start = time.perf_counter()
        for _ in range(1000):
            to_toon(data, mode="auto")
        elapsed = time.perf_counter() - start
        
        avg_time_ms = (elapsed / 1000) * 1000
        print(f"\n[Benchmark] Small data serialization: {avg_time_ms:.3f} ms/op")
        assert avg_time_ms < 10.0, f"Serialization too slow: {avg_time_ms} ms"

    def test_parse_small_data(self):
        """Benchmark parsing of small TOON strings."""
        toon_text = """name: Luz
age: 16
active: true"""
        
        start = time.perf_counter()
        for _ in range(1000):
            from_toon(toon_text)
        elapsed = time.perf_counter() - start
        
        avg_time_ms = (elapsed / 1000) * 1000
        print(f"\n[Benchmark] Small data parsing: {avg_time_ms:.3f} ms/op")
        assert avg_time_ms < 5.0, f"Parsing too slow: {avg_time_ms} ms"

    def test_serialize_tabular_data(self):
        """Benchmark serialization of tabular arrays."""
        data = generate_large_data(100)
        
        start = time.perf_counter()
        toon = to_toon(data, mode="auto")
        elapsed = time.perf_counter() - start
        
        elapsed_ms = elapsed * 1000
        print(f"\n[Benchmark] Tabular data serialization (100 rows): {elapsed_ms:.3f} ms")
        assert elapsed_ms < 100.0, f"Tabular serialization too slow: {elapsed_ms} ms"
        
        # Verify it uses tabular format
        assert "users[100]" in toon

    def test_parse_tabular_data(self):
        """Benchmark parsing of tabular TOON format."""
        data = generate_large_data(100)
        toon = to_toon(data, mode="auto")
        
        start = time.perf_counter()
        parsed = from_toon(toon)
        elapsed = time.perf_counter() - start
        
        elapsed_ms = elapsed * 1000
        print(f"\n[Benchmark] Tabular data parsing (100 rows): {elapsed_ms:.3f} ms")
        assert elapsed_ms < 50.0, f"Tabular parsing too slow: {elapsed_ms} ms"
        assert parsed == data

    def test_round_trip_performance(self):
        """Benchmark complete round-trip conversion."""
        data = generate_large_data(500)
        
        start = time.perf_counter()
        toon = to_toon(data, mode="auto")
        parsed = from_toon(toon)
        elapsed = time.perf_counter() - start
        
        elapsed_ms = elapsed * 1000
        print(f"\n[Benchmark] Round-trip (500 rows): {elapsed_ms:.3f} ms")
        assert elapsed_ms < 200.0, f"Round-trip too slow: {elapsed_ms} ms"
        assert parsed == data

    def test_nested_structure_performance(self):
        """Benchmark deeply nested structures."""
        data = generate_nested_data(depth=10, width=5)
        
        start = time.perf_counter()
        toon = to_toon(data, mode="auto")
        parsed = from_toon(toon)
        elapsed = time.perf_counter() - start
        
        elapsed_ms = elapsed * 1000
        print(f"\n[Benchmark] Nested structure (depth 10): {elapsed_ms:.3f} ms")
        assert elapsed_ms < 50.0, f"Nested structure too slow: {elapsed_ms} ms"
        assert parsed == data

    def test_large_file_serialization(self):
        """Benchmark serialization of large datasets."""
        data = generate_large_data(1000)
        
        start = time.perf_counter()
        toon = to_toon(data, mode="compact")
        elapsed = time.perf_counter() - start
        
        elapsed_ms = elapsed * 1000
        size_kb = len(toon) / 1024
        throughput_mb_s = (len(toon) / 1024 / 1024) / elapsed if elapsed > 0 else 0
        
        print(f"\n[Benchmark] Large file serialization (1000 rows):")
        print(f"  Time: {elapsed_ms:.3f} ms")
        print(f"  Size: {size_kb:.2f} KB")
        print(f"  Throughput: {throughput_mb_s:.2f} MB/s")
        
        assert elapsed_ms < 500.0, f"Large file serialization too slow: {elapsed_ms} ms"

    def test_comparison_with_json(self):
        """Compare TOON performance with standard JSON."""
        data = generate_large_data(100)
        
        # JSON serialization
        start = time.perf_counter()
        json_str = json.dumps(data, separators=(",", ":"))
        json_parsed = json.loads(json_str)
        json_time = time.perf_counter() - start
        
        # TOON serialization
        start = time.perf_counter()
        toon_str = to_toon(data, mode="compact")
        toon_parsed = from_toon(toon_str)
        toon_time = time.perf_counter() - start
        
        json_ms = json_time * 1000
        toon_ms = toon_time * 1000
        
        print(f"\n[Benchmark] Performance comparison (100 rows):")
        print(f"  JSON:  {json_ms:.3f} ms")
        print(f"  TOON:  {toon_ms:.3f} ms")
        print(f"  Ratio: {toon_ms/json_ms:.2f}x")
        
        # TOON may be slower than JSON due to additional features (comments, tabular format, etc.)
        # But should still be reasonable (within 20x for this dataset size)
        # For larger datasets, TOON's tabular format becomes more efficient
        assert toon_ms < json_ms * 20, f"TOON too slow compared to JSON: {toon_ms} vs {json_ms} ms"
        assert toon_parsed == json_parsed == data

    def test_multiline_string_performance(self):
        """Benchmark multiline string handling."""
        multiline_text = "Line 1\n" * 100 + "Line 101"
        data = {"description": multiline_text}
        
        start = time.perf_counter()
        toon = to_toon(data, mode="auto")
        parsed = from_toon(toon)
        elapsed = time.perf_counter() - start
        
        elapsed_ms = elapsed * 1000
        print(f"\n[Benchmark] Multiline string (100 lines): {elapsed_ms:.3f} ms")
        assert elapsed_ms < 20.0, f"Multiline string too slow: {elapsed_ms} ms"
        assert parsed == data

    def test_validation_performance(self):
        """Benchmark validation speed."""
        from toonpy import validate_toon
        
        data = generate_large_data(200)
        toon = to_toon(data, mode="auto")
        
        start = time.perf_counter()
        for _ in range(100):
            is_valid, _ = validate_toon(toon)
        elapsed = time.perf_counter() - start
        
        avg_time_ms = (elapsed / 100) * 1000
        print(f"\n[Benchmark] Validation: {avg_time_ms:.3f} ms/op")
        # Adjusted threshold to account for system variability
        assert avg_time_ms < 15.0, f"Validation too slow: {avg_time_ms} ms"
        assert is_valid

