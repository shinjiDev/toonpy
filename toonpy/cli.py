"""
Command line interface for toonpy.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .api import from_toon, to_toon
from .errors import ToonError, ToonSyntaxError

MODES = ("auto", "compact", "readable")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="toonpy", description="TOON ⇄ JSON conversion toolkit.")
    sub = parser.add_subparsers(dest="command", required=True)

    to_cmd = sub.add_parser("to", help="Convert JSON to TOON")
    to_cmd.add_argument("--in", dest="input_path", required=True, help="Input JSON file")
    to_cmd.add_argument("--out", dest="output_path", required=True, help="Output TOON file")
    to_cmd.add_argument("--mode", choices=MODES, default="auto", help="Serialization mode")
    to_cmd.add_argument("--indent", type=int, default=2, help="Indentation size")

    from_cmd = sub.add_parser("from", help="Convert TOON to JSON")
    from_cmd.add_argument("--in", dest="input_path", required=True, help="Input TOON file")
    from_cmd.add_argument("--out", dest="output_path", required=True, help="Output JSON file")
    from_cmd.add_argument("--permissive", action="store_true", help="Enable permissive parse mode")

    fmt_cmd = sub.add_parser("fmt", help="Format a TOON file")
    fmt_cmd.add_argument("--in", dest="input_path", required=True, help="Input TOON file")
    fmt_cmd.add_argument("--out", dest="output_path", required=True, help="Output TOON file")
    fmt_cmd.add_argument("--indent", type=int, default=2, help="Indentation size")
    fmt_cmd.add_argument("--mode", choices=MODES, default="readable", help="Serialization mode")

    return parser


def cmd_to(args: argparse.Namespace) -> int:
    data = _read_json(args.input_path)
    toon_text = to_toon(data, indent=args.indent, mode=args.mode)
    Path(args.output_path).write_text(toon_text, encoding="utf-8")
    return 0


def cmd_from(args: argparse.Namespace) -> int:
    text = Path(args.input_path).read_text(encoding="utf-8")
    data = from_toon(text, mode="permissive" if args.permissive else "strict")
    Path(args.output_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return 0


def cmd_fmt(args: argparse.Namespace) -> int:
    text = Path(args.input_path).read_text(encoding="utf-8")
    data = from_toon(text)
    toon_text = to_toon(data, indent=args.indent, mode=args.mode)
    Path(args.output_path).write_text(toon_text, encoding="utf-8")
    return 0


def _read_json(path: str) -> object:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "to":
            return cmd_to(args)
        if args.command == "from":
            return cmd_from(args)
        if args.command == "fmt":
            return cmd_fmt(args)
        parser.error("Unknown command")
    except ToonSyntaxError as exc:
        print(f"TOON syntax error: {exc}", file=sys.stderr)
        return 2
    except ToonError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3
    except OSError as exc:
        print(f"I/O error: {exc}", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

