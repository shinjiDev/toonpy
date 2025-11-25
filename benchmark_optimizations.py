"""
Benchmark detallado de optimizaciones aplicadas a toonpy/parser.py
Compara versiones ANTES y DESPUÉS de cada optimización.
"""

import time
import json
import re
from typing import List
from io import StringIO

# ============================================================================
# BENCHMARKING UTILITIES
# ============================================================================

def benchmark(func, *args, iterations=100000, **kwargs):
    """Ejecuta una función múltiples veces y retorna el tiempo promedio."""
    start = time.perf_counter()
    for _ in range(iterations):
        func(*args, **kwargs)
    end = time.perf_counter()
    return (end - start) / iterations * 1_000_000  # microsegundos


def compare(name, before_func, after_func, test_cases, iterations=100000):
    """Compara dos implementaciones y muestra las mejoras."""
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
        
        print(f"\n  📊 Caso: {case_name}")
        print(f"     Antes:      {before_time:.3f} μs")
        print(f"     Después:    {after_time:.3f} μs")
        print(f"     Mejora:     {improvement:+.1f}%")
        print(f"     Speedup:    {speedup:.2f}x")
    
    # Promedio
    avg_improvement = sum(r['improvement'] for r in results) / len(results)
    avg_speedup = sum(r['speedup'] for r in results) / len(results)
    print(f"\n  ⭐ PROMEDIO:")
    print(f"     Mejora:     {avg_improvement:+.1f}%")
    print(f"     Speedup:    {avg_speedup:.2f}x")
    
    return results


# ============================================================================
# 1. OPTIMIZACIÓN: CACHÉ DE LITERALES EN _parse_token()
# ============================================================================

# ANTES: Sin caché, usando .lower()
def parse_token_OLD(token: str) -> object:
    token = token.strip()
    if token == "":
        return None
    if token == "[]":
        return []
    if token == "{}":
        return {}
    if token.startswith("\""):
        return json.loads(token)
    
    # ❌ PROBLEMA: Siempre llama .lower() aunque no sea booleano/null
    lowered = token.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    
    # Intentar parsear como número
    try:
        if '.' in token or 'e' in token or 'E' in token:
            return float(token)
        return int(token)
    except ValueError:
        return token

# DESPUÉS: Con caché de literales
_LITERAL_CACHE = {
    "true": True, "True": True, "TRUE": True,
    "false": False, "False": False, "FALSE": False,
    "null": None, "None": None, "NULL": None,
}

def parse_token_NEW(token: str) -> object:
    token = token.strip()
    if not token:
        return None
    
    # ✅ OPTIMIZACIÓN: Caché O(1) sin .lower()
    if token in _LITERAL_CACHE:
        return _LITERAL_CACHE[token]
    
    if token == "[]":
        return []
    if token == "{}":
        return {}
    
    first_char = token[0]
    if first_char == "\"":
        return json.loads(token)
    
    # ✅ OPTIMIZACIÓN: Early rejection por primer carácter
    if first_char.isdigit() or (first_char == '-' and len(token) > 1):
        try:
            if '.' in token or 'e' in token or 'E' in token:
                return float(token)
            return int(token)
        except ValueError:
            pass
    
    return token


def benchmark_parse_token():
    test_cases = [
        ("Boolean true", ("true",), {}),
        ("Boolean True", ("True",), {}),
        ("Boolean false", ("false",), {}),
        ("Null value", ("null",), {}),
        ("Integer", ("42",), {}),
        ("Float", ("3.14",), {}),
        ("String identifier", ("my_key",), {}),
        ("Quoted string", ('"hello"',), {}),
        ("Empty array", ("[]",), {}),
        ("Empty object", ("{}",), {}),
    ]
    
    return compare(
        "1. Caché de Literales en _parse_token()",
        parse_token_OLD,
        parse_token_NEW,
        test_cases,
        iterations=50000
    )


# ============================================================================
# 2. OPTIMIZACIÓN: guess_number() SIN REGEX
# ============================================================================

NUMBER_RE = re.compile(r"""
    ^
    -?
    (?:
        0
        |
        [1-9][0-9]*
    )
    (?:
        \.[0-9]+
    )?
    (?:
        [eE][+-]?[0-9]+
    )?
    $
""", re.VERBOSE)

# ANTES: Con regex siempre
def guess_number_OLD(token: str):
    if not NUMBER_RE.match(token):
        return None
    if "." in token or "e" in token.lower():
        return float(token)
    return int(token)

