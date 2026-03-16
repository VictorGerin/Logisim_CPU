#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert minterm lines (split output format) to a sum-of-products boolean equation.

Reads lines in the form "input output", uses only the input part (string of 0, 1, x, -),
and produces one product term per line, joined by "+\n". Each bit is mapped to a
variable name; 0/1 become literals (negated or asserted depending on --negate).

As a module:
  from gen_eq import gen_eq
  result = gen_eq(lines, map_names=["A2", "A1", "A0"], negate=False)

CLI usage:
  python gen_eq.py --stdin -m A2 -m A1 -m A0
  python gen_eq.py -i file.txt -m A2 -m A1 -m A0
  python gen_eq.py --stdin -n -m A -m B -m C
"""

import argparse
import sys


def gen_eq(lines, map_names, negate=False):
    """
    Build a sum-of-products equation string from minterm lines.

    Args:
        lines: Iterable of strings in "input [output]" format (only first token used).
        map_names: List of variable names, one per input bit position.
        negate: If True, swap literals (1 -> negated, 0 -> asserted).

    Returns:
        String of product terms separated by "+\n".
    """
    if not map_names:
        return ""

    map_names = [name.replace('[', '').replace(']', '') for name in map_names]
    # Replicate JS: each map entry has a trailing space for alignment
    map_with_space = [f"{name} " for name in map_names]
    n = len(map_with_space)
    terms = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        input_part = line.split(None, 1)[0]
        chars = list(input_part)
        # Iterate only over positions that have a map name
        limit = min(len(chars), n)
        first_has_printed = False
        parts = []

        for i in range(limit):
            c = chars[i]
            has_value = False
            if c == "1":
                has_value = True
                prefix = "/" if negate else " "
                parts.append(f"{prefix}{map_with_space[i]}")
            elif c == "0":
                has_value = True
                prefix = " " if negate else "/"
                parts.append(f"{prefix}{map_with_space[i]}")
            else:
                # don't-care (x or -)
                parts.append(" " * (len(map_with_space[i]) + 2))

            if has_value and first_has_printed:
                parts[-1] = "*" + parts[-1]
            if has_value:
                first_has_printed = True

        # Filter empty (JS: filter(obj => obj)); in our case we don't add empty strings
        term_str = "".join(p for p in parts if p)
        terms.append(term_str)

    return "+\n".join(terms)


def main():
    parser = argparse.ArgumentParser(
        description="Convert minterm lines to sum-of-products boolean equation."
    )
    parser.add_argument(
        "-m",
        "--map",
        action="append",
        default=[],
        metavar="NAME",
        help="Variable name per input bit (repeat for each bit, e.g. -m A2 -m A1 -m A0)",
    )
    parser.add_argument(
        "-n",
        "--negate",
        action="store_true",
        help="Swap literals: 1 -> negated, 0 -> asserted",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read from STDIN (default if -i not given)",
    )
    parser.add_argument(
        "-i",
        "--input",
        metavar="FILE",
        help="Input file (ignored if --stdin is set)",
    )
    args = parser.parse_args()

    if not args.map:
        parser.error("At least one --map / -m is required")

    if args.stdin or args.input is None:
        lines = sys.stdin.read().splitlines()
    else:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except FileNotFoundError:
            print("File not found", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)

    result = gen_eq(lines, args.map, negate=args.negate)
    print(result)


if __name__ == "__main__":
    main()
