from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from toontools import from_toon, to_toon


def main() -> None:
    json_path = Path(__file__).resolve().parents[1] / "examples" / "example1.json"
    toon_path = Path(__file__).resolve().parents[1] / "examples" / "example1.demo.toon"
    roundtrip_path = Path(__file__).resolve().parents[1] / "examples" / "example1.demo.json"

    data = json.loads(json_path.read_text(encoding="utf-8"))
    toon_text = to_toon(data, mode="auto")
    toon_path.write_text(toon_text, encoding="utf-8")

    parsed = from_toon(toon_text)
    roundtrip_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")

    try:
        import tiktoken  # type: ignore[import-not-found]

        enc = tiktoken.get_encoding("cl100k_base")
        json_tokens = len(enc.encode(json.dumps(data)))
        toon_tokens = len(enc.encode(toon_text))
        print(f"JSON tokens: {json_tokens}")
        print(f"TOON tokens: {toon_tokens}")
        print(f"Savings: {json_tokens - toon_tokens}")
    except Exception:
        print("tiktoken not installed; skipping token counts.")


if __name__ == "__main__":
    main()

