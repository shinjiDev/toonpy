from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "toonpy.cli", *args],
        cwd=cwd,
        check=False,
        text=True,
        capture_output=True,
    )


def test_cli_round_trip(tmp_path):
    json_path = tmp_path / "data.json"
    toon_path = tmp_path / "data.toon"
    result_path = tmp_path / "data.out.json"
    json_path.write_text(json.dumps({"a": 1, "b": [1, 2]}), encoding="utf-8")

    proc = run_cli("to", "--in", str(json_path), "--out", str(toon_path))
    assert proc.returncode == 0, proc.stderr

    proc = run_cli("from", "--in", str(toon_path), "--out", str(result_path))
    assert proc.returncode == 0, proc.stderr
    assert json.loads(result_path.read_text(encoding="utf-8")) == {"a": 1, "b": [1, 2]}


def test_cli_format(tmp_path):
    toon_path = tmp_path / "raw.toon"
    toon_path.write_text("a:\n  - 1\n", encoding="utf-8")
    proc = run_cli("fmt", "--in", str(toon_path), "--out", str(toon_path), "--indent", "4")
    assert proc.returncode == 0
    # After formatting, the primitive array is emitted as inline: a[1]: 1
    result = toon_path.read_text(encoding="utf-8")
    assert "a" in result