# DESPUÉS: Try/except con early rejection
def guess_number_NEW(token: str):
    if not token:
        return None
    
    first = token[0]
    if not (first.isdigit() or first == '-'):
        return None
    
    try:
        if '.' in token or 'e' in token or 'E' in token:
            val = float(token)
            if not NUMBER_RE.match(token):
                return None
            return val
        return int(token)
    except ValueError:
        return None


def benchmark_guess_number():
    test_cases = [
        ("Integer pequeño", ("42",), {}),
        ("Integer grande", ("123456789",), {}),
        ("Float simple", ("3.14",), {}),
        ("Float científico", ("1e5",), {}),
        ("Número negativo", ("-42",), {}),
        ("No es número", ("abc",), {}),
        ("String con números", ("abc123",), {}),
    ]
    
    return compare(
        "2. guess_number() - Try/Except vs Regex",
        guess_number_OLD,
        guess_number_NEW,
        test_cases,
        iterations=50000
    )


# ============================================================================
# 3. OPTIMIZACIÓN: split_escaped_row() CON SLICING
# ============================================================================

# ANTES: Construcción carácter por carácter con listas
def split_escaped_row_OLD(line: str, separator: str = "|") -> List[str]:
    parts: List[str] = []
    buf: List[str] = []
    in_string = False
    escape = False
    
    for ch in line:
        if escape:
            buf.append(ch)
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == "\"":
            in_string = not in_string
            buf.append(ch)
            continue
        if ch == separator and not in_string:
            part = "".join(buf).strip()
            if part.startswith(separator):
                part = part[1:].strip()
            parts.append(part)
            buf = []
            continue
        buf.append(ch)
    
    if buf:
        parts.append("".join(buf).strip())
    
    cleaned = [p for p in (part.strip(separator).strip() for part in parts) if p != ""]
    return cleaned or parts

# DESPUÉS: String slicing
def split_escaped_row_NEW(line: str, separator: str = "|") -> List[str]:
    if not line:
        return []
    
    if separator not in line:
        stripped = line.strip()
        return [stripped] if stripped else []
    
    parts: List[str] = []
    start = 0
    in_string = False
    i = 0
    line_len = len(line)
    
    while i < line_len:
        ch = line[i]
        
        if ch == "\\" and i + 1 < line_len:
            i += 2
            continue
        
        if ch == "\"":
            in_string = not in_string
            i += 1
            continue
        
        if ch == separator and not in_string:
            part = line[start:i].strip().strip(separator).strip()
            if part:
                parts.append(part)
            start = i + 1
        
        i += 1
    
    if start < line_len:
        part = line[start:].strip().strip(separator).strip()
        if part:
            parts.append(part)
    
    return parts if parts else [line.strip()]


def benchmark_split_escaped_row():
    test_cases = [
        ("Tabla simple", ("| 1 | Luz |",), {"separator": "|"}),
        ("Tabla con espacios", ("| 42 | The Owl House | 2020 |",), {"separator": "|"}),
        ("Tabla con strings", ('| 1 | "Light glyph" | "Magic" |',), {"separator": "|"}),
        ("Pipe dentro de string", ('| name | "value with | pipe" |',), {"separator": "|"}),
        ("CSV simple", ("1,Luz,14",), {"separator": ","}),
        ("CSV con comillas", ('1,"Eda Clawthorne","Witch"',), {"separator": ","}),
    ]
    
    return compare(
        "3. split_escaped_row() - Lista vs Slicing",
        split_escaped_row_OLD,
        split_escaped_row_NEW,
        test_cases,
        iterations=30000
    )


# ============================================================================
# 4. OPTIMIZACIÓN: _remove_block_comments() CON StringIO
# ============================================================================

# ANTES: Lista de strings
def remove_block_comments_OLD(text: str) -> str:
    result: List[str] = []
    i = 0
    depth = 0
    while i < len(text):
        if text.startswith("/*", i):
            depth += 1
            i += 2
            continue
        if depth > 0:
            if text.startswith("*/", i):
                depth -= 1
                i += 2
                continue
            result.append("\n" if text[i] == "\n" else " ")
            i += 1
            continue
        result.append(text[i])
        i += 1
    return "".join(result)

