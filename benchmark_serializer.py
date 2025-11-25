"""
Detailed benchmark for serializer optimizations in toonpy/serializer.py
Compares BEFORE and AFTER implementations of each optimization.
"""

import time
import json
from typing import Any, Mapping, Sequence


# ============================================================================
# BENCHMARKING UTILITIES
# ============================================================================

def benchmark(func, *args, iterations=50000, **kwargs):
    """Execute a function multiple times and return average time."""
    start = time.perf_counter()
    for _ in range(iterations):
        func(*args, **kwargs)
    end = time.perf_counter()
    return (end - start) / iterations * 1_000_000  # microseconds


def compare(name, before_func, after_func, test_cases, iterations=50000):
    """Compare two implementations and show improvements."""
    print(f"\n{'='*70}")
    print(f"🔬 BENCHMARK: {name}")
    print(f"{'='*70}")
    
    results = []
    for case_name, args, kwargs in test_cases:
        before_time = benchmark(before_func, *args, iterations=iterations, **kwargs)
        after_time = benchmark(after_func, *args, iterations=iterations, **kwargs)
        improvement = ((before_time - after_time) / before_time) * 100
        speedup = before_time / after_time
        
        results.append({
            'case': case_name,
            'before': before_time,
            'after': after_time,
            'improvement': improvement,
            'speedup': speedup
        })
        
        print(f"\n  📊 Case: {case_name}")
        print(f"     Before:     {before_time:.3f} μs")
        print(f"     After:      {after_time:.3f} μs")
        print(f"     Improvement: {improvement:+.1f}%")
        print(f"     Speedup:    {speedup:.2f}x")
    
    # Average
    avg_improvement = sum(r['improvement'] for r in results) / len(results)
    avg_speedup = sum(r['speedup'] for r in results) / len(results)
    print(f"\n  ⭐ AVERAGE:")
    print(f"     Improvement: {avg_improvement:+.1f}%")
    print(f"     Speedup:    {avg_speedup:.2f}x")
    
    return results


# ============================================================================
# 1. OPTIMIZATION: SCALAR CACHE IN _format_scalar()
# ============================================================================

def string_needs_quotes(value: str) -> bool:
    """Check if string needs quotes (simplified version)."""
    if not value or value in ("true", "false", "null"):
        return True
    return not value[0].isalpha() and value[0] != "_"

# BEFORE: No cache
def format_scalar_OLD(value: Any, *, force_string: bool = False) -> str:
    if value is None and not force_string:
        return "null"
    if value is True and not force_string:
        return "true"
    if value is False and not force_string:
        return "false"
    if isinstance(value, (int, float)) and not force_string:
        return repr(value)
    if isinstance(value, str):
        if not force_string and not string_needs_quotes(value):
            return value
        return json.dumps(value)
    if force_string:
        return json.dumps(str(value))
    return format_scalar_OLD(str(value), force_string=True)

# AFTER: With cache
_SCALAR_CACHE = {
    None: "null",
    True: "true",
    False: "false",
}

def format_scalar_NEW(value: Any, *, force_string: bool = False) -> str:
    # Optimization: Cache lookup for common values (O(1))
    if not force_string and value in _SCALAR_CACHE:
        return _SCALAR_CACHE[value]
    
    # Numbers: fast path with isinstance check
    if not force_string and isinstance(value, (int, float)):
        return repr(value)
    
    # Strings: check if quotes needed
    if isinstance(value, str):
        if not force_string and not string_needs_quotes(value):
            return value
        return json.dumps(value)
    
    # Force string mode
    if force_string:
        return json.dumps(str(value))
    
    # Fallback: convert to string and quote
    return format_scalar_NEW(str(value), force_string=True)


def benchmark_format_scalar():
    test_cases = [
        ("None value", (None,), {}),
        ("Boolean true", (True,), {}),
        ("Boolean false", (False,), {}),
        ("Integer", (42,), {}),
        ("Float", (3.14,), {}),
        ("String identifier", ("my_key",), {}),
        ("Quoted string", ("hello world",), {}),
        ("Number repr", (123456,), {}),
    ]
    
    return compare(
        "1. Scalar Cache in _format_scalar()",
        format_scalar_OLD,
        format_scalar_NEW,
        test_cases,
        iterations=30000
    )


# ============================================================================
# 2. OPTIMIZATION: _inline_container_repr()
# ============================================================================

