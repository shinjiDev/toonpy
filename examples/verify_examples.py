#!/usr/bin/env python3
"""Verify that all examples round-trip correctly."""

import sys
from pathlib import Path

# Add parent directory to path to import toontools
sys.path.insert(0, str(Path(__file__).parent.parent))

from toontools import to_toon, from_toon
import json
import os

examples = [
    "example1",
    "example2", 
    "example3",
    "example4",
    "example5",
    "example6",
    "example7",
    "example8",
]

print("Verifying examples...")
print("-" * 50)

all_ok = True
for ex in examples:
    json_path = f"{ex}.json"
    toon_path = f"{ex}.toon"
    
    # Test JSON -> TOON -> JSON round-trip
    try:
        with open(json_path, encoding="utf-8") as f:
            original = json.load(f)
        toon = to_toon(original, mode="auto")
        parsed = from_toon(toon)
        
        if parsed == original:
            print(f"✓ {ex}: Round-trip OK")
        else:
            print(f"✗ {ex}: Round-trip FAILED")
            all_ok = False
    except Exception as e:
        print(f"✗ {ex}: Error - {e}")
        all_ok = False
    
    # Test TOON -> JSON parsing
    try:
        with open(toon_path, encoding="utf-8") as f:
            toon_text = f.read()
        parsed = from_toon(toon_text)
        print(f"  {ex}.toon: Parse OK")
    except Exception as e:
        print(f"  {ex}.toon: Parse FAILED - {e}")
        all_ok = False

print("-" * 50)
if all_ok:
    print("All examples verified successfully!")
else:
    print("Some examples failed verification.")
    exit(1)

