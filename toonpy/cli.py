"""
Command line interface for toonpy.

Provides the `toonpy` command-line tool with subcommands for converting
between JSON and TOON formats, and for formatting TOON files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .api import from_toon, to_toon, HAS_YAML, HAS_TOML
from .errors import ToonError, ToonSyntaxError

# Optional YAML imports
if HAS_YAML:
    from .api import to_yaml_from_toon, to_toon_from_yaml

# Optional TOML imports
if HAS_TOML:
    from .api import to_toml_from_toon, to_toon_from_toml

MODES = ("auto", "compact", "readable")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser.
    
    Creates an ArgumentParser with subcommands for:
    - "to": Convert JSON to TOON
    - "from": Convert TOON to JSON
    - "fmt": Format/reformat a TOON file
    
    Returns:
        Configured ArgumentParser instance
    """
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

    # YAML commands (only if PyYAML is installed)
    if HAS_YAML:
        yaml_to_toon_cmd = sub.add_parser("yaml-to-toon", help="Convert YAML to TOON")
        yaml_to_toon_cmd.add_argument("--in", dest="input_path", required=True, help="Input YAML file")
        yaml_to_toon_cmd.add_argument("--out", dest="output_path", required=True, help="Output TOON file")
        yaml_to_toon_cmd.add_argument("--mode", choices=MODES, default="auto", help="Serialization mode")
        yaml_to_toon_cmd.add_argument("--indent", type=int, default=2, help="Indentation size")

        toon_to_yaml_cmd = sub.add_parser("toon-to-yaml", help="Convert TOON to YAML")
        toon_to_yaml_cmd.add_argument("--in", dest="input_path", required=True, help="Input TOON file")
        toon_to_yaml_cmd.add_argument("--out", dest="output_path", required=True, help="Output YAML file")
        toon_to_yaml_cmd.add_argument("--permissive", action="store_true", help="Enable permissive parse mode")

    # TOML commands (only if tomli/tomli_w are installed)
    if HAS_TOML:
        toml_to_toon_cmd = sub.add_parser("toml-to-toon", help="Convert TOML to TOON")
        toml_to_toon_cmd.add_argument("--in", dest="input_path", required=True, help="Input TOML file")
        toml_to_toon_cmd.add_argument("--out", dest="output_path", required=True, help="Output TOON file")
        toml_to_toon_cmd.add_argument("--mode", choices=MODES, default="auto", help="Serialization mode")
        toml_to_toon_cmd.add_argument("--indent", type=int, default=2, help="Indentation size")

        toon_to_toml_cmd = sub.add_parser("toon-to-toml", help="Convert TOON to TOML")
        toon_to_toml_cmd.add_argument("--in", dest="input_path", required=True, help="Input TOON file")
        toon_to_toml_cmd.add_argument("--out", dest="output_path", required=True, help="Output TOML file")
        toon_to_toml_cmd.add_argument("--permissive", action="store_true", help="Enable permissive parse mode")

    return parser


def cmd_to(args: argparse.Namespace) -> int:
    """Execute the 'to' subcommand: Convert JSON to TOON.
    
    Reads a JSON file, converts it to TOON format, and writes the result
    to the output file.
    
    Args:
        args: Parsed command-line arguments with input_path, output_path,
              indent, and mode attributes
        
    Returns:
        Exit code (0 for success)
        
    Raises:
        json.JSONDecodeError: If input file is not valid JSON
        OSError: If file I/O fails
    """
    data = _read_json(args.input_path)
    toon_text = to_toon(data, indent=args.indent, mode=args.mode)
    Path(args.output_path).write_text(toon_text, encoding="utf-8")
    return 0


