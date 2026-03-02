#!/usr/bin/env python3
"""
Convert Logisim truth table export to Espresso PLA format.

Usage:
  python logisim_to_pla.py                    # read from STDIN, write to STDOUT
  python logisim_to_pla.py -i INPUT.txt       # read from file, write to STDOUT
  python logisim_to_pla.py -o OUTPUT.pla      # read from STDIN, write to file
  python logisim_to_pla.py -i INPUT.txt -o OUTPUT.pla

Input: STDIN by default; use -i to read from a file.
Output: STDOUT by default; use -o to write to a file.
"""

import argparse
import re
import sys


def parse_spec(spec):
    """
    Parse a column spec like 'A[2..0]' or 'Nome' (single bit).
    Returns list of (bit_count, labels) e.g. (3, ['A2','A1','A0']) or (1, ['Nome']).
    """
    spec = spec.strip()
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\[(\d+)\.\.(\d+)\]$", spec)
    if m:
        name, high, low = m.group(1), int(m.group(2)), int(m.group(3))
        if high < low:
            high, low = low, high
        n = high - low + 1
        labels = [f"{name}{i}" for i in range(high, low - 1, -1)]
        return n, labels
    # single bit
    if spec:
        return 1, [spec]
    return 0, []


def parse_header(line):
    """
    Parse header line 'A[2..0] B[1..0] | S[2..0]'.
    Returns (input_labels, output_labels) or (None, None) if not a valid header.
    """
    if "|" not in line or line.strip().startswith("#"):
        return None, None
    left, _, right = line.partition("|")
    input_tokens = left.split()
    output_tokens = right.split()
    if not input_tokens or not output_tokens:
        return None, None
    input_labels = []
    output_labels = []
    for t in input_tokens:
        n, labels = parse_spec(t)
        input_labels.extend(labels)
    for t in output_tokens:
        n, labels = parse_spec(t)
        output_labels.extend(labels)
    return input_labels, output_labels


def normalize_bits(s):
    """Map '0'/'1' as-is; 'x'/'X'/'-' -> '-' for don't-care."""
    out = []
    for c in s:
        if c in "01":
            out.append(c)
        elif c in "xX-":
            out.append("-")
        else:
            raise ValueError(f"invalid character in bit string: {c!r}")
    return "".join(out)


def parse_data_line(line, num_inputs, num_outputs):
    """
    Parse a data line like '  000     00    |   000  '.
    Returns (input_bits, output_bits) or None if line should be skipped.
    """
    line = line.strip()
    if not line or line.startswith("#") or set(line.strip()) <= {"~", " "}:
        return None
    if "|" not in line:
        return None
    left, _, right = line.partition("|")
    # Concatenate all input tokens (digits/x/-) in order
    input_str = "".join(left.split())
    output_str = "".join(right.split())
    if len(input_str) != num_inputs or len(output_str) != num_outputs:
        return None
    try:
        inp = normalize_bits(input_str)
        out = normalize_bits(output_str)
        return inp, out
    except ValueError:
        return None


def read_logisim(lines):
    """
    Read Logisim data from an iterable of lines; return (input_labels, output_labels, rows).
    rows is list of (input_bits, output_bits).
    """
    input_labels = None
    output_labels = None

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("#"):
            continue
        if set(line_stripped.replace(" ", "")) <= {"~"}:
            continue
        if "|" in line and input_labels is None:
            il, ol = parse_header(line)
            if il is not None:
                input_labels, output_labels = il, ol
                break

    if input_labels is None or output_labels is None:
        raise SystemExit("Error: no valid header line (expected '... | ...' with column names)")

    num_inputs = len(input_labels)
    num_outputs = len(output_labels)
    rows = []

    for line in lines:
        row = parse_data_line(line, num_inputs, num_outputs)
        if row is not None:
            rows.append(row)

    return input_labels, output_labels, rows


def write_pla(f, input_labels, output_labels, rows):
    """Write Espresso PLA to file-like f (e.g. sys.stdout or open file)."""
    f.write(f".i {len(input_labels)}\n")
    f.write(f".o {len(output_labels)}\n")
    f.write(".ilb " + " ".join(input_labels) + "\n")
    f.write(".ob " + " ".join(output_labels) + "\n")
    f.write(f".p {len(rows)}\n")
    for inp, out in rows:
        f.write(f"{inp} {out}\n")
    f.write(".e\n")


def main():
    parser = argparse.ArgumentParser(
        description="Convert Logisim truth table to Espresso PLA format."
    )
    parser.add_argument(
        "-i", "--input",
        metavar="FILE",
        help="Logisim truth table file (default: read from STDIN)",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Output PLA file (default: write to STDOUT)",
    )
    args = parser.parse_args()

    if args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            sys.exit(f"Error: file not found: {args.input}")
        except OSError as e:
            sys.exit(f"Error reading {args.input}: {e}")
    else:
        lines = sys.stdin.readlines()

    try:
        input_labels, output_labels, rows = read_logisim(lines)
    except SystemExit:
        raise
    except Exception as e:
        sys.exit(f"Error parsing input: {e}")

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                write_pla(f, input_labels, output_labels, rows)
            print(f"Wrote {len(rows)} terms to {args.output}", file=sys.stderr)
        except OSError as e:
            sys.exit(f"Error writing {args.output}: {e}")
    else:
        write_pla(sys.stdout, input_labels, output_labels, rows)



if __name__ == "__main__":
    main()
