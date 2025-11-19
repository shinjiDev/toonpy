"""
Script para comparar performance antes y después de optimizaciones.
Ejecuta los benchmarks múltiples veces y muestra estadísticas.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import statistics
import time
from toonpy import to_toon, from_toon
from toonpy.serializer import ToonSerializer
import json


def generate_large_data(size: int = 1000):
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


def generate_nested_data(depth: int = 5, width: int = 10):
    """Generate deeply nested data for benchmarking."""
    result = {}
    current = result
    for i in range(depth):
        current[f"level{i}"] = {}
        current = current[f"level{i}"]
        for j in range(width):
            current[f"item{j}"] = f"value{i}_{j}"
    return result


def benchmark_serialize_small(runs: int = 100):
    """Benchmark small data serialization."""
    data = {"name": "Luz", "age": 16, "active": True}
    times = []
    
    for _ in range(runs):
        start = time.perf_counter()
        to_toon(data)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "min": min(times),
        "max": max(times),
    }


def benchmark_parse_small(runs: int = 100):
    """Benchmark small data parsing."""
    toon_text = """name: "Luz"
age: 16
active: true
"""
    times = []
    
    for _ in range(runs):
        start = time.perf_counter()
        from_toon(toon_text)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "min": min(times),
        "max": max(times),
    }


def benchmark_serialize_tabular(runs: int = 50):
    """Benchmark tabular data serialization."""
    data = generate_large_data(100)
    times = []
    
    serializer = ToonSerializer(mode="auto")
    for _ in range(runs):
        start = time.perf_counter()
        serializer.dumps(data)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "min": min(times),
        "max": max(times),
    }


def benchmark_parse_tabular(runs: int = 50):
    """Benchmark tabular data parsing."""
    data = generate_large_data(100)
    toon_text = to_toon(data, mode="auto")
    times = []
    
    for _ in range(runs):
        start = time.perf_counter()
        from_toon(toon_text)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "min": min(times),
        "max": max(times),
    }


def benchmark_nested_structure(runs: int = 50):
    """Benchmark nested structure serialization."""
    data = generate_nested_data(depth=10, width=10)
    times = []
    
    serializer = ToonSerializer()
    for _ in range(runs):
        start = time.perf_counter()
        serializer.dumps(data)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "min": min(times),
        "max": max(times),
    }


def benchmark_round_trip(runs: int = 20):
    """Benchmark round-trip performance."""
    data = generate_large_data(500)
    times = []
    
    for _ in range(runs):
        start = time.perf_counter()
        toon = to_toon(data, mode="auto")
        parsed = from_toon(toon)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        assert parsed == data  # Verify correctness
    
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "min": min(times),
        "max": max(times),
    }


def print_results(name: str, results: dict):
    """Print benchmark results in a formatted way."""
    print(f"\n{'='*60}")
    print(f"[BENCHMARK] {name}")
    print(f"{'='*60}")
    print(f"  Mean:   {results['mean']:.3f} ms")
    print(f"  Median: {results['median']:.3f} ms")
    print(f"  Min:    {results['min']:.3f} ms")
    print(f"  Max:    {results['max']:.3f} ms")
    if results['stdev'] > 0:
        print(f"  StdDev: {results['stdev']:.3f} ms")


def main():
    import sys
    import io
    # Fix encoding for Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("Ejecutando benchmarks de performance (version optimizada)")
    print("=" * 60)
    
    print("\nEjecutando benchmarks... Esto puede tomar unos momentos...")
    
    # Small data
    print("\n1. Serializacion de datos pequenos...")
    small_serialize = benchmark_serialize_small(runs=200)
    print_results("Serialización Pequeña (200 runs)", small_serialize)
    
    print("\n2. Parsing de datos pequenos...")
    small_parse = benchmark_parse_small(runs=200)
    print_results("Parsing Pequeno (200 runs)", small_parse)
    
    # Tabular data
    print("\n3. Serializacion de datos tabulares (100 rows)...")
    tabular_serialize = benchmark_serialize_tabular(runs=100)
    print_results("Serializacion Tabular (100 runs)", tabular_serialize)
    
    print("\n4. Parsing de datos tabulares (100 rows)...")
    tabular_parse = benchmark_parse_tabular(runs=100)
    print_results("Parsing Tabular (100 runs)", tabular_parse)
    
    # Nested structure
    print("\n5. Serializacion de estructuras anidadas (depth 10)...")
    nested = benchmark_nested_structure(runs=100)
    print_results("Estructuras Anidadas (100 runs)", nested)
    
    # Round trip
    print("\n6. Round-trip completo (500 rows)...")
    round_trip = benchmark_round_trip(runs=50)
    print_results("Round-Trip (50 runs)", round_trip)
    
    # Comparison with JSON
    print("\n7. Comparacion con JSON (100 rows)...")
    data = generate_large_data(100)
    
    json_times = []
    for _ in range(100):
        start = time.perf_counter()
        json.dumps(data, separators=(",", ":"))
        elapsed = (time.perf_counter() - start) * 1000
        json_times.append(elapsed)
    
    toon_times = []
    for _ in range(100):
        start = time.perf_counter()
        to_toon(data, mode="auto")
        elapsed = (time.perf_counter() - start) * 1000
        toon_times.append(elapsed)
    
    json_mean = statistics.mean(json_times)
    toon_mean = statistics.mean(toon_times)
    ratio = toon_mean / json_mean if json_mean > 0 else 0
    
    print(f"\n{'='*60}")
    print("[BENCHMARK] Comparacion JSON vs TOON")
    print(f"{'='*60}")
    print(f"  JSON:  {json_mean:.3f} ms (mean)")
    print(f"  TOON:  {toon_mean:.3f} ms (mean)")
    print(f"  Ratio: {ratio:.2f}x")
    
    print("\n" + "="*60)
    print("[OK] Benchmarks completados!")
    print("="*60)


if __name__ == "__main__":
    main()