def cmd_from(args: argparse.Namespace) -> int:
    """Execute the 'from' subcommand: Convert TOON to JSON.
    
    Reads a TOON file, parses it, and writes the result as JSON to the
    output file.
    
    Args:
        args: Parsed command-line arguments with input_path, output_path,
              and permissive attributes
        
    Returns:
        Exit code (0 for success)
        
    Raises:
        ToonSyntaxError: If TOON file is malformed
        OSError: If file I/O fails
    """
    text = Path(args.input_path).read_text(encoding="utf-8")
    data = from_toon(text, mode="permissive" if args.permissive else "strict")
    Path(args.output_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return 0


def cmd_fmt(args: argparse.Namespace) -> int:
    """Execute the 'fmt' subcommand: Format a TOON file.
    
    Reads a TOON file, parses it, and reformats it according to the
    specified indentation and mode settings. Useful for normalizing
    TOON file formatting.
    
    Args:
        args: Parsed command-line arguments with input_path, output_path,
              indent, and mode attributes
        
    Returns:
        Exit code (0 for success)
        
    Raises:
        ToonSyntaxError: If TOON file is malformed
        OSError: If file I/O fails
    """
    text = Path(args.input_path).read_text(encoding="utf-8")
    data = from_toon(text)
    toon_text = to_toon(data, indent=args.indent, mode=args.mode)
    Path(args.output_path).write_text(toon_text, encoding="utf-8")
    return 0


def _read_json(path: str) -> object:
    """Read and parse a JSON file.
    
    Args:
        path: Path to JSON file
        
    Returns:
        Parsed Python object (dict, list, or scalar)
        
    Raises:
        json.JSONDecodeError: If file is not valid JSON
        OSError: If file cannot be read
    """
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def cmd_yaml_to_toon(args: argparse.Namespace) -> int:
    """Execute the 'yaml-to-toon' subcommand: Convert YAML to TOON.
    
    Reads a YAML file, converts it to TOON format, and writes the result
    to the output file.
    
    Args:
        args: Parsed command-line arguments with input_path, output_path,
              indent, and mode attributes
        
    Returns:
        Exit code (0 for success)
        
    Raises:
        yaml.YAMLError: If input file is not valid YAML
        OSError: If file I/O fails
    """
    if not HAS_YAML:
        print("Error: PyYAML is not installed. Install with: pip install toontools[yaml]", file=sys.stderr)
        return 3
    
    text = Path(args.input_path).read_text(encoding="utf-8")
    toon_text = to_toon_from_yaml(text, indent=args.indent, mode=args.mode)
    Path(args.output_path).write_text(toon_text, encoding="utf-8")
    return 0


def cmd_toon_to_yaml(args: argparse.Namespace) -> int:
    """Execute the 'toon-to-yaml' subcommand: Convert TOON to YAML.
    
    Reads a TOON file, parses it, and writes the result as YAML to the
    output file.
    
    Args:
        args: Parsed command-line arguments with input_path, output_path,
              and permissive attributes
        
    Returns:
        Exit code (0 for success)
        
    Raises:
        ToonSyntaxError: If TOON file is malformed
        OSError: If file I/O fails
    """
    if not HAS_YAML:
        print("Error: PyYAML is not installed. Install with: pip install toontools[yaml]", file=sys.stderr)
        return 3
    
    text = Path(args.input_path).read_text(encoding="utf-8")
    yaml_text = to_yaml_from_toon(text, mode="permissive" if args.permissive else "strict")
    Path(args.output_path).write_text(yaml_text, encoding="utf-8")
    return 0


def cmd_toml_to_toon(args: argparse.Namespace) -> int:
    """Execute the 'toml-to-toon' subcommand: Convert TOML to TOON.
    
    Reads a TOML file, converts it to TOON format, and writes the result
    to the output file.
    
    Args:
        args: Parsed command-line arguments with input_path, output_path,
              indent, and mode attributes
        
    Returns:
        Exit code (0 for success)
        
    Raises:
        tomli.TOMLDecodeError: If input file is not valid TOML
        OSError: If file I/O fails
    """
    if not HAS_TOML:
        print("Error: tomli is not installed. Install with: pip install toontools[toml]", file=sys.stderr)
        return 3
    
    text = Path(args.input_path).read_text(encoding="utf-8")
    toon_text = to_toon_from_toml(text, indent=args.indent, mode=args.mode)
    Path(args.output_path).write_text(toon_text, encoding="utf-8")
    return 0


def cmd_toon_to_toml(args: argparse.Namespace) -> int:
    """Execute the 'toon-to-toml' subcommand: Convert TOON to TOML.
    
    Reads a TOON file, parses it, and writes the result as TOML to the
    output file.
    
    Args:
        args: Parsed command-line arguments with input_path, output_path,
              and permissive attributes
        
    Returns:
        Exit code (0 for success)
        
    Raises:
        ToonSyntaxError: If TOON file is malformed
        OSError: If file I/O fails
    """
    if not HAS_TOML:
        print("Error: tomli_w is not installed. Install with: pip install toontools[toml]", file=sys.stderr)
        return 3
    
    text = Path(args.input_path).read_text(encoding="utf-8")
    toml_text = to_toml_from_toon(text)
    Path(args.output_path).write_text(toml_text, encoding="utf-8")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the toonpy CLI.
    
    Parses command-line arguments, dispatches to appropriate subcommand,
    and handles errors with appropriate exit codes.
    
    Args:
        argv: Command-line arguments (defaults to sys.argv if None)
        
    Returns:
        Exit code:
        - 0: Success
        - 2: TOON syntax error
        - 3: General toonpy error
        - 4: I/O error
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "to":
            return cmd_to(args)
        if args.command == "from":
            return cmd_from(args)
        if args.command == "fmt":
            return cmd_fmt(args)
        if args.command == "yaml-to-toon":
            return cmd_yaml_to_toon(args)
        if args.command == "toon-to-yaml":
            return cmd_toon_to_yaml(args)
        if args.command == "toml-to-toon":
            return cmd_toml_to_toon(args)
        if args.command == "toon-to-toml":
            return cmd_toon_to_toml(args)
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

