"""
Script to run benchmarks multiple times and gather statistics.
"""

import subprocess
import sys
import statistics

def run_benchmark():
    """Run one benchmark execution and extract mean values."""
    result = subprocess.run(
        [sys.executable, "scripts/benchmark_comparison.py"],
        capture_output=True,
        text=True,
        cwd="."
    )
    
    means = []
    for line in result.stdout.split('\n'):
        if 'Mean:' in line:
            # Extract numeric value
            parts = line.split()
            for i, part in enumerate(parts):
                if part == 'Mean:':
                    if i + 1 < len(parts):
                        try:
                            means.append(float(parts[i + 1]))
                        except ValueError:
                            pass
    return means

def main():
    print("Running benchmarks multiple times to validate results...")
    print("=" * 70)
    
    all_results = {
        "Small serialization": [],
        "Small parsing": [],
        "Tabular serialization": [],
        "Tabular parsing": [],
        "Nested structures": [],
        "Round-trip": []
    }
    
    num_runs = 5
    for i in range(num_runs):
        print(f"\n[{i+1}/{num_runs}] Running benchmark...")
        means = run_benchmark()
        
        if len(means) >= 6:
            all_results["Small serialization"].append(means[0])
            all_results["Small parsing"].append(means[1])
            all_results["Tabular serialization"].append(means[2])
            all_results["Tabular parsing"].append(means[3])
            all_results["Nested structures"].append(means[4])
            all_results["Round-trip"].append(means[5])
    
    print("\n" + "=" * 70)
    print("RESULT SUMMARY (5 runs)")
    print("=" * 70)
    
    for name, values in all_results.items():
        if values:
            mean = statistics.mean(values)
            median = statistics.median(values)
            stdev = statistics.stdev(values) if len(values) > 1 else 0
            min_val = min(values)
            max_val = max(values)
            
            print(f"\n{name}:")
            print(f"  Mean:   {mean:.3f} ms")
            print(f"  Median: {median:.3f} ms")
            print(f"  Min:    {min_val:.3f} ms")
            print(f"  Max:    {max_val:.3f} ms")
            print(f"  StdDev: {stdev:.3f} ms")
            variability = ((max_val - min_val) / mean * 100) if mean else 0
            print(f"  Range:  {max_val - min_val:.3f} ms ({variability:.1f}% variability)")
    
    print("\n" + "=" * 70)
    print("Comparison with original numbers (after initial optimizations):")
    print("=" * 70)
    
    original = {
        "Small serialization": 0.015,
        "Small parsing": 0.028,
        "Tabular serialization": 0.620,
        "Tabular parsing": 1.826,
        "Nested structures": 0.477,
        "Round-trip": 12.505
    }
    
    for name, values in all_results.items():
        if values and name in original:
            current_mean = statistics.mean(values)
            original_val = original[name]
            diff = current_mean - original_val
            diff_pct = (diff / original_val) * 100
            
            status = "✅" if abs(diff_pct) < 10 else "⚠️" if diff_pct < 0 else "❌"
            print(f"{status} {name}:")
            print(f"   Original: {original_val:.3f} ms")
            print(f"   Actual:   {current_mean:.3f} ms")
            print(f"   Diferencia: {diff:+.3f} ms ({diff_pct:+.1f}%)")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()