# DESPUÉS: StringIO con early return
def remove_block_comments_NEW(text: str) -> str:
    if "/*" not in text:
        return text
    
    result = StringIO()
    i = 0
    depth = 0
    text_len = len(text)
    
    while i < text_len:
        if i + 1 < text_len:
            two_char = text[i:i+2]
            if two_char == "/*":
                depth += 1
                i += 2
                continue
            if depth > 0 and two_char == "*/":
                depth -= 1
                i += 2
                continue
        
        if depth > 0:
            result.write('\n' if text[i] == '\n' else ' ')
        else:
            result.write(text[i])
        
        i += 1
    
    return result.getvalue()


def benchmark_remove_block_comments():
    test_cases = [
        ("Sin comentarios", ("key: value\nname: test",), {}),
        ("Un comentario simple", ("key: /* comment */ value",), {}),
        ("Comentario multilínea", ("key: value\n/* This is\na comment */\nname: test",), {}),
        ("Múltiples comentarios", ("/* c1 */ key: value /* c2 */\nname: test /* c3 */",), {}),
        ("Comentario anidado", ("/* outer /* inner */ still commented */ key: value",), {}),
        ("Documento largo sin comentarios", ("key: value\n" * 50,), {}),
    ]
    
    return compare(
        "4. _remove_block_comments() - Lista vs StringIO",
        remove_block_comments_OLD,
        remove_block_comments_NEW,
        test_cases,
        iterations=10000
    )


# ============================================================================
# 5. BENCHMARK INTEGRADO: PARSING COMPLETO
# ============================================================================

def benchmark_integrated():
    """Benchmark de documentos TOON completos."""
    from toonpy import from_toon
    
    print(f"\n{'='*70}")
    print(f"🔬 BENCHMARK INTEGRADO: Documentos Completos")
    print(f"{'='*70}")
    
    test_docs = {
        "Objeto simple": """
name: Luz
age: 14
active: true
mentor: null
""",
        "Array con valores": """
- true
- false
- null
- 42
- 3.14
- "text"
""",
        "Tabla simple": """
crew[3]{id,name,role}:
    1,Luz,Student
    2,Eda,Mentor
    3,King,Demon
""",
        "Documento mixto": """
show: "The Owl House"
season: 1
active: true
episodes: 19
rating: null
characters:
    - name: Luz
      age: 14
    - name: Eda
      age: null
""",
        "Con comentarios": """
/* Metadata */
name: Test // inline comment
# Another comment
value: 42
/* Multi
   line
   comment */
active: true
""",
    }
    
    for name, doc in test_docs.items():
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            from_toon(doc)
        elapsed = (time.perf_counter() - start) / iterations * 1000  # ms
        
        print(f"\n  📄 {name}")
        print(f"     Tiempo: {elapsed:.3f} ms")
        print(f"     Tamaño: {len(doc)} caracteres")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "="*70)
    print("🚀 BENCHMARKS DE OPTIMIZACIONES - toonpy/parser.py")
    print("="*70)
    print("\nMidiendo el impacto de cada optimización aplicada...")
    print("(Valores en microsegundos μs, 1μs = 0.001ms)")
    
    all_results = {}
    
    # Ejecutar todos los benchmarks
    all_results['parse_token'] = benchmark_parse_token()
    all_results['guess_number'] = benchmark_guess_number()
    all_results['split_escaped_row'] = benchmark_split_escaped_row()
    all_results['remove_block_comments'] = benchmark_remove_block_comments()
    
    # Benchmark integrado
    benchmark_integrated()
    
    # Resumen final
    print(f"\n\n{'='*70}")
    print("📊 RESUMEN GENERAL DE OPTIMIZACIONES")
    print(f"{'='*70}\n")
    
    summary = [
        ("Caché de literales (_parse_token)", all_results['parse_token']),
        ("Try/except en guess_number()", all_results['guess_number']),
        ("String slicing en split_escaped_row()", all_results['split_escaped_row']),
        ("StringIO en _remove_block_comments()", all_results['remove_block_comments']),
    ]
    
    for i, (name, results) in enumerate(summary, 1):
        avg_improvement = sum(r['improvement'] for r in results) / len(results)
        avg_speedup = sum(r['speedup'] for r in results) / len(results)
        
        print(f"{i}. {name}")
        print(f"   ✨ Mejora promedio: {avg_improvement:+.1f}%")
        print(f"   🚀 Speedup: {avg_speedup:.2f}x\n")
    
    # Impacto global estimado
    total_avg_improvement = sum(
        sum(r['improvement'] for r in results) / len(results)
        for _, results in summary
    ) / len(summary)
    
    print(f"{'='*70}")
    print(f"⭐ IMPACTO GLOBAL ESTIMADO: {total_avg_improvement:+.1f}%")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()