# BEFORE: Check emptiness after isinstance
def inline_container_repr_OLD(value: Any) -> str | None:
    if isinstance(value, Mapping) and not value:
        return "{}"
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) and not value:
        return "[]"
    return None

# AFTER: Check emptiness first
def inline_container_repr_NEW(value: Any) -> str | None:
    # Optimization: Check emptiness first (cheaper than isinstance for non-empty)
    if not value:
        if isinstance(value, Mapping):
            return "{}"
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return "[]"
    return None


def benchmark_inline_container():
    test_cases = [
        ("Empty dict", ({},), {}),
        ("Empty list", ([],), {}),
        ("Non-empty dict", ({"key": "value"},), {}),
        ("Non-empty list", ([1, 2, 3],), {}),
        ("String (not container)", ("hello",), {}),
        ("Integer", (42,), {}),
    ]
    
    return compare(
        "2. Optimized _inline_container_repr()",
        inline_container_repr_OLD,
        inline_container_repr_NEW,
        test_cases,
        iterations=50000
    )


# ============================================================================
# 3. INTEGRATED BENCHMARK: COMPLETE SERIALIZATION
# ============================================================================

def benchmark_integrated():
    """Benchmark complete document serialization."""
    from toonpy import to_toon
    
    print(f"\n{'='*70}")
    print(f"🔬 INTEGRATED BENCHMARK: Complete Documents")
    print(f"{'='*70}")
    
    test_docs = {
        "Simple object": {
            "name": "Luz",
            "age": 14,
            "active": True,
            "mentor": None
        },
        "With array": {
            "show": "The Owl House",
            "characters": ["Luz", "Eda", "King"]
        },
        "With table": {
            "crew": [
                {"id": 1, "name": "Luz", "age": 14},
                {"id": 2, "name": "Eda", "age": None},
                {"id": 3, "name": "King", "age": 8},
            ]
        },
        "Complex nested": {
            "show": "The Owl House",
            "season": 1,
            "active": True,
            "episodes": 19,
            "rating": None,
            "characters": [
                {"name": "Luz", "age": 14, "magic": True},
                {"name": "Eda", "age": None, "magic": True},
            ]
        },
        "Many booleans": {
            "flag1": True,
            "flag2": False,
            "flag3": True,
            "flag4": False,
            "flag5": None,
            "flag6": True,
        },
    }
    
    for name, doc in test_docs.items():
        iterations = 10000
        start = time.perf_counter()
        for _ in range(iterations):
            to_toon(doc)
        elapsed = (time.perf_counter() - start) / iterations * 1000  # ms
        
        # Estimate document complexity
        json_size = len(json.dumps(doc, separators=(",", ":")))
        
        print(f"\n  📄 {name}")
        print(f"     Time:       {elapsed:.3f} ms")
        print(f"     JSON size:  {json_size} bytes")
        print(f"     Throughput: {1/elapsed*1000:.0f} docs/sec")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "="*70)
    print("🚀 SERIALIZER OPTIMIZATION BENCHMARKS - toonpy/serializer.py")
    print("="*70)
    print("\nMeasuring impact of each optimization...")
    print("(Values in microseconds μs, 1μs = 0.001ms)")
    
    all_results = {}
    
    # Run all benchmarks
    all_results['format_scalar'] = benchmark_format_scalar()
    all_results['inline_container'] = benchmark_inline_container()
    
    # Integrated benchmark
    benchmark_integrated()
    
    # Final summary
    print(f"\n\n{'='*70}")
    print("📊 GENERAL SUMMARY OF OPTIMIZATIONS")
    print(f"{'='*70}\n")
    
    summary = [
        ("Scalar cache (_format_scalar)", all_results['format_scalar']),
        ("Optimized _inline_container_repr()", all_results['inline_container']),
    ]
    
    for i, (name, results) in enumerate(summary, 1):
        avg_improvement = sum(r['improvement'] for r in results) / len(results)
        avg_speedup = sum(r['speedup'] for r in results) / len(results)
        
        print(f"{i}. {name}")
        print(f"   ✨ Average improvement: {avg_improvement:+.1f}%")
        print(f"   🚀 Speedup: {avg_speedup:.2f}x\n")
    
    # Global estimated impact
    total_avg_improvement = sum(
        sum(r['improvement'] for r in results) / len(results)
        for _, results in summary
    ) / len(summary)
    
    print(f"{'='*70}")
    print(f"⭐ ESTIMATED GLOBAL IMPACT: {total_avg_improvement:+.1f}%")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()

