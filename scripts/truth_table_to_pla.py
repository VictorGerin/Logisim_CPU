#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert Logisim truth table to a single PLA file (all input and output bits per term).

Reads a truth table in InstructionDecoder/Logisim format, minimizes it with Espresso
by default, and writes one PLA file with no header (only data lines), interpretable
by a PLA component (e.g. like PLA_bit3.txt).

Usage:
  python scripts/truth_table_to_pla.py Circuits/Docs/InstructionDecoder.txt
  python scripts/truth_table_to_pla.py INPUT.txt --out-pla Circuits/Docs/InstructionDecoder.pla
  python scripts/truth_table_to_pla.py INPUT.txt --no-minimize --out-pla output.pla
  python scripts/truth_table_to_pla.py INPUT.txt --use-x
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _pla_data_lines_only(pla_text: str) -> str:
    """Return only data lines (no .i, .o, .ilb, .ob, .p, .e header).
    Don't-cares in the output column (- or x) are replaced with 0."""
    lines = []
    for line in pla_text.splitlines():
        s = line.strip()
        if s and not s.startswith("."):
            parts = s.split()
            if len(parts) >= 2:
                output = parts[-1].replace("-", "0").replace("x", "0")
                line = " ".join(parts[:-1] + [output])
            lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Logisim truth table to a single PLA file (all output bits per line)."
    )
    parser.add_argument(
        "truth_table",
        type=Path,
        metavar="FILE",
        help="Path to Logisim truth table .txt file",
    )
    parser.add_argument(
        "--out-pla",
        type=Path,
        default=None,
        metavar="FILE",
        help="Output PLA file (default: write to stdout)",
    )
    parser.add_argument(
        "--no-minimize",
        action="store_true",
        help="Do not run Espresso (minimization is the default); write raw PLA (more lines)",
    )
    parser.add_argument(
        "--espresso",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to Espresso executable (default: auto-detect from repo or PATH)",
    )
    parser.add_argument(
        "--use-x",
        action="store_true",
        help="Write 'x' instead of '-' for don't-care in output file",
    )
    args = parser.parse_args()

    input_path = args.truth_table.resolve()
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        return 1

    # Parse truth table
    try:
        lines = input_path.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        print(f"Error reading {input_path}: {e}", file=sys.stderr)
        return 1

    import logisim_to_pla  # type: ignore

    try:
        input_labels, output_labels, rows = logisim_to_pla.read_logisim(lines)
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error parsing truth table: {e}", file=sys.stderr)
        return 1

    # Build raw PLA
    pla_buf = io.StringIO()
    logisim_to_pla.write_pla(pla_buf, input_labels, output_labels, rows)
    pla_text = pla_buf.getvalue()

    # Optionally minimize with Espresso
    if not args.no_minimize:
        repo_root = _repo_root()
        if args.espresso is not None:
            espresso_cmd = [str(args.espresso.resolve())]
        else:
            try:
                from run_pipeline import _default_espresso_cmd  # type: ignore
                espresso_cmd = _default_espresso_cmd(repo_root)
            except Exception:
                espresso_cmd = None
        if espresso_cmd:
            try:
                from run_pipeline import _run_espresso  # type: ignore
                pla_text = _run_espresso(espresso_cmd, pla_text, cwd=repo_root)
            except SystemExit:
                print("Warning: Espresso failed; writing raw PLA.", file=sys.stderr)
                # keep pla_text as raw
        # else: no espresso found, keep raw

    if args.use_x:
        pla_text = pla_text.replace("-", "x")

    # Output without header (like PLA_bit3.txt: only data lines)
    out_content = _pla_data_lines_only(pla_text)
    num_terms = len([l for l in out_content.splitlines() if l.strip()])

    if args.out_pla is not None:
        out_path = args.out_pla.resolve()
        try:
            out_path.write_text(out_content, encoding="utf-8")
        except OSError as e:
            print(f"Error writing {out_path}: {e}", file=sys.stderr)
            return 1
        print(f"Wrote {num_terms} terms to {out_path}", file=sys.stderr)
    else:
        print(out_content, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
