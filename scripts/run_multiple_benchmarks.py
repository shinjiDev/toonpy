"""
Script para ejecutar benchmarks múltiples veces y obtener estadísticas.
"""

import subprocess
import sys
import statistics

def run_benchmark():
    """Ejecuta un benchmark y extrae los valores Mean."""
    result = subprocess.run(
        [sys.executable, "scripts/benchmark_comparison.py"],
        capture_output=True,
        text=True,
        cwd="."
    )
    
    means = []
    for line in result.stdout.split('\n'):
        if 'Mean:' in line:
            # Extraer el valor numérico
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
    print("Ejecutando benchmarks múltiples veces para validar resultados...")
    print("=" * 70)
    
    all_results = {
        "Serialización pequeña": [],
        "Parsing pequeño": [],
        "Serialización tabular": [],
        "Parsing tabular": [],
        "Estructuras anidadas": [],
        "Round-trip": []
    }
    
    num_runs = 5
    for i in range(num_runs):
        print(f"\n[{i+1}/{num_runs}] Ejecutando benchmark...")
        means = run_benchmark()
        
        if len(means) >= 6:
            all_results["Serialización pequeña"].append(means[0])
            all_results["Parsing pequeño"].append(means[1])
            all_results["Serialización tabular"].append(means[2])
            all_results["Parsing tabular"].append(means[3])
            all_results["Estructuras anidadas"].append(means[4])
            all_results["Round-trip"].append(means[5])
    
    print("\n" + "=" * 70)
    print("RESUMEN DE RESULTADOS (5 ejecuciones)")
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
            print(f"  Range:  {max_val - min_val:.3f} ms ({((max_val - min_val) / mean * 100):.1f}% variabilidad)")
    
    print("\n" + "=" * 70)
    print("Comparación con números originales (después de primeras optimizaciones):")
    print("=" * 70)
    
    original = {
        "Serialización pequeña": 0.015,
        "Parsing pequeño": 0.028,
        "Serialización tabular": 0.620,
        "Parsing tabular": 1.826,
        "Estructuras anidadas": 0.477,
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

