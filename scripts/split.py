#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Split Espresso PLA output by output bit index.

Reads lines in the form "input output", keeps only lines where the output bit
at the given index is '1', and prints "input output_bit" (one char per line).
Optionally replaces '-' with 'x' in the output (default: on).

As a module:
  from split import split_espresso_by_bit
  lines = split_espresso_by_bit(lines, var_index=0, replace_dash_to_x=True)

CLI usage:
  python split.py <index>              # read from STDIN
  python split.py <file> <index>       # read from file
  python split.py --no-dash-to-x <file> <index>
"""

import argparse
import sys


def split_espresso_by_bit(lines, var_index, replace_dash_to_x=True):
    """
    Filter Espresso PLA lines by output bit index.

    Keeps only lines where the output bit at var_index is '1', and returns
    lines in the form "input output_bit". Optionally replaces '-' with 'x'.

    Args:
        lines: Iterable of strings (e.g. file lines), each "input output".
        var_index: Index of the output bit to filter on (0-based).
        replace_dash_to_x: If True, replace '-' with 'x' in output lines.

    Returns:
        List of strings, one per kept minterm: "input output_bit".
    """
    result_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("."):
            continue
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        input_part, output_part = parts
        if var_index < 0 or var_index >= len(output_part):
            continue
        output_bit = output_part[var_index]
        if output_bit != "1":
            continue
        out_line = f"{input_part} {output_bit}"
        if replace_dash_to_x:
            out_line = out_line.replace("-", "x")
        result_lines.append(out_line)
    return result_lines


def main():
    parser = argparse.ArgumentParser(
        description="Split Espresso PLA output by output bit index."
    )
    parser.add_argument(
        "args",
        nargs="+",
        metavar="file_or_index",
        help="Either <index> (read STDIN) or <file> <index>",
    )
    parser.add_argument(
        "--no-dash-to-x",
        action="store_true",
        help="Do not replace '-' with 'x' in output lines",
    )
    parsed = parser.parse_args()
    replace_dash_to_x = not parsed.no_dash_to_x
    args = parsed.args

    file_path = None
    try:
        if len(args) == 1:
            var_index = int(args[0])
        elif len(args) == 2:
            file_path = args[0]
            var_index = int(args[1])
        else:
            parser.error("Expected 1 or 2 arguments: [file] <index>")
    except ValueError:
        parser.error("Index must be an integer")

    if file_path is not None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except FileNotFoundError:
            print("File not found", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        lines = sys.stdin.read().splitlines()

    result_lines = split_espresso_by_bit(lines, var_index, replace_dash_to_x)
    print("\n".join(result_lines))


if __name__ == "__main__":
    main()
