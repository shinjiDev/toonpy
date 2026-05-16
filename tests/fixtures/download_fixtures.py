"""Download and cache TOON spec fixtures from the official repo."""
import json
import urllib.request
import urllib.error
from pathlib import Path

BASE = "https://raw.githubusercontent.com/toon-format/spec/main/tests/fixtures"
DECODE = [
    "primitives", "numbers", "objects", "arrays-primitive", "arrays-tabular",
    "arrays-nested", "delimiters", "whitespace", "root-form",
    "validation-errors", "indentation-errors", "blank-lines", "path-expansion",
]
ENCODE = [
    "primitives", "objects", "arrays-primitive", "arrays-tabular",
    "arrays-nested", "arrays-objects", "delimiters", "whitespace",
    "options", "key-folding",
]

def download_all():
    root = Path(__file__).parent
    for category, names in [("decode", DECODE), ("encode", ENCODE)]:
        out_dir = root / category
        out_dir.mkdir(exist_ok=True)
        for name in names:
            url = f"{BASE}/{category}/{name}.json"
            dest = out_dir / f"{name}.json"
            print(f"Downloading {url} ...")
            try:
                with urllib.request.urlopen(url) as resp:
                    data = json.loads(resp.read())
                dest.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
                print(f"  -> {dest} ({len(data['tests'])} tests)")
            except urllib.error.HTTPError as e:
                print(f"  ! Skipped (HTTP {e.code})")

if __name__ == "__main__":
    download_all()
